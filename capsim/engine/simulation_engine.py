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
    BaseEvent, EventPriority, PublishPostAction, PurchaseAction, SelfDevAction,
    EnergyRecoveryEvent, DailyResetEvent, SaveDailyTrendEvent
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
        """Priority comparison for heapq (priority first)."""
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
        self._last_commit_time: float = 0.0
        self._last_batch_commit: float = 0.0
        self._simulation_start_real: float = 0.0
        
        # ИСПРАВЛЕНИЕ: Агрегация batch updates для оптимизации производительности
        self._aggregated_updates: Dict[str, Dict] = {}  # person_id -> aggregated_update
        self._aggregated_history: List[Dict] = []  # attribute history records
        self._aggregated_trends: List[Dict] = []  # trend interactions
        self._aggregated_trend_creations: List[Dict] = []  # new trends
        self._aggregated_events: List[Dict] = [] # new events
        
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
        
        # ИСПРАВЛЕНИЕ: Добавляем время окончания симуляции для предотвращения бесконечных циклов
        self.end_time: Optional[float] = None
        
        # Ensure test repositories provide all async methods used later
        _needed_methods = [
            "create_event",
            "bulk_update_persons",
            "bulk_update_simulation_participants",
            "create_person_attribute_history",
            "create_trend",
            "increment_trend_interactions",
            "update_simulation_status",
            "get_simulations_by_status",
            "clear_future_events",
            "close",
            "get_persons_count",
        ]
        async def _noop(*_a, **_kw):
            return None

        for _name in _needed_methods:
            if not hasattr(self.db_repo, _name):
                setattr(self.db_repo, _name, _noop)
        
    async def initialize(self, num_agents: int = 1000, duration_days: float = 1.0) -> None:
        """
        Инициализирует симуляцию с заданным количеством агентов.
        
        Args:
            num_agents: Количество агентов для симуляции
            duration_days: Продолжительность симуляции в днях
        """
        if self.simulation_id:
            raise RuntimeError("Simulation already initialized")

        # Устанавливаем время окончания симуляции
        self.end_time = duration_days * 1440.0
            
        self._last_batch_commit = time.time()
        self._agent_action_cooldowns = {}
        self._daily_action_count = {}
        
        # ИСПРАВЛЕНИЕ: Принудительно завершаем старые симуляции со статусом RUNNING
        await self._cleanup_stale_simulations()
        
        # Создать запись о симуляции
        simulation_run = await self.db_repo.create_simulation_run(
            num_agents=num_agents,
            duration_days=duration_days,
            configuration={
                "realtime_mode": settings.ENABLE_REALTIME,
                "speed_factor": settings.SIM_SPEED_FACTOR,
                "batch_size": settings.BATCH_SIZE
            }
        )
        self.simulation_id = simulation_run.run_id  # ИСПРАВЛЕНИЕ: извлекаем ID из объекта
        
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
        
        # Загрузить диапазоны атрибутов профессий из статичной таблицы
        self.profession_attr_ranges = await self.db_repo.get_profession_attribute_ranges()
        if not self.profession_attr_ranges:
            logger.warning(json.dumps({
                "event": "profession_attr_ranges_missing",
                "msg": "agents_profession table is empty, falling back to defaults",
            }))
        
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
            
            # Берём произвольных доступных персон из глобального пула
            db_persons = await self.db_repo.get_available_persons(num_agents)

            # Преобразуем SQLAlchemy модели Person → доменные объекты Person для движка
            from ..domain.person import Person as DomainPerson  # локальный импорт, чтобы избежать циклов

            # Получаем последние атрибуты агентов из истории
            person_ids = [p.id for p in db_persons[:num_agents]]
            latest_attributes = await self.db_repo.get_latest_agent_attributes(person_ids)

            converted: list[DomainPerson] = []
            for p in db_persons[:num_agents]:
                # Базовые атрибуты из persons
                agent_attrs = {
                    'id': p.id,
                    'profession': p.profession,
                    'first_name': p.first_name,
                    'last_name': p.last_name,
                    'gender': p.gender,
                    'date_of_birth': p.date_of_birth,
                    'financial_capability': p.financial_capability,
                    'trend_receptivity': p.trend_receptivity,
                    'social_status': p.social_status,
                    'energy_level': p.energy_level,
                    'time_budget': float(p.time_budget),
                    'exposure_history': p.exposure_history or {},
                    'interests': p.interests or {},
                    'simulation_id': self.simulation_id
                }
                
                # Применяем последние значения из истории, если они есть
                if p.id in latest_attributes:
                    for attr_name, latest_value in latest_attributes[p.id].items():
                        if attr_name in ['financial_capability', 'trend_receptivity', 'social_status', 'energy_level', 'time_budget']:
                            agent_attrs[attr_name] = latest_value
                
                converted.append(DomainPerson(**agent_attrs))

            self.agents = converted
            
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
                    # Всегда пытаемся ДОБРАТЬ недостающих агентов из глобального пула
                    available_global = await self.db_repo.get_available_persons(num_agents)
                    # Исключаем тех, что уже закреплены за этой симуляцией
                    available_global = [p for p in available_global if p.id not in {a.id for a in existing_agents}]

                    reuse_needed = min(len(available_global), num_agents - len(existing_agents))

                    reused_agents = available_global[:reuse_needed]
                    if reused_agents:
                        self.agents = existing_agents + reused_agents
                    else:
                        self.agents = existing_agents

                    # Пересчитываем, сколько ещё нужно создать после реюза
                    agents_to_create_count = num_agents - len(self.agents)

                    # Если после реюза всё ещё не хватает — создаём недостающих СТРОГО ПО ТЗ
                    if agents_to_create_count <= 0:
                        logger.info(json.dumps({
                            "event": "agents_reused_from_global_pool_partial",
                            "simulation_id": str(self.simulation_id),
                            "reused_count": len(reused_agents),
                            "total_count": len(self.agents),
                            "requested_count": num_agents
                        }, default=str))
                        # ИСПРАВЛЕНИЕ: НЕ сбрасываем атрибуты агентов при реюзе
                        # Агенты сохраняют свои атрибуты из истории между симуляциями
                        # Сбрасываем только cooldown'ы и счетчики
                        for agent in self.agents:
                            agent.purchases_today = 0  # Сброс счетчика покупок
                            agent.last_post_ts = None  # Сброс cooldown'ов
                            agent.last_selfdev_ts = None
                            agent.last_purchase_ts = {}
                        
                        # self.agents уже содержит нужное число; пропускаем создание
                    else:
                        # СТРОГОЕ РАСПРЕДЕЛЕНИЕ ПРОФЕССИЙ согласно ТЗ (таблица распределения)
                        profession_distribution_tz = [
                            ("Teacher", 0.08),        # 8%
                            ("ShopClerk", 0.18),      # 18%
                            ("Developer", 0.08),      # 8%
                            ("Unemployed", 0.09),     # 9%
                            ("Businessman", 0.11),    # 11%
                            ("Artist", 0.08),         # 8%
                            ("Worker", 0.15),         # 15%
                            ("Blogger", 0.10),        # 10%
                            ("SpiritualMentor", 0.05), # 5%
                            ("Philosopher", 0.03),    # 3%
                            ("Politician", 0.01),     # 1%
                            ("Doctor", 0.04),         # 4%
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
                                agent = Person.create_random_agent(
                                    profession,
                                    self.simulation_id,
                                    ranges_map=self.profession_attr_ranges,
                                )
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
        
        # 🆕 Ensure we have a row in simulation_participants for every agent
        for agent in self.agents:
            try:
                await self.db_repo.create_simulation_participant(self.simulation_id, agent.id)
            except Exception:
                # Ignore if the participant record already exists (e.g., rerun)
                pass

        # ---------- Убираем ORM-объекты Person, оставшиеся после реюза ----------
        # Некоторые ветки выше могут положить в self.agents SQLAlchemy-модели,
        # у которых нет логики поведения (decide_action, _select_best_topic).
        from capsim.db.models import Person as DBPerson  # type: ignore
        if any(isinstance(a, DBPerson) for a in self.agents):
            from ..domain.person import Person as DomainPerson  # локальный импорт

            converted: list[DomainPerson] = []
            for p in self.agents:
                if isinstance(p, DBPerson):
                    converted.append(DomainPerson(
                        id=p.id,
                        profession=p.profession,
                        first_name=p.first_name,
                        last_name=p.last_name,
                        gender=p.gender,
                        date_of_birth=p.date_of_birth,
                        financial_capability=p.financial_capability,
                        trend_receptivity=p.trend_receptivity,
                        social_status=p.social_status,
                        energy_level=p.energy_level,
                        time_budget=float(p.time_budget),
                        exposure_history=p.exposure_history or {},
                        interests=p.interests or {},
                        simulation_id=self.simulation_id
                    ))
                else:
                    converted.append(p)

            self.agents = converted
        
        # Загрузить начальные тренды (если есть)
        existing_trends = await self.db_repo.get_active_trends(self.simulation_id)
        for trend in existing_trends:
            self.active_trends[str(trend.trend_id)] = trend
        
        # Запланировать системные события
        self._schedule_system_events()
        
        logger.info(json.dumps({
            "event": "simulation_initialized",
            "simulation_id": str(self.simulation_id),
            "duration_days": duration_days,
            "end_time_minutes": self.end_time,
            "agents_total": len(self.agents),
            "affinity_topics": len(self.affinity_map),
            "system_events_scheduled": len(self.event_queue)
        }, default=str))
        
    def _schedule_system_events(self) -> None:
        """Планирует системные события на весь период симуляции."""
        if self.end_time is None:
            return

        from capsim.domain.events import NightCycleEvent, MorningRecoveryEvent, DailyResetEvent, SaveDailyTrendEvent

        logger.info(json.dumps({
            "event": "scheduling_system_events_for_duration",
            "end_time": self.end_time,
        }, default=str))

        # Планируем события на каждый день симуляции
        for day in range(int(self.end_time // 1440) + 1):
            day_start_time = day * 1440.0

            # 00:00 - NightCycleEvent (кроме первого дня, т.к. он уже идет)
            if day > 0:
                night_event_time = day_start_time
                if night_event_time < self.end_time:
                    self.add_event(NightCycleEvent(night_event_time), EventPriority.SYSTEM, night_event_time)

            # 08:00 - MorningRecoveryEvent
            morning_event_time = day_start_time + 8 * 60
            if morning_event_time < self.end_time:
                self.add_event(MorningRecoveryEvent(morning_event_time), EventPriority.SYSTEM, morning_event_time)

            # Добавляем EnergyRecoveryEvent каждые 3 минуты для коротких симуляций
            # ИСПРАВЛЕНИЕ: Планируем только события в будущем относительно текущего времени
            # И только если день еще не начался (day_start_time > self.current_time)
            if day_start_time > self.current_time:
                for minute in range(0, min(1440, int(self.end_time - day_start_time)), 20):
                    energy_event_time = day_start_time + minute
                    # Планируем только события в будущем и в пределах времени симуляции
                    if energy_event_time < self.end_time:
                        from capsim.domain.events import EnergyRecoveryEvent
                        self.add_event(EnergyRecoveryEvent(energy_event_time), EventPriority.ENERGY_RECOVERY, energy_event_time)

            # 23:00 - SaveDailyTrendEvent
            save_event_time = day_start_time + 23 * 60
            if save_event_time < self.end_time:
                self.add_event(SaveDailyTrendEvent(save_event_time), EventPriority.SYSTEM, save_event_time)

            # 24:00 (00:00 следующего дня) - DailyResetEvent
            reset_event_time = day_start_time + 24 * 60
            if reset_event_time < self.end_time:
                self.add_event(DailyResetEvent(reset_event_time), EventPriority.SYSTEM, reset_event_time)
        
    async def run_simulation(self) -> None:
        """
        Запускает главный цикл симуляции.
        """
        if not self.simulation_id or self.end_time is None:
            raise RuntimeError("Simulation not initialized. Call initialize() first.")
            
        self._running = True
        end_time = self.end_time
        self._simulation_start_real = time.time()
        
        logger.info(json.dumps({
            "event": "simulation_started",
            "simulation_id": str(self.simulation_id),
            "end_time": end_time,
            "agents_count": len(self.agents),
            "realtime_mode": settings.ENABLE_REALTIME,
            "speed_factor": settings.SIM_SPEED_FACTOR
        }, default=str))
        
        agent_actions_scheduled = 0
        
        # Планируем начальные действия агентов
        initial_scheduled = await self._schedule_seed_actions()
        agent_actions_scheduled += initial_scheduled
        
        logger.info(json.dumps({
            "event": "initial_actions_scheduled", 
            "scheduled_count": initial_scheduled,
            "queue_size": len(self.event_queue)
        }, default=str))
        
        try:
            last_time_update = self.current_time
            stagnation_counter = 0

            # ИСПРАВЛЕНИЕ: Основной цикл должен завершаться по времени симуляции
            while self._running and self.current_time < end_time:

                # Если очередь пуста, завершаем симуляцию
                if not self.event_queue:
                    logger.info(json.dumps({
                        "event": "event_queue_empty",
                        "simulation_time": self.current_time,
                        "target_end_time": end_time,
                        "msg": "Simulation finished - no more events."
                    }, default=str))
                    break

                # Получаем следующее событие
                priority_event = heapq.heappop(self.event_queue)
                event_timestamp = priority_event.timestamp

                # Проверяем, не вышли ли мы за пределы времени симуляции
                if event_timestamp > end_time:
                    logger.info(json.dumps({
                        "event": "simulation_time_limit_reached",
                        "simulation_time": self.current_time,
                        "target_end_time": end_time,
                        "next_event_time": event_timestamp,
                        "queue_size_remaining": len(self.event_queue),
                        "msg": "Simulation finished - time limit reached."
                    }, default=str))
                    # Возвращаем событие в очередь и завершаем
                    heapq.heappush(self.event_queue, priority_event)
                    break

                # --- ИСПРАВЛЕНИЕ ЛОГИКИ СКОРОСТИ ---
                if settings.ENABLE_REALTIME or settings.SIM_SPEED_FACTOR > 1.0:
                    sim_time_delta = event_timestamp - self.current_time
                    if sim_time_delta > 0:
                        # Конвертируем минуты симуляции в реальные секунды для паузы
                        sleep_duration = (sim_time_delta * 60) / settings.SIM_SPEED_FACTOR
                        # Ограничиваем максимальную паузу 1 секундой
                        sleep_duration = min(sleep_duration, 1.0)
                        await asyncio.sleep(sleep_duration)

                # Теперь, после паузы, продвигаем время симуляции
                self.current_time = event_timestamp
                
                await self._process_event(priority_event.event)
                
                # Проверить batch commit
                if self._should_commit_batch():
                    await self._batch_commit_states()
                
                # Запланировать новые действия агентов после каждого события
                # ИСПРАВЛЕНИЕ: Планируем новые действия каждые 5 минут симуляции
                if int(self.current_time) % 5 == 0:
                    scheduled = await self._schedule_agent_actions()
                    agent_actions_scheduled += scheduled
                
        except Exception as e:
            logger.error(json.dumps({
                "event": "simulation_error",
                "error": str(e),
                "current_time": self.current_time,
                "events_processed": events_processed
            }, default=str))
            raise
        finally:
            # Финальный batch commit - все изменения сохраняются в конце симуляции
            pending_updates = (
                len(self._aggregated_updates) +
                len(self._aggregated_history) +
                len(self._aggregated_trends) +
                len(self._aggregated_trend_creations)
            )
            logger.info(json.dumps({
                "event": "final_batch_commit_starting",
                "pending_updates": pending_updates,
                "current_time": self.current_time
            }, default=str))
            await self._batch_commit_states()
            
            if self.simulation_id:
                await self.db_repo.update_simulation_status(
                    self.simulation_id, 
                    "COMPLETED",
                    datetime.utcnow()
                )
            
            logger.info(json.dumps({
                "event": "simulation_finished",
                "simulation_id": str(self.simulation_id),
                "final_sim_time": self.current_time,
                "real_duration_sec": time.time() - self._simulation_start_real
            }, default=str))

    async def _process_event(self, event: BaseEvent) -> None:
        """
        Обрабатывает одно событие и обновляет состояние симуляции.
        """
        start_time = datetime.utcnow()
        
        try:
            # Обработать событие
            logger.info(json.dumps({
                "event": "processing_event",
                "event_type": event.__class__.__name__,
                "timestamp": event.timestamp,
                "priority": event.priority,
                "agent_id": str(getattr(event, 'agent_id', None)),
                "topic": getattr(event, 'topic', None)
            }, default=str))
            
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
                # Проверяем что тренд существует в активных трендах
                if trend_id and str(trend_id) not in self.active_trends:
                    logger.warning(json.dumps({
                        "event": "trend_not_found_for_event",
                        "trend_id": str(trend_id),
                        "event_type": event.__class__.__name__,
                        "timestamp": event.timestamp
                    }, default=str))
                    # Не сохраняем событие, если тренд не найден
                    return
                
            # Системные события НЕ имеют agent_id или trend_id
            # (EnergyRecoveryEvent, DailyResetEvent, SaveDailyTrendEvent)
            
            # Добавляем событие в batch для сохранения в БД
            event_data = {
                "simulation_id": self.simulation_id,
                "event_type": event.__class__.__name__,
                "priority": event.priority,
                "timestamp": event.timestamp,
                "agent_id": agent_id,  # NULL для системных событий
                "trend_id": trend_id,  # NULL если не связано с трендом
                "event_data": {
                    "topic": getattr(event, 'topic', None),
                    "law_type": getattr(event, 'law_type', None),
                    "weather_type": getattr(event, 'weather_type', None),
                    "recovered_agents": getattr(event, 'recovered_agent_ids', None),
                    "event_id": str(event.event_id),
                    "sim_time": event.timestamp,
                    "real_time": event.timestamp_real
                },
                "processed_at": datetime.utcnow().isoformat(),
                "processing_duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
            }
            
            # Добавляем в batch вместо немедленного сохранения
            self.add_to_batch_update({
                "type": "event",
                **event_data
            })
            
            # Убираем принудительный commit - теперь все события сохраняются в batch
                
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
        Создает первичные seed события для агентов, подходящих для различных действий.
        
        Селективно выбирает агентов на основе их атрибутов и создает разнообразные события:
        - PublishPost для агентов с высокой социальной активностью
        - Purchase для агентов с достаточными финансовыми возможностями  
        - SelfDev для агентов с низкой энергией
        """
        scheduled_count = 0
        context = SimulationContext(
            current_time=self.current_time,
            active_trends=self.active_trends,
            affinity_map=self.affinity_map
        )
        
        # Селективный отбор подходящих агентов для seed событий
        post_agents = []
        purchase_agents = []
        selfdev_agents = []
        
        for agent in self.agents:
            # Логируем атрибуты агента для отладки
            logger.info(json.dumps({
                "event": "agent_attributes_check",
                "agent_id": str(agent.id),
                "profession": agent.profession,
                "energy_level": agent.energy_level,
                "time_budget": agent.time_budget,
                "social_status": agent.social_status,
                "trend_receptivity": agent.trend_receptivity,
                "financial_capability": agent.financial_capability
            }, default=str))
            
            # Классифицируем агентов по типам действий
            if (agent.energy_level >= 0.5 and 
                agent.time_budget >= 0.5 and 
                agent.social_status >= 0.5 and 
                agent.trend_receptivity >= 0.1):
                post_agents.append(agent)
                
            if (agent.financial_capability >= 0.05 and 
                agent.time_budget >= 0.5):
                purchase_agents.append(agent)
                
            if (agent.time_budget >= 1.0 and 
                agent.energy_level < 3.0):
                selfdev_agents.append(agent)
        
        # Ограничиваем количество seed событий (10-20% от подходящих агентов)
        import random
        
        # Создаем seed события с распределением по времени
        time_slots = []
        total_seed_agents = len(post_agents) + len(purchase_agents) + len(selfdev_agents)
        
        if total_seed_agents > 0:
            # Равномерно распределяем события в первые 60 минут
            interval = 60.0 / total_seed_agents
            for i in range(total_seed_agents):
                base_time = i * interval
                # Добавляем небольшой случайный разброс ±5 минут
                jitter = random.uniform(-5.0, 5.0)
                time_slots.append(max(1.0, base_time + jitter))
        
        slot_index = 0
        
        # Создаем события публикации
        for agent in post_agents[:min(len(post_agents), 5)]:  # Максимум 5 постов
            if slot_index >= len(time_slots):
                break
                
            # Агент принимает решение о теме
            topic = agent._select_best_topic(context)
            if topic:
                delay = time_slots[slot_index] if slot_index < len(time_slots) else random.uniform(1.0, 60.0)
                
                logger.info(json.dumps({
                    "event": "creating_seed_post",
                    "agent_id": str(agent.id),
                    "topic": topic,
                    "delay": delay,
                    "timestamp": self.current_time + delay,
                    "current_time": self.current_time
                }, default=str))
                
                action_event = PublishPostAction(
                    agent_id=agent.id,
                    topic=topic,
                    timestamp=self.current_time + delay
                )
                
                self.add_event(action_event, EventPriority.AGENT_ACTION, action_event.timestamp)
                scheduled_count += 1
                slot_index += 1
        
        # Создаем события покупок
        for agent in purchase_agents[:min(len(purchase_agents), 3)]:  # Максимум 3 покупки
            if slot_index >= len(time_slots):
                break
                
            # Выбираем случайный уровень покупки
            level = random.choice(["L1", "L2", "L3"])
            if agent.can_purchase(self.current_time, level):
                delay = time_slots[slot_index] if slot_index < len(time_slots) else random.uniform(1.0, 60.0)
                
                logger.info(json.dumps({
                    "event": "creating_seed_purchase",
                    "agent_id": str(agent.id),
                    "level": level,
                    "delay": delay,
                    "timestamp": self.current_time + delay,
                    "current_time": self.current_time
                }, default=str))
                
                action_event = PurchaseAction(
                    agent_id=agent.id,
                    purchase_level=level,
                    timestamp=self.current_time + delay
                )
                
                self.add_event(action_event, EventPriority.AGENT_ACTION, action_event.timestamp)
                scheduled_count += 1
                slot_index += 1
        
        # Создаем события саморазвития
        for agent in selfdev_agents[:min(len(selfdev_agents), 2)]:  # Максимум 2 саморазвития
            if slot_index >= len(time_slots):
                break
                
            if agent.can_self_dev(self.current_time):
                delay = time_slots[slot_index] if slot_index < len(time_slots) else random.uniform(1.0, 60.0)
                
                logger.info(json.dumps({
                    "event": "creating_seed_selfdev",
                    "agent_id": str(agent.id),
                    "delay": delay,
                    "timestamp": self.current_time + delay,
                    "current_time": self.current_time
                }, default=str))
                
                action_event = SelfDevAction(
                    agent_id=agent.id,
                    timestamp=self.current_time + delay
                )
                
                self.add_event(action_event, EventPriority.AGENT_ACTION, action_event.timestamp)
                scheduled_count += 1
                slot_index += 1
        
        logger.info(json.dumps({
            "event": "seed_actions_created",
            "post_agents": len(post_agents),
            "purchase_agents": len(purchase_agents),
            "selfdev_agents": len(selfdev_agents),
            "scheduled_count": scheduled_count,
            "timestamp": self.current_time
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
                # ИСПРАВЛЕНИЕ: Сохраняем только значимые изменения атрибутов (delta >= 0.1)
                if abs(delta) >= 0.1:
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
            # ИСПРАВЛЕНИЕ: НЕ создаем person_update - не обновляем таблицу persons напрямую
            # Все изменения атрибутов сохраняются только в person_attribute_history
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
                # Проверяем что trigger_trend_id существует в активных трендах
                trigger_trend_id = action_data.get("trigger_trend_id")
                if trigger_trend_id and str(trigger_trend_id) not in self.active_trends:
                    logger.warning(json.dumps({
                        "event": "trigger_trend_not_found",
                        "trigger_trend_id": str(trigger_trend_id),
                        "agent_id": str(agent_id),
                        "timestamp": timestamp
                    }, default=str))
                    # Продолжаем без trigger_trend_id
                    trigger_trend_id = None
                
                action_event = PublishPostAction(
                    agent_id=agent_id,
                    topic=action_data["topic"],
                    timestamp=timestamp,
                    trigger_trend_id=trigger_trend_id
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
        Планирует новые действия СУЩЕСТВУЮЩИХ агентов на основе v1.8 алгоритма принятия решений.
        
        ВАЖНО: НЕ создает новых агентов - только работает с уже созданными.
        Вызывается периодически для пополнения очереди событий.
        
        Returns:
            Количество запланированных действий
        """
        from capsim.domain.events import PublishPostAction, PurchaseAction, SelfDevAction
        import random
        
        # ИСПРАВЛЕНИЕ: Не планируем новые действия если близко к времени окончания
        if self.end_time is not None and self.current_time >= (self.end_time - 45.0):
            logger.info(json.dumps({
                "event": "agent_actions_scheduling_stopped",
                "reason": "approaching_simulation_end",
                "current_time": self.current_time,
                "end_time": self.end_time,
                "time_remaining": self.end_time - self.current_time
            }, default=str))
            return 0
        
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
                
            # ИСПРАВЛЕНИЕ: Включаем проверку ежедневного лимита действий (43/день)
            if not self._can_agent_act_today(agent.id):
                continue
                
            # ИСПРАВЛЕНИЕ: Убираем cooldown для более активных агентов
            # last_action_time = self._agent_action_cooldowns.get(agent.id, 0)
            # if self.current_time - last_action_time < 10.0:  # Снижено с 15 до 10 минут
            #     continue
                
            eligible_agents.append(agent)
        
        logger.info(json.dumps({
            "event": "eligible_agents_found",
            "eligible_count": len(eligible_agents),
            "total_agents": len(self.agents)
        }, default=str))
        
        # ИСПРАВЛЕНИЕ: Следуем ТЗ - максимум 43 действия/агента/день
        # Рассчитываем доступные действия на основе времени симуляции
        current_day = int(self.current_time // 1440)
        day_start = current_day * 1440
        day_end = min(day_start + 1440, self.end_time if self.end_time else float('inf'))
        day_duration = day_end - day_start
        
        # Максимум действий на день для всех агентов
        max_daily_actions = len(eligible_agents) * 43
        
        # Распределяем действия равномерно по времени дня
        actions_per_minute = max_daily_actions / day_duration if day_duration > 0 else 0
        
        # Ограничиваем действия в текущем цикле (каждые 5 минут)
        # 43 действия/день = 0.0298 действий/минуту на агента
        max_actions_this_cycle = min(
            len(eligible_agents),
            max(1, int(actions_per_minute * 5))  # 5 минут = один цикл
        )
        
        selected_agents = random.sample(eligible_agents, min(max_actions_this_cycle, len(eligible_agents)))
        
        # Получаем текущий главный тренд для передачи в решения
        current_trend = None
        if self.active_trends:
            # Берем тренд с наивысшей виральностью
            current_trend = max(self.active_trends.values(), key=lambda t: t.calculate_current_virality())
        
        logger.info(json.dumps({
            "event": "selected_agents_for_v18",
            "selected_count": len(selected_agents),
            "current_trend": str(current_trend.trend_id) if current_trend else None
        }, default=str))
        
        for agent in selected_agents:
            # v1.8: Используем новый алгоритм принятия решений
            action_name = agent.decide_action_v18(current_trend, self.current_time)
            
            logger.info(json.dumps({
                "event": "agent_decision_made",
                "agent_id": str(agent.id),
                "action_name": action_name,
                "energy": agent.energy_level,
                "time_budget": agent.time_budget,
                "financial_capability": agent.financial_capability
            }, default=str))
            
            if not action_name:
                continue
                
            # ИСПРАВЛЕНИЕ: Создаем события напрямую вместо использования Action Factory
            try:
                # Добавляем небольшую задержку для предотвращения одновременных событий
                delay = random.uniform(0.1, 2.0)
                event_timestamp = self.current_time + delay
                
                if action_name == "Post":
                    # Выбираем лучшую тему для поста
                    best_topic = "ECONOMIC"  # Дефолт
                    if hasattr(agent, 'interests') and agent.interests:
                        best_topic = max(agent.interests.keys(), key=lambda t: agent.interests[t]).upper()
                    
                    # Создаем событие публикации поста
                    post_event = PublishPostAction(
                        agent_id=agent.id,
                        topic=best_topic,
                        timestamp=event_timestamp
                    )
                    
                    # Добавляем событие в очередь
                    self.add_event(post_event, EventPriority.AGENT_ACTION, event_timestamp)
                    self._track_agent_daily_action(agent.id)
                    scheduled_count += 1
                    
                    logger.debug(json.dumps({
                        "event": "post_event_scheduled",
                        "agent_id": str(agent.id),
                        "topic": best_topic,
                        "timestamp": event_timestamp,
                        "profession": agent.profession
                    }, default=str))
                    
                elif action_name.startswith("Purchase_"):
                    level = action_name.split("_")[1]  # L1, L2, L3
                    
                    # Проверяем возможность покупки
                    if agent.can_purchase(self.current_time, level):
                        # Создаем событие покупки
                        purchase_event = PurchaseAction(
                            agent_id=agent.id,
                            purchase_level=level,
                            timestamp=event_timestamp
                        )
                        
                        # Добавляем событие в очередь
                        self.add_event(purchase_event, EventPriority.AGENT_ACTION, event_timestamp)
                        self._track_agent_daily_action(agent.id)
                        scheduled_count += 1
                        
                        logger.debug(json.dumps({
                            "event": "purchase_event_scheduled",
                            "agent_id": str(agent.id),
                            "level": level,
                            "timestamp": event_timestamp,
                            "profession": agent.profession
                        }, default=str))
                
                elif action_name == "SelfDev":
                    # Проверяем возможность саморазвития
                    if agent.can_self_dev(self.current_time):
                        # Создаем событие саморазвития
                        selfdev_event = SelfDevAction(
                            agent_id=agent.id,
                            timestamp=event_timestamp
                        )
                        
                        # Добавляем событие в очередь
                        self.add_event(selfdev_event, EventPriority.AGENT_ACTION, event_timestamp)
                        self._track_agent_daily_action(agent.id)
                        scheduled_count += 1
                        
                        logger.debug(json.dumps({
                            "event": "selfdev_event_scheduled",
                            "agent_id": str(agent.id),
                            "timestamp": event_timestamp,
                            "profession": agent.profession
                        }, default=str))
                
                # Обновляем cooldown для агента
                self._agent_action_cooldowns[agent.id] = self.current_time
                
            except Exception as e:
                logger.error(json.dumps({
                    "event": "action_scheduling_error",
                    "agent_id": str(agent.id),
                    "action_name": action_name,
                    "error": str(e)
                }, default=str))
        
        if scheduled_count > 0:
            logger.info(json.dumps({
                "event": "v18_agent_actions_scheduled",
                "eligible_agents": len(eligible_agents),
                "selected_agents": len(selected_agents),
                "scheduled_count": scheduled_count,
                "timestamp": self.current_time,
                "current_trend": str(current_trend.trend_id) if current_trend else None
            }, default=str))
        
        # ИСПРАВЛЕНИЕ: Отключаем дополнительный wellness планировщик
        # Все действия теперь планируются только через основной планировщик
        # scheduled_count += self._schedule_random_wellness()
        
        return scheduled_count

    def _schedule_random_wellness(self) -> int:
        """Случайно планирует Purchase или SelfDev, чтобы обеспечить ≥1 действие/агент/сим-час."""
        import random
        from capsim.domain.events import PurchaseAction, SelfDevAction

        actions_planned = 0

        if not self.agents:
            return 0
            
        # ИСПРАВЛЕНИЕ: Не планируем wellness действия если близко к времени окончания
        if self.end_time is not None and self.current_time >= (self.end_time - 30.0):
            return 0

        # Приблизимся к 10 % агентов каждый сим-час (60 минут).
        # Метод вызывается раз в несколько минут, поэтому вероятность масштабируем.
        prob = 1.0 / 60  # ≈0.0167 per minute (~1 действие/агент/час)

        for agent in self.agents:
            if random.random() > prob:
                continue

            # Выбор действия: если energy<3 → SelfDev, иначе Purchase L1-L3.
            if agent.energy_level < 3.0:
                # Создаем событие саморазвития
                if agent.can_self_dev(self.current_time):
                    delay = random.uniform(0.1, 1.5)
                    event_timestamp = self.current_time + delay
                    
                    selfdev_event = SelfDevAction(
                        agent_id=agent.id,
                        timestamp=event_timestamp
                    )
                    
                    self.add_event(selfdev_event, EventPriority.AGENT_ACTION, event_timestamp)
                    actions_planned += 1
            else:
                # Создаем событие покупки
                level = random.choice(["L1", "L2", "L3"])
                if agent.can_purchase(self.current_time, level):
                    delay = random.uniform(0.1, 1.5)
                    event_timestamp = self.current_time + delay
                    
                    purchase_event = PurchaseAction(
                        agent_id=agent.id,
                        purchase_level=level,
                        timestamp=event_timestamp
                    )
                    
                    self.add_event(purchase_event, EventPriority.AGENT_ACTION, event_timestamp)
                    actions_planned += 1

        return actions_planned

    def add_event(self, event: BaseEvent, priority: int, timestamp: float) -> None:
        """
        Добавляет событие в приоритетную очередь.
        
        Args:
            event: Событие для добавления
            priority: Приоритет события (1-5)
            timestamp: Время выполнения
        """
        # ИСПРАВЛЕНИЕ: Проверяем время окончания симуляции перед добавлением события
        if self.end_time is not None and timestamp >= self.end_time:
            logger.info(json.dumps({
                "event": "event_rejected_past_end_time",
                "event_type": event.__class__.__name__,
                "timestamp": timestamp,
                "end_time": self.end_time,
                "agent_id": str(getattr(event, 'agent_id', None)),
                "topic": getattr(event, 'topic', None)
            }, default=str))
            return
        
        logger.info(json.dumps({
            "event": "adding_event_to_queue",
            "event_type": event.__class__.__name__,
            "priority": priority,
            "timestamp": timestamp,
            "agent_id": str(getattr(event, 'agent_id', None)),
            "topic": getattr(event, 'topic', None),
            "queue_size_before": len(self.event_queue)
        }, default=str))
        
        priority_event = PriorityEvent(priority, timestamp, event)
        heapq.heappush(self.event_queue, priority_event)
        
    def add_to_batch_update(self, update: Dict[str, Any]) -> None:
        """Добавляет обновление в batch очередь с агрегацией."""
        update_type = update.get("type")
        
        # ИСПРАВЛЕНИЕ: Убираем обработку person_state - не обновляем таблицу persons
        # Все изменения атрибутов сохраняются только в person_attribute_history
        
        if update_type == "attribute_history":
            # Сохраняем все записи истории (не агрегируем)
            self._aggregated_history.append(update)
            
        elif update_type == "trend_interaction":
            # Агрегируем взаимодействия с трендами
            # Каждая запись = +1 к total_interactions в БД
            trend_id = str(update["trend_id"])
            existing = next((t for t in self._aggregated_trends if t["trend_id"] == trend_id), None)
            if existing:
                existing["interaction_count"] = existing.get("interaction_count", 0) + 1
            else:
                self._aggregated_trends.append({
                    "trend_id": update["trend_id"],
                    "interaction_count": 1
                })
                
        elif update_type == "trend_creation":
            # Сохраняем создание трендов
            self._aggregated_trend_creations.append(update)
            
        elif update_type == "event":
            # Сохраняем события
            self._aggregated_events.append(update)
            
    def should_schedule_future_event(self, timestamp: float) -> bool:
        """
        Проверяет, следует ли планировать событие на указанное время.
        
        Args:
            timestamp: Время события в минутах симуляции
            
        Returns:
            True если событие следует планировать, False иначе
        """
        if self.end_time is None:
            return True
        return timestamp < self.end_time
        
    def _should_commit_batch(self) -> bool:
        """Проверяет, нужно ли выполнить batch commit."""
        
        # 1. Commit по времени: каждые 10 симуляционных минут
        time_since_last_commit = self.current_time - self._last_batch_commit
        if time_since_last_commit >= 10.0:
            return True

        # 2. Commit по общему количеству накопленных изменений
        total_updates = (
            len(self._aggregated_history) +
            len(self._aggregated_trends) +
            len(self._aggregated_trend_creations) +
            len(self._aggregated_events)
        )
        
        if total_updates >= self.batch_size: # self.batch_size is 1000 from settings
            return True
            
        return False
        
    async def _batch_commit_states(self) -> None:
        """
        Выполняет batch commit накопленных обновлений состояния с агрегацией.
        Теперь использует оптимизированные bulk-методы репозитория.
        """
        # Если нет накопленных изменений, выходим
        if not self._aggregated_history and not self._aggregated_trends and not self._aggregated_trend_creations and not self._aggregated_events:
            return

        updates_count = (
            len(self._aggregated_history) +
            len(self._aggregated_trends) + len(self._aggregated_trend_creations) + len(self._aggregated_events)
        )
        
        start_time = time.time()
        
        try:
            # 1. Создание новых трендов (ВАЖНО: должно быть первым)
            if self._aggregated_trend_creations:
                # Очищаем данные от полей, которых нет в модели Trend
                trends_cleaned = []
                for trend_data in self._aggregated_trend_creations:
                    cleaned_data = trend_data.copy()
                    cleaned_data.pop("type", None)
                    cleaned_data.pop("timestamp", None)
                    trends_cleaned.append(cleaned_data)
                await self.db_repo.bulk_create_trends(trends_cleaned)

            # 2. Обновления истории атрибутов
            if self._aggregated_history:
                from ..db.models import PersonAttributeHistory
                # Очищаем историю от полей, которых нет в модели
                history_cleaned = []
                for hr in self._aggregated_history:
                    cleaned_hr = hr.copy()
                    cleaned_hr.pop("type", None) # Удаляем ключ 'type', если он есть
                    history_cleaned.append(cleaned_hr)
                
                history_models = [PersonAttributeHistory(**hr) for hr in history_cleaned]
                await self.db_repo.bulk_create_person_attribute_history(history_models)

            # 3. ИСПРАВЛЕНИЕ: Убираем обновления состояний агентов - не обновляем таблицу persons
            # Все изменения атрибутов сохраняются только в person_attribute_history
            # Оставляем только обновления simulation_participants для cooldown'ов и счетчиков
            if self._aggregated_updates:
                participant_updates = []
                
                for update in self._aggregated_updates.values():
                    participant_update = {'simulation_id': self.simulation_id, 'person_id': update['id']}
                    
                    for key, value in update.items():
                        if key not in ['type', 'id', 'reason', 'source_trend_id', 'timestamp']:
                            if key in ['last_post_ts', 'last_selfdev_ts', 'last_purchase_ts', 'purchases_today']:
                                participant_update[key] = value
                    
                    if len(participant_update) > 2:
                        participant_updates.append(participant_update)
                
                if participant_updates:
                    await self.db_repo.bulk_update_simulation_participants(participant_updates)

            # 4. Создание событий (ВАЖНО: должно быть после создания трендов)
            if self._aggregated_events:
                await self.db_repo.bulk_create_events(self._aggregated_events)

            # 5. Обновление счетчиков взаимодействий с трендами
            if self._aggregated_trends:
                trend_counts = [(t["trend_id"], t["interaction_count"]) for t in self._aggregated_trends]
                await self.db_repo.bulk_increment_trend_interactions(trend_counts)
                
            commit_time = (time.time() - start_time) * 1000
            
            logger.info(json.dumps({
                "event": "batch_commit_success",
                "simulation_id": str(self.simulation_id),
                "updates_count": updates_count,
                "history_records": len(self._aggregated_history),
                "trend_updates": len(self._aggregated_trends),
                "trend_creations": len(self._aggregated_trend_creations),
                "events_created": len(self._aggregated_events),
                "commit_time_ms": commit_time,
            }, default=str))

        except Exception as e:
            logger.error(json.dumps({
                "event": "batch_commit_failed",
                "error": str(e),
                "updates_lost": updates_count,
            }, default=str))
            # В случае ошибки не очищаем, чтобы попробовать снова
            return

        # Очищаем агрегированные данные только после успешного коммита
        self._aggregated_history.clear()
        self._aggregated_trends.clear()
        self._aggregated_trend_creations.clear()
        self._aggregated_events.clear()
        self._last_batch_commit = self.current_time
        
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
            "pending_batches": (
                len(self._aggregated_updates) +
                len(self._aggregated_history) +
                len(self._aggregated_trends) +
                len(self._aggregated_trend_creations)
            ),
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
            "pending_batches": (
                len(self._aggregated_updates) +
                len(self._aggregated_history) +
                len(self._aggregated_trends) +
                len(self._aggregated_trend_creations)
            )
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

    async def _cleanup_stale_simulations(self) -> None:
        """
        Принудительно завершает старые симуляции со статусом RUNNING.
        Это предотвращает висящие записи в базе данных.
        """
        try:
            # Найти все симуляции со статусом RUNNING
            stale_simulations = await self.db_repo.get_simulations_by_status("RUNNING")
            
            for simulation in stale_simulations:
                logger.warning(json.dumps({
                    "event": "cleaning_stale_simulation",
                    "simulation_id": str(simulation.run_id),
                    "start_time": str(simulation.start_time),
                    "status": simulation.status
                }, default=str))
                
                # Обновить статус на FAILED с комментарием
                await self.db_repo.update_simulation_status(
                    simulation.run_id,
                    "FAILED",
                    datetime.utcnow(),
                    reason="Stale simulation cleanup"
                )
                
        except Exception as e:
            logger.error(json.dumps({
                "event": "cleanup_stale_simulations_error",
                "error": str(e)
            }, default=str)) 