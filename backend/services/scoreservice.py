import logging
from typing import Dict, Optional
from backend.models.schemas import CompetitorAnalysis, ImageAnalysis

logger = logging.getLogger("competitionmonitor.scorer")


class DesignToolsScoringService:
    """
    Сервис для scoring анализов конкурентов в нише AI Design Tools.
    Использует кастомные метрики для дизайна.
    
    Метрики:
    - design_score: Качество визуального дизайна (0-10)
    - animation_potential: Потенциал анимаций (0-10)
    - feature_richness: Богатство функций (0-10)
    - ux_rating: Рейтинг UX/UI (0-10)
    - overall_threat_level: Общий уровень угрозы (low/medium/high)
    """
    
    # Ключевые слова для оценки
    DESIGN_KEYWORDS = {
        "ui/ux": 2, "дизайн": 2, "интерфейс": 1.5,
        "фигма": 1, "canva": 1, "adobe": 1,
        "vector": 1.5, "растровый": 1, "svg": 1,
        "css": 1, "анимация": 2, "переходы": 1.5
    }
    
    ANIMATION_KEYWORDS = {
        "анимация": 3, "переходы": 2, "движение": 2,
        "lottie": 2, "gsap": 2, "три.js": 2.5,
        "webgl": 2.5, "canvas": 1.5, "gpu": 2
    }
    
    FEATURE_KEYWORDS = {
        "ai": 3, "ml": 3, "нейросеть": 3, "алгоритм": 2,
        "автоматизация": 2, "обработка": 1.5, "фильтры": 1,
        "слои": 1, "группировка": 1, "версионирование": 2,
        "коллаборация": 2, "синхронизация": 1.5
    }
    
    UX_KEYWORDS = {
        "интуитивный": 2, "удобство": 1.5, "простота": 1.5,
        "доступность": 2, "a11y": 2, "wcag": 1.5,
        "адаптивный": 1.5, "мобильный": 1, "оптимизация": 1
    }
    
    def __init__(self):
        """Инициализация сервиса скоринга"""
        logger.info("🎨 Инициализация DesignToolsScoringService")
        logger.info(f"   📊 Ключевые слова для дизайна: {len(self.DESIGN_KEYWORDS)}")
        logger.info(f"   🎬 Ключевые слова для анимаций: {len(self.ANIMATION_KEYWORDS)}")
        logger.info(f"   ⚙️  Ключевые слова для функций: {len(self.FEATURE_KEYWORDS)}")
        logger.info(f"   👥 Ключевые слова для UX: {len(self.UX_KEYWORDS)}")
    
    def _score_text(self, text: str, keywords: Dict[str, float]) -> float:
        """
        Оценивает текст по наличию ключевых слов
        
        Args:
            text: Текст для анализа
            keywords: Словарь ключевых слов с весами
            
        Returns:
            float: Оценка 0-10
        """
        if not text:
            return 0.0
        
        text_lower = text.lower()
        score = 0.0
        
        for keyword, weight in keywords.items():
            if keyword in text_lower:
                score += weight
        
        # Нормализуем к 0-10
        max_score = sum(keywords.values())
        normalized = (score / max_score * 10) if max_score > 0 else 0
        
        return min(10.0, normalized)
    
    def _analyze_strengths(self, strengths: list) -> Dict[str, float]:
        """
        Анализирует сильные стороны для выявления специфичных метрик
        
        Args:
            strengths: Список сильных сторон
            
        Returns:
            dict: Выявленные метрики
        """
        combined_text = " ".join(strengths).lower()
        
        return {
            "design_focus": self._score_text(combined_text, self.DESIGN_KEYWORDS),
            "animation_focus": self._score_text(combined_text, self.ANIMATION_KEYWORDS),
            "ai_features": self._score_text(combined_text, self.FEATURE_KEYWORDS),
            "ux_emphasis": self._score_text(combined_text, self.UX_KEYWORDS),
        }
    
    def score_competitor_text(self, analysis: CompetitorAnalysis) -> Dict:
        """
        Скорит текстовый анализ конкурента для AI Design Tools
        
        Args:
            analysis: Объект анализа от Perplexity
            
        Returns:
            dict: Объект со скорами
        """
        logger.info("📊 Скоринг текстового анализа...")
        
        # Объединяем все текстовые данные
        combined_text = " ".join([
            " ".join(analysis.strengths),
            " ".join(analysis.weaknesses),
            " ".join(analysis.unique_offers),
            analysis.summary
        ])
        
        # Рассчитываем основные метрики
        design_score = self._score_text(combined_text, self.DESIGN_KEYWORDS)
        animation_potential = self._score_text(combined_text, self.ANIMATION_KEYWORDS)
        feature_richness = self._score_text(combined_text, self.FEATURE_KEYWORDS)
        ux_rating = self._score_text(combined_text, self.UX_KEYWORDS)
        
        # Анализируем сильные стороны
        strengths_analysis = self._analyze_strengths(analysis.strengths)
        
        # Определяем уровень угрозы
        overall_score = (design_score + animation_potential + feature_richness + ux_rating) / 4
        if overall_score >= 7.5:
            threat_level = "high"
        elif overall_score >= 5:
            threat_level = "medium"
        else:
            threat_level = "low"
        
        result = {
            "design_score": round(design_score, 2),
            "animation_potential": round(animation_potential, 2),
            "feature_richness": round(feature_richness, 2),
            "ux_rating": round(ux_rating, 2),
            "overall_threat_level": threat_level,
            "overall_score": round(overall_score, 2),
            "strengths_analysis": {k: round(v, 2) for k, v in strengths_analysis.items()},
            "recommendations": self._generate_recommendations(
                design_score, animation_potential, feature_richness, ux_rating,
                analysis.weaknesses
            )
        }
        
        logger.info(f"✅ Скоринг завершен: threat_level={threat_level}, overall={overall_score:.2f}")
        return result
    
    def score_competitor_image(self, image_analysis: ImageAnalysis) -> Dict:
        """
        Скорит анализ изображения конкурента
        
        Args:
            image_analysis: Объект анализа изображения
            
        Returns:
            dict: Объект со скорами
        """
        logger.info("🖼️  Скоринг анализа изображения...")
        
        # Используем готовый visual_style_score
        design_score = image_analysis.visual_style_score
        
        # Анализируем маркетинговые insights для потенциала
        combined_text = " ".join(image_analysis.marketing_insights).lower()
        animation_potential = self._score_text(combined_text, self.ANIMATION_KEYWORDS)
        
        result = {
            "design_score": design_score,
            "animation_potential": round(animation_potential, 2),
            "visual_style_details": image_analysis.visual_style_analysis,
            "cta_effectiveness": image_analysis.cta_analysis,
            "marketing_insights": image_analysis.marketing_insights,
            "recommendations": image_analysis.recommendations
        }
        
        logger.info(f"✅ Скоринг изображения: design={design_score}, animation={animation_potential:.2f}")
        return result
    
    def _generate_recommendations(self, design: float, animation: float, 
                                 features: float, ux: float, weaknesses: list) -> list:
        """
        Генерирует специфичные рекомендации на основе метрик
        
        Args:
            design, animation, features, ux: Оценки метрик
            weaknesses: Список слабых сторон
            
        Returns:
            list: Рекомендации
        """
        recommendations = []
        
        if design < 5:
            recommendations.append("🎨 Улучшить дизайн интерфейса - инвестировать в UI/UX")
        
        if animation < 5:
            recommendations.append("🎬 Добавить микроанимации для улучшения взаимодействия")
        
        if features < 5:
            recommendations.append("⚙️  Расширить функциональность, особенно AI-features")
        
        if ux < 5:
            recommendations.append("👥 Улучшить доступность и эргономику интерфейса")
        
        if "цена" in " ".join(weaknesses).lower():
            recommendations.append("💰 Конкурировать по качеству, а не по цене")
        
        if "ai" not in " ".join(weaknesses).lower() and features > 6:
            recommendations.append("🤖 Конкурент активно использует AI - это угроза")
        
        return recommendations
    
    def compare_competitors(self, scores: Dict[str, Dict]) -> Dict:
        """
        Сравнивает несколько конкурентов
        
        Args:
            scores: Словарь {имя_конкурента: объект_скора}
            
        Returns:
            dict: Сравнительный анализ
        """
        logger.info(f"📊 Сравнение {len(scores)} конкурентов...")
        
        competitors_sorted = sorted(
            scores.items(),
            key=lambda x: x[1].get("overall_score", 0),
            reverse=True
        )
        
        return {
            "ranking": [{"name": name, "score": score["overall_score"]} 
                       for name, score in competitors_sorted],
            "threat_levels": {
                "high": sum(1 for _, s in scores.items() if s.get("overall_threat_level") == "high"),
                "medium": sum(1 for _, s in scores.items() if s.get("overall_threat_level") == "medium"),
                "low": sum(1 for _, s in scores.items() if s.get("overall_threat_level") == "low"),
            },
            "market_analysis": self._analyze_market(scores)
        }
    
    def _analyze_market(self, scores: Dict[str, Dict]) -> Dict:
        """Анализирует общее состояние рынка"""
        avg_design = sum(s.get("design_score", 0) for s in scores.values()) / len(scores) if scores else 0
        avg_animation = sum(s.get("animation_potential", 0) for s in scores.values()) / len(scores) if scores else 0
        avg_features = sum(s.get("feature_richness", 0) for s in scores.values()) / len(scores) if scores else 0
        avg_ux = sum(s.get("ux_rating", 0) for s in scores.values()) / len(scores) if scores else 0
        
        return {
            "avg_design_score": round(avg_design, 2),
            "avg_animation_potential": round(avg_animation, 2),
            "avg_feature_richness": round(avg_features, 2),
            "avg_ux_rating": round(avg_ux, 2),
            "market_maturity": self._assess_maturity(avg_design, avg_animation, avg_features, avg_ux)
        }
    
    def _assess_maturity(self, design: float, animation: float, features: float, ux: float) -> str:
        """Оценивает зрелость рынка"""
        avg_score = (design + animation + features + ux) / 4
        
        if avg_score >= 7.5:
            return "mature"  # Рынок зрелый, высокая конкуренция
        elif avg_score >= 5:
            return "growing"  # Рынок растет
        else:
            return "emerging"  # Рынок зарождается, есть возможности


# Экземпляр сервиса
scorer = DesignToolsScoringService()
