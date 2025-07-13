"""
Events - классы событий для дискретно-событийной симуляции CAPSIM.
"""

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4
from dataclasses import dataclass
import json
import logging
from enum import IntEnum
import sys
import random

if TYPE_CHECKING:
    from ..engine.simulation_engine import SimulationEngine

logger = logging.getLogger(__name__)


class EventPriority(IntEnum):
    """Event priority levels for v1.8 priority queue system."""
    SYSTEM = 100       # DailyResetEvent, EnergyRecoveryEvent - highest priority
    AGENT_ACTION = 50  # PublishPost, Purchase, SelfDev actions
    TREND = 30         # TrendInfluenceEvent - social influence processing
    ENERGY_RECOVERY = 20  # EnergyRecoveryEvent - lower priority than agent actions
    LAW = 15           # LawEvent - external law changes
    WEATHER = 10       # WeatherEvent - external weather changes
    LOW = 0            # Default/fallback priority


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
            
        # Проверить возможность действия согласно ТЗ v1.8
        if not agent.can_post(self.timestamp):
            logger.info(json.dumps({
                "event": "action_rejected",
                "agent_id": str(self.agent_id),
                "reason": "insufficient_resources",
                "energy": agent.energy_level,
                "time_budget": agent.time_budget,
                "trend_receptivity": agent.trend_receptivity,
                "timestamp": self.timestamp,
                "day_time": self.timestamp % 1440
            }, default=str))
            return
            
        # Создать новый тренд
        from ..domain.trend import Trend, CoverageLevel
        import random
        
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
        
        # Уровень охвата теперь зависит от социального статуса (v1.10 tweak)
        if agent.social_status >= 4.0:
            coverage = CoverageLevel.HIGH.value
        elif agent.social_status < 1.5:  # Low при низком статусе
            coverage = CoverageLevel.LOW.value
        else:
            coverage = CoverageLevel.MIDDLE.value  # Middle по умолчанию
            
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
        
        # v1.9: Случайное присвоение sentiment (50/50) согласно ТЗ v1.9
        sentiment = random.choice(["Positive", "Negative"])
        
        new_trend = Trend.create_from_action(
            topic=self.topic,
            originator_id=self.agent_id,
            simulation_id=agent.simulation_id,
            base_virality=base_virality,
            coverage_level=coverage,
            parent_id=parent_trend_id,  # ИСПРАВЛЕНИЕ: Используем parent_trend_id
            sentiment=sentiment  # v1.9: Добавляем случайный sentiment
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
            "sentiment": new_trend.sentiment,
            "timestamp": self.timestamp
        })
        
        # v1.9: Убираем мгновенные эффекты для автора согласно ТЗ v1.9
        # Эффекты будут применены через PostEffect систему в TrendInfluenceEvent
        
        # v1.9: Обновляем только cooldown и tracking атрибуты
        agent.last_post_ts = self.timestamp
        
        # Добавить в batch обновления (только tracking атрибуты)
        engine.add_to_batch_update({
            "type": "person_state",
            "id": self.agent_id,
            "last_post_ts": agent.last_post_ts,  # v1.9: Время последнего поста
            "reason": "PublishPostAction",
            "timestamp": self.timestamp
        })
        
        # Записываем метрики
        from ..common.metrics import record_action
        record_action("Post", "", agent.profession)
        
        # Запланировать распространение влияния тренда только если тренд успешно создан
        if new_trend and new_trend.trend_id:
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
        }, default=str))

        # Тренд будет сохранен в batch commit


class EnergyRecoveryEvent(BaseEvent):
    """Event для восстановления энергии агентов."""
    
    def __init__(self, timestamp: float):
        super().__init__(EventPriority.ENERGY_RECOVERY, timestamp)
    
    def process(self, engine: "SimulationEngine") -> None:
        """Execute energy recovery for all agents."""
        # v1.9: passive recovery rebalance — 0.12 every 5 sim-minutes
        recovery_amount = 0.12
        self.recovered_agent_ids: list[str] = []  # For logging into events table

        for agent in engine.agents:
            if agent.energy_level < 5:
                old_energy = agent.energy_level
                agent.energy_level = min(5, agent.energy_level + recovery_amount)
                self.recovered_agent_ids.append(str(agent.id))
                
                # ИСПРАВЛЕНИЕ: Создаем запись в person_attribute_history
                engine.add_to_batch_update({
                    "type": "attribute_history",
                    "person_id": agent.id,
                    "simulation_id": engine.simulation_id,
                    "attribute_name": "energy_level",
                    "old_value": old_energy,
                    "new_value": agent.energy_level,
                    "delta": recovery_amount,
                    "reason": "EnergyRecovery",
                    "source_trend_id": None,
                    "change_timestamp": self.timestamp
                })
        
        # ИСПРАВЛЕНИЕ: Проверяем время окончания симуляции перед планированием следующего события
        next_timestamp = self.timestamp + 5
        if engine.should_schedule_future_event(next_timestamp):
            next = EnergyRecoveryEvent(next_timestamp)
            engine.add_event(next, EventPriority.ENERGY_RECOVERY, next_timestamp)
        else:
            logger.info(json.dumps({
                "event": "energy_recovery_cycle_ended",
                "reason": "simulation_end_time_reached",
                "timestamp": self.timestamp,
                "end_time": engine.end_time
            }, default=str))
        
        logger.info(json.dumps({
            "event": "energy_recovery_completed",
            "updated_agents": len(engine.agents),
            "recovery_amount": recovery_amount,
            "recovered_agents": len(self.recovered_agent_ids),
            "timestamp": self.timestamp
        }, default=str))


# ---------------- v1.9 DAILY CYCLE ----------------


class NightCycleEvent(BaseEvent):
    """Marks the start of nightly inactivity period (00:00-08:00). Purely logging for now."""

    def __init__(self, timestamp: float):
        super().__init__(EventPriority.SYSTEM, timestamp)

    def process(self, engine: "SimulationEngine") -> None:
        # ИСПРАВЛЕНИЕ: Проверяем время окончания симуляции перед планированием следующего события
        next_timestamp = self.timestamp + 1440.0
        if engine.should_schedule_future_event(next_timestamp):
            next_night = NightCycleEvent(next_timestamp)
            engine.add_event(next_night, EventPriority.SYSTEM, next_timestamp)
        else:
            logger.info(json.dumps({
                "event": "night_cycle_ended",
                "reason": "simulation_end_time_reached",
                "timestamp": self.timestamp,
                "end_time": engine.end_time
            }, default=str))

        logger.info(json.dumps({
            "event": "night_cycle_start",
            "timestamp": self.timestamp
        }, default=str))


class MorningRecoveryEvent(BaseEvent):
    """Restores energy & finances at 08:00 each day."""

    def __init__(self, timestamp: float):
        super().__init__(EventPriority.SYSTEM, timestamp)

    def process(self, engine: "SimulationEngine") -> None:
        from capsim.common.settings import action_config as _ac

        energy_bonus = _ac.night_recovery["energy_bonus"] if hasattr(_ac, "night_recovery") else 1.2
        financial_bonus = _ac.night_recovery["financial_bonus"] if hasattr(_ac, "night_recovery") else 1.0

        recovered = 0
        for agent in engine.agents:
            changes: dict[str, float] = {}

            if agent.energy_level < 5.0:
                delta_e = min(5.0, agent.energy_level + energy_bonus) - agent.energy_level
                if delta_e:
                    changes["energy_level"] = delta_e

            if agent.financial_capability < 5.0:
                delta_f = min(5.0, agent.financial_capability + financial_bonus) - agent.financial_capability
                if delta_f:
                    changes["financial_capability"] = delta_f

            if not changes:
                continue

            # Apply effects
            agent.apply_effects(changes)

            # ИСПРАВЛЕНИЕ: Убираем person_state update - не обновляем таблицу persons
            # Все изменения атрибутов сохраняются только в person_attribute_history

            # Add attribute_history for each change
            for attr, delta in changes.items():
                engine.add_to_batch_update({
                    "type": "attribute_history",
                    "person_id": agent.id,
                    "simulation_id": engine.simulation_id,
                    "attribute_name": attr,
                    "old_value": getattr(agent, attr) - delta,
                    "new_value": getattr(agent, attr),
                    "delta": delta,
                    "reason": "MorningRecovery",
                    "source_trend_id": None,
                    "change_timestamp": self.timestamp
                })
            recovered += 1

        # ИСПРАВЛЕНИЕ: Проверяем время окончания симуляции перед планированием следующего события
        next_timestamp = self.timestamp + 1440.0
        if engine.should_schedule_future_event(next_timestamp):
            next_morning = MorningRecoveryEvent(next_timestamp)
            engine.add_event(next_morning, EventPriority.SYSTEM, next_timestamp)
        else:
            logger.info(json.dumps({
                "event": "morning_recovery_cycle_ended",
                "reason": "simulation_end_time_reached",
                "timestamp": self.timestamp,
                "end_time": engine.end_time
            }, default=str))

        logger.info(json.dumps({
            "event": "morning_recovery_completed",
            "recovered_agents": recovered,
            "energy_bonus": energy_bonus,
            "financial_bonus": financial_bonus,
            "timestamp": self.timestamp
        }, default=str))


class DailyResetEvent(BaseEvent):
    """v1.8: Event для ежедневного сброса счетчиков агентов (каждые 1440 минут)."""
    
    def __init__(self, timestamp: float):
        super().__init__(EventPriority.SYSTEM, timestamp)
    
    def process(self, engine: "SimulationEngine") -> None:
        """Execute daily reset for all agents."""
        reset_count = 0
        
        for agent in engine.agents:
            reset_done = False
            if agent.purchases_today > 0:
                agent.purchases_today = 0
                reset_done = True
            # v1.8: обнуляем per-level timestamps
            if getattr(agent, 'last_purchase_ts', None):
                agent.last_purchase_ts = {"L1": None, "L2": None, "L3": None}
                reset_done = True
            if reset_done:
                reset_count += 1
        
        # ИСПРАВЛЕНИЕ: Проверяем время окончания симуляции перед планированием следующего события
        next_timestamp = self.timestamp + 1440.0
        if engine.should_schedule_future_event(next_timestamp):
            next_reset = DailyResetEvent(timestamp=next_timestamp)
            engine.add_event(next_reset, EventPriority.SYSTEM, next_timestamp)
            next_reset_log = next_timestamp
        else:
            logger.info(json.dumps({
                "event": "daily_reset_cycle_ended",
                "reason": "simulation_end_time_reached",
                "timestamp": self.timestamp,
                "end_time": engine.end_time
            }, default=str))
            next_reset_log = None
        
        logger.info(json.dumps({
            "event": "daily_reset_completed",
            "reset_agents": reset_count,
            "total_agents": len(engine.agents),
            "timestamp": self.timestamp,
            "next_reset": next_reset_log
        }, default=str))


class PurchaseAction(BaseEvent):
    """v1.8: Event для покупок агентов."""
    
    def __init__(self, agent_id: UUID, purchase_level: str, timestamp: float):
        super().__init__(EventPriority.AGENT_ACTION, timestamp)
        self.agent_id = agent_id
        self.purchase_level = purchase_level  # L1, L2, L3
    
    def process(self, engine: "SimulationEngine") -> None:
        """Execute purchase action согласно ТЗ v1.9."""
        from ..common.settings import action_config
        import random
        
        agent = next((a for a in engine.agents if a.id == self.agent_id), None)
        if not agent:
            return
            
        # Получаем эффекты для данного уровня покупки согласно ТЗ v1.9
        effects = action_config.effects["PURCHASE"][self.purchase_level]
        
        # Случайная стоимость в заданном диапазоне согласно ТЗ v1.9
        cost_range = effects["cost_range"]
        actual_cost = random.uniform(cost_range[0], cost_range[1])
        
        # Создаем эффекты с реальной стоимостью
        purchase_effects = {
            "financial_capability": -actual_cost,
            "energy_level": effects.get("energy_level", 0.0),
            "time_budget": effects.get("time_budget", 0.0),
        }
        if "social_status" in effects:
            purchase_effects["social_status"] = effects["social_status"]
        
        # Применяем эффекты к агенту
        agent.apply_effects(purchase_effects)
        
        # Update v1.8 tracking attributes
        agent.purchases_today += 1
        agent.last_purchase_ts[self.purchase_level] = self.timestamp
        
        # ИСПРАВЛЕНИЕ: Создаем записи в person_attribute_history для каждого измененного атрибута
        # Сохраняем изменения атрибутов в историю
        for attr_name, delta in purchase_effects.items():
            old_value = getattr(agent, attr_name) - delta
            engine.add_to_batch_update({
                "type": "attribute_history",
                "person_id": self.agent_id,
                "simulation_id": engine.simulation_id,
                "attribute_name": attr_name,
                "old_value": old_value,
                "new_value": getattr(agent, attr_name),
                "delta": delta,
                "reason": f"PurchaseAction_{self.purchase_level}",
                "source_trend_id": None,
                "change_timestamp": self.timestamp
            })
        
        # Обновляем только tracking атрибуты в simulation_participants
        engine.add_to_batch_update({
            "type": "person_state",
            "id": self.agent_id,
            "purchases_today": agent.purchases_today,
            "last_purchase_ts": agent.last_purchase_ts,
            "reason": f"PurchaseAction_{self.purchase_level}",
            "timestamp": self.timestamp
        })
        
        # Записываем метрики
        from ..common.metrics import record_action
        record_action("Purchase", self.purchase_level, agent.profession)
        
        logger.info(json.dumps({
            "event": "purchase_completed",
            "agent_id": str(self.agent_id),
            "level": self.purchase_level,
            "actual_cost": actual_cost,
            "financial_capability_after": agent.financial_capability,
            "purchases_today": agent.purchases_today,
            "timestamp": self.timestamp
        }, default=str))


class SelfDevAction(BaseEvent):
    """v1.8: Event для саморазвития агентов."""
    
    def __init__(self, agent_id: UUID, timestamp: float):
        super().__init__(EventPriority.AGENT_ACTION, timestamp)
        self.agent_id = agent_id
    
    def process(self, engine: "SimulationEngine") -> None:
        """Execute self-development action согласно ТЗ v1.8."""
        from ..common.settings import action_config
        
        agent = next((a for a in engine.agents if a.id == self.agent_id), None)
        if not agent:
            return
            
        # Получаем эффекты саморазвития согласно ТЗ v1.8
        effects = action_config.effects["SELF_DEV"]
        
        # Применяем эффекты к агенту
        agent.apply_effects(effects)
        
        # Update v1.8 tracking attributes
        agent.last_selfdev_ts = self.timestamp
        
        # ИСПРАВЛЕНИЕ: Создаем записи в person_attribute_history для каждого измененного атрибута
        # Сохраняем изменения атрибутов в историю
        for attr_name, delta in effects.items():
            old_value = getattr(agent, attr_name) - delta
            engine.add_to_batch_update({
                "type": "attribute_history",
                "person_id": self.agent_id,
                "simulation_id": engine.simulation_id,
                "attribute_name": attr_name,
                "old_value": old_value,
                "new_value": getattr(agent, attr_name),
                "delta": delta,
                "reason": "SelfDevAction",
                "source_trend_id": None,
                "change_timestamp": self.timestamp
            })
        
        # Обновляем только tracking атрибуты в simulation_participants
        engine.add_to_batch_update({
            "type": "person_state",
            "id": self.agent_id,
            "last_selfdev_ts": agent.last_selfdev_ts,
            "reason": "SelfDevAction",
            "timestamp": self.timestamp
        })
        
        # Записываем метрики
        from ..common.metrics import record_action
        record_action("SelfDev", "", agent.profession)
        
        logger.info(json.dumps({
            "event": "selfdev_completed",
            "agent_id": str(self.agent_id),
            "energy_level_after": agent.energy_level,
            "time_budget_after": agent.time_budget,
            "timestamp": self.timestamp
        }, default=str))


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
        
        # ИСПРАВЛЕНИЕ: Проверяем время окончания симуляции перед планированием следующего события
        next_timestamp = self.timestamp + 1440.0
        if engine.should_schedule_future_event(next_timestamp):
            next_save = SaveDailyTrendEvent(next_timestamp)
            engine.add_event(next_save, EventPriority.SYSTEM, next_timestamp)
        else:
            logger.info(json.dumps({
                "event": "daily_trend_save_cycle_ended",
                "reason": "simulation_end_time_reached",
                "timestamp": self.timestamp,
                "end_time": engine.end_time
            }, default=str))
        
        logger.info(json.dumps({
            "event": "daily_trends_saved",
            "simulation_day": current_day,
            "topics_processed": len(topic_stats),
            "timestamp": self.timestamp
        }, default=str))


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
        }, default=str))


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
        }, default=str))


class TrendInfluenceEvent(BaseEvent):
    """Событие распространения влияния тренда."""
    
    def __init__(self, timestamp: float, trend_id: UUID):
        super().__init__(EventPriority.TREND, timestamp)
        self.trend_id = trend_id

    # -------------------- v1.9 helpers --------------------
    @staticmethod
    def _calculate_reader_effects(sentiment: str, aligned: bool) -> dict[str, float]:
        """Return attribute deltas based on sentiment matrix from tech_v1.9."""
        # Восприимчивость (trend_receptivity)
        receptivity_delta = 0.01 if (aligned or sentiment == "Negative") else 0.0

        # Энергия
        if sentiment == "Positive":
            energy_delta = 0.02 if aligned else 0.015
        else:  # Negative
            energy_delta = -0.015 if aligned else -0.01

        return {
            "trend_receptivity": receptivity_delta,
            "energy_level": energy_delta,
        }

    # v1.9: aggregated effect for the author (PostEffect)
    @staticmethod
    def _calculate_author_post_effect(author_id: UUID, trend: "Trend", audience_updates: list[dict], event_timestamp: float) -> dict:
        """Compute social_status delta for the author based on audience reaction.

        Implementation follows tech_v1.9 spec (log-scaled reach, sentiment multiplier, clamped −1..1).
        Returns UpdateState-like dict ready for engine._process_update_state_batch.
        """
        import math

        total_reach = len(audience_updates)
        if total_reach == 0:
            return {}

        # Sum of energy deltas applied to audience (positive or negative)
        total_energy_change = sum(
            upd["attribute_changes"].get("energy_level", 0.0) for upd in audience_updates
        )

        reach_multiplier = math.log(total_reach + 1, 10)  # log base 10
        sentiment_multiplier = 1.0 if trend.sentiment == "Positive" else -1.0

        post_effect_delta = (total_energy_change * reach_multiplier * sentiment_multiplier) / 50
        # Clamp to [-1.0, 1.0]
        post_effect_delta = max(-1.0, min(1.0, post_effect_delta))

        return {
            "agent_id": author_id,
            "attribute_changes": {"social_status": post_effect_delta},
            "reason": "PostEffect",
            "source_trend_id": trend.trend_id,
            "timestamp": event_timestamp,
        }
    
    def process(self, engine: "SimulationEngine") -> None:
        """
        Обрабатывает распространение влияния тренда через пакеты updatestate.
        """
        # Найти тренд в активных трендах движка
        trend = engine.active_trends.get(str(self.trend_id))
        
        if not trend:
            logger.warning(json.dumps({
                "event": "trend_not_found_in_active_list",
                "trend_id": str(self.trend_id),
                "timestamp": self.timestamp
            }, default=str))
            return

        # ИСПРАВЛЕНИЕ: Предотвращаем лавинообразный рост событий, ограничивая "вирусность"
        if trend.total_interactions > 100:
            logger.info(json.dumps({
                "event": "trend_influence_skipped",
                "reason": "interaction_limit_exceeded",
                "trend_id": str(self.trend_id),
                "total_interactions": trend.total_interactions,
                "timestamp": self.timestamp
            }, default=str))
            return
            
        # 1. Определяем, кто из агентов "увидит" этот тренд
        # Используем `coverage_level` для определения количества затронутых агентов
        audience_size = int(len(engine.agents) * trend.get_coverage_factor())
        potential_audience = random.sample(engine.agents, min(len(engine.agents), audience_size))
        
        # 2. Обрабатываем влияние на каждого "увидевшего" агента
        update_states = []
        response_actions = []
        influenced_agents_count = 0
        
        # ИСПРАВЛЕНИЕ: Радикально уменьшаем вероятность ответа, чтобы остановить лавину
        likeliness_to_respond = 0.05  # было 0.2
        
        for agent in potential_audience:
            if agent.id == trend.originator_id:
                continue # Автор не влияет сам на себя

            # Проверяем, может ли агент вообще увидеть этот тренд
            # ИСПРАВЛЕНИЕ: Порог affinity теперь >= 2.5
            if agent.trend_receptivity > 0.5 and agent.get_affinity_for_topic(trend.topic) >= 2.5:
                # Определяем соответствие интересов
                from capsim.common.topic_mapping import topic_to_interest_category
                try:
                    interest_category = topic_to_interest_category(trend.topic)
                except KeyError:
                    interest_category = None

                aligned = False
                if interest_category:
                    interest_value = agent.interests.get(interest_category, 0.0)
                    aligned = interest_value > 3.0

                # Рассчитываем дельты по новой матрице
                attribute_changes = self._calculate_reader_effects(trend.sentiment, aligned)

                # Создаем пакет updatestate для агента
                update_state = {
                    "agent_id": agent.id,
                    "attribute_changes": attribute_changes,
                    "reason": "TrendInfluence",
                    "source_trend_id": trend.trend_id,
                    "timestamp": self.timestamp
                }
                update_states.append(update_state)
                
                # Применяем изменения к агенту
                agent.update_state(attribute_changes)
                
                # Добавляем взаимодействие с трендом
                trend.add_interaction()
                influenced_agents_count += 1
                
                # ИСПРАВЛЕНИЕ: Добавляем обновление тренда в batch
                # НЕ передаем total_interactions - это будет обновлено в БД через increment
                engine.add_to_batch_update({
                    "type": "trend_interaction",
                    "trend_id": trend.trend_id,
                    "timestamp": self.timestamp
                })
                
                # Записываем в историю воздействий
                agent.exposure_history[str(trend.trend_id)] = self.timestamp
                
                # Проверяем возможность создания ответного действия
                # ИСПРАВЛЕНИЕ: Еще сильнее снижаем вероятность ответного поста
                response_probability = (
                    trend.calculate_current_virality() / 5.0 * agent.social_status / 5.0 * likeliness_to_respond
                ) / 2.0 # Дополнительно делим на 2
                
                if (random.random() < response_probability and 
                    agent.energy_level >= 0.3 and  # ИСПРАВЛЕНИЕ: Еще больше снижаем требования к энергии
                    engine._can_agent_act_today(agent.id)):
                    
                    # ИСПРАВЛЕНИЕ: Создаем ответный пост на ту же тему что и родительский тренд
                    response_topic = trend.topic  # Используем тему родительского тренда
                    
                    # Создаем будущее действие с parent_trend_id только если тренд существует
                    if trend and trend.trend_id:
                        response_delay = random.uniform(10.0, 60.0)
                        response_timestamp = self.timestamp + response_delay
                        
                        # ИСПРАВЛЕНИЕ: Проверяем время окончания симуляции перед планированием ответного поста
                        if engine.should_schedule_future_event(response_timestamp):
                            new_action = {
                                "agent_id": agent.id,
                                "action_type": "PublishPostAction",
                                "topic": response_topic,
                                "timestamp": response_timestamp,
                                "trigger_trend_id": trend.trend_id  # Указываем что это ответ на тренд
                            }
                            response_actions.append(new_action)
                        else:
                            logger.debug(json.dumps({
                                "event": "response_post_rejected_past_end_time",
                                "agent_id": str(agent.id),
                                "response_timestamp": response_timestamp,
                                "end_time": engine.end_time,
                                "trend_id": str(trend.trend_id)
                            }, default=str))
                    
                    # ИСПРАВЛЕНИЕ: НЕ увеличиваем total_interactions здесь - это отдельное взаимодействие
                    # Ответный пост будет создан как отдельное событие и добавит своё взаимодействие
        
        # --------------- PostEffect для автора ----------------
        author_effect_update = self._calculate_author_post_effect(trend.originator_id, trend, update_states, self.timestamp)
        if author_effect_update:
            # Применяем изменения к автору в памяти
            author = next((a for a in engine.agents if a.id == trend.originator_id), None)
            if author:
                author.update_state(author_effect_update["attribute_changes"])

            update_states.append(author_effect_update)

        # Пакетная обработка updatestate (читатели + автор)
        if update_states:
            engine._process_update_state_batch(update_states)
            
        # Пакетное планирование новых действий
        if response_actions:
            scheduled_count = engine._schedule_actions_batch(response_actions)
            
            logger.info(json.dumps({
                "event": "response_actions_scheduled",
                "original_trend": str(trend.trend_id),
                "scheduled_count": scheduled_count,
                "timestamp": self.timestamp
            }, default=str))
        
        logger.info(json.dumps({
            "event": "trend_influence_processed",
            "trend_id": str(self.trend_id),
            "influenced_agents": influenced_agents_count,
            "author_post_effect_applied": bool(author_effect_update),
            "post_effect_delta": author_effect_update.get("attribute_changes", {}).get("social_status") if author_effect_update else 0.0,
            "update_states_created": len(update_states),
            "new_actions_scheduled": len(response_actions),
            "total_interactions": trend.total_interactions,
            "current_virality": trend.calculate_current_virality(),
            "timestamp": self.timestamp
        }, default=str))

        # События будут сохранены в batch commit 