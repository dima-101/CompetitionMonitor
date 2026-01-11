import os
import logging
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

# Настройка логирования
def setup_logging():
    log_format = "%(asctime)s - %(levelname)-8s - %(name)-25s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(),
        ]
    )
    
    # Отключаем шум от сторонних библиотек
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("playwright").setLevel(logging.WARNING)
    
    return logging.getLogger("competitionmonitor")

logger = setup_logging()

class Settings(BaseSettings):
    """
    Конфигурация приложения CompetitionMonitor
    Использует Perplexity Pro для анализа текста
    """
    
    # Perplexity Pro API Configuration
    perplexity_api_key: str = os.getenv("PERPLEXITY_API_KEY", "")
    perplexity_base_url: str = "https://api.perplexity.ai/chat/completions"
    perplexity_model: str = "sonar"  # Бесплатная модель для ученической версии
    
    # Proxy API Configuration (опционально для vision/резервно)
    proxy_api_key: str = os.getenv("PROXY_API_KEY", "")
    proxy_api_base_url: str = "https://api.proxyapi.ru/openai/v1"
    proxy_api_vision_model: str = "gpt-4o-mini"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # History Configuration
    history_file: str = "history.json"
    max_history_items: int = 10
    
    # Parser Configuration (Playwright)
    parser_timeout: int = 10000  # миллисекунды
    parser_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    # Application Settings
    app_env: str = os.getenv("APP_ENV", "development")
    debug: bool = app_env == "development"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Логирование при запуске
if __name__ != "__main__":
    logger.info("=" * 60)
    logger.info("🚀 CompetitionMonitor - Инициализация конфигурации")
    logger.info("=" * 60)
    logger.info(f"📍 Окружение: {settings.app_env}")
    logger.info(f"🔑 Perplexity Pro настроен: {'✅' if settings.perplexity_api_key else '❌'}")
    logger.info(f"🔑 Proxy API настроен: {'✅' if settings.proxy_api_key else '❌'}")
    logger.info(f"🌐 API: http://{settings.api_host}:{settings.api_port}")
    logger.info(f"📝 Модель Perplexity: {settings.perplexity_model}")
    logger.info(f"⏱️  Parser timeout: {settings.parser_timeout}ms")
    logger.info("=" * 60)
