import os
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form
from openai import OpenAI
from PIL import Image
import io
import base64
import logging
from typing import Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="Мультимодальный Анализатор ДЗ Модуль 4")

# ===== МУЛЬТИМОДАЛКА ДЗ НАЙДЕН app =====
from fastapi import UploadFile, File, Form
from openai import OpenAI
from PIL import Image
import io, base64, os
from dotenv import load_dotenv

load

# OpenAI Proxy клиент
client = OpenAI(
    api_key=os.getenv("OPENAI_PROXY_API_KEY"),
    base_url=os.getenv("OPENAI_PROXY_BASE_URL", "https://api.openai-proxy.ru/v1")
)

@app.get("/")
async def root():
    return {"message": "Мультимодальный API для ДЗ готов! POST /analyze_image/"}

@app.post("/analyze_image/")
async def analyze_image(
    file: UploadFile = File(..., description="Загрузи изображение"),
    prompt: str = Form("Опиши изображение подробно на русском", description="Твой промпт")
):
    try:
        # 1. Читаем файл
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # 2. Base64 для OpenAI Vision
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode()
        
        # 3. Запрос к GPT-4o-mini (мультимодалка)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Промпт: {prompt}"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        result = {
            "status": "success",
            "filename": file.filename,
            "analysis": response.choices[0].message.content,
            "model": "gpt-4o-mini-vision"
        }
        
        logger.info(f"✅ Анализ успешен: {file.filename}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка анализа: {str(e)}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

