"""
Trend - класс для представления информационных трендов в симуляции.
"""

from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import math


class CoverageLevel(Enum):
    """Уровни охвата тренда."""
    LOW = "Low"
    MIDDLE = "Middle" 
    HIGH = "High"


class TrendTopic(Enum):
    """Доступные темы трендов."""
    ECONOMIC = "Economic"
    HEALTH = "Health"
    SPIRITUAL = "Spiritual"
    CONSPIRACY = "Conspiracy"
    SCIENCE = "Science"
    CULTURE = "Culture"
    SPORT = "Sport"


class Sentiment(Enum):
    """Тональность тренда."""
    POSITIVE = "Positive"
    NEGATIVE = "Negative"


@dataclass
class Trend:
    """
    Представляет информационный тренд в социальной сети.
    
    Содержит информацию о:
    - Виральности и охвате
    - Авторе и родительском тренде
    - Количестве взаимодействий
    """
    
    # Core identification
    trend_id: UUID = field(default_factory=uuid4)
    topic: str = ""  # One of TrendTopic values
    originator_id: UUID = field(default_factory=uuid4)
    parent_trend_id: Optional[UUID] = None
    
    # Temporal data
    timestamp_start: datetime = field(default_factory=datetime.utcnow)
    
    # Virality metrics
    base_virality_score: float = 0.0  # 0.0-5.0 scale
    coverage_level: str = CoverageLevel.LOW.value
    total_interactions: int = 0

    # v1.9 sentiment
    sentiment: str = Sentiment.POSITIVE.value  # "Positive" | "Negative"
    
    # Simulation metadata
    simulation_id: UUID = field(default_factory=uuid4)

    # ------------------------------
    # Dataclass hooks / validation
    # ------------------------------

    def __post_init__(self):
        if self.sentiment not in (Sentiment.POSITIVE.value, Sentiment.NEGATIVE.value):
            raise ValueError(f"Invalid sentiment '{self.sentiment}'. Must be 'Positive' or 'Negative'.")
        
    def calculate_current_virality(self) -> float:
        """
        Рассчитывает текущую виральность с учетом взаимодействий.
        
        Формула: new_score = min(5.0, base_virality + 0.05 * log(interactions + 1))
        
        Returns:
            Текущий показатель виральности
        """
        if self.total_interactions == 0:
            return self.base_virality_score
            
        logarithmic_bonus = 0.05 * math.log(self.total_interactions + 1)
        return min(5.0, self.base_virality_score + logarithmic_bonus)
        
    def add_interaction(self) -> None:
        """
        Регистрирует новое взаимодействие с трендом.
        """
        self.total_interactions += 1
        
    def is_active(self, current_time: datetime, threshold_days: int = 3) -> bool:
        """
        Проверяет активность тренда на основе времени последнего взаимодействия.
        
        Args:
            current_time: Текущее время симуляции
            threshold_days: Порог неактивности в днях
            
        Returns:
            True если тренд считается активным
        """
        time_since_start = current_time - self.timestamp_start
        return time_since_start.days < threshold_days
        
    def get_coverage_factor(self) -> float:
        """
        Возвращает числовой коэффициент охвата.
        
        Returns:
            Коэффициент: Low=0.3, Middle=0.6, High=1.0
        """
        coverage_map = {
            CoverageLevel.LOW.value: 0.3,
            CoverageLevel.MIDDLE.value: 0.6,
            CoverageLevel.HIGH.value: 1.0
        }
        return coverage_map.get(self.coverage_level, 0.3)
        
    @classmethod
    def create_from_action(
        cls,
        topic: str,
        originator_id: UUID,
        simulation_id: UUID,
        base_virality: float,
        coverage_level: str = CoverageLevel.LOW.value,
        parent_id: Optional[UUID] = None,
        *, sentiment: str | None = None
    ) -> "Trend":
        """
        Создает новый тренд из действия агента.
        
        Args:
            topic: Тема тренда
            originator_id: ID агента-автора
            simulation_id: ID симуляции
            base_virality: Базовая виральность
            coverage_level: Уровень охвата
            parent_id: ID родительского тренда (для ответов)
            
        Returns:
            Новый экземпляр Trend
        """
        import random

        sentiment_val = (
            sentiment
            if sentiment in (Sentiment.POSITIVE.value, Sentiment.NEGATIVE.value)
            else random.choice([Sentiment.POSITIVE.value, Sentiment.NEGATIVE.value])
        )

        return cls(
            topic=topic,
            originator_id=originator_id,
            simulation_id=simulation_id,
            base_virality_score=base_virality,
            coverage_level=coverage_level,
            parent_trend_id=parent_id,
            sentiment=sentiment_val
        ) 