import os
import json
import sqlite3
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors
from dotenv import load_dotenv
import uvicorn

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
DB_PATH = "analyses.db"
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="CompetitionMonitor MVP", version="1.0")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competitor_name TEXT NOT NULL,
            analysis_text TEXT NOT NULL,
            image_base64 TEXT,
            analysis_result TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("✅ База данных инициализирована")

init_db()

class AnalysisRequest(BaseModel):
    text: str
    competitor_name: str = "Конкурент"
    image: Optional[str] = None

class CompareRequest(BaseModel):
    analysis_ids: list[int]

def analyze_with_perplexity(text: str, image_base64: Optional[str] = None) -> dict:
    logger.info("🔑 API ключ: " + API_KEY[:20] + "...")
    
    content = [
        {
            "type": "text",
            "text": f"""Проанализируй информацию о конкуренте. Дай SWOT анализ.

Информация:
{text}

Верни ТОЛЬКО валидный JSON без markdown:
{{
    "strengths": "Сильные стороны",
    "weaknesses": "Слабые стороны",
    "opportunities": "Возможности",
    "threats": "Угрозы",
    "recommendations": "Рекомендации",
    "image_insights": "Insights если есть фото"
}}"""
        }
    ]
    
    if image_base64:
        content.append({
            "type": "image",
            "image": image_base64
        })
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sonar",
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    logger.info("📤 Отправляю в Perplexity...")
    
    try:
        response = requests.post(PERPLEXITY_URL, headers=headers, json=payload)
        logger.info(f"📥 Status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"❌ Ошибка: {response.text}")
            return {"error": f"API error: {response.status_code}"}
        
        data = response.json()
        response_text = data["choices"][0]["message"]["content"]
        
        try:
            analysis = json.loads(response_text)
            logger.info("✨ JSON распарсен!")
            return analysis
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                logger.info("✨ JSON извлечен!")
                return analysis
            return {"error": "Invalid JSON"}
    
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        return {"error": str(e)}

def save_analysis(competitor_name: str, text: str, analysis: dict, image_base64: Optional[str] = None) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO analyses (competitor_name, analysis_text, image_base64, analysis_result)
        VALUES (?, ?, ?, ?)
    ''', (competitor_name, text, image_base64, json.dumps(analysis)))
    conn.commit()
    analysis_id = cursor.lastrowid
    conn.close()
    logger.info(f"💾 Сохранено ID: {analysis_id}")
    return analysis_id

def generate_pdf(analysis_id: int, competitor_name: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT analysis_result FROM analyses WHERE id = ?', (analysis_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    analysis = json.loads(row[0])
    pdf_path = f"analysis_{analysis_id}.pdf"
    
    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor("#667eea"),
        spaceAfter=30,
        alignment=1
    )
    
    elements.append(Paragraph(f"📊 Анализ: {competitor_name}", title_style))
    elements.append(Spacer(1, 0.3*inch))
    
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=2
    )
    elements.append(Paragraph(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}", date_style))
    elements.append(Spacer(1, 0.2*inch))
    
    sections = [
        ("💪 Сильные стороны", "strengths"),
        ("⚠️ Слабые стороны", "weaknesses"),
        ("🎯 Возможности", "opportunities"),
        ("🚨 Угрозы", "threats"),
    ]
    
    for title, key in sections:
        if key in analysis and analysis[key]:
            heading = ParagraphStyle(
                f'Heading_{key}',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor("#333"),
                spaceAfter=10,
                spaceBefore=10
            )
            elements.append(Paragraph(title, heading))
            
            text_style = ParagraphStyle(
                f'Text_{key}',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.HexColor("#555"),
                spaceAfter=15
            )
            elements.append(Paragraph(analysis[key], text_style))
    
    if "recommendations" in analysis and analysis["recommendations"]:
        heading = ParagraphStyle(
            'RecommendationsHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor("#667eea"),
            spaceAfter=10,
            spaceBefore=10
        )
        elements.append(Paragraph("📋 Рекомендации", heading))
        
        text_style = ParagraphStyle(
            'RecommendationsText',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor("#555"),
            spaceAfter=15
        )
        elements.append(Paragraph(analysis["recommendations"], text_style))
    
    doc.build(elements)
    logger.info(f"📄 PDF: {pdf_path}")
    return pdf_path

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return open(html_path, encoding='utf-8').read()
    return "<h1>CompetitionMonitor MVP готов!</h1><p>Frontend не найден</p>"

@app.post("/analyzetext")
async def analyze_text(request: AnalysisRequest):
    try:
        logger.info(f"🔍 Анализирую: {request.competitor_name}")
        
        analysis = analyze_with_perplexity(request.text, request.image)
        
        if "error" in analysis:
            return {"success": False, "analysis": analysis}
        
        analysis_id = save_analysis(
            request.competitor_name,
            request.text,
            analysis,
            request.image
        )
        
        return {
            "success": True,
            "analysis": analysis,
            "analysis_id": analysis_id
        }
    
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        return {"success": False, "analysis": {"error": str(e)}}

@app.get("/history")
async def get_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, competitor_name, created_at FROM analyses ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    
    history = [
        {
            "id": row[0],
            "competitor_name": row[1],
            "created_at": row[2]
        }
        for row in rows
    ]
    
    return {"success": True, "history": history}

@app.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT competitor_name, analysis_result FROM analyses WHERE id = ?', (analysis_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {
        "success": True,
        "competitor_name": row[0],
        "analysis": json.loads(row[1])
    }

@app.get("/export-pdf/{analysis_id}")
async def export_pdf(analysis_id: int):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT competitor_name FROM analyses WHERE id = ?', (analysis_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        pdf_path = generate_pdf(analysis_id, row[0])
        return FileResponse(pdf_path, filename=f"analysis_{analysis_id}.pdf")
    
    except Exception as e:
        logger.error(f"❌ Ошибка PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/compare")
async def compare_competitors(request: CompareRequest):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        competitors = []
        for analysis_id in request.analysis_ids:
            cursor.execute('SELECT competitor_name, analysis_result FROM analyses WHERE id = ?', (analysis_id,))
            row = cursor.fetchone()
            if row:
                competitors.append({
                    "name": row[0],
                    "analysis": json.loads(row[1])
                })
        
        conn.close()
        
        if not competitors:
            raise HTTPException(status_code=404, detail="No analyses found")
        
        return {"success": True, "competitors": competitors}
    
    except Exception as e:
        logger.error(f"❌ Ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "✅ API работает", "db": "✅ БД доступна"}

if __name__ == "__main__":
    logger.info(f"✅ API ключ: {API_KEY[:20]}...")
    logger.info("🚀 Backend запускается...")
    logger.info("📊 Endpoints: / /analyzetext /history /analysis/{id} /export-pdf/{id} /compare")
    logger.info("📷 Поддержка: Text + Images")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
