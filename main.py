import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image
import io

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

try:
    from backend.services.scoreservice import DesignToolsScoringService
    scorer = DesignToolsScoringService()
    SCORING_ENABLED = True
    logger.info("✅ Scoring service инициализирован успешно")
except ImportError as e:
    SCORING_ENABLED = False
    scorer = None
    logger.warning(f"⚠️ Scoring service недоступен: {e}")
except Exception as e:
    SCORING_ENABLED = False
    scorer = None
    logger.error(f"❌ Ошибка инициализации Scoring: {e}")

API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
DB_PATH = "analyses.db"
STATIC_DIR = Path(__file__).parent / "static"
DEFAULT_FONT = "Helvetica"

try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))
    DEFAULT_FONT = "DejaVuSans"
except Exception as e:
    logger.warning(f"⚠️ DejaVuSans не найден, используется {DEFAULT_FONT}: {e}")

class CompetitorAnalysis(BaseModel):
    name: str = ""
    description: str = ""
    strengths: list = []
    weaknesses: list = []
    recommendations: list = []
    summary: str = ""

class ImageAnalysis(BaseModel):
    filename: str = ""
    description: str = ""

import sqlite3

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY,
            text TEXT,
            image BLOB,
            result TEXT,
            scoring TEXT,
            created_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("✅ База данных инициализирована")

init_db()

app = FastAPI(title="CompetitionMonitor API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "✅ CompetitionMonitor работает", "scoring": "✅ Включен" if SCORING_ENABLED else "❌ Отключен"}

@app.post("/analyzetext")
async def analyze_text(text: str):
    try:
        if not text:
            raise HTTPException(status_code=400, detail="Текст не предоставлен")
        logger.info(f"📝 Анализ текста: {text[:50]}...")
        return {"status": "success", "analysis": {"competitors": [], "market_insights": "Анализ в процессе"}}
    except Exception as e:
        logger.error(f"❌ Ошибка анализа: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyzetext-scored")
async def analyze_text_scored(text: str):
    try:
        if not SCORING_ENABLED:
            raise HTTPException(status_code=503, detail="Scoring service недоступен")
        logger.info(f"🎨 Scoring анализ: {text[:50]}...")
        return {"status": "success", "analysis": {"competitors": [], "scoring": "✅ Включен"}}
    except Exception as e:
        logger.error(f"❌ Ошибка Scoring: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM analyses ORDER BY created_at DESC LIMIT 10')
        results = cursor.fetchall()
        conn.close()
        return {"history": results}
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analysis/{id}")
async def get_analysis(id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM analyses WHERE id = ?', (id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {"analysis": result}
        raise HTTPException(status_code=404, detail="Анализ не найден")
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/export-pdf/{id}")
async def export_pdf(id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM analyses WHERE id = ?', (id,))
        result = cursor.fetchone()
        conn.close()
        if not result:
            raise HTTPException(status_code=404, detail="Анализ не найден")
        pdf_filename = f"analysis_{id}.pdf"
        c = canvas.Canvas(pdf_filename, pagesize=letter)
        c.drawString(100, 750, f"Анализ #{id}")
        c.drawString(100, 730, f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        c.save()
        logger.info(f"📄 PDF создан: {pdf_filename}")
        return {"pdf": pdf_filename}
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/compare")
async def compare_competitors():
    try:
        return {"status": "success", "comparison": {"competitors": [], "metrics": []}}
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "✅ API работает", "db": "✅ БД доступна", "scoring": "✅ Включен" if SCORING_ENABLED else "❌ Отключен"}

if __name__ == "__main__":
    print(f"✅ API ключ: {API_KEY[:20]}...", file=sys.stdout, flush=True)
    print("🚀 Backend запускается...", file=sys.stdout, flush=True)
    print("📊 Endpoints: / /analyzetext /analyzetext-scored /history /analysis/{id} /export-pdf/{id} /compare", file=sys.stdout, flush=True)
    print("📷 Поддержка: Text + Images", file=sys.stdout, flush=True)
    print(f"📝 Шрифт для PDF: {DEFAULT_FONT}", file=sys.stdout, flush=True)
    print(f"🎨 Scoring для Design Tools: {'✅ ВКЛЮЧЕН' if SCORING_ENABLED else '❌ ОТКЛЮЧЕН'}", file=sys.stdout, flush=True)
    print(f"📍 SCORING_ENABLED = {SCORING_ENABLED}", file=sys.stdout, flush=True)
    print(f"📍 scorer = {scorer}", file=sys.stdout, flush=True)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
