import json
import re
import time
import logging
from typing import Optional
import requests
from backend.config import settings
from backend.models.schemas import CompetitorAnalysis

logger = logging.getLogger("competitionmonitor.perplexity")


class PerplexityService:
    """
    Сервис для анализа текста через Perplexity Pro API
    Использует модель 'sonar' (бесплатная для учеников)
    """
    
    def __init__(self):
        """Инициализация Perplexity сервиса"""
        self.api_key = settings.perplexity_api_key
        self.base_url = settings.perplexity_base_url
        self.model = settings.perplexity_model
        
        logger.info("=" * 60)
        logger.info("🔧 Инициализация PerplexityService")
        logger.info("=" * 60)
        logger.info(f"📍 API URL: {self.base_url}")
        logger.info(f"🧠 Модель: {self.model}")
        logger.info(f"🔑 API Key настроен: {'✅' if self.api_key else '❌'}")
        
        if not self.api_key:
            logger.warning("⚠️  PERPLEXITY_API_KEY не установлен в .env!")
        
        logger.info("=" * 60)
    
    def _parse_json_response(self, content: str) -> dict:
        """
        Парсит JSON из ответа модели, даже если он обёрнут в markdown
        
        Args:
            content: Текст ответа от Perplexity
            
        Returns:
            dict: Распарсенный JSON
        """
        logger.debug(f"🔍 Парсинг JSON из ответа ({len(content)} символов)")
        
        # Пытаемся найти JSON в markdown блоках
        json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
            logger.debug("✅ JSON найден в markdown блоке")
        
        # Пытаемся найти JSON в фигурных скобках
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
            logger.debug("✅ JSON найден в скобках")
        
        try:
            result = json.loads(content)
            logger.debug(f"✅ JSON успешно распарсен, ключи: {list(result.keys())}")
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️  Ошибка парсинга JSON: {str(e)}")
            logger.debug(f"📝 Попытка контента: {content[:200]}...")
            return {}
    
    async def analyze_text(self, text: str) -> CompetitorAnalysis:
        """
        Анализирует текст конкурента через Perplexity Pro
        
        Args:
            text: Текст для анализа (описание конкурента, услуга и т.д.)
            
        Returns:
            CompetitorAnalysis: Объект с результатами анализа
        """
        logger.info("=" * 60)
        logger.info(f"📊 Начало анализа текста ({len(text)} символов)")
        logger.info("=" * 60)
        
        if not text or len(text) < 10:
            logger.warning("⚠️  Текст слишком короткий (< 10 символов)")
            return CompetitorAnalysis()
        
        # Система промпт для анализа конкурентов
        system_prompt = """Ты эксперт по анализу конкурентов. Твоя задача - глубоко анализировать информацию о конкурентах и предоставлять структурированные, практические insights.

Анализируй следующие аспекты:
1. СИЛЬНЫЕ СТОРОНЫ - Что делает конкурент хорошо?
2. СЛАБЫЕ СТОРОНЫ - Где у него пробелы?
3. УНИКАЛЬНЫЕ ПРЕДЛОЖЕНИЯ - Что выделяет его на рынке?
4. ВОЗМОЖНОСТИ - Как можно атаковать/конкурировать?
5. РЕКОМЕНДАЦИИ - Конкретные шаги по противодействию

Отвечай ТОЛЬКО в JSON формате, без дополнительного текста."""
        
        analysis_prompt = f"""
Проанализируй следующую информацию о конкуренте:

{text[:3000]}

Верни ответ в точно таком JSON формате:
{{
    "strengths": ["сильная сторона 1", "сильная сторона 2", ...],
    "weaknesses": ["слабая сторона 1", "слабая сторона 2", ...],
    "unique_offers": ["уникальное предложение 1", "уникальное предложение 2", ...],
    "opportunities": ["возможность атаки 1", "возможность атаки 2", ...],
    "recommendations": ["рекомендация 1", "рекомендация 2", ...],
    "summary": "Краткое резюме анализа (3-5 предложений)"
}}

Будь конкретен. Каждый пункт должен быть actionable (применяемым).
"""
        
        try:
            start_time = time.time()
            logger.info("🚀 Отправка запроса в Perplexity Pro...")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
                "top_p": 0.9,
                "top_k": 0,
            }
            
            # Отправляем запрос
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                verify=False,
                timeout=30
            )
            
            elapsed = time.time() - start_time
            logger.info(f"✅ Получен ответ от Perplexity ({elapsed:.2f}с)")
            
            if response.status_code != 200:
                error_msg = f"API ошибка {response.status_code}: {response.text[:200]}"
                logger.error(f"❌ {error_msg}")
                return CompetitorAnalysis()
            
            # Парсим ответ
            data = response.json()
            
            if "choices" not in data or len(data["choices"]) == 0:
                logger.error("❌ Неожиданный формат ответа от API")
                return CompetitorAnalysis()
            
            analysis_text = data["choices"][0]["message"]["content"]
            logger.info(f"📝 Получен анализ ({len(analysis_text)} символов)")
            logger.debug(f"Контент: {analysis_text[:300]}...")
            
            # Парсим JSON из ответа
            analysis_data = self._parse_json_response(analysis_text)
            
            if not analysis_data:
                logger.warning("⚠️  Не удалось распарсить JSON, возвращаем пустой результат")
                return CompetitorAnalysis()
            
            # Создаём объект анализа
            result = CompetitorAnalysis(
                strengths=analysis_data.get("strengths", []),
                weaknesses=analysis_data.get("weaknesses", []),
                unique_offers=analysis_data.get("unique_offers", []),
                opportunities=analysis_data.get("opportunities", []),
                recommendations=analysis_data.get("recommendations", []),
                summary=analysis_data.get("summary", "")
            )
            
            logger.info(f"✅ Анализ завершен успешно")
            logger.info(f"   📊 Найдено: {len(result.strengths)} сильные, "
                       f"{len(result.weaknesses)} слабые, "
                       f"{len(result.recommendations)} рекомендаций")
            logger.info("=" * 60)
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error("❌ Timeout: Perplexity не ответил за 30 сек")
            return CompetitorAnalysis()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Ошибка запроса: {str(e)}")
            return CompetitorAnalysis()
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {str(e)}")
            logger.exception("Полный трейбек:")
            return CompetitorAnalysis()
    
    async def ask_question(self, question: str) -> str:
        """
        Простой вопрос-ответ для диалога
        
        Args:
            question: Вопрос пользователя
            
        Returns:
            str: Ответ от Perplexity
        """
        logger.debug(f"❓ Вопрос: {question[:100]}...")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 1000,
                "top_p": 0.9,
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                verify=False,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data["choices"][0]["message"]["content"]
                logger.debug(f"✅ Получен ответ ({len(answer)} символов)")
                return answer
            else:
                logger.error(f"❌ API ошибка {response.status_code}")
                return f"Ошибка API: {response.status_code}"
                
        except Exception as e:
            logger.error(f"❌ Ошибка: {str(e)}")
            return f"Ошибка: {str(e)}"


# Экземпляр сервиса для использования в приложении
perplexity_service = PerplexityService()
