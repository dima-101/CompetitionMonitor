import os
import sys
import logging
import json
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
import requests
import sqlite3


# ==================== КОНФИГУРАЦИЯ ====================
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


# Import scoring service
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


# API Key
API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
DB_PATH = "analyses.db"

logger.info(f"✅ API ключ загружен: {API_KEY[:20] if API_KEY else 'НЕ НАЙДЕН'}...")


# ==================== МОДЕЛИ ====================
class AnalysisRequest(BaseModel):
    text: str


# ==================== DATABASE ====================


def init_db():
    """Инициализация БД"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY,
            text TEXT,
            result TEXT,
            scoring TEXT,
            created_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("✅ База данных инициализирована")


init_db()


# ==================== HELPER FUNCTIONS ====================


def parse_competitors_from_text(text):
    """Парсит конкурентов из текста Perplexity"""
    competitors = []
    
    if not text:
        logger.warning("⚠️ Empty text passed to parser")
        return competitors
    
    logger.info(f"📝 Parsing text ({len(text)} chars)")
    
    # Regex patterns для разных форматов
    patterns = [
        # Pattern 1: - **Name** – desc or : desc
        r'^[\s]*[\-\*]\s+\*\*([^*]+?)\*\*\s*(?:–|-|:)\s*(.+?)(?:\n|$)',
        
        # Pattern 2: **Name** – desc (start of line)
        r'^[\s]*\*\*([^*]+?)\*\*\s*(?:–|-|:)\s*(.+?)(?:\n|$)',
        
        # Pattern 3: **Name**: desc
        r'\*\*([^*]+?)\*\*:\s*([^.\n]+)',
        
        # Pattern 4: 1. **Name** – desc
        r'^\d+\.\s+\*\*([^*]+?)\*\*\s*(?:–|-|:)\s*(.+?)(?:\n|$)',
    ]
    
    seen_names = set()
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.MULTILINE)
        
        for match in matches:
            try:
                name = match.group(1).strip()
                desc = match.group(2).strip()
                
                # Фильтруем
                if not name or len(name) < 2:
                    continue
                
                if not name[0].isupper():
                    continue
                
                # Пропускаем дубликаты
                name_lower = name.lower()
                if name_lower in seen_names:
                    continue
                
                # Очищаем описание
                desc = re.sub(r'\[\d+\]', '', desc).strip()
                
                # Минимум 10 символов
                if len(desc) < 10:
                    continue
                
                desc = desc.rstrip('.')
                
                logger.info(f"✅ Found: {name} → {desc[:50]}...")
                
                seen_names.add(name_lower)
                competitors.append({
                    "name": name,
                    "description": desc[:200],
                    "strengths": [],
                    "weaknesses": [],
                    "score": {}
                })
            
            except Exception as e:
                logger.warning(f"⚠️ Error parsing match: {e}")
                continue
    
    logger.info(f"✅ TOTAL PARSED: {len(competitors)} competitors")
    for c in competitors:
        logger.info(f"   - {c['name']}: {c['description'][:40]}...")
    
    return competitors[:10]


# ==================== FASTAPI APP ====================
app = FastAPI(title="CompetitionMonitor API", version="1.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== ENDPOINTS ====================


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "✅ CompetitionMonitor работает",
        "scoring": "✅ Включен" if SCORING_ENABLED else "❌ Отключен",
        "api_key": "✅ Загружен" if API_KEY else "❌ НЕ загружен"
    }


@app.get("/analyzetext-scored")
async def analyze_text_scored(text: str):
    """
    Анализ конкурентов с Scoring через Perplexity API
    
    Usage:
    GET /analyzetext-scored?text=Figma%20competing%20with%20Sketch
    """
    try:
        logger.info(f"🎨 === SCORING ANALYSIS START ===")
        logger.info(f"🎨 Input text: {text[:50]}...")
        
        # ===== VALIDATION =====
        if not text or len(text.strip()) == 0:
            logger.error("❌ Empty text provided")
            raise HTTPException(status_code=400, detail="Текст не предоставлен")
        
        if not SCORING_ENABLED:
            logger.error("❌ SCORING_ENABLED = False")
            raise HTTPException(status_code=503, detail="Scoring service недоступен")
        
        if not API_KEY:
            logger.error("❌ API_KEY не найден в .env")
            raise HTTPException(status_code=503, detail="API ключ не найден")
        
        logger.info(f"✅ Validation OK")
        logger.info(f"✅ API Key: {API_KEY[:20]}...")
        logger.info(f"✅ Scorer: {type(scorer).__name__}")
        
        # ===== PERPLEXITY API REQUEST =====
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        prompt = f"""Analyze the following text about design tools and identify all competitors mentioned.

For each competitor found, provide:
1. **Name** - The product/tool name (use **bold** format)
2. Brief description of what it does

Format your response as:
- **CompetitorName** – Brief description
- **CompetitorName2** – Brief description

Text to analyze:
{text}
"""
        
        payload = {
            "model": "sonar-pro",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        logger.info(f"🚀 Calling Perplexity API...")
        response = requests.post(PERPLEXITY_URL, json=payload, headers=headers, timeout=30)
        logger.info(f"📊 Status Code: {response.status_code}")
        
        if response.status_code != 200:
            error_text = response.text[:300]
            logger.error(f"❌ API ERROR {response.status_code}: {error_text}")
            raise HTTPException(
                status_code=response.status_code, 
                detail=f"Perplexity API error: {error_text}"
            )
        
        api_response = response.json()
        analysis_text = api_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        if not analysis_text:
            logger.error("❌ Empty response from Perplexity")
            raise HTTPException(status_code=502, detail="Пустой ответ от API")
        
        logger.info(f"📝 RAW TEXT LENGTH: {len(analysis_text)} chars")
        logger.info(f"📝 RAW TEXT RECEIVED:\n{analysis_text}")
        
        # ===== PARSING COMPETITORS =====
        competitors = parse_competitors_from_text(analysis_text)
        logger.info(f"✅ PARSING COMPLETE: {len(competitors)} competitors found")
        
        # ===== APPLY SCORING =====
        if scorer and competitors:
            logger.info(f"🎨 Applying scoring to {len(competitors)} competitors...")
            for competitor in competitors:
                try:
                    score = scorer.score_text(competitor['description'])
                    competitor['score'] = score
                    logger.info(f"   ✅ Scored: {competitor['name']}")
                except Exception as e:
                    logger.warning(f"⚠️ Scoring failed for {competitor['name']}: {e}")
                    competitor['score'] = {}
        else:
            logger.warning(f"⚠️ Scoring skipped: scorer={scorer}, competitors={len(competitors)}")
        
        # ===== BUILD RESPONSE =====
        result = {
            "status": "success",
            "analysis": {
                "competitors": competitors,
                "raw_response": analysis_text[:500],
                "scoring_enabled": SCORING_ENABLED,
                "total_found": len(competitors),
                "api_used": "perplexity-sonar-pro"
            }
        }
        
        logger.info(f"✅ === ANALYSIS COMPLETE ===")
        logger.info(f"✅ Result: {len(competitors)} competitors")
        return result
        
    except requests.exceptions.Timeout:
        logger.error("❌ TIMEOUT: Perplexity API не ответил за 30 сек")
        raise HTTPException(status_code=504, detail="API timeout (30s)")
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ CONNECTION ERROR: {str(e)}")
        raise HTTPException(status_code=503, detail="Cannot connect to Perplexity API")
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"❌ EXCEPTION: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ==================== STARTUP ====================


if __name__ == "__main__":
    logger.info(f"\n{'='*70}")
    logger.info(f"✅ API ключ: {API_KEY[:20]}..." if API_KEY else f"❌ API ключ НЕ найден!")
    logger.info(f"✅ Scoring: {'ВКЛЮЧЕН' if SCORING_ENABLED else 'ОТКЛЮЧЕН'}")
    logger.info(f"🚀 Backend запускается на http://0.0.0.0:8000")
    logger.info(f"{'='*70}\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
