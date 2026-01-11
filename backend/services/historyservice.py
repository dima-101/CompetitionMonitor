import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import List
from backend.config import settings
from backend.models.schemas import HistoryItem

logger = logging.getLogger("competitionmonitor.history")


class HistoryService:
    """
    Сервис для управления историей запросов
    Сохраняет в JSON файл локально
    """
    
    def __init__(self):
        """Инициализация сервиса истории"""
        self.history_file = Path(settings.history_file)
        self.max_items = settings.max_history_items
        
        logger.info("=" * 60)
        logger.info("🔧 Инициализация HistoryService")
        logger.info("=" * 60)
        logger.info(f"📁 История файл: {self.history_file.absolute()}")
        logger.info(f"📊 Макс элементов: {self.max_items}")
        
        self._ensure_file_exists()
        
        # Загружаем текущую историю
        history = self.load_history()
        logger.info(f"📝 Загружено {len(history)} записей истории")
        logger.info("=" * 60)
    
    def _ensure_file_exists(self):
        """Создаёт файл истории если его нет"""
        if not self.history_file.exists():
            logger.info(f"📁 Создание файла истории: {self.history_file}")
            self.history_file.write_text("[]", encoding="utf-8")
            logger.info("✅ Файл истории создан")
        else:
            logger.debug(f"✅ Файл истории уже существует")
    
    def load_history(self) -> List[dict]:
        """
        Загружает историю из JSON файла
        
        Returns:
            List[dict]: Список записей истории
        """
        try:
            content = self.history_file.read_text(encoding="utf-8")
            history = json.loads(content)
            logger.debug(f"✅ История загружена ({len(history)} записей)")
            return history
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️  Ошибка парсинга JSON: {str(e)}")
            return []
        except FileNotFoundError:
            logger.warning(f"⚠️  Файл истории не найден")
            return []
    
    def save_history(self, history: List[dict]):
        """
        Сохраняет историю в JSON файл
        
        Args:
            history: Список записей для сохранения
        """
        try:
            self.history_file.write_text(
                json.dumps(history, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8"
            )
            logger.debug(f"✅ История сохранена ({len(history)} записей)")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения истории: {str(e)}")
    
    def add_entry(
        self,
        request_type: str,
        request_summary: str,
        response_summary: str,
        tokens_used: int = None
    ) -> HistoryItem:
        """
        Добавляет новую запись в историю
        
        Args:
            request_type: Тип запроса (text, image, parse)
            request_summary: Краткое резюме запроса (до 200 символов)
            response_summary: Краткое резюме ответа (до 500 символов)
            tokens_used: Количество использованных токенов (опционально)
            
        Returns:
            HistoryItem: Добавленная запись
        """
        logger.info("=" * 60)
        logger.info(f"📝 Добавление записи в историю (тип: {request_type})")
        logger.info("=" * 60)
        
        history = self.load_history()
        
        # Обрезаем резюме если слишком длинные
        request_summary = request_summary[:200]
        response_summary = response_summary[:500]
        
        # Создаём новую запись
        item_dict = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "request_type": request_type,
            "request_summary": request_summary,
            "response_summary": response_summary,
            "tokens_used": tokens_used
        }
        
        # Добавляем в начало (новые записи первыми)
        history.insert(0, item_dict)
        
        # Ограничиваем количество записей
        history = history[:self.max_items]
        
        # Сохраняем
        self.save_history(history)
        
        logger.info(f"✅ Запись добавлена")
        logger.info(f"   🔑 ID: {item_dict['id']}")
        logger.info(f"   📝 Тип: {request_type}")
        logger.info(f"   📊 Запрос: {request_summary[:50]}...")
        logger.info("=" * 60)
        
        return HistoryItem(**item_dict)
    
    def get_history(self) -> List[HistoryItem]:
        """
        Получает список всех записей истории
        
        Returns:
            List[HistoryItem]: Список моделей HistoryItem
        """
        history = self.load_history()
        return [HistoryItem(**item) for item in history]
    
    def clear_history(self):
        """Очищает всю историю"""
        logger.warning("🧹 Очистка всей истории...")
        self.save_history([])
        logger.info("✅ История очищена")
    
    def get_summary_stats(self) -> dict:
        """
        Возвращает статистику по истории
        
        Returns:
            dict: Статистика использования
        """
        history = self.load_history()
        
        text_count = sum(1 for h in history if h.get("request_type") == "text")
        image_count = sum(1 for h in history if h.get("request_type") == "image")
        parse_count = sum(1 for h in history if h.get("request_type") == "parse")
        total_tokens = sum(h.get("tokens_used", 0) for h in history)
        
        stats = {
            "total_requests": len(history),
            "text_requests": text_count,
            "image_requests": image_count,
            "parse_requests": parse_count,
            "total_tokens_used": total_tokens,
            "max_items": self.max_items
        }
        
        logger.info(f"📊 Статистика истории: {stats}")
        return stats


# Экземпляр сервиса
history_service = HistoryService()
