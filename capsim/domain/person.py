"""
Person - класс агента симуляции с атрибутами и поведением.
"""

from typing import Dict, Optional, TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import datetime
from dataclasses import dataclass, field
import random
import os

if TYPE_CHECKING:
    from ..engine.simulation_engine import SimulationContext


@dataclass
class Person:
    """
    Агент симуляции с динамическими атрибутами и поведением.
    
    Represents an agent with:
    - 12 profession types (ShopClerk, Worker, Developer, etc.)
    - Dynamic attributes (energy, social status, trend receptivity)
    - Social interaction capabilities
    """
    
    # Core attributes
    id: UUID = field(default_factory=uuid4)
    profession: str = ""
    
    # Dynamic attributes (0.0-5.0 scale)
    financial_capability: float = 0.0
    trend_receptivity: float = 0.0
    social_status: float = 0.0
    energy_level: float = 5.0
    
    # Time and interaction tracking
    time_budget: int = 0  # 0-5 actions per day
    exposure_history: Dict[str, datetime] = field(default_factory=dict)
    interests: Dict[str, float] = field(default_factory=dict)
    
    # Simulation metadata
    simulation_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def decide_action(self, context: "SimulationContext") -> Optional[str]:
        """
        Принимает решение о следующем действии агента.
        
        Использует формулу:
        score = 0.5 * interest + 0.3 * social_status/5 + 0.2 * random(0-1)
        
        Args:
            context: Контекст симуляции с доступными трендами
            
        Returns:
            Тип действия или None если агент не активен
        """
        if not self.can_perform_action("any"):
            return None
            
        # Получаем threshold из ENV
        threshold = float(os.getenv("DECIDE_SCORE_THRESHOLD", "0.25"))
        
        # Проверяем доступные действия и их приоритеты
        possible_actions = ["PublishPostAction"]
        
        for action_type in possible_actions:
            if not self.can_perform_action(action_type):
                continue
                
            # Выбираем тему на основе интересов и склонностей
            best_topic = self._select_best_topic(context)
            if not best_topic:
                continue
                
            interest_score = self.get_interest_in_topic(best_topic)
            affinity_score = self.get_affinity_for_topic(best_topic)
            
            # Формула принятия решения
            score = (
                0.5 * interest_score / 5.0 +
                0.3 * self.social_status / 5.0 +
                0.2 * random.random()
            ) * affinity_score / 5.0
            
            if score >= threshold:
                return action_type
                
        return None
        
    def _select_best_topic(self, context: "SimulationContext") -> Optional[str]:
        """Выбирает лучшую тему для поста на основе интересов."""
        if not self.interests:
            return "ECONOMIC"  # Дефолтная тема
            
        # Находим тему с наивысшим интересом
        best_topic = max(self.interests.keys(), key=lambda t: self.interests[t])
        return best_topic.upper()
        
    def update_state(self, changes: Dict[str, float]) -> None:
        """
        Обновляет состояние агента на основе внешних воздействий.
        
        Args:
            changes: Словарь изменений {attribute: delta}
        """
        for attribute, delta in changes.items():
            if hasattr(self, attribute):
                current_value = getattr(self, attribute)
                
                # Применяем ограничения по диапазону
                if attribute in ["energy_level", "financial_capability", 
                               "trend_receptivity", "social_status"]:
                    new_value = max(0.0, min(5.0, current_value + delta))
                elif attribute == "time_budget":
                    new_value = max(0, min(5, int(current_value + delta)))
                else:
                    new_value = current_value + delta
                    
                setattr(self, attribute, new_value)
        
    def can_perform_action(self, action_type: str) -> bool:
        """
        Проверяет возможность выполнения действия.
        
        Args:
            action_type: Тип действия для проверки
            
        Returns:
            True если действие возможно
        """
        # Базовые проверки для любого действия
        if action_type == "any":
            return self.energy_level > 0 and self.time_budget > 0
            
        # Проверки для конкретных действий
        if action_type == "PublishPostAction":
            return (
                self.energy_level >= 1.0 and 
                self.time_budget >= 1 and
                self.trend_receptivity > 0
            )
            
        return False
        
    def get_interest_in_topic(self, topic: str) -> float:
        """
        Возвращает уровень интереса к теме.
        
        Args:
            topic: Тема для проверки (Economic, Health, etc.)
            
        Returns:
            Уровень интереса (0.0-5.0)
        """
        # Маппинг тем к категориям интересов
        topic_mapping = {
            "ECONOMIC": "Economics",
            "HEALTH": "Wellbeing", 
            "SPIRITUAL": "Religion",
            "CONSPIRACY": "Politics",
            "SCIENCE": "Education",
            "CULTURE": "Entertainment",
            "SPORT": "Entertainment"
        }
        
        interest_category = topic_mapping.get(topic, "Economics")
        return self.interests.get(interest_category, 2.5)  # Дефолт средний интерес
        
    def get_affinity_for_topic(self, topic: str) -> float:
        """
        Возвращает коэффициент склонности к теме на основе профессии.
        
        Args:
            topic: Тема (Economic, Health, Spiritual, etc.)
            
        Returns:
            Коэффициент склонности (1-5)
        """
        # Affinity map из ТЗ - матрица соответствия профессий к темам трендов
        base_affinities = {
            "ShopClerk": {"ECONOMIC": 3, "HEALTH": 2, "SPIRITUAL": 2, "CONSPIRACY": 3, "SCIENCE": 1, "CULTURE": 2, "SPORT": 2},
            "Worker": {"ECONOMIC": 3, "HEALTH": 3, "SPIRITUAL": 2, "CONSPIRACY": 3, "SCIENCE": 1, "CULTURE": 2, "SPORT": 3},
            "Developer": {"ECONOMIC": 3, "HEALTH": 2, "SPIRITUAL": 1, "CONSPIRACY": 2, "SCIENCE": 5, "CULTURE": 3, "SPORT": 2},
            "Politician": {"ECONOMIC": 5, "HEALTH": 4, "SPIRITUAL": 2, "CONSPIRACY": 2, "SCIENCE": 3, "CULTURE": 3, "SPORT": 2},
            "Blogger": {"ECONOMIC": 4, "HEALTH": 4, "SPIRITUAL": 3, "CONSPIRACY": 4, "SCIENCE": 3, "CULTURE": 5, "SPORT": 4},
            "Businessman": {"ECONOMIC": 5, "HEALTH": 3, "SPIRITUAL": 2, "CONSPIRACY": 2, "SCIENCE": 3, "CULTURE": 3, "SPORT": 3},
            "Doctor": {"ECONOMIC": 3, "HEALTH": 5, "SPIRITUAL": 2, "CONSPIRACY": 1, "SCIENCE": 5, "CULTURE": 2, "SPORT": 3},
            "Teacher": {"ECONOMIC": 3, "HEALTH": 4, "SPIRITUAL": 3, "CONSPIRACY": 2, "SCIENCE": 4, "CULTURE": 4, "SPORT": 3},
            "Unemployed": {"ECONOMIC": 4, "HEALTH": 3, "SPIRITUAL": 3, "CONSPIRACY": 4, "SCIENCE": 2, "CULTURE": 3, "SPORT": 3},
            "Artist": {"ECONOMIC": 2, "HEALTH": 2, "SPIRITUAL": 4, "CONSPIRACY": 2, "SCIENCE": 2, "CULTURE": 5, "SPORT": 2},
            "SpiritualMentor": {"ECONOMIC": 2, "HEALTH": 3, "SPIRITUAL": 5, "CONSPIRACY": 3, "SCIENCE": 2, "CULTURE": 3, "SPORT": 2},
            "Philosopher": {"ECONOMIC": 3, "HEALTH": 3, "SPIRITUAL": 5, "CONSPIRACY": 3, "SCIENCE": 4, "CULTURE": 4, "SPORT": 1}
        }
        
        profession_affinities = base_affinities.get(self.profession, {})
        return profession_affinities.get(topic, 2.5)  # Дефолт средняя склонность
        
    @classmethod
    def create_random_agent(cls, profession: str, simulation_id: UUID) -> "Person":
        """
        Создает случайного агента с заданной профессией.
        
        Args:
            profession: Профессия агента
            simulation_id: ID симуляции
            
        Returns:
            Новый экземпляр Person
        """
        # Диапазоны атрибутов по профессиям из ТЗ (таблица 2.4)
        profession_ranges = {
            "ShopClerk": {
                "financial_capability": (2, 4), "trend_receptivity": (1, 3), 
                "social_status": (1, 3), "time_budget": (3, 5)
            },
            "Worker": {
                "financial_capability": (2, 4), "trend_receptivity": (1, 3),
                "social_status": (1, 2), "time_budget": (3, 5)
            },
            "Developer": {
                "financial_capability": (3, 5), "trend_receptivity": (3, 5),
                "social_status": (2, 4), "time_budget": (2, 4)
            },
            "Politician": {
                "financial_capability": (3, 5), "trend_receptivity": (3, 5),
                "social_status": (4, 5), "time_budget": (2, 4)
            },
            "Blogger": {
                "financial_capability": (2, 4), "trend_receptivity": (4, 5),
                "social_status": (3, 5), "time_budget": (3, 5)
            },
            "Businessman": {
                "financial_capability": (4, 5), "trend_receptivity": (2, 4),
                "social_status": (4, 5), "time_budget": (2, 4)
            },
            "SpiritualMentor": {
                "financial_capability": (1, 3), "trend_receptivity": (2, 5),
                "social_status": (2, 4), "time_budget": (2, 4)
            },
            "Philosopher": {
                "financial_capability": (1, 3), "trend_receptivity": (1, 3),
                "social_status": (1, 3), "time_budget": (2, 4)
            },
            "Unemployed": {
                "financial_capability": (1, 2), "trend_receptivity": (3, 5),
                "social_status": (1, 2), "time_budget": (3, 5)
            },
            "Teacher": {
                "financial_capability": (1, 3), "trend_receptivity": (1, 3),
                "social_status": (2, 4), "time_budget": (2, 4)
            },
            "Artist": {
                "financial_capability": (1, 3), "trend_receptivity": (2, 4),
                "social_status": (2, 4), "time_budget": (3, 5)
            },
            "Doctor": {
                "financial_capability": (2, 4), "trend_receptivity": (1, 3),
                "social_status": (3, 5), "time_budget": (1, 2)
            }
        }
        
        ranges = profession_ranges.get(profession, profession_ranges["Worker"])
        
        # Генерируем интересы согласно ТЗ (6 категорий интересов)
        interest_ranges = {
            "ShopClerk": {
                "Economics": (4.59, 5.0), "Wellbeing": (0.74, 1.34), "Spirituality": (0.64, 1.24),
                "Knowledge": (1.15, 1.75), "Creativity": (1.93, 2.53), "Society": (2.70, 3.30)
            },
            "Worker": {
                "Economics": (3.97, 4.57), "Wellbeing": (1.05, 1.65), "Spirituality": (1.86, 2.46),
                "Knowledge": (1.83, 2.43), "Creativity": (0.87, 1.47), "Society": (0.69, 1.29)
            },
            "Developer": {
                "Economics": (1.82, 2.42), "Wellbeing": (1.15, 1.75), "Spirituality": (0.72, 1.32),
                "Knowledge": (4.05, 4.65), "Creativity": (2.31, 2.91), "Society": (1.59, 2.19)
            },
            "Politician": {
                "Economics": (0.51, 1.11), "Wellbeing": (1.63, 2.23), "Spirituality": (0.32, 0.92),
                "Knowledge": (2.07, 2.67), "Creativity": (1.73, 2.33), "Society": (3.57, 4.17)
            },
            "Blogger": {
                "Economics": (1.32, 1.92), "Wellbeing": (1.01, 1.61), "Spirituality": (1.20, 1.80),
                "Knowledge": (1.23, 1.83), "Creativity": (3.27, 3.87), "Society": (2.43, 3.03)
            },
            "Businessman": {
                "Economics": (4.01, 4.61), "Wellbeing": (0.76, 1.36), "Spirituality": (0.91, 1.51),
                "Knowledge": (1.35, 1.95), "Creativity": (2.04, 2.64), "Society": (2.42, 3.02)
            },
            "SpiritualMentor": {
                "Economics": (0.62, 1.22), "Wellbeing": (2.04, 2.64), "Spirituality": (3.86, 4.46),
                "Knowledge": (2.11, 2.71), "Creativity": (2.12, 2.72), "Society": (1.95, 2.55)
            },
            "Philosopher": {
                "Economics": (1.06, 1.66), "Wellbeing": (2.22, 2.82), "Spirituality": (3.71, 4.31),
                "Knowledge": (3.01, 3.61), "Creativity": (2.21, 2.81), "Society": (1.80, 2.40)
            },
            "Unemployed": {
                "Economics": (0.72, 1.32), "Wellbeing": (1.38, 1.98), "Spirituality": (3.69, 4.29),
                "Knowledge": (2.15, 2.75), "Creativity": (2.33, 2.93), "Society": (2.42, 3.02)
            },
            "Teacher": {
                "Economics": (1.32, 1.92), "Wellbeing": (2.16, 2.76), "Spirituality": (1.40, 2.00),
                "Knowledge": (3.61, 4.21), "Creativity": (1.91, 2.51), "Society": (2.24, 2.84)
            },
            "Artist": {
                "Economics": (0.86, 1.46), "Wellbeing": (0.91, 1.51), "Spirituality": (2.01, 2.61),
                "Knowledge": (1.82, 2.42), "Creativity": (3.72, 4.32), "Society": (1.94, 2.54)
            },
            "Doctor": {
                "Economics": (1.02, 1.62), "Wellbeing": (3.97, 4.57), "Spirituality": (1.37, 1.97),
                "Knowledge": (2.01, 2.61), "Creativity": (1.58, 2.18), "Society": (2.45, 3.05)
            }
        }
        
        # Получаем диапазоны интересов для профессии
        profession_interests = interest_ranges.get(profession, interest_ranges["Worker"])
        base_interests = {}
        for interest_name, (min_val, max_val) in profession_interests.items():
            base_interests[interest_name] = round(random.uniform(min_val, max_val), 2)
        
        # Добавляем energy_level диапазоны из ТЗ
        energy_ranges = {
            "ShopClerk": (2, 5), "Worker": (2, 5), "Developer": (2, 5), "Politician": (2, 4),
            "Blogger": (2, 5), "Businessman": (2, 5), "SpiritualMentor": (3, 5), "Philosopher": (2, 4),
            "Unemployed": (3, 5), "Teacher": (1, 3), "Artist": (4, 5), "Doctor": (2, 4)
        }
        
        energy_range = energy_ranges.get(profession, (2, 5))
        
        return cls(
            profession=profession,
            simulation_id=simulation_id,
            financial_capability=random.uniform(*ranges["financial_capability"]),
            social_status=random.uniform(*ranges["social_status"]),
            trend_receptivity=random.uniform(*ranges["trend_receptivity"]),
            energy_level=random.uniform(*energy_range),
            time_budget=random.randint(*ranges["time_budget"]),
            interests=base_interests
        ) 