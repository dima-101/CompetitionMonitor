from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== ЗАПРОСЫ ====================

class TextAnalysisRequest(BaseModel):
    """Запрос на анализ текста конкурента"""
    text: str = Field(..., min_length=10, max_length=5000, 
                      description="Текст для анализа (10-5000 символов)")


class ImageAnalysisRequest(BaseModel):
    """Запрос на анализ изображения"""
    image_base64: str = Field(..., description="Изображение в формате base64")
    image_type: str = Field("image/jpeg", description="MIME тип: image/jpeg, image/png, image/webp")


class ParseDemoRequest(BaseModel):
    """Запрос на парсинг URL"""
    url: str = Field(..., description="URL сайта конкурента")


# ==================== МОДЕЛИ АНАЛИЗА ====================

class CompetitorAnalysis(BaseModel):
    """Анализ текста конкурента (от Perplexity)"""
    strengths: List[str] = Field(default_factory=list, 
                                 description="Сильные стороны конкурента")
    weaknesses: List[str] = Field(default_factory=list, 
                                  description="Слабые стороны конкурента")
    unique_offers: List[str] = Field(default_factory=list, 
                                     description="Уникальные предложения")
    opportunities: List[str] = Field(default_factory=list, 
                                     description="Возможности для атаки")
    recommendations: List[str] = Field(default_factory=list, 
                                       description="Рекомендации по противодействию")
    summary: str = Field(default="", 
                        description="Краткое резюме анализа (3-5 предложений)")


class ImageAnalysis(BaseModel):
    """Анализ изображения (от Vision API через Proxy)"""
    description: str = Field(default="", 
                             description="Описание визуального контента")
    marketing_insights: List[str] = Field(default_factory=list, 
                                         description="Маркетинговые insights")
    visual_style_score: int = Field(default=5, ge=0, le=10, 
                                   description="Оценка визуального стиля 0-10")
    visual_style_analysis: str = Field(default="", 
                                      description="Анализ визуального стиля")
    cta_analysis: str = Field(default="", 
                             description="Анализ призыва к действию")
    recommendations: List[str] = Field(default_factory=list, 
                                      description="Рекомендации для улучшения")


class ParsedContent(BaseModel):
    """Распарсенный контент с веб-сайта"""
    url: str
    title: Optional[str] = None
    h1: Optional[str] = None
    meta_description: Optional[str] = None
    first_paragraph: Optional[str] = None
    screenshot_base64: Optional[str] = None
    analysis: Optional[CompetitorAnalysis] = None
    error: Optional[str] = None


# ==================== ОТВЕТЫ ====================

class TextAnalysisResponse(BaseModel):
    """Ответ на анализ текста"""
    success: bool
    analysis: Optional[CompetitorAnalysis] = None
    error: Optional[str] = None


class ImageAnalysisResponse(BaseModel):
    """Ответ на анализ изображения"""
    success: bool
    analysis: Optional[ImageAnalysis] = None
    error: Optional[str] = None


class ParseDemoResponse(BaseModel):
    """Ответ на запрос парсинга"""
    success: bool
    data: Optional[ParsedContent] = None
    error: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Ответ проверки здоровья API"""
    status: str
    service: str
    version: str
    perplexity_configured: bool
    proxy_api_configured: bool


# ==================== ИСТОРИЯ ====================

class HistoryItem(BaseModel):
    """Элемент истории запроса"""
    id: str = Field(..., description="UUID запроса")
    timestamp: datetime = Field(..., description="Время запроса")
    request_type: str = Field(..., description="Тип запроса: text, image, parse")
    request_summary: str = Field(..., description="Краткое резюме запроса (до 200 символов)")
    response_summary: str = Field(..., description="Краткое резюме ответа (до 500 символов)")
    tokens_used: Optional[int] = None  # Для отслеживания использования токенов


class HistoryResponse(BaseModel):
    """Ответ со списком истории"""
    items: List[HistoryItem]
    total: int


class ClearHistoryResponse(BaseModel):
    """Ответ на очистку истории"""
    success: bool
    message: str


# ==================== УТИЛИТЫ ====================

class ErrorResponse(BaseModel):
    """Стандартный ответ об ошибке"""
    success: bool = False
    error: str
    status_code: int = 400
