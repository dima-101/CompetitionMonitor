import httpx
import json
from typing import Optional
from backend.config import settings, logger
from pydantic import BaseModel

class CompetitorAnalysis(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    unique_offers: list[str]
    opportunities: list[str]
    recommendations: list[str]
    summary: str

class PerplexityService:
    def __init__(self):
        self.api_url = settings.PERPLEXITY_API_URL
        self.api_key = settings.PERPLEXITY_API_KEY
        self.model = settings.PERPLEXITY_MODEL
        logger.info(f"🔧 Инициализация PerplexityService")
        logger.info(f"📍 API URL: {self.api_url}")
        logger.info(f"🧠 Модель: {self.model}")
        logger.info(f"🔑 API Key настроен: ✅")

    async def analyze_text(self, text: str) -> CompetitorAnalysis:
        """Анализ конкурента с улучшенным промптом"""
        
        prompt = f"""Ты - опытный бизнес-аналитик и эксперт по конкурентной разведке. 
Твоя задача: дать глубокий, структурированный анализ конкурента на основе предоставленной информации.

ИНФОРМАЦИЯ О КОНКУРЕНТЕ:
{text}

ТРЕБУЕМЫЙ ФОРМАТ ОТВЕТА (JSON):
{{
  "strengths": ["список 3-5 сильных сторон"],
  "weaknesses": ["список 3-5 слабых мест"],
  "unique_offers": ["список 2-3 уникальных предложений"],
  "opportunities": ["список 2-3 возможностей для развития"],
  "recommendations": ["список 3-5 рекомендаций для конкуренции"],
  "summary": "краткое резюме (1-2 предложения)"
}}

ИНСТРУКЦИИ:
1. Будь конкретным и практичным
2. Учитывай актуальные тренды рынка
3. Фокусируйся на практическом применении
4. Считай реальные сценарии
5. Предложи actionable recommendations

Возвращай ТОЛЬКО валидный JSON без дополнительного текста."""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "Ты JSON API. Возвращай только валидный JSON."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.7,
                        "max_tokens": 2000
                    }
                )
                
                logger.info(f"📊 Perplexity Status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    try:
                        json_start = content.find('{')
                        json_end = content.rfind('}') + 1
                        if json_start >= 0 and json_end > json_start:
                            json_str = content[json_start:json_end]
                            analysis_dict = json.loads(json_str)
                        else:
                            analysis_dict = json.loads(content)
                        
                        logger.info(f"✅ Анализ получен успешно")
                        return CompetitorAnalysis(**analysis_dict)
                    
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ JSON Parse Error: {e}")
                        logger.error(f"Raw content: {content[:200]}")
                        return CompetitorAnalysis(
                            strengths=["Требуется более детальная информация"],
                            weaknesses=[],
                            unique_offers=[],
                            opportunities=[],
                            recommendations=["Предоставьте более подробное описание конкурента"],
                            summary="Ошибка парсинга ответа"
                        )
                else:
                    logger.error(f"❌ Perplexity Error: {response.status_code}")
                    return CompetitorAnalysis(
                        strengths=[],
                        weaknesses=[],
                        unique_offers=[],
                        opportunities=[],
                        recommendations=[],
                        summary="Ошибка при запросе к Perplexity"
                    )
        
        except Exception as e:
            logger.error(f"❌ Exception: {str(e)}")
            return CompetitorAnalysis(
                strengths=[],
                weaknesses=[],
                unique_offers=[],
                opportunities=[],
                recommendations=[],
                summary=f"Ошибка: {str(e)}"
            )

perplexity_service = PerplexityService()
