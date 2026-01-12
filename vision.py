from fastapi import FastAPI, UploadFile, File, Form
from openai import OpenAI
from PIL import Image
import io, base64, os, logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ДЗ Модуль 4 - Мультимодалка")

client = OpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai"
)

@app.get("/")
async def root():
    return {"msg": "Vision API готов на /analyze_image/"}

@app.post("/analyze_image/")
async def analyze_image(file: UploadFile = File(...), prompt: str = Form("Опиши подробно")):
    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_b64 = base64.b64encode(buffered.getvalue()).decode()
        
        response = client.chat.completions.create(
            model="sonar-pro",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                ]
            }],
            max_tokens=1000
        )
        
        logger.info(f"✅ Анализ: {file.filename}")
        return {"analysis": response.choices[0].message.content}
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
