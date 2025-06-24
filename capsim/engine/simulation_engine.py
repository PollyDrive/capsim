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
        
    async def initialize(self, num_agents: int = 1000) -> None:
        """
        Инициализирует симуляцию с заданным количеством агентов.
        
        Args:
            num_agents: Количество агентов для создания
        """
        logger.info(json.dumps({
            "event": "simulation_initializing",
            "num_agents": num_agents,
            "batch_size": self.batch_size
        }))
        
        # Создать запуск симуляции
        simulation_run = await self.db_repo.create_simulation_run(
            num_agents=num_agents,
            duration_days=1,  # По умолчанию 1 день
            configuration={
                "batch_size": self.batch_size,
                "batch_timeout": self.batch_timeout_minutes,
                "trend_archive_days": self.trend_archive_threshold_days
            }
        )
        self.simulation_id = simulation_run.run_id
        
        # Загрузить affinity map из БД
        self.affinity_map = await self.db_repo.load_affinity_map()
        
        # НОВАЯ ЛОГИКА: проверяем существующих агентов для данной симуляции
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
            }))
        else:
            # Недостаточно агентов - создаем недостающих
            agents_to_create_count = num_agents - existing_count
            
            # Генерируем недостающих агентов согласно ТЗ распределению
            profession_distribution = [
                ("Teacher", int(agents_to_create_count * 0.20)),      # 20%
                ("ShopClerk", int(agents_to_create_count * 0.18)),    # 18%
                ("Developer", int(agents_to_create_count * 0.12)),    # 12%
                ("Unemployed", int(agents_to_create_count * 0.09)),   # 9%
                ("Businessman", int(agents_to_create_count * 0.08)),  # 8%
                ("Artist", int(agents_to_create_count * 0.08)),       # 8%
                ("Worker", int(agents_to_create_count * 0.07)),       # 7%
                ("Blogger", int(agents_to_create_count * 0.05)),      # 5%
                ("SpiritualMentor", int(agents_to_create_count * 0.03)), # 3%
                ("Philosopher", int(agents_to_create_count * 0.02)),  # 2%
                ("Politician", int(agents_to_create_count * 0.01)),   # 1%
                ("Doctor", int(agents_to_create_count * 0.01)),       # 1%
            ]
            
            # Корректируем для точного количества
            total_assigned = sum(count for _, count in profession_distribution)
            if total_assigned < agents_to_create_count:
                remaining = agents_to_create_count - total_assigned
                profession_distribution[0] = ("Teacher", profession_distribution[0][1] + remaining)
            
            agents_to_create = []
            for profession, count in profession_distribution:
                for _ in range(count):
                    agent = Person.create_random_agent(profession, self.simulation_id)
                    agents_to_create.append(agent)
                
            # Создаем только недостающих агентов
            if agents_to_create:
                await self.db_repo.bulk_create_persons(agents_to_create)
            
            # Объединяем существующих и новых агентов
            self.agents = existing_agents + agents_to_create
            
            logger.info(json.dumps({
                "event": "agents_supplemented",
                "simulation_id": str(self.simulation_id),
                "existing_count": existing_count,
                "created_count": len(agents_to_create),
                "total_count": len(self.agents),
                "requested_count": num_agents
            }))
        
        # Загрузить начальные тренды (если есть)
        existing_trends = await self.db_repo.get_active_trends(self.simulation_id)
        for trend in existing_trends:
            self.active_trends[str(trend.trend_id)] = trend
        
        # Запланировать системные события
        self._schedule_system_events()
        
        logger.info(json.dumps({
            "event": "simulation_initialized",
            "simulation_id": str(self.simulation_id),
            "agents_created": len(self.agents),
            "affinity_topics": len(self.affinity_map),
            "system_events_scheduled": len(self.event_queue)
        }))
        
    def _schedule_system_events(self) -> None:
        """Планирует системные события."""
        # Первое восстановление энергии через 6 часов
        energy_event = EnergyRecoveryEvent(360.0)
        self.add_event(energy_event, EventPriority.SYSTEM, 360.0)
        
        # Первый сброс времени в конце дня (1440 минут)
        reset_event = DailyResetEvent(1440.0)
        self.add_event(reset_event, EventPriority.SYSTEM, 1440.0)
        
        # Первое сохранение статистики в конце дня
        save_event = SaveDailyTrendEvent(1440.0)
        self.add_event(save_event, EventPriority.SYSTEM, 1440.0)
        
    async def run_simulation(self, duration_days: int = 1) -> None:
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
        }))
        
        events_processed = 0
        agent_actions_scheduled = 0
        
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
                # вместо батчевого планирования каждые 15 минут
                if events_processed % 10 == 0:  # Каждые 10 событий
                    scheduled = await self._schedule_agent_actions()
                    agent_actions_scheduled += scheduled
                else:
                    # Если очередь пуста, продвигаем время и планируем действия
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
            }))
            raise
        finally:
            # Финальный batch commit
            await self._batch_commit_states()
            
            # Обновить статус симуляции
            await self.db_repo.update_simulation_status(
                self.simulation_id, 
                "COMPLETED",
                datetime.utcnow().isoformat()
            )
            
            logger.info(json.dumps({
                "event": "simulation_completed",
                "simulation_id": str(self.simulation_id),
                "duration_minutes": self.current_time,
                "events_processed": events_processed,
                "agent_actions_scheduled": agent_actions_scheduled,
                "final_agents": len(self.agents),
                "final_trends": len(self.active_trends)
            }))
        
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
            
            # Записать событие в БД
            from ..db.models import Event as DBEvent
            db_event = DBEvent(
                simulation_id=self.simulation_id,
                event_type=event.__class__.__name__,
                priority=event.priority,
                timestamp=event.timestamp,
                agent_id=getattr(event, 'agent_id', None),
                trend_id=getattr(event, 'trend_id', None),
                event_data={
                    "topic": getattr(event, 'topic', None),
                    "law_type": getattr(event, 'law_type', None),
                    "weather_type": getattr(event, 'weather_type', None)
                }
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            db_event.processing_duration_ms = processing_time
            
            await self.db_repo.create_event(db_event)
            
        except Exception as e:
            logger.error(json.dumps({
                "event": "event_processing_error",
                "event_type": event.__class__.__name__,
                "event_id": str(event.event_id),
                "error": str(e),
                "timestamp": event.timestamp
            }))
            
    async def _schedule_agent_actions(self) -> int:
        """Планирует действия агентов на основе их решений."""
        scheduled_count = 0
        context = SimulationContext(
            current_time=self.current_time,
            active_trends=self.active_trends,
            affinity_map=self.affinity_map
        )
        
        for agent in self.agents:
            if agent.energy_level <= 0 or agent.time_budget <= 0:
                continue
                
            # Агент принимает решение
            action_type = agent.decide_action(context)
            if not action_type:
                continue
                
            # Создать событие действия
            if action_type == "PublishPostAction":
                topic = agent._select_best_topic(context)
                if topic:
                    # Случайная задержка от 1 до 30 минут
                    import random
                    delay = random.uniform(1.0, 30.0)
                    
                    action_event = PublishPostAction(
                        agent_id=agent.id,
                        topic=topic,
                        timestamp=self.current_time + delay
                    )
                    
                    self.add_event(action_event, EventPriority.AGENT_ACTION, action_event.timestamp)
                    scheduled_count += 1
        
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
                trend_updates = [u for u in self._batch_updates if u.get("type") == "trend_interaction"]
                
                # Сохранить обновления персонажей
                if person_updates:
                    await self.db_repo.bulk_update_persons(person_updates)
                
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
                    "person_updates": len(person_updates),
                    "trend_updates": len(trend_updates),
                    "commit_time_ms": commit_time,
                    "attempt": attempt + 1
                }))
                return
                
            except Exception as e:
                if attempt < retry_attempts - 1:
                    backoff_time = backoffs[min(attempt, len(backoffs) - 1)]
                    logger.warning(json.dumps({
                        "event": "batch_commit_retry",
                        "error": str(e),
                        "attempt": attempt + 1,
                        "backoff_seconds": backoff_time
                    }))
                    await asyncio.sleep(backoff_time)
                else:
                    logger.error(json.dumps({
                        "event": "batch_commit_failed",
                        "error": str(e),
                        "updates_lost": updates_count,
                        "final_attempt": attempt + 1
                    }))
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
            }))
        
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
        }))
        
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
        }))
        
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
        }))
        
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
                    datetime.utcnow().isoformat()
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
        })) 