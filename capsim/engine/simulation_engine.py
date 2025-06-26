"""
SimulationEngine - центральный координатор дискретно-событийной симуляции CAPSIM.
"""

from typing import List, Dict, Optional, Any, TYPE_CHECKING
from uuid import UUID
import heapq
import asyncio
import os
import json
import logging
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from ..domain.person import Person
from ..domain.trend import Trend
from ..domain.events import (
    BaseEvent, EventPriority, PublishPostAction, EnergyRecoveryEvent, 
    DailyResetEvent, SaveDailyTrendEvent
)
from ..common.clock import Clock, create_clock
from ..common.settings import settings

if TYPE_CHECKING:
    from ..db.repositories import DatabaseRepository

logger = logging.getLogger(__name__)


@dataclass
class SimulationContext:
    """Контекст симуляции для передачи агентам."""
    current_time: float
    active_trends: Dict[str, Trend]
    affinity_map: Dict[str, Dict[str, float]]


@dataclass
class PriorityEvent:
    """Event wrapper with priority for event queue."""
    priority: int
    timestamp: float
    event: BaseEvent
    
    def __lt__(self, other):
        """Priority comparison for heapq."""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.timestamp < other.timestamp


class SimulationEngine:
    """
    Центральный координатор всех операций симуляции.
    
    Управляет:
    - Приоритетной очередью событий
    - Агентами симуляции  
    - Активными трендами
    - Batch-commit операциями
    """
    
    def __init__(self, db_repo: "DatabaseRepository", clock: Clock = None):
        self.agents: List[Person] = []
        self.current_time: float = 0.0  # simulation time in minutes
        self.event_queue: List[PriorityEvent] = []
        self.active_trends: Dict[str, Trend] = {}
        self.affinity_map: Dict[str, Dict[str, float]] = {}
        
        # Performance tracking
        self._batch_updates: List[Dict] = []
        self._last_commit_time: float = 0.0
        self._last_batch_commit: float = 0.0
        self._simulation_start_real: float = 0.0
        
        # Configuration from settings
        self.batch_size = settings.BATCH_SIZE
        self.batch_timeout_minutes = float(os.getenv("BATCH_TIMEOUT_MIN", "1.0"))
        self.trend_archive_threshold_days = settings.TREND_ARCHIVE_THRESHOLD_DAYS
        
        # Clock for realtime support
        self.clock = clock or create_clock(settings.ENABLE_REALTIME)
        
        # Dependencies
        self.db_repo = db_repo
        self.simulation_id: Optional[UUID] = None
        self._running = False
        
        # НОВОЕ: Флаг для принудительного commit после определенных событий
        self._force_commit_after_this_event = False
        
    async def initialize(self, num_agents: int = 1000) -> None:
        """
        Инициализирует симуляцию с заданным количеством агентов.
        
        ВАЖНО: 
        1. Агенты создаются ТОЛЬКО если их недостаточно для симуляции
        2. Глобальный лимит 1000 агентов НЕ должен превышаться
        3. Распределение профессий строго согласно ТЗ
        
        Args:
            num_agents: Количество агентов для симуляции
        """
        if self.simulation_id:
            raise RuntimeError("Simulation already initialized")
            
        self._last_batch_commit = time.time()
        self._agent_action_cooldowns = {}
        self._daily_action_count = {}
        
        # Создать запуск симуляции
        simulation_run = await self.db_repo.create_simulation_run(
            num_agents=num_agents,
            duration_days=1,  # По умолчанию 1 день
            configuration={
                "batch_size": self.batch_size,
                "batch_timeout": self.batch_timeout_minutes,
                "trend_archive_days": self.trend_archive_threshold_days,
                "sim_speed_factor": settings.SIM_SPEED_FACTOR
            }
        )
        self.simulation_id = simulation_run.run_id
        
        # ИСПРАВЛЕНИЕ: Обновляем статус на RUNNING при инициализации
        await self.db_repo.update_simulation_status(
            self.simulation_id, 
            "RUNNING",
            datetime.utcnow()
        )
        
        # Обновляем метрику активных симуляций
        try:
            from ..common.metrics import SIMULATION_COUNT
            SIMULATION_COUNT.set(1)  # Теперь у нас есть одна активная симуляция
        except ImportError:
            pass  # Метрики недоступны
        
        # Загрузить affinity map из БД
        self.affinity_map = await self.db_repo.load_affinity_map()
        
        # ИСПРАВЛЕНИЕ: Проверяем общее количество агентов в системе
        total_existing_agents = await self.db_repo.get_persons_count()
        
        if total_existing_agents >= 1000:
            # Достигнут глобальный лимит - используем существующих агентов
            logger.warning(json.dumps({
                "event": "global_agent_limit_reached",
                "total_existing": total_existing_agents,
                "requested": num_agents,
                "action": "using_existing_agents"
            }, default=str))
            
            # Берем случайных агентов из существующих
            existing_agents = await self.db_repo.get_persons_for_simulation(None, num_agents)
            self.agents = existing_agents[:num_agents]
            
            logger.info(json.dumps({
                "event": "agents_reused_from_global_pool",
                "simulation_id": str(self.simulation_id),
                "reused_count": len(self.agents),
                "requested_count": num_agents,
                "total_system_agents": total_existing_agents
            }, default=str))
        else:
            # Проверяем существующих агентов для данной симуляции
            existing_agents = await self.db_repo.get_persons_for_simulation(self.simulation_id, num_agents)
            existing_count = len(existing_agents)
            
            if existing_count >= num_agents:
                # Достаточно агентов - используем первых N по порядку создания
                self.agents = existing_agents[:num_agents]
                logger.info(json.dumps({
                    "event": "agents_reused",
                    "simulation_id": str(self.simulation_id),
                    "reused_count": len(self.agents),
                    "requested_count": num_agents
                }, default=str))
            else:
                # Недостаточно агентов - создаем недостающих СТРОГО ПО ТЗ
                agents_to_create_count = min(num_agents - existing_count, 1000 - total_existing_agents)
                
                if agents_to_create_count <= 0:
                    # Не можем создать новых агентов из-за лимита
                    logger.warning(json.dumps({
                        "event": "cannot_create_new_agents",
                        "reason": "global_limit_reached",
                        "total_existing": total_existing_agents,
                        "existing_for_simulation": existing_count,
                        "requested": num_agents
                    }, default=str))
                    
                    # Используем все доступные агенты
                    self.agents = existing_agents
                else:
                    # СТРОГОЕ РАСПРЕДЕЛЕНИЕ ПРОФЕССИЙ согласно ТЗ (таблица распределения)
                    profession_distribution_tz = [
                        ("Teacher", 0.20),        # 20%
                        ("ShopClerk", 0.18),      # 18%
                        ("Developer", 0.12),      # 12%
                        ("Unemployed", 0.09),     # 9%
                        ("Businessman", 0.08),    # 8%
                        ("Artist", 0.08),         # 8%
                        ("Worker", 0.07),         # 7%
                        ("Blogger", 0.05),        # 5%
                        ("SpiritualMentor", 0.03), # 3%
                        ("Philosopher", 0.02),    # 2%
                        ("Politician", 0.01),     # 1%
                        ("Doctor", 0.01),         # 1%
                    ]
                    
                    # Вычисляем точное количество агентов по профессиям
                    profession_counts = []
                    total_assigned = 0
                    
                    for profession, percentage in profession_distribution_tz:
                        count = int(agents_to_create_count * percentage)
                        profession_counts.append((profession, count))
                        total_assigned += count
                    
                    # Добавляем оставшихся агентов к самой популярной профессии (Teacher)
                    if total_assigned < agents_to_create_count:
                        remaining = agents_to_create_count - total_assigned
                        profession_counts[0] = ("Teacher", profession_counts[0][1] + remaining)
                    
                    agents_to_create = []
                    for profession, count in profession_counts:
                        for _ in range(count):
                            agent = Person.create_random_agent(profession, self.simulation_id)
                            agents_to_create.append(agent)
                        
                    # Создаем только недостающих агентов
                    if agents_to_create:
                        await self.db_repo.bulk_create_persons(agents_to_create)
                    
                    # Объединяем существующих и новых агентов
                    self.agents = existing_agents + agents_to_create
                    
                    logger.info(json.dumps({
                        "event": "agents_created_according_tz",
                        "simulation_id": str(self.simulation_id),
                        "existing_count": existing_count,
                        "created_count": len(agents_to_create),
                        "total_count": len(self.agents),
                        "requested_count": num_agents,
                        "profession_distribution": {prof: count for prof, count in profession_counts},
                    }, default=str))
        
        # Загрузить начальные тренды (если есть)
        existing_trends = await self.db_repo.get_active_trends(self.simulation_id)
        for trend in existing_trends:
            self.active_trends[str(trend.trend_id)] = trend
        
        # Запланировать системные события
        self._schedule_system_events()
        
        logger.info(json.dumps({
            "event": "simulation_initialized",
            "simulation_id": str(self.simulation_id),
            "agents_total": len(self.agents),
            "affinity_topics": len(self.affinity_map),
            "system_events_scheduled": len(self.event_queue)
        }, default=str))
        
    def _schedule_system_events(self) -> None:
        """Планирует системные события."""
        # ИСПРАВЛЕНИЕ: Создаем больше системных событий для полноценной симуляции
        
        # Первое восстановление энергии через 6 часов (360 минут)
        energy_event = EnergyRecoveryEvent(360.0)
        self.add_event(energy_event, EventPriority.SYSTEM, 360.0)
        
        # Ежедневный сброс через 24 часа (1440 минут)
        daily_reset = DailyResetEvent(1440.0)
        self.add_event(daily_reset, EventPriority.SYSTEM, 1440.0)
        
        # Сохранение дневной статистики через 23 часа (1380 минут)
        daily_save = SaveDailyTrendEvent(1380.0)
        self.add_event(daily_save, EventPriority.SYSTEM, 1380.0)
        
        # ДОБАВЛЯЕМ: Более частые события восстановления энергии
        for hour in range(6, 25, 6):  # Каждые 6 часов
            if hour * 60.0 <= 1440.0:  # В пределах дня
                energy_event = EnergyRecoveryEvent(hour * 60.0)
                self.add_event(energy_event, EventPriority.SYSTEM, hour * 60.0)
        
    async def run_simulation(self, duration_days: float = 1.0) -> None:
        """
        Запускает основной цикл симуляции.
        
        Args:
            duration_days: Продолжительность симуляции в днях
        """
        if not self.simulation_id:
            raise RuntimeError("Simulation not initialized. Call initialize() first.")
            
        self._running = True
        end_time = duration_days * 1440.0  # Конвертируем дни в минуты
        self._simulation_start_real = time.time()
        
        logger.info(json.dumps({
            "event": "simulation_started",
            "simulation_id": str(self.simulation_id),
            "duration_days": duration_days,
            "end_time": end_time,
            "agents_count": len(self.agents),
            "realtime_mode": settings.ENABLE_REALTIME,
            "speed_factor": settings.SIM_SPEED_FACTOR
        }, default=str))
        
        events_processed = 0
        agent_actions_scheduled = 0
        
        # Логируем начальное состояние очереди
        # Временно отключаем логирование очереди событий из-за проблем с UUID
        # self._log_event_queue_status()
        
        # ИСПРАВЛЕНИЕ: Планируем начальные действия агентов для заполнения очереди
        initial_scheduled = await self._schedule_seed_actions()
        agent_actions_scheduled += initial_scheduled
        
        logger.info(json.dumps({
            "event": "initial_actions_scheduled", 
            "scheduled_count": initial_scheduled,
            "queue_size": len(self.event_queue)
        }, default=str))
        
        try:
            while self._running and self.current_time < end_time:
                # Обработать следующее событие из очереди
                if self.event_queue:
                    priority_event = heapq.heappop(self.event_queue)
                    
                    # Конвертировать sim_time в real_time для realtime режима
                    if priority_event.event.timestamp_real is None:
                        priority_event.event.timestamp_real = (
                            self._simulation_start_real + 
                            priority_event.timestamp * 60.0 / settings.SIM_SPEED_FACTOR
                        )
                    
                    # Ожидание до времени события в realtime режиме
                    if settings.ENABLE_REALTIME:
                        await self.clock.sleep_until(priority_event.timestamp)
                    
                    self.current_time = priority_event.timestamp
                    
                    # Обработать событие
                    await self._process_event(priority_event.event)
                    events_processed += 1
                    
                    # Проверить batch commit
                    if self._should_commit_batch():
                        await self._batch_commit_states()
                
                # Запланировать новые действия агентов после каждого события
                if events_processed % 50 == 0:  # ИСПРАВЛЕНИЕ: каждые 50 событий вместо 10
                    scheduled = await self._schedule_agent_actions()
                    agent_actions_scheduled += scheduled
                    # Логируем состояние очереди каждые 50 событий
                    # self._log_event_queue_status()
                else:
                    # Если очередь пуста, продвигаем время и планируем действия
                    if not self.event_queue:
                        self.current_time += 5.0  # Продвигаем на 5 минут симуляции
                        scheduled = await self._schedule_agent_actions()
                        agent_actions_scheduled += scheduled
                
                # Небольшая пауза для cooperative multitasking
                await asyncio.sleep(0.1 if settings.ENABLE_REALTIME else 0.001)
                
        except Exception as e:
            logger.error(json.dumps({
                "event": "simulation_error",
                "error": str(e),
                "current_time": self.current_time,
                "events_processed": events_processed
            }, default=str))
            raise
        finally:
            # Финальный batch commit
            await self._batch_commit_states()
            
            # ИСПРАВЛЕНИЕ: Обновить статус симуляции на COMPLETED с end_time
            await self.db_repo.update_simulation_status(
                self.simulation_id, 
                "COMPLETED",
                datetime.utcnow()
            )
            
            logger.info(json.dumps({
                "event": "simulation_completed",
                "simulation_id": str(self.simulation_id),
                "duration_minutes": self.current_time,
                "events_processed": events_processed,
                "agent_actions_scheduled": agent_actions_scheduled,
                "final_agents": len(self.agents),
                "final_trends": len(self.active_trends)
            }, default=str))
        
    async def _process_event(self, event: BaseEvent) -> None:
        """
        Обрабатывает одно событие из очереди.
        
        Args:
            event: Событие для обработки
        """
        start_time = datetime.utcnow()
        
        try:
            # Обработать событие
            event.process(self)
            
            # ИСПРАВЛЕНИЕ: Определяем agent_id и trend_id на основе типа события
            agent_id = None
            trend_id = None
            
            # События агентов имеют agent_id
            if hasattr(event, 'agent_id'):
                agent_id = event.agent_id
                
            # События трендов имеют trend_id  
            if hasattr(event, 'trend_id'):
                trend_id = event.trend_id
                
            # Системные события НЕ имеют agent_id или trend_id
            # (EnergyRecoveryEvent, DailyResetEvent, SaveDailyTrendEvent)
            
            # Записать событие в БД ВСЕГДА после обработки
            from ..db.models import Event as DBEvent
            db_event = DBEvent(
                simulation_id=self.simulation_id,
                event_type=event.__class__.__name__,
                priority=event.priority,
                timestamp=event.timestamp,
                agent_id=agent_id,  # NULL для системных событий
                trend_id=trend_id,  # NULL если не связано с трендом
                event_data={
                    "topic": getattr(event, 'topic', None),
                    "law_type": getattr(event, 'law_type', None),
                    "weather_type": getattr(event, 'weather_type', None),
                    "event_id": str(event.event_id),
                    "sim_time": event.timestamp,
                    "real_time": event.timestamp_real
                },
                processed_at=datetime.utcnow()
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            db_event.processing_duration_ms = processing_time
            
            # Принудительно сохраняем событие в БД
            await self.db_repo.create_event(db_event)
            
            # Проверка на принудительный commit после критических событий
            if getattr(self, '_force_commit_after_this_event', False):
                await self._batch_commit_states()
                self._force_commit_after_this_event = False
                
        except Exception as e:
            logger.error(json.dumps({
                "event": "event_processing_error",
                "event_type": event.__class__.__name__,
                "event_id": str(event.event_id),
                "error": str(e),
                "timestamp": event.timestamp
            }, default=str))
            raise
        
    async def _schedule_seed_actions(self) -> int:
        """
        Создает первичные seed события для агентов, подходящих для PublishPost.
        
        Селективно выбирает агентов на основе их атрибутов:
        - Достаточная энергия (>= 1.5)  
        - Достаточный временной бюджет (>= 2)
        - Высокая социальная активность (social_status >= 2.0)
        - Склонность к публикациям (trend_receptivity >= 2.0)
        """
        scheduled_count = 0
        context = SimulationContext(
            current_time=self.current_time,
            active_trends=self.active_trends,
            affinity_map=self.affinity_map
        )
        
        # Селективный отбор подходящих агентов для seed событий
        suitable_agents = []
        for agent in self.agents:
            if (agent.energy_level >= 1.5 and 
                agent.time_budget >= 2 and
                agent.social_status >= 2.0 and
                agent.trend_receptivity >= 2.0):
                suitable_agents.append(agent)
        
        # Ограничиваем количество seed событий (10-20% от подходящих агентов)
        import random
        seed_count = max(1, min(len(suitable_agents), int(len(suitable_agents) * 0.15)))
        selected_agents = random.sample(suitable_agents, seed_count)
        
        logger.info(json.dumps({
            "event": "seed_selection",
            "total_agents": len(self.agents),
            "suitable_agents": len(suitable_agents),
            "selected_for_seed": seed_count,
            "timestamp": self.current_time
        }, default=str))
        
        # Создаем seed события с распределением по времени
        time_slots = []
        if selected_agents:
            # Равномерно распределяем события в первые 60 минут
            interval = 60.0 / len(selected_agents)
            for i in range(len(selected_agents)):
                base_time = i * interval
                # Добавляем небольшой случайный разброс ±5 минут
                jitter = random.uniform(-5.0, 5.0)
                time_slots.append(max(1.0, base_time + jitter))
        
        for i, agent in enumerate(selected_agents):
            # Проверяем ежедневный лимит действий (43 в день)
            if not self._can_agent_act_today(agent.id):
                continue
                
            # Агент принимает решение о теме
            topic = agent._select_best_topic(context)
            if topic:
                # Используем предрассчитанный временной слот
                delay = time_slots[i] if i < len(time_slots) else random.uniform(1.0, 60.0)
                
                action_event = PublishPostAction(
                    agent_id=agent.id,
                    topic=topic,
                    timestamp=self.current_time + delay
                )
                
                self.add_event(action_event, EventPriority.AGENT_ACTION, action_event.timestamp)
                self._track_agent_daily_action(agent.id)
                scheduled_count += 1
                
                logger.debug(json.dumps({
                    "event": "seed_action_scheduled",
                    "agent_id": str(agent.id),
                    "topic": topic,
                    "delay_minutes": delay,
                    "timestamp": action_event.timestamp
                }, default=str))
        
        return scheduled_count

    def _can_agent_act_today(self, agent_id: UUID) -> bool:
        """Проверяет может ли агент еще действовать сегодня (лимит 43 действия)."""
        current_day = int(self.current_time // 1440)
        day_key = f"{agent_id}_{current_day}"
        
        if not hasattr(self, '_daily_action_counts'):
            self._daily_action_counts = {}
            
        current_count = self._daily_action_counts.get(day_key, 0)
        return current_count < 43

    def _track_agent_daily_action(self, agent_id: UUID) -> None:
        """Отслеживает количество действий агента за день."""
        current_day = int(self.current_time // 1440)
        day_key = f"{agent_id}_{current_day}"
        
        if not hasattr(self, '_daily_action_counts'):
            self._daily_action_counts = {}
            
        self._daily_action_counts[day_key] = self._daily_action_counts.get(day_key, 0) + 1

    def _process_update_state_batch(self, update_state_batch: List[Dict]) -> None:
        """
        Пакетная обработка updatestate для множества агентов.
        
        ВАЖНО: Изменения записываются в person_attribute_history, а не создают новых агентов.
        
        Args:
            update_state_batch: Список пакетов изменений состояния агентов
        """
        for update_state in update_state_batch:
            agent_id = update_state["agent_id"]
            agent = next((a for a in self.agents if str(a.id) == str(agent_id)), None)
            if not agent:
                continue
            for attr_name, delta in update_state["attribute_changes"].items():
                old_value = getattr(agent, attr_name, None)
                # Применяем изменение
                if attr_name in ["energy_level", "financial_capability", "trend_receptivity", "social_status"]:
                    new_value = max(0.0, min(5.0, old_value + delta))
                elif attr_name == "time_budget":
                    new_value = max(0, min(5, int(old_value + delta)))
                else:
                    new_value = old_value + delta
                setattr(agent, attr_name, new_value)
                history_record = {
                    "type": "attribute_history",
                    "person_id": agent_id,
                    "simulation_id": self.simulation_id,
                    "attribute_name": attr_name,
                    "old_value": old_value,
                    "new_value": new_value,
                    "delta": delta,
                    "reason": update_state["reason"],
                    "source_trend_id": update_state.get("source_trend_id"),
                    "change_timestamp": update_state["timestamp"]
                }
                self.add_to_batch_update(history_record)
            person_update = {
                "type": "person_state",
                "id": agent_id,
                "reason": update_state["reason"],
                "source_trend_id": update_state.get("source_trend_id"),
                "timestamp": update_state["timestamp"]
            }
            for attr, delta in update_state["attribute_changes"].items():
                person_update[attr] = getattr(agent, attr, None)
            self.add_to_batch_update(person_update)
        logger.info(json.dumps({
            "event": "update_state_batch_processed",
            "batch_size": len(update_state_batch),
            "timestamp": self.current_time
        }, default=str))

    def _schedule_actions_batch(self, new_actions_batch: List[Dict]) -> int:
        """
        Пакетное планирование новых действий агентов.
        
        Args:
            new_actions_batch: Список новых действий для планирования
            
        Returns:
            Количество запланированных действий
        """
        scheduled_count = 0
        
        for action_data in new_actions_batch:
            agent_id = action_data["agent_id"]
            action_type = action_data["action_type"]
            timestamp = action_data["timestamp"]
            
            if action_type == "PublishPostAction":
                action_event = PublishPostAction(
                    agent_id=agent_id,
                    topic=action_data["topic"],
                    timestamp=timestamp,
                    trigger_trend_id=action_data.get("trigger_trend_id")
                )
                
                self.add_event(action_event, EventPriority.AGENT_ACTION, timestamp)
                self._track_agent_daily_action(agent_id)
                scheduled_count += 1
                
                logger.debug(json.dumps({
                    "event": "batch_action_scheduled",
                    "agent_id": str(agent_id),
                    "action_type": action_type,
                    "topic": action_data["topic"],
                    "timestamp": timestamp,
                    "trigger_trend": str(action_data.get("trigger_trend_id", ""))
                }, default=str))
        
        return scheduled_count
        
    async def _schedule_agent_actions(self) -> int:
        """
        Планирует новые действия СУЩЕСТВУЮЩИХ агентов на основе текущего состояния симуляции.
        
        ВАЖНО: НЕ создает новых агентов - только работает с уже созданными.
        Вызывается периодически для пополнения очереди событий.
        
        Returns:
            Количество запланированных действий
        """
        scheduled_count = 0
        context = SimulationContext(
            current_time=self.current_time,
            active_trends=self.active_trends,
            affinity_map=self.affinity_map
        )
        
        # Инициализируем кулдауны если нужно
        if not hasattr(self, '_agent_action_cooldowns'):
            self._agent_action_cooldowns = {}
        
        # Работаем ТОЛЬКО с уже созданными агентами
        eligible_agents = []
        for agent in self.agents:
            if agent.energy_level <= 0 or agent.time_budget <= 0:
                continue
                
            # Проверяем ежедневный лимит действий
            if not self._can_agent_act_today(agent.id):
                continue
                
            # Проверяем кулдаун агента (минимум 30 минут между действиями)
            last_action_time = self._agent_action_cooldowns.get(agent.id, 0)
            if self.current_time - last_action_time < 30.0:
                continue
                
            eligible_agents.append(agent)
        
        # Ограничиваем количество действий до 10% от доступных агентов за один вызов
        import random
        max_actions = max(1, min(len(eligible_agents), int(len(eligible_agents) * 0.1)))
        selected_agents = random.sample(eligible_agents, min(max_actions, len(eligible_agents)))
        
        for agent in selected_agents:
            # Агент принимает решение
            action_type = agent.decide_action(context)
            if not action_type:
                continue
                
            # Создать событие действия
            if action_type == "PublishPostAction":
                topic = agent._select_best_topic(context)
                if topic:
                    # Случайная задержка от 1 до 30 минут
                    delay = random.uniform(1.0, 30.0)
                    
                    action_event = PublishPostAction(
                        agent_id=agent.id,
                        topic=topic,
                        timestamp=self.current_time + delay
                    )
                    
                    self.add_event(action_event, EventPriority.AGENT_ACTION, action_event.timestamp)
                    self._track_agent_daily_action(agent.id)
                    
                    # Устанавливаем кулдаун для агента
                    self._agent_action_cooldowns[agent.id] = self.current_time
                    
                    scheduled_count += 1
        
        if scheduled_count > 0:
            logger.debug(json.dumps({
                "event": "agent_actions_scheduled",
                "eligible_agents": len(eligible_agents),
                "selected_agents": len(selected_agents),
                "scheduled_count": scheduled_count,
                "timestamp": self.current_time
            }, default=str))
        
        return scheduled_count

    def add_event(self, event: BaseEvent, priority: int, timestamp: float) -> None:
        """
        Добавляет событие в приоритетную очередь.
        
        Args:
            event: Событие для добавления
            priority: Приоритет события (1-5)
            timestamp: Время выполнения
        """
        priority_event = PriorityEvent(priority, timestamp, event)
        heapq.heappush(self.event_queue, priority_event)
        
    def add_to_batch_update(self, update: Dict[str, Any]) -> None:
        """Добавляет обновление в batch очередь."""
        self._batch_updates.append(update)
        
    def _should_commit_batch(self) -> bool:
        """Проверяет нужно ли выполнить batch commit."""
        # Commit по размеру
        if len(self._batch_updates) >= self.batch_size:
            return True
            
        # Commit по времени (адаптированному к realtime режиму)
        if settings.ENABLE_REALTIME:
            # В realtime режиме используем wall-clock время
            time_since_last = time.time() - self._last_commit_time
            timeout_seconds = settings.get_batch_timeout_seconds()
            if time_since_last >= timeout_seconds:
                return True
        else:
            # В fast режиме используем sim время
            if self.current_time - self._last_batch_commit >= self.batch_timeout_minutes:
                return True
            
        return False
        
    async def _batch_commit_states(self) -> None:
        """
        Выполняет batch commit накопленных обновлений состояния.
        
        ВАЖНО: Сохраняет изменения в person_attribute_history и обновляет состояния агентов.
        
        Включает ретраи с экспоненциальным backoff при ошибках.
        """
        if not self._batch_updates:
            return
            
        updates_count = len(self._batch_updates)
        retry_attempts = settings.BATCH_RETRY_ATTEMPTS
        backoffs = settings.get_batch_retry_backoffs()
        
        for attempt in range(retry_attempts):
            try:
                start_time = time.time()
                
                # Разделить обновления по типам
                person_updates = [u for u in self._batch_updates if u.get("type") == "person_state"]
                history_records = [u for u in self._batch_updates if u.get("type") == "attribute_history"]
                trend_updates = [u for u in self._batch_updates if u.get("type") == "trend_interaction"]
                trend_creations = [u for u in self._batch_updates if u.get("type") == "trend_creation"]
                
                # ИСПРАВЛЕНИЕ: Сохранить записи истории атрибутов
                if history_records:
                    from ..db.models import PersonAttributeHistory
                    for history_data in history_records:
                        # Создаем DB модель истории атрибутов
                        db_history = PersonAttributeHistory(
                            person_id=history_data["person_id"],
                            simulation_id=history_data["simulation_id"],
                            attribute_name=history_data["attribute_name"],
                            old_value=history_data["old_value"],
                            new_value=history_data["new_value"],
                            delta=history_data["delta"],
                            reason=history_data["reason"],
                            source_trend_id=history_data.get("source_trend_id"),
                            change_timestamp=history_data["change_timestamp"]
                        )
                        await self.db_repo.create_person_attribute_history(db_history)
                
                # ИСПРАВЛЕНИЕ: Обновить состояния агентов
                if person_updates:
                    # Преобразуем в формат ожидаемый bulk_update_persons
                    formatted_updates = []
                    for update in person_updates:
                        formatted_update = {
                            'id': update['id'],  # Основной ключ для UPDATE
                        }
                        # Добавляем только измененные атрибуты (исключаем мета-поля)
                        for key, value in update.items():
                            if key not in ['type', 'id', 'reason', 'source_trend_id', 'timestamp']:
                                formatted_update[key] = value
                        formatted_updates.append(formatted_update)
                    
                    await self.db_repo.bulk_update_persons(formatted_updates)
                
                # ИСПРАВЛЕНИЕ: Создать новые тренды в БД
                if trend_creations:
                    from ..db.models import Trend as DBTrend
                    for trend_data in trend_creations:
                        # Создаем DB модель из данных
                        db_trend = DBTrend(
                            trend_id=trend_data["trend_id"],
                            simulation_id=trend_data["simulation_id"],
                            topic=trend_data["topic"],
                            originator_id=trend_data["originator_id"],
                            base_virality_score=trend_data["base_virality_score"],
                            coverage_level=trend_data["coverage_level"]
                        )
                        await self.db_repo.create_trend(db_trend)
                
                # ИСПРАВЛЕНИЕ: Сохранить взаимодействия с трендами
                if trend_updates:
                    for update in trend_updates:
                        await self.db_repo.increment_trend_interactions(update["trend_id"])
                
                commit_time = (time.time() - start_time) * 1000
                
                # Очистить batch
                self._batch_updates.clear()
                self._last_batch_commit = self.current_time
                
                logger.info(json.dumps({
                    "event": "batch_commit_success",
                    "simulation_id": str(self.simulation_id),
                    "updates_count": updates_count,
                    "history_records": len(history_records),
                    "person_updates": len(person_updates),
                    "trend_updates": len(trend_updates),
                    "trend_creations": len(trend_creations),
                    "commit_time_ms": commit_time,
                    "attempt": attempt + 1
                }, default=str))
                return
                
            except Exception as e:
                if attempt < retry_attempts - 1:
                    backoff_time = backoffs[min(attempt, len(backoffs) - 1)]
                    logger.warning(json.dumps({
                        "event": "batch_commit_retry",
                        "error": str(e),
                        "attempt": attempt + 1,
                        "backoff_seconds": backoff_time
                    }, default=str))
                    await asyncio.sleep(backoff_time)
                else:
                    logger.error(json.dumps({
                        "event": "batch_commit_failed",
                        "error": str(e),
                        "updates_lost": updates_count,
                        "final_attempt": attempt + 1
                    }, default=str))
                    # Очистить batch даже при ошибке, чтобы избежать накопления
                    self._batch_updates.clear()
        
    async def archive_inactive_trends(self) -> None:
        """
        Архивирует неактивные тренды (без взаимодействий 3+ дня).
        """
        current_datetime = datetime.utcnow() - timedelta(minutes=self.current_time)
        archived_count = 0
        
        trends_to_remove = []
        for trend_id, trend in self.active_trends.items():
            if not trend.is_active(current_datetime, self.trend_archive_threshold_days):
                trends_to_remove.append(trend_id)
                archived_count += 1
                
        # Удалить неактивные тренды
        for trend_id in trends_to_remove:
            del self.active_trends[trend_id]
            
        if archived_count > 0:
            logger.info(json.dumps({
                "event": "trends_archived",
                "archived_count": archived_count,
                "active_remaining": len(self.active_trends),
                "timestamp": self.current_time
            }, default=str))
        
    def get_simulation_stats(self) -> Dict:
        """
        Возвращает статистику текущего состояния симуляции.
        
        Returns:
            Словарь с метриками симуляции
        """
        active_agents = sum(1 for agent in self.agents if agent.energy_level > 0)
        
        return {
            "simulation_id": str(self.simulation_id) if self.simulation_id else None,
            "current_time": self.current_time,
            "active_agents": active_agents,
            "total_agents": len(self.agents),
            "active_trends": len(self.active_trends),
            "queue_size": len(self.event_queue),
            "pending_batches": len(self._batch_updates),
            "running": self._running
        }
        
    async def shutdown(self) -> None:
        """Graceful shutdown симуляции."""
        self._running = False
        
        # Финальный commit
        await self._batch_commit_states()
        
        logger.info(json.dumps({
            "event": "simulation_shutdown",
            "final_time": self.current_time,
            "final_stats": self.get_simulation_stats()
        }, default=str))
        
    def clear_event_queue(self) -> int:
        """
        Очищает очередь событий и возвращает количество удаленных событий.
        
        Returns:
            Количество очищенных событий
        """
        cleared_count = len(self.event_queue)
        self.event_queue.clear()
        
        logger.info(json.dumps({
            "event": "event_queue_cleared",
            "simulation_id": str(self.simulation_id) if self.simulation_id else None,
            "cleared_events": cleared_count,
            "current_time": self.current_time
        }, default=str))
        
        return cleared_count
        
    async def stop_simulation(self, method: str = "graceful") -> None:
        """
        Останавливает симуляцию с указанным методом.
        
        Args:
            method: "graceful" или "force"
        """
        stop_start_time = time.time()
        
        logger.info(json.dumps({
            "event": "simulation_stop_initiated",
            "simulation_id": str(self.simulation_id) if self.simulation_id else None,
            "method": method,
            "current_time": self.current_time,
            "queue_size": len(self.event_queue),
            "pending_batches": len(self._batch_updates)
        }, default=str))
        
        if method == "graceful":
            # Graceful stop: завершить текущие операции
            self._running = False
            
            # Финальный batch commit
            await self._batch_commit_states()
            
            # Очистить очередь событий
            cleared_events = self.clear_event_queue()
            
            # Обновить статус симуляции в БД
            if self.simulation_id:
                await self.db_repo.update_simulation_status(
                    self.simulation_id, 
                    "STOPPED",
                    datetime.utcnow()
                )
                
        elif method == "force":
            # Force stop: немедленная остановка
            self._running = False
            
            # Очистить очередь без batch commit
            cleared_events = self.clear_event_queue()
            
            # Принудительно завершить в БД
            if self.simulation_id:
                await self.db_repo.force_complete_simulation(self.simulation_id)
                
        stop_duration = time.time() - stop_start_time
        
        logger.info(json.dumps({
            "event": "simulation_stopped",
            "simulation_id": str(self.simulation_id) if self.simulation_id else None,
            "method": method,
            "stop_duration_seconds": stop_duration,
            "events_cleared": cleared_events,
            "final_time": self.current_time,
            "data_preserved": method == "graceful"
        }, default=str)) 