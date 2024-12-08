import g4f
import graphviz
import json

def generate_flowchart_json(task_description):
    prompt = f"""
    Преобразуй следующее описание задачи в JSON для блок-схемы. Не пиши никакое описание и текст, только JSON пожалуйста. Нужно чтобы в блоках не было текста кроме начало и конец. Нужно генерировать так чтобы потом просто можно было это перевести в код. Используй вместо текста например: "Добавить 1" используй "переменная = переменная + 1(вместо слов используй переменные названные латинскими буквами)". После выполнения программа должна заканчиваться. Программа должна идти дальне, а не создавать новые отвлетления(типо без начала). Не создавай лишние ноды пожалуйста.

    Формат JSON:
    {{
        "blocks": [
            {{"id": "1", "type": "start", "text": "Начало"}},
            {{"id": "2", "type": "process", "text": "Шаг 1"}},
            {{"id": "3", "type": "decision", "text": "Условие?", "yes": "4", "no": "5"}},
            {{"id": "4", "type": "end", "text": "Конец"}}
        ],
        "connections": [
            {{"from": "1", "to": "2"}},
            {{"from": "2", "to": "3"}},
            {{"from": "3", "to": "4", "condition": "yes"}},
            {{"from": "3", "to": "5", "condition": "no"}}
        ]
    }}

    Описание задачи:
    {task_description}

    Ответ:
    """

    response = g4f.ChatCompletion.create(
        model=g4f.models.gpt_4,
        messages=[{"role": "user", "content": prompt}]
    )
    
    if isinstance(response, str):
        response_cleaned = response.strip("```").strip() #там в ответе есть '''. эта штука их убирает
        if response_cleaned.startswith("json"):
            response_cleaned = response_cleaned[4:].strip()
        try:
            return json.loads(response_cleaned)
        except json.JSONDecodeError as e:
            print("ошибка декодирования JSON:", e)
            print("ответ от модели (после очистки):", response_cleaned)
            return None
    else:
        print("неизвестный формат ответа:", response)
        return None


# из json в картинку
def generate_flowchart_png(json_data, output_filename="flowchart"):
    if json_data is None:
        print("ошибка: JSON данных нет, пропуск создания PNG.")
        return

    dot = graphviz.Digraph(format='png')
    dot.attr(splines="ortho", size="0", rankdir="TB")

    # добавляем блоки
    for block in json_data["blocks"]:
        if block["type"] == "start":
            dot.node(block["id"], block["text"], shape="ellipse", style="filled", color="lightgreen")
        elif block["type"] == "process":
            dot.node(block["id"], block["text"], shape="box")
        elif block["type"] == "decision":
            dot.node(block["id"], block["text"], shape="diamond", style="filled", color="lightblue")
        elif block["type"] == "end":
            dot.node(block["id"], block["text"], shape="ellipse", style="filled", color="lightcoral", rank="sink")

    # добавляем соединения
    for connection in json_data["connections"]:
        label = connection.get("condition", "")
        dot.edge(connection["from"], connection["to"], xlabel=label)

    # сохраняем
    dot.render(output_filename, cleanup=True)

def genflow(task, png_name): # ввод: задача, название пнг
    json_task_gen = generate_flowchart_json(task)
    if json_task_gen:
        print("JSON сгенерирован")
        print("создание png")
        return generate_flowchart_png(json_task_gen, png_name)
    else:
        print('не удалось сгенерировать JSON')
        return 'не удалось сгенерировать JSON'
    
# эта часть кода для работы api. для запуска использовать команду fastapi run text2flow.py (вместо run использовать dev если файл будет переделываться)
from typing import Union
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
import random
from fastapi import Response
import io
from PIL import Image

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

@app.get('/genflow/{arguments}', responses={200: {"content": {"image/png": {}}}}, response_class=StreamingResponse)
def genflow_api(arguments: str, name: Union[str, None] = random.randint(1, 9999)):
    json_data = generate_flowchart_json(arguments)
    if json_data is None:
        return Response(content="Не удалось сгенерировать JSON", media_type="text/plain", status_code=500)
    
    generate_flowchart_png(json_data, name)

    try:
        file_stream = open(f'{name}.png', "rb")
        return StreamingResponse(
            file_stream,
            media_type="image/png",
            headers={"Content-Disposition": f"inline; filename={name}.png"}
        )
    except Exception as e:
        return Response(content=f"Ошибка при создании PNG: {str(e)}", media_type="text/plain", status_code=500)
