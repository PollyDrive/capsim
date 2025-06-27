"""
Events - классы событий для дискретно-событийной симуляции CAPSIM.
"""

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4
from dataclasses import dataclass
import json
import logging

if TYPE_CHECKING:
    from ..engine.simulation_engine import SimulationEngine

logger = logging.getLogger(__name__)


class EventPriority:
    """Константы приоритетов событий."""
    LAW = 1
    WEATHER = 2
    TREND = 3
    AGENT_ACTION = 4
    SYSTEM = 5


@dataclass
class BaseEvent(ABC):
    """
    Базовый класс для всех событий симуляции.
    """
    event_id: UUID
    priority: int
    timestamp: float  # simulation time in minutes
    timestamp_real: Optional[float] = None  # real wall-clock timestamp for realtime mode
    
    def __init__(self, priority: int, timestamp: float, timestamp_real: Optional[float] = None):
        self.event_id = uuid4()
        self.priority = priority
        self.timestamp = timestamp
        self.timestamp_real = timestamp_real
    
    @abstractmethod
    def process(self, engine: "SimulationEngine") -> None:
        """
        Обрабатывает событие в контексте симуляции.
        
        Args:
            engine: SimulationEngine instance
        """
        pass


class PublishPostAction(BaseEvent):
    """Событие публикации поста агентом."""
    
    def __init__(self, agent_id: UUID, topic: str, timestamp: float, trigger_trend_id: Optional[UUID] = None):
        super().__init__(EventPriority.AGENT_ACTION, timestamp)
        self.agent_id = agent_id
        self.topic = topic
        self.trigger_trend_id = trigger_trend_id
        
    def process(self, engine: "SimulationEngine") -> None:
        """
        Обрабатывает публикацию поста.
        
        1. Проверяет ограничения агента (энергия, время)
        2. Создает новый тренд через TrendProcessor
        3. Обновляет состояние агента
        4. Запускает распространение влияния
        """
        # Найти агента
        agent = None
        for person in engine.agents:
            if person.id == self.agent_id:
                agent = person
                break
                
        if not agent:
            logger.warning(json.dumps({
                "event": "agent_not_found",
                "agent_id": str(self.agent_id),
                "timestamp": self.timestamp
            }))
            return
            
        # Проверить возможность действия
        if not agent.can_perform_action("PublishPostAction"):
            logger.info(json.dumps({
                "event": "action_rejected",
                "agent_id": str(self.agent_id),
                "reason": "insufficient_resources",
                "energy": agent.energy_level,
                "time_budget": agent.time_budget
            }))
            return
            
        # Создать новый тренд
        from ..domain.trend import Trend, CoverageLevel
        
        # ИСПРАВЛЕНИЕ: Более реалистичная базовая виральность
        # Базовая виральность зависит от социального статуса агента и его экспертизы в теме
        topic_affinity = agent.get_affinity_for_topic(self.topic)
        expertise_bonus = (topic_affinity / 5.0) * 0.5  # Бонус до 0.5
        
        base_virality = min(3.0,  # Максимум 3.0 для базовой виральности
            (agent.social_status * 0.4) +  # Социальный статус влияет на виральность
            (agent.trend_receptivity * 0.3) +  # Восприимчивость к трендам
            expertise_bonus +  # Бонус за экспертизу в теме
            0.5  # Базовый минимум
        )
        
        # Уровень охвата зависит от финансовых возможностей
        if agent.financial_capability >= 4.0:
            coverage = CoverageLevel.HIGH.value
        elif agent.social_status < 1.5:  # ИСПРАВЛЕНИЕ: Low только при низком социальном статусе
            coverage = CoverageLevel.LOW.value
        else:
            coverage = CoverageLevel.MIDDLE.value  # ИСПРАВЛЕНИЕ: Middle по умолчанию
            
        # ИСПРАВЛЕНИЕ: Проверяем является ли это ответом на существующий тренд
        parent_trend_id = None
        
        # Проверяем есть ли trigger_trend_id (это ответный пост)
        if self.trigger_trend_id:  # ИСПРАВЛЕНИЕ: убираем hasattr, проверяем значение
            parent_trend_id = self.trigger_trend_id
        else:
            # Ищем последний активный тренд той же темы (возможный parent)
            # Только если это НЕ seed пост (т.е. есть активные тренды с interactions > 0)
            active_trends_same_topic = [
                trend for trend in engine.active_trends.values()
                if (trend.topic == self.topic and 
                    trend.originator_id != agent.id and
                    trend.total_interactions > 0)
            ]
            
            if active_trends_same_topic:
                # Это ответный пост - берем самый активный тренд как родительский
                parent_trend = max(active_trends_same_topic, key=lambda t: t.total_interactions)
                parent_trend_id = parent_trend.trend_id
        
        new_trend = Trend.create_from_action(
            topic=self.topic,
            originator_id=self.agent_id,
            simulation_id=agent.simulation_id,
            base_virality=base_virality,
            coverage_level=coverage,
            parent_id=parent_trend_id  # ИСПРАВЛЕНИЕ: Используем parent_trend_id
        )
        
        # Добавить тренд в активные тренды
        engine.active_trends[str(new_trend.trend_id)] = new_trend
        
        # ИСПРАВЛЕНИЕ: Сохранить тренд в базу данных
        engine.add_to_batch_update({
            "type": "trend_creation",
            "trend_id": new_trend.trend_id,
            "simulation_id": new_trend.simulation_id,
            "topic": new_trend.topic,
            "originator_id": new_trend.originator_id,
            "base_virality_score": new_trend.base_virality_score,
            "coverage_level": new_trend.coverage_level,
            "timestamp": self.timestamp
        })
        
        # Обновить состояние агента
        agent.update_state({
            "energy_level": -0.1,  # ИСПРАВЛЕНИЕ: увеличиваем трату энергии до 0.1
            "time_budget": -0.1,     # Тратим время
            "social_status": 0.1   # Небольшой прирост статуса от публикации
        })
        
        # Добавить в batch обновления (только состояние, без истории)
        engine.add_to_batch_update({
            "type": "person_state",
            "id": self.agent_id,
            "energy_level": agent.energy_level,
            "time_budget": agent.time_budget,
            "social_status": agent.social_status,
            "reason": "PublishPostAction",
            "timestamp": self.timestamp
        })
        
        # КРИТИЧЕСКИ ВАЖНО: Пометить что нужен принудительный commit для сохранения тренда
        # Это предотвращает FK нарушения при создании TrendInfluenceEvent
        engine._force_commit_after_this_event = True
        
        # Запланировать распространение влияния тренда
        influence_event = TrendInfluenceEvent(
            timestamp=self.timestamp + 5.0,  # Через 5 минут
            trend_id=new_trend.trend_id
        )
        engine.add_event(influence_event, EventPriority.TREND, influence_event.timestamp)
        
        logger.info(json.dumps({
            "event": "post_published",
            "agent_id": str(self.agent_id),
            "trend_id": str(new_trend.trend_id),
            "topic": self.topic,
            "virality": base_virality,
            "coverage": coverage,
            "timestamp": self.timestamp
        }))


class EnergyRecoveryEvent(BaseEvent):
    """Системное событие восстановления энергии агентов."""
    
    def __init__(self, timestamp: float):
        super().__init__(EventPriority.SYSTEM, timestamp)
        
    def process(self, engine: "SimulationEngine") -> None:
        """
        Восстанавливает энергию всех агентов.
        
        Логика:
        - Если energy_level < 3.0: устанавливается 5.0
        - Иначе: добавляется 2.0 (максимум 5.0)
        """
        recovery_count = 0
        batch_updates = []
        
        for agent in engine.agents:
            old_energy = agent.energy_level
            
            if agent.energy_level < 3.0:
                agent.energy_level = 5.0
            else:
                agent.energy_level = min(5.0, agent.energy_level + 2.0)
                
            if agent.energy_level != old_energy:
                recovery_count += 1
                batch_updates.append({
                    "type": "person_state", 
                    "id": agent.id,
                    "energy_level": agent.energy_level,
                    "reason": "EnergyRecovery",
                    "timestamp": self.timestamp
                })
                
                batch_updates.append({
                    "type": "attribute_history",
                    "simulation_id": agent.simulation_id,
                    "person_id": agent.id,
                    "attribute_name": "energy_level",
                    "old_value": old_energy,
                    "new_value": agent.energy_level,
                    "delta": agent.energy_level - old_energy,
                    "reason": "EnergyRecovery",
                    "change_timestamp": self.timestamp
                })
        
        # Добавить все обновления в batch
        for update in batch_updates:
            engine.add_to_batch_update(update)
            
        # Запланировать следующее восстановление энергии (каждые 6 часов = 360 минут)
        next_recovery = EnergyRecoveryEvent(self.timestamp + 360.0)
        engine.add_event(next_recovery, EventPriority.SYSTEM, next_recovery.timestamp)
        
        logger.info(json.dumps({
            "event": "energy_recovery_completed",
            "agents_affected": recovery_count,
            "total_agents": len(engine.agents),
            "next_recovery_at": self.timestamp + 360.0,
            "timestamp": self.timestamp
        }))


class DailyResetEvent(BaseEvent):
    """Системное событие сброса временных бюджетов."""
    
    def __init__(self, timestamp: float):
        super().__init__(EventPriority.SYSTEM, timestamp)
        
    def process(self, engine: "SimulationEngine") -> None:
        """
        Сбрасывает временные бюджеты агентов по профессиям.
        """
        # Временные бюджеты по профессиям согласно ТЗ
        profession_budgets = {
            "ShopClerk": (3, 5),
            "Worker": (3, 5), 
            "Developer": (2, 4),
            "Politician": (2, 4),
            "Blogger": (3, 5),
            "Businessman": (2, 4),
            "SpiritualMentor": (2, 4),
            "Philosopher": (2, 4),
            "Unemployed": (3, 5),
            "Teacher": (2, 4),
            "Artist": (3, 5),
            "Doctor": (1, 2)
        }
        
        import random
        reset_count = 0
        batch_updates = []
        
        for agent in engine.agents:
            budget_range = profession_budgets.get(agent.profession, (1, 3))
            old_budget = agent.time_budget
            agent.time_budget = random.randint(*budget_range)
            
            if agent.time_budget != old_budget:
                reset_count += 1
                batch_updates.append({
                    "type": "person_state",
                    "id": agent.id,
                    "time_budget": agent.time_budget,
                    "reason": "DailyReset",
                    "timestamp": self.timestamp
                })
        
        # Добавить обновления в batch
        for update in batch_updates:
            engine.add_to_batch_update(update)
            
        # Запланировать следующий сброс (каждые 24 часа = 1440 минут)
        next_reset = DailyResetEvent(self.timestamp + 1440.0)
        engine.add_event(next_reset, EventPriority.SYSTEM, next_reset.timestamp)
        
        # НОВОЕ: Сбрасываем ежедневные счетчики действий агентов
        current_day = int(self.timestamp // 1440)
        if hasattr(engine, '_daily_action_counts'):
            # Удаляем счетчики предыдущих дней
            keys_to_remove = []
            for key in engine._daily_action_counts:
                if key.endswith(f"_{current_day - 1}") or key.endswith(f"_{current_day - 2}"):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del engine._daily_action_counts[key]
                
            logger.info(json.dumps({
                "event": "daily_action_counters_cleaned",
                "removed_keys": len(keys_to_remove),
                "current_day": current_day,
                "timestamp": self.timestamp
            }))
        
        logger.info(json.dumps({
            "event": "daily_reset_completed",
            "budgets_reset": reset_count,
            "next_reset_time": self.timestamp + 1440.0,
            "timestamp": self.timestamp
        }))


class SaveDailyTrendEvent(BaseEvent):
    """Системное событие сохранения дневной статистики трендов."""
    
    def __init__(self, timestamp: float):
        super().__init__(EventPriority.SYSTEM, timestamp)
        
    def process(self, engine: "SimulationEngine") -> None:
        """
        Сохраняет агрегированную статистику трендов за день.
        """
        # TODO: Implement daily trend statistics aggregation
        current_day = int(self.timestamp // 1440) + 1  # День симуляции
        
        # Группируем активные тренды по темам
        topic_stats = {}
        for trend in engine.active_trends.values():
            topic = trend.topic
            if topic not in topic_stats:
                topic_stats[topic] = {
                    "total_interactions": 0,
                    "virality_scores": [],
                    "unique_authors": set(),
                    "top_trend": None,
                    "max_virality": 0.0
                }
                
            stats = topic_stats[topic]
            stats["total_interactions"] += trend.total_interactions
            stats["virality_scores"].append(trend.calculate_current_virality())
            stats["unique_authors"].add(trend.originator_id)
            
            current_virality = trend.calculate_current_virality()
            if current_virality > stats["max_virality"]:
                stats["max_virality"] = current_virality
                stats["top_trend"] = trend.trend_id
        
        # Запланировать следующее сохранение статистики
        next_save = SaveDailyTrendEvent(self.timestamp + 1440.0)
        engine.add_event(next_save, EventPriority.SYSTEM, next_save.timestamp)
        
        logger.info(json.dumps({
            "event": "daily_trends_saved",
            "simulation_day": current_day,
            "topics_processed": len(topic_stats),
            "timestamp": self.timestamp
        }))


class LawEvent(BaseEvent):
    """Внешнее событие изменения законодательства."""
    
    def __init__(self, timestamp: float, law_type: str, impact_factor: float):
        super().__init__(EventPriority.LAW, timestamp)
        self.law_type = law_type
        self.impact_factor = impact_factor
        
    def process(self, engine: "SimulationEngine") -> None:
        """
        Обрабатывает законодательные изменения.
        
        Влияет на всех агентов симуляции.
        """
        # TODO: Implement law impact processing
        logger.info(json.dumps({
            "event": "law_event_processed",
            "law_type": self.law_type,
            "impact_factor": self.impact_factor,
            "affected_agents": len(engine.agents),
            "timestamp": self.timestamp
        }))


class WeatherEvent(BaseEvent):
    """Внешнее событие изменения погодных условий."""
    
    def __init__(self, timestamp: float, weather_type: str, severity: float):
        super().__init__(EventPriority.WEATHER, timestamp)
        self.weather_type = weather_type
        self.severity = severity
        
    def process(self, engine: "SimulationEngine") -> None:
        """
        Обрабатывает влияние погодных условий на агентов.
        """
        # TODO: Implement weather impact processing
        logger.info(json.dumps({
            "event": "weather_event_processed",
            "weather_type": self.weather_type,
            "severity": self.severity,
            "timestamp": self.timestamp
        }))


class TrendInfluenceEvent(BaseEvent):
    """Событие распространения влияния тренда."""
    
    def __init__(self, timestamp: float, trend_id: UUID):
        super().__init__(EventPriority.TREND, timestamp)
        self.trend_id = trend_id
        
    def process(self, engine: "SimulationEngine") -> None:
        """
        Обрабатывает распространение влияния тренда через пакеты updatestate.
        """
        # Найти тренд
        trend = engine.active_trends.get(str(self.trend_id))
        if not trend:
            logger.warning(json.dumps({
                "event": "trend_not_found",
                "trend_id": str(self.trend_id),
                "timestamp": self.timestamp
            }))
            return
            
        # Рассчитываем параметры влияния
        current_virality = trend.calculate_current_virality()
        coverage_factor = trend.get_coverage_factor()
        
        # Создаем пакеты updatestate для всех затронутых агентов
        update_state_batch = []
        new_actions_batch = []
        influenced_agents = 0
        
        for agent in engine.agents:
            # Агент не влияет сам на себя
            if agent.id == trend.originator_id:
                continue
                
            # Проверка вероятности влияния
            influence_probability = (
                current_virality / 5.0 * 
                coverage_factor * 
                agent.trend_receptivity / 5.0 * 
                agent.get_affinity_for_topic(trend.topic) / 5.0
            )
            
            import random
            if random.random() < influence_probability:
                # Рассчитываем силу влияния
                influence_strength = min(0.5, current_virality * 0.2)  # ИСПРАВЛЕНИЕ: Увеличиваем силу влияния
                
                # Создаем пакет updatestate для агента
                update_state = {
                    "agent_id": agent.id,
                    "attribute_changes": {
                        "trend_receptivity": influence_strength * 0.2,
                        "social_status": influence_strength * 0.1,
                        "energy_level": -0.01  # ИСПРАВЛЕНИЕ: снижаем усталость от просмотра до 0.01
                    },
                    "reason": "TrendInfluence",
                    "source_trend_id": trend.trend_id,
                    "timestamp": self.timestamp
                }
                update_state_batch.append(update_state)
                
                # Применяем изменения к агенту
                agent.update_state(update_state["attribute_changes"])
                
                # Добавляем взаимодействие с трендом
                trend.add_interaction()
                influenced_agents += 1
                
                # ИСПРАВЛЕНИЕ: Добавляем обновление тренда в batch
                engine.add_to_batch_update({
                    "type": "trend_interaction",
                    "trend_id": trend.trend_id,
                    "total_interactions": trend.total_interactions,
                    "timestamp": self.timestamp
                })
                
                # Записываем в историю воздействий
                agent.exposure_history[str(trend.trend_id)] = self.timestamp
                
                # Проверяем возможность создания ответного действия
                response_probability = (
                    influence_strength * 
                    agent.social_status / 5.0 * 
                    0.6  # ИСПРАВЛЕНИЕ: Увеличиваем базовую вероятность ответа
                )
                
                if (random.random() < response_probability and 
                    agent.energy_level >= 0.5 and  # ИСПРАВЛЕНИЕ: Снижаем требования к энергии для ответных постов
                    engine._can_agent_act_today(agent.id)):
                    
                    # ИСПРАВЛЕНИЕ: Создаем ответный пост на ту же тему что и родительский тренд
                    response_topic = trend.topic  # Используем тему родительского тренда
                    
                    # Создаем будущее действие с parent_trend_id
                    response_delay = random.uniform(10.0, 60.0)
                    new_action = {
                        "agent_id": agent.id,
                        "action_type": "PublishPostAction",
                        "topic": response_topic,
                        "timestamp": self.timestamp + response_delay,
                        "trigger_trend_id": trend.trend_id  # Указываем что это ответ на тренд
                    }
                    new_actions_batch.append(new_action)
                    
                    # ИСПРАВЛЕНИЕ: Увеличиваем total_interactions у родительского тренда
                    trend.add_interaction()
        
        # Пакетная обработка updatestate
        if update_state_batch:
            engine._process_update_state_batch(update_state_batch)
            
        # Пакетное планирование новых действий
        if new_actions_batch:
            scheduled_count = engine._schedule_actions_batch(new_actions_batch)
            
            logger.info(json.dumps({
                "event": "response_actions_scheduled",
                "original_trend": str(trend.trend_id),
                "scheduled_count": scheduled_count,
                "timestamp": self.timestamp
            }))
        
        logger.info(json.dumps({
            "event": "trend_influence_processed",
            "trend_id": str(self.trend_id),
            "influenced_agents": influenced_agents,
            "update_states_created": len(update_state_batch),
            "new_actions_scheduled": len(new_actions_batch),
            "total_interactions": trend.total_interactions,
            "current_virality": current_virality,
            "timestamp": self.timestamp
        })) 