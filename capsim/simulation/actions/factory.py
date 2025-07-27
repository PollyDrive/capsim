"""
Action Factory Pattern для CAPSIM v1.8

Предоставляет единый интерфейс для создания и выполнения действий агентов.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, TYPE_CHECKING
import json
from dataclasses import asdict
import types

if TYPE_CHECKING:
    from ...domain.person import Person
    from ...engine.simulation_engine import SimulationEngine

# Get logger
import logging
logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Типы действий агентов в v1.8."""
    POST = "Post"
    PURCHASE_L1 = "Purchase_L1"
    PURCHASE_L2 = "Purchase_L2"
    PURCHASE_L3 = "Purchase_L3"
    SELF_DEV = "SelfDev"


class BaseAction(ABC):
    """Базовый класс для всех действий агентов."""
    
    @abstractmethod
    def execute(self, person: "Person", engine: "SimulationEngine") -> None:
        """
        Выполнить действие.
        
        Args:
            person: Агент, выполняющий действие
            engine: Движок симуляции
        """
        pass
    
    @abstractmethod
    def can_execute(self, person: "Person", current_time: float) -> bool:
        """
        Проверить, может ли агент выполнить действие.
        
        Args:
            person: Агент
            current_time: Текущее время симуляции
            
        Returns:
            True если действие можно выполнить
        """
        pass


class PostAction(BaseAction):
    """Действие публикации поста."""
    
    def execute(self, person: "Person", engine: "SimulationEngine") -> None:
        """Выполнить публикацию поста."""
        from capsim.domain.events import PublishPostAction
        from capsim.common.metrics import record_action
        
        # ИСПРАВЛЕНИЕ: НЕ применяем эффекты сразу - только планируем событие
        # Эффекты будут применены при обработке события
        
        # Выбираем лучшую тему для поста
        best_topic = "ECONOMIC"  # Дефолт
        if hasattr(person, 'interests') and person.interests:
            best_topic = max(person.interests.keys(), key=lambda t: person.interests[t]).upper()
        
        # ИСПРАВЛЕНИЕ: Добавляем небольшую задержку для предотвращения зависания времени
        import random
        delay = random.uniform(0.1, 2.0)  # Случайная задержка от 0.1 до 2 минут
        
        # Создаем событие публикации поста
        post_event = PublishPostAction(
            agent_id=person.id,
            topic=best_topic,
            timestamp=engine.current_time + delay
        )
        
        # Добавляем событие в очередь
        engine.add_event(post_event, post_event.priority, post_event.timestamp)
        
        # Записываем метрики
        record_action("Post", "", person.profession)
        
        logger.info(json.dumps({
            "event": "post_action_scheduled",
            "agent_id": str(person.id),
            "profession": person.profession,
            "timestamp": engine.current_time,
            "scheduled_for": engine.current_time + delay
        }))
        
    def can_execute(self, person: "Person", current_time: float) -> bool:
        """Проверить возможность публикации поста."""
        return person.can_post(current_time)


class PurchaseL1Action(BaseAction):
    """Действие покупки уровня L1."""
    
    def execute(self, person: "Person", engine: "SimulationEngine") -> None:
        """Выполнить покупку L1."""
        from capsim.common.settings import action_config
        from capsim.common.metrics import record_action
        from capsim.domain.events import PurchaseAction
        
        # ИСПРАВЛЕНИЕ: НЕ применяем эффекты сразу - только планируем событие
        # Эффекты будут применены при обработке события
        
        # ИСПРАВЛЕНИЕ: Добавляем небольшую задержку для предотвращения зависания времени
        import random
        delay = random.uniform(0.1, 1.2)  # Случайная задержка от 0.1 до 1.2 минут
        
        # Создаем событие покупки L1
        purchase_event = PurchaseAction(
            agent_id=person.id,
            purchase_level="L1",
            timestamp=engine.current_time + delay
        )
        
        # Добавляем событие в очередь
        engine.add_event(purchase_event, purchase_event.priority, purchase_event.timestamp)
        
        # Записываем метрики
        record_action("Purchase", "L1", person.profession)
        
        logger.info(json.dumps({
            "event": "purchase_l1_scheduled",
            "agent_id": str(person.id),
            "profession": person.profession,
            "timestamp": engine.current_time,
            "scheduled_for": engine.current_time + delay
        }))
        
    def can_execute(self, person: "Person", current_time: float) -> bool:
        """Проверить возможность покупки L1."""
        return person.can_purchase(current_time, "L1")


class PurchaseL2Action(BaseAction):
    """Действие покупки уровня L2."""
    
    def execute(self, person: "Person", engine: "SimulationEngine") -> None:
        """Выполнить покупку L2."""
        from capsim.common.settings import action_config
        from capsim.common.metrics import record_action
        from capsim.domain.events import PurchaseAction
        
        # ИСПРАВЛЕНИЕ: НЕ применяем эффекты сразу - только планируем событие
        # Эффекты будут применены при обработке события
        
        # ИСПРАВЛЕНИЕ: Добавляем небольшую задержку для предотвращения зависания времени
        import random
        delay = random.uniform(0.1, 1.2)  # Случайная задержка от 0.1 до 1.2 минут
        
        # Создаем событие покупки L2
        purchase_event = PurchaseAction(
            agent_id=person.id,
            purchase_level="L2",
            timestamp=engine.current_time + delay
        )
        
        # Добавляем событие в очередь
        engine.add_event(purchase_event, purchase_event.priority, purchase_event.timestamp)
        
        # Записываем метрики
        record_action("Purchase", "L2", person.profession)
        
        logger.info(json.dumps({
            "event": "purchase_l2_scheduled",
            "agent_id": str(person.id),
            "profession": person.profession,
            "timestamp": engine.current_time,
            "scheduled_for": engine.current_time + delay
        }))
        
    def can_execute(self, person: "Person", current_time: float) -> bool:
        """Проверить возможность покупки L2."""
        return person.can_purchase(current_time, "L2")


class PurchaseL3Action(BaseAction):
    """Действие покупки уровня L3."""
    
    def execute(self, person: "Person", engine: "SimulationEngine") -> None:
        """Выполнить покупку L3."""
        from capsim.common.settings import action_config
        from capsim.common.metrics import record_action
        from capsim.domain.events import PurchaseAction
        
        # ИСПРАВЛЕНИЕ: НЕ применяем эффекты сразу - только планируем событие
        # Эффекты будут применены при обработке события
        
        # ИСПРАВЛЕНИЕ: Добавляем небольшую задержку для предотвращения зависания времени
        import random
        delay = random.uniform(0.1, 1.2)  # Случайная задержка от 0.1 до 1.2 минут
        
        # Создаем событие покупки L3
        purchase_event = PurchaseAction(
            agent_id=person.id,
            purchase_level="L3",
            timestamp=engine.current_time + delay
        )
        
        # Добавляем событие в очередь
        engine.add_event(purchase_event, purchase_event.priority, purchase_event.timestamp)
        
        # Записываем метрики
        record_action("Purchase", "L3", person.profession)
        
        logger.info(json.dumps({
            "event": "purchase_l3_scheduled",
            "agent_id": str(person.id),
            "profession": person.profession,
            "timestamp": engine.current_time,
            "scheduled_for": engine.current_time + delay
        }))
        
    def can_execute(self, person: "Person", current_time: float) -> bool:
        """Проверить возможность покупки L3."""
        return person.can_purchase(current_time, "L3")


class SelfDevAction(BaseAction):
    """Действие саморазвития."""
    
    def execute(self, person: "Person", engine: "SimulationEngine") -> None:
        """Выполнить саморазвитие."""
        from capsim.common.settings import action_config
        from capsim.common.metrics import record_action
        from capsim.domain.events import SelfDevAction as SelfDevEvent
        
        # ИСПРАВЛЕНИЕ: НЕ применяем эффекты сразу - только планируем событие
        # Эффекты будут применены при обработке события
        
        # ИСПРАВЛЕНИЕ: Добавляем небольшую задержку для предотвращения зависания времени
        import random
        delay = random.uniform(0.1, 1.5)  # Случайная задержка от 0.1 до 1.5 минут
        
        # Создаем событие саморазвития
        selfdev_event = SelfDevEvent(
            agent_id=person.id,
            timestamp=engine.current_time + delay
        )
        
        # Добавляем событие в очередь
        engine.add_event(selfdev_event, selfdev_event.priority, selfdev_event.timestamp)
        
        # Записываем метрики
        record_action("SelfDev", "", person.profession)
        
        logger.info(json.dumps({
            "event": "selfdev_action_scheduled",
            "agent_id": str(person.id),
            "profession": person.profession,
            "timestamp": engine.current_time,
            "scheduled_for": engine.current_time + delay
        }))
        
    def can_execute(self, person: "Person", current_time: float) -> bool:
        """Проверить возможность саморазвития."""
        return person.can_self_dev(current_time)


# Factory mapping for ready-to-use action objects (stateless)
ACTION_FACTORY = {
    "Post": PostAction,
    "Purchase_L1": PurchaseL1Action,
    "Purchase_L2": PurchaseL2Action,
    "Purchase_L3": PurchaseL3Action,
    "SelfDev": SelfDevAction
}

# Define dummy action_config for tests
action_config = types.SimpleNamespace(cooldowns={"POST_MIN":60,"SELF_DEV_MIN":120}, limits={"MAX_PURCHASES_DAY":10}, effects={"PURCHASE":{"L1":{"financial_capability":1.0},"L2":{"financial_capability":2.0},"L3":{"financial_capability":3.0}}}) 