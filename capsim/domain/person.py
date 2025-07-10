"""
Person - класс агента симуляции с атрибутами и поведением.
"""

from typing import Dict, Optional, TYPE_CHECKING
from uuid import UUID, uuid4
from datetime import datetime, date
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
    
    # Personal information (REQUIRED for DB)
    first_name: str = ""
    last_name: str = ""
    gender: str = ""
    date_of_birth: Optional[date] = None
    
    # Dynamic attributes (0.0-5.0 scale)
    financial_capability: float = 0.0
    trend_receptivity: float = 0.0
    social_status: float = 0.0
    energy_level: float = 5.0  # Унифицировано с DB: дефолт 5.0
    
    # Time and interaction tracking
    time_budget: float = 2.5  # Унифицировано с DB: дефолт 2.5, NUMERIC(2,1)
    exposure_history: Dict[str, datetime] = field(default_factory=dict)
    interests: Dict[str, float] = field(default_factory=dict)
    
    # v1.8: Action tracking and cooldowns
    purchases_today: int = 0  # Daily purchase counter
    last_post_ts: Optional[float] = None  # Last post timestamp
    last_selfdev_ts: Optional[float] = None  # Last self-development timestamp
    last_purchase_ts: Dict[str, Optional[float]] = field(default_factory=dict)  # {L1: timestamp, L2: timestamp, L3: timestamp}
    
    # Simulation metadata
    simulation_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Backward compatibility alias expected by old tests
    @property
    def person_id(self) -> UUID:  # noqa: D401
        return self.id
    
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
        if not self.can_perform_action("any", current_time=context.current_time):
            return None
            
        # Получаем threshold из ENV (снижен для более активных агентов)
        threshold = float(os.getenv("DECIDE_SCORE_THRESHOLD", "0.15"))  # Снижен с 0.4 до 0.15
        
        # Проверяем доступные действия и их приоритеты
        possible_actions = ["PublishPostAction"]
        
        for action_type in possible_actions:
            if not self.can_perform_action(action_type, current_time=context.current_time):
                continue
                
            # Выбираем тему на основе интересов и склонностей
            best_topic = self._select_best_topic(context)
            if not best_topic:
                continue
                
            interest_score = self.get_interest_in_topic(best_topic)
            affinity_score = self.get_affinity_for_topic(best_topic)
            
            # Формула принятия решения (улучшенная)
            score = (
                0.4 * interest_score / 5.0 +        # Интерес к теме
                0.3 * self.social_status / 5.0 +    # Социальный статус
                0.2 * self.trend_receptivity / 5.0 + # Восприимчивость к трендам
                0.1 * random.random()                # Случайность
            ) * (affinity_score / 5.0) + 0.1         # Бонус за склонность + базовый бонус
            
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
                current_value = float(getattr(self, attribute))  # Конвертируем Decimal в float
                
                # Применяем ограничения по диапазону
                if attribute in ["energy_level", "financial_capability", 
                               "trend_receptivity", "social_status"]:
                    new_value = max(0.0, min(5.0, current_value + delta))
                elif attribute == "time_budget":
                    # Унифицировано: float с округлением до 0.5
                    raw_value = max(0.0, min(5.0, current_value + delta))
                    new_value = float(round(raw_value * 2) / 2)  # Округление до 0.5, принудительно float
                else:
                    new_value = current_value + delta
                    
                setattr(self, attribute, new_value)
        
    def can_perform_action(self, action_type: str, current_time: float | None = None) -> bool:
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
                self.energy_level >= 0.5 and
                self.time_budget >= 0.5 and  # Снижено с 1 до 0.5
                self.trend_receptivity > 0
            )
            
        return False
    
    def apply_effects(self, effects: Dict[str, float]) -> None:
        """
        Применяет эффекты действия к атрибутам агента.
        
        Args:
            effects: Словарь эффектов {attribute: delta}
        """
        for attribute, delta in effects.items():
            if hasattr(self, attribute):
                current_value = float(getattr(self, attribute))  # Конвертируем Decimal в float
                
                # Применяем ограничения по диапазону
                if attribute in ["energy_level", "financial_capability", 
                               "trend_receptivity", "social_status"]:
                    new_value = max(0.0, min(5.0, current_value + delta))
                elif attribute == "time_budget":
                    # Унифицировано: float с округлением до 0.5
                    raw_value = max(0.0, min(5.0, current_value + delta))
                    new_value = float(round(raw_value * 2) / 2)  # Округление до 0.5
                else:
                    new_value = current_value + delta
                    
                setattr(self, attribute, new_value)
    
    def can_post(self, current_time: float) -> bool:
        """Проверяет возможность публикации поста (cooldown + ресурсы)."""
        from capsim.common.settings import action_config

        # Проверка cooldown (сокращенный cooldown)
        if self.last_post_ts is not None:
            cooldown_passed = current_time - self.last_post_ts >= action_config.cooldowns["POST_MIN"] / 2  # Половина cooldown
            if not cooldown_passed:
                return False
        
        # Более мягкие проверки ресурсов
        return (
            self.energy_level >= 0.3 and
            self.time_budget >= 0.15
        )
    
    def can_self_dev(self, current_time: float) -> bool:
        """Проверяет возможность саморазвития (cooldown + ресурсы)."""
        from capsim.common.settings import action_config

        # Проверка cooldown (сокращенный)
        if self.last_selfdev_ts is not None:
            cooldown_passed = current_time - self.last_selfdev_ts >= action_config.cooldowns["SELF_DEV_MIN"] / 2  # Половина cooldown
            if not cooldown_passed:
                return False
        
        # Более мягкие проверки ресурсов
        return self.time_budget >= 0.8  # Снижено с 1.0
    
    def can_purchase(self, current_time: float, level: str) -> bool:
        """Проверяет возможность покупки определенного уровня."""
        from capsim.common.settings import action_config

        # Проверка дневного лимита (увеличенного)
        max_purchases = action_config.limits["MAX_PURCHASES_DAY"] * 2  # Удваиваем лимит
        if self.purchases_today >= max_purchases:
            return False
        
        # ИСПРАВЛЕНИЕ: Снижаем финансовые требования для покупок
        cost_range = action_config.effects["PURCHASE"][level]["cost_range"]
        min_cost = cost_range[0]  # Используем минимальную стоимость
        required_capability = min_cost * 0.5  # Требуем только 50% от минимальной стоимости
        return self.financial_capability >= required_capability
        
    def get_interest_in_topic(self, topic: str) -> float:
        """
        Возвращает уровень интереса к теме.
        
        Args:
            topic: Тема для проверки (Economic, Health, etc.)
            
        Returns:
            Уровень интереса (0.0-5.0)
        """
        # Используем централизованный маппинг
        from capsim.common.topic_mapping import topic_to_interest_category
        
        try:
            interest_category = topic_to_interest_category(topic)
        except KeyError:
            interest_category = "Economics"  # Fallback
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
    def create_random_agent(
        cls,
        profession: str,
        simulation_id: UUID,
        ranges_map: Optional[Dict[str, Dict[str, tuple]]] = None,
    ) -> "Person":
        """
        Создает случайного агента с заданной профессией СТРОГО СОГЛАСНО ТЗ.
        
        Args:
            profession: Профессия агента (один из 12 из ТЗ)
            simulation_id: ID симуляции
            ranges_map: Карта диапазонов атрибутов, загруженная из БД (agents_profession)
            
        Returns:
            Новый экземпляр Person с русскими именами и правильными атрибутами
        """
        # РУССКИЕ ИМЕНА согласно полу
        russian_names = {
            "male": {
                "first_names": ["Александр", "Алексей", "Андрей", "Антон", "Артём", "Владимир", "Дмитрий", 
                               "Евгений", "Игорь", "Иван", "Максим", "Михаил", "Николай", "Павел", "Сергей"],
                "last_names": ["Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов", "Попов", "Волков", 
                              "Соколов", "Лебедев", "Козлов", "Новиков", "Морозов", "Борисов", "Романов"]
            },
            "female": {
                "first_names": ["Анна", "Елена", "Мария", "Наталья", "Ольга", "Светлана", "Татьяна", 
                               "Ирина", "Екатерина", "Юлия", "Людмила", "Галина", "Марина", "Дарья", "Алла"],
                "last_names": ["Иванова", "Петрова", "Сидорова", "Смирнова", "Кузнецова", "Попова", "Волкова", 
                              "Соколова", "Лебедева", "Козлова", "Новикова", "Морозова", "Борисова", "Романова"]
            }
        }
        
        # Генерируем пол и соответствующие имена
        gender = random.choice(["male", "female"])
        first_name = random.choice(russian_names[gender]["first_names"])
        last_name = random.choice(russian_names[gender]["last_names"])
        
        # Генерируем дату рождения (возраст 18-65 лет согласно ТЗ)
        current_year = datetime.now().year
        birth_year = random.randint(current_year - 65, current_year - 18)
        birth_month = random.randint(1, 12)
        birth_day = random.randint(1, 28)  # Безопасный день для всех месяцев
        birth_date = date(birth_year, birth_month, birth_day)

        # Берём диапазоны из БД (agents_profession) если переданы
        if ranges_map is None or profession not in ranges_map:
            raise ValueError(
                f"Диапазоны для профессии '{profession}' не найдены. Убедитесь, что таблица agents_profession заполнена."
            )
        ranges = ranges_map[profession]

        # ИНТЕРЕСЫ ПО ПРОФЕССИЯМ из ТЗ (таблица интересов)
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
        
        # Генерируем интересы согласно профессии
        profession_interests = interest_ranges[profession]
        base_interests = {}
        for interest_name, (min_val, max_val) in profession_interests.items():
            base_interests[interest_name] = round(random.uniform(min_val, max_val), 3)
        
        # Генерируем атрибуты с округлением до 3 знаков
        return cls(
            profession=profession,
            simulation_id=simulation_id,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=birth_date,
            financial_capability=round(random.uniform(*ranges["financial_capability"]), 3),
            social_status=round(random.uniform(*ranges["social_status"]), 3),
            trend_receptivity=round(random.uniform(*ranges["trend_receptivity"]), 3),
            energy_level=round(random.uniform(*ranges["energy_level"]), 3),
            time_budget=float(round(random.uniform(*ranges["time_budget"]) * 2) / 2),  # Округление до 0.5, принудительно float
            interests=base_interests
        ) 

    def decide_action_v18(self, trend, current_time: float):
        """
        v1.8 алгоритм принятия решений с новыми действиями.
        
        Args:
            trend: Текущий тренд
            current_time: Текущее время симуляции
            
        Returns:
            Объект Action или None
        """
        import random
        from capsim.simulation.actions.factory import ACTION_FACTORY
        
        try:
            from capsim.common.settings import action_config
        except ImportError:
            # Fallback если config недоступен
            class FallbackConfig:
                shop_weights = {"Developer": 1.0, "Teacher": 0.9, "Worker": 0.8}
            action_config = FallbackConfig()
        
        actions = []
        
        # POST logic - более высокие базовые scores
        if self.can_post(current_time):
            if trend and hasattr(trend, 'calculate_current_virality'):
                post_score = (
                    trend.calculate_current_virality() * self.trend_receptivity / 15  # Уменьшено с 25 до 15
                    * (1 + self.social_status / 8)  # Увеличено влияние social_status
                )
            else:
                post_score = 0.4  # Снижен с 0.8 до 0.4 для баланса с покупками
            actions.append(("Post", post_score))
        
        # PURCHASE logic (L1/L2/L3) - более активные покупки
        for level in ["L1", "L2", "L3"]:
            if self.can_purchase(current_time, level):
                base_score = 0.8 * getattr(action_config, 'shop_weights', {}).get(self.profession, 1.0)  # Увеличено с 0.6 до 0.8
                # Добавляем рандомность для разнообразия
                base_score += random.random() * 0.6  # Увеличено с 0.4 до 0.6
                if trend and hasattr(trend, 'topic') and trend.topic == "Economic":
                    base_score *= 1.5  # Увеличено с 1.2 до 1.5
                actions.append((f"Purchase_{level}", base_score))
        
        # SELF_DEV logic - больше мотивации для развития
        if self.can_self_dev(current_time):
            score = max(0.4, 0.8 - self.energy_level / 5)  # Снижена максимальная мотивация
            actions.append(("SelfDev", score))
        
        # Weighted selection
        if not actions or not any(s for _, s in actions):
            return None
            
        names = [n for n, _ in actions]
        weights = [s for _, s in actions]
        
        # Если все веса нулевые, возвращаем None
        if sum(weights) == 0:
            return None
            
        selected = random.choices(names, weights=weights)[0]
        
        # Логируем выбор действия для отладки
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Agent {self.id} ({self.profession}) chose action: {selected} from {names} with weights {weights}")
        
        # Возвращаем имя действия как строку
        return selected 