"""
Database repositories for CAPSIM 2.0 - CRUD operations and batch processing.
"""

import json
import logging
from datetime import datetime, date
from typing import List, Dict, Optional, Any, Set, Tuple
from uuid import UUID, uuid4

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, insert, update, delete, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import StaticPool

from .models import (
    SimulationRun, Person, SimulationParticipant, Trend, Event, 
    PersonAttributeHistory, AgentInterests, AffinityMap, DailyTrendSummary,
    TopicInterestMapping, AgentsProfession
)

logger = logging.getLogger(__name__)

# Глобальная переменная для трекинга уникальных имен в сессии
_used_names: Set[str] = set()

def generate_russian_name(gender: str = None) -> Dict[str, str]:
    """
    Генерирует русское имя и фамилию с помощью faker.
    
    Args:
        gender: "male" или "female". Если None, выбирается случайно.
        
    Returns:
        Dict с ключами {"first_name": str, "last_name": str, "gender": str}
        
    Raises:
        ValueError: если не удается сгенерировать уникальное имя после 100 попыток
    """
    global _used_names
    
    fake = Faker("ru_RU")
    
    # Если пол не задан, выбираем случайно
    if gender is None:
        gender = fake.random.choice(["male", "female"])
    
    attempts = 0
    max_attempts = 100
    
    while attempts < max_attempts:
        try:
            if gender == "male":
                first_name = fake.first_name_male()
                last_name = fake.last_name_male()
            else:  # female
                first_name = fake.first_name_female()
                last_name = fake.last_name_female()
            
            # Проверяем что имя содержит только одно слово (без отчества)
            if " " in first_name or " " in last_name:
                attempts += 1
                continue
                
            # Создаем уникальный идентификатор
            full_name = f"{first_name} {last_name}"
            
            # Проверяем уникальность в рамках сессии
            if full_name not in _used_names:
                _used_names.add(full_name)
                return {
                    "first_name": first_name,
                    "last_name": last_name, 
                    "gender": gender
                }
                
        except Exception as e:
            logger.warning(f"Ошибка генерации имени: {e}")
            
        attempts += 1
    
    # Если не удалось сгенерировать уникальное имя
    raise ValueError(f"Не удалось сгенерировать уникальное русское имя после {max_attempts} попыток")

def reset_names_session():
    """Сбрасывает счетчик уникальных имен для новой сессии."""
    global _used_names
    _used_names.clear()

def convert_domain_person_to_db_model(domain_person: "Person") -> Person:
    """
    Конвертирует доменный объект Person в SQLAlchemy модель Person.
    
    Args:
        domain_person: Доменный объект Person
        
    Returns:
        SQLAlchemy модель Person
    """
    return Person(
        id=domain_person.id,
        profession=domain_person.profession,
        first_name=domain_person.first_name,
        last_name=domain_person.last_name,
        gender=domain_person.gender,
        date_of_birth=domain_person.date_of_birth,
        financial_capability=domain_person.financial_capability,
        trend_receptivity=domain_person.trend_receptivity,
        social_status=domain_person.social_status,
        energy_level=domain_person.energy_level,
        time_budget=domain_person.time_budget,
        exposure_history=domain_person.exposure_history,
        interests=domain_person.interests,
        created_at=domain_person.created_at,
        updated_at=datetime.utcnow()
    )

class DatabaseRepository:
    """
    Main repository class for CAPSIM database operations.
    
    Handles:
    - CRUD operations for all entities
    - Batch commit with retry logic
    - Database connection management
    """
    
    def __init__(self, database_url: str, readonly_url: Optional[str] = None):
        self.engine = create_async_engine(database_url, echo=False)
        self.readonly_engine = create_async_engine(readonly_url or database_url, echo=False)
        
        # Session makers
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        self.ReadOnlySession = sessionmaker(
            bind=self.readonly_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Batch processing
        self._batch_updates: List[Dict[str, Any]] = []
        self._batch_size = 100
        self._retry_attempts = 3
        self._retry_backoffs = [1, 2, 4]  # seconds
        
    async def close(self):
        """Close database connections."""
        await self.engine.dispose()
        await self.readonly_engine.dispose()
        
    # Simulation Run operations
    async def create_simulation_run(self, num_agents: int, duration_days: int, 
                                  configuration: Optional[Dict] = None) -> SimulationRun:
        """Create new simulation run."""
        async with self.SessionLocal() as session:
            simulation = SimulationRun(
                num_agents=num_agents,
                duration_days=duration_days,
                configuration=configuration
            )
            session.add(simulation)
            await session.commit()
            await session.refresh(simulation)
            
            logger.info(json.dumps({
                "event": "simulation_created",
                "simulation_id": str(simulation.run_id),
                "num_agents": num_agents,
                "duration_days": duration_days
            }))
            
            return simulation
            
    async def get_simulation_run(self, simulation_id: UUID) -> Optional[SimulationRun]:
        """Get simulation run by ID."""
        async with self.ReadOnlySession() as session:
            result = await session.execute(
                select(SimulationRun).where(SimulationRun.run_id == simulation_id)
            )
            return result.scalar_one_or_none()
            
    async def update_simulation_status(self, simulation_id: UUID, status: str, 
                                     end_time: Optional[datetime] = None, 
                                     reason: Optional[str] = None) -> None:
        """Update simulation status."""
        async with self.SessionLocal() as session:
            stmt = update(SimulationRun).where(
                SimulationRun.run_id == simulation_id
            ).values(status=status)
            
            if end_time:
                stmt = stmt.values(end_time=end_time)
                
            await session.execute(stmt)
            await session.commit()
            
            logger.info(json.dumps({
                "event": "simulation_status_updated",
                "simulation_id": str(simulation_id),
                "status": status,
                "reason": reason
            }))
            
    async def get_active_simulations(self) -> List[SimulationRun]:
        """Get all active (running) simulations."""
        async with self.ReadOnlySession() as session:
            result = await session.execute(
                select(SimulationRun).where(
                    SimulationRun.status.in_(["RUNNING", "ACTIVE", "STOPPING"])
                ).order_by(SimulationRun.start_time.desc())
            )
            return result.scalars().all()
            
    async def get_simulations_by_status(self, status: str) -> List[SimulationRun]:
        """Get simulations by specific status."""
        async with self.ReadOnlySession() as session:
            result = await session.execute(
                select(SimulationRun).where(
                    SimulationRun.status == status
                ).order_by(SimulationRun.start_time.desc())
            )
            return result.scalars().all()
            
    async def clear_future_events(self, simulation_id: UUID, 
                                force: bool = False) -> int:
        """Clear future events for simulation."""
        async with self.SessionLocal() as session:
            # Get current simulation time
            if not force:
                result = await session.execute(
                    select(SimulationRun).where(SimulationRun.run_id == simulation_id)
                )
                simulation = result.scalar_one_or_none()
                if not simulation:
                    return 0
                    
                # Calculate current simulation time
                current_time = (datetime.utcnow() - simulation.start_time).total_seconds() / 60
                
                # Delete future events
                stmt = delete(Event).where(
                    Event.simulation_id == simulation_id,
                    Event.timestamp > current_time
                )
            else:
                # Force delete all events
                stmt = delete(Event).where(Event.simulation_id == simulation_id)
                
            result = await session.execute(stmt)
            await session.commit()
            
            deleted_count = result.rowcount
            logger.info(json.dumps({
                "event": "future_events_cleared",
                "simulation_id": str(simulation_id),
                "deleted_count": deleted_count,
                "force": force
            }))
            
            return deleted_count
            
    async def force_complete_simulation(self, simulation_id: UUID) -> None:
        """Force complete simulation by updating status and end time."""
        async with self.SessionLocal() as session:
            stmt = update(SimulationRun).where(
                SimulationRun.run_id == simulation_id
            ).values(
                status="COMPLETED",
                end_time=datetime.utcnow()
            )
            
            await session.execute(stmt)
            await session.commit()
            
            logger.info(json.dumps({
                "event": "simulation_force_completed",
                "simulation_id": str(simulation_id)
            }))
            
    # Person operations (now global)
    async def create_person(self, person: "Person") -> None:
        """Create a new global person."""
        async with self.SessionLocal() as session:
            # Convert domain object to SQLAlchemy model if needed
            if not hasattr(person, '_sa_instance_state'):
                db_person = convert_domain_person_to_db_model(person)
                session.add(db_person)
            else:
                session.add(person)
            await session.commit()
            
    async def create_simulation_participant(self, simulation_id: UUID, person_id: UUID) -> None:
        """Create a simulation participant record."""
        async with self.SessionLocal() as session:
            participant = SimulationParticipant(
                simulation_id=simulation_id,
                person_id=person_id
            )
            session.add(participant)
            await session.commit()
            
    async def create_person_attribute_history(self, history_record: "PersonAttributeHistory") -> None:
        """Create person attribute history record."""
        async with self.SessionLocal() as session:
            session.add(history_record)
            await session.commit()
            
    async def bulk_create_person_attribute_history(self, history_records: List["PersonAttributeHistory"]) -> None:
        """Bulk create person attribute history records in a single transaction to avoid connection explosion."""
        async with self.SessionLocal() as session:
            # Add all records in one batch and commit once
            session.add_all(history_records)
            await session.commit()
            
    async def bulk_create_persons(self, persons: List["Person"]) -> None:
        """Bulk create persons (now global)."""
        async with self.SessionLocal() as session:
            # Check if we're at the limit
            count_result = await session.execute(select(Person))
            current_count = len(count_result.scalars().all())
            
            if current_count + len(persons) > 1000:
                raise ValueError(f"Cannot create {len(persons)} persons. Current: {current_count}, Limit: 1000")
            
            # Convert domain objects to SQLAlchemy models
            db_persons = [convert_domain_person_to_db_model(person) for person in persons]
            
            # Bulk insert persons
            session.add_all(db_persons)
            await session.commit()
            
            logger.info(json.dumps({
                "event": "persons_bulk_created",
                "count": len(persons),
                "total_persons": current_count + len(persons)
            }))
            
    async def get_persons_count(self) -> int:
        """Get total count of global persons."""
        async with self.ReadOnlySession() as session:
            result = await session.execute(select(Person))
            return len(result.scalars().all())
            
    async def get_persons_for_simulation(self, simulation_id: UUID, limit: int = 1000) -> List["Person"]:
        """Get persons participating in a simulation."""
        async with self.ReadOnlySession() as session:
            # Get participants for this simulation
            result = await session.execute(
                select(SimulationParticipant.person_id)
                .where(SimulationParticipant.simulation_id == simulation_id)
                .limit(limit)
            )
            participant_ids = result.scalars().all()
            
            if not participant_ids:
                return []
            
            # Get the actual person objects
            result = await session.execute(
                select(Person).where(Person.id.in_(participant_ids))
            )
            return result.scalars().all()
            
    async def get_available_persons(self, limit: int = 1000) -> List["Person"]:
        """Get available global persons for new simulations."""
        async with self.ReadOnlySession() as session:
            result = await session.execute(
                select(Person).limit(limit)
            )
            return result.scalars().all()
            
    async def get_latest_agent_attributes(self, person_ids: List[UUID]) -> Dict[UUID, Dict[str, float]]:
        """
        Получает последние значения атрибутов агентов из person_attribute_history.
        
        Args:
            person_ids: Список ID агентов
            
        Returns:
            Словарь {person_id: {attribute_name: latest_value}}
        """
        if not person_ids:
            return {}
            
        async with self.ReadOnlySession() as session:
            # Получаем последние значения атрибутов для каждого агента
            query = text("""
                WITH latest_attributes AS (
                    SELECT 
                        person_id,
                        attribute_name,
                        new_value,
                        ROW_NUMBER() OVER (
                            PARTITION BY person_id, attribute_name 
                            ORDER BY change_timestamp DESC, created_at DESC
                        ) as rn
                    FROM capsim.person_attribute_history
                    WHERE person_id = ANY(:person_ids)
                )
                SELECT person_id, attribute_name, new_value
                FROM latest_attributes
                WHERE rn = 1
            """)
            
            result = await session.execute(query, {"person_ids": person_ids})
            rows = result.fetchall()
            
            # Группируем результаты по person_id
            attributes_by_person = {}
            for row in rows:
                person_id = row[0]
                attribute_name = row[1]
                new_value = row[2]
                
                if person_id not in attributes_by_person:
                    attributes_by_person[person_id] = {}
                    
                attributes_by_person[person_id][attribute_name] = new_value
                
            return attributes_by_person
            
    async def get_person(self, person_id: UUID) -> Optional[Person]:
        """Get person by ID."""
        async with self.ReadOnlySession() as session:
            result = await session.execute(
                select(Person).where(Person.id == person_id)
            )
            return result.scalar_one_or_none()
            
    # Simulation Participant operations
    async def get_simulation_participant(self, simulation_id: UUID, person_id: UUID) -> Optional[SimulationParticipant]:
        """Get simulation participant record."""
        async with self.ReadOnlySession() as session:
            result = await session.execute(
                select(SimulationParticipant).where(
                    SimulationParticipant.simulation_id == simulation_id,
                    SimulationParticipant.person_id == person_id
                )
            )
            return result.scalar_one_or_none()
            
    async def update_simulation_participant(self, simulation_id: UUID, person_id: UUID, 
                                          updates: Dict[str, Any]) -> None:
        """Update simulation participant attributes."""
        async with self.SessionLocal() as session:
            stmt = update(SimulationParticipant).where(
                SimulationParticipant.simulation_id == simulation_id,
                SimulationParticipant.person_id == person_id
            ).values(**updates)
            
            await session.execute(stmt)
            await session.commit()
            
    async def bulk_create_trends(self, trends_data: List[Dict]) -> None:
        """Bulk-создание новых трендов с обработкой дубликатов."""
        if not trends_data:
            return
        
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        async with self.SessionLocal() as session:
            async with session.begin():
                try:
                    # Используем ON CONFLICT DO NOTHING для игнорирования дубликатов
                    stmt = pg_insert(Trend).values(trends_data)
                    stmt = stmt.on_conflict_do_nothing(index_elements=['trend_id'])
                    await session.execute(stmt)
                except SQLAlchemyError as e:
                    logger.error(f"Bulk create trends failed: {e}")
                    # Не пробрасываем ошибку, чтобы не прерывать симуляцию из-за дублей
                
    async def bulk_increment_trend_interactions(self, trend_counts: List[Tuple[UUID, int]]) -> None:
        """Bulk-инкремент взаимодействий для трендов с учетом количества для каждого тренда."""
        if not trend_counts:
            return
        async with self.SessionLocal() as session:
            try:
                for trend_id, count in trend_counts:
                    # ИСПРАВЛЕНИЕ: Используем правильный SQL синтаксис для инкремента с указанием схемы
                    await session.execute(
                        text("UPDATE capsim.trends SET total_interactions = total_interactions + :count WHERE trend_id = :trend_id")
                        .bindparams(count=count, trend_id=trend_id)
                    )
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Bulk increment trend interactions failed: {e}")
                raise
            
    async def get_simulation_participants_count(self, simulation_id: UUID) -> int:
        """
        Возвращает количество участников в симуляции.
        """
        async with self.ReadOnlySession() as session:
            result = await session.execute(
                select(SimulationParticipant).where(
                    SimulationParticipant.simulation_id == simulation_id
                )
            )
            return len(result.scalars().all())
            
    # Trend operations
    async def create_trend(self, trend: Trend) -> None:
        """Create new trend."""
        async with self.SessionLocal() as session:
            session.add(trend)
            await session.commit()
            
    async def get_active_trends(self, simulation_id: UUID) -> List[Trend]:
        """Get all active trends for a simulation."""
        async with self.ReadOnlySession() as session:
            result = await session.execute(
                select(Trend).where(Trend.simulation_id == simulation_id)
            )
            return result.scalars().all()
            
    async def increment_trend_interactions(self, trend_id: UUID) -> None:
        """Increment interaction count for a trend."""
        async with self.SessionLocal() as session:
            await session.execute(
                update(Trend).where(
                    Trend.trend_id == trend_id
                ).values(
                    interaction_count=Trend.interaction_count + 1
                )
            )
            await session.commit()
            
    # Event operations
    async def create_event(self, event: Event) -> None:
        """Create new event."""
        async with self.SessionLocal() as session:
            session.add(event)
            await session.commit()
            
    async def bulk_create_events(self, events_data: List[Dict]) -> None:
        """Bulk-создание новых событий."""
        if not events_data:
            return
        
        from ..db.models import Event as DBEvent
        
        async with self.SessionLocal() as session:
            # Создаем объекты Event из данных
            db_events = []
            for event_data in events_data:
                # Очищаем данные от служебных полей
                cleaned_data = event_data.copy()
                cleaned_data.pop("type", None)
                
                # Конвертируем processed_at обратно в datetime
                if "processed_at" in cleaned_data and isinstance(cleaned_data["processed_at"], str):
                    cleaned_data["processed_at"] = datetime.fromisoformat(cleaned_data["processed_at"].replace("Z", "+00:00"))
                
                # Конвертируем UUID строки обратно в UUID объекты
                if "simulation_id" in cleaned_data and isinstance(cleaned_data["simulation_id"], str):
                    cleaned_data["simulation_id"] = UUID(cleaned_data["simulation_id"])
                if "agent_id" in cleaned_data and cleaned_data["agent_id"] and isinstance(cleaned_data["agent_id"], str):
                    cleaned_data["agent_id"] = UUID(cleaned_data["agent_id"])
                if "trend_id" in cleaned_data and cleaned_data["trend_id"] and isinstance(cleaned_data["trend_id"], str):
                    cleaned_data["trend_id"] = UUID(cleaned_data["trend_id"])
                
                db_event = DBEvent(**cleaned_data)
                db_events.append(db_event)
            
            # Добавляем все события в сессию
            session.add_all(db_events)
            await session.commit()
            
    # Affinity and interests operations
    async def load_affinity_map(self) -> Dict[str, Dict[str, float]]:
        """Load the entire affinity map from the database."""
        async with self.ReadOnlySession() as session:
            result = await session.execute(select(AffinityMap))
            affinity_map = {}
            
            for row in result.scalars().all():
                if row.profession not in affinity_map:
                    affinity_map[row.profession] = {}
                affinity_map[row.profession][row.topic] = row.affinity_score
                
            return affinity_map
            
    async def bulk_insert_affinity_map(self, affinity_data: Dict[str, Dict[str, float]]) -> None:
        """Bulk insert affinity map data."""
        async with self.SessionLocal() as session:
            # Clear existing data
            await session.execute(delete(AffinityMap))
            
            # Insert new data
            for profession, topics in affinity_data.items():
                for topic, score in topics.items():
                    affinity = AffinityMap(
                        profession=profession,
                        topic=topic,
                        affinity_score=score
                    )
                    session.add(affinity)
                    
            await session.commit()
            
            logger.info(json.dumps({
                "event": "affinity_map_loaded",
                "professions": len(affinity_data),
                "total_mappings": sum(len(topics) for topics in affinity_data.values())
            }))
            
    async def bulk_insert_agent_interests(self, interests_data: List[Dict]) -> None:
        """Bulk insert agent interests data."""
        async with self.SessionLocal() as session:
            # Clear existing data
            await session.execute(delete(AgentInterests))
            
            # Insert new data
            for interest in interests_data:
                agent_interest = AgentInterests(**interest)
                session.add(agent_interest)
                
            await session.commit()
            
            logger.info(json.dumps({
                "event": "agent_interests_loaded",
                "count": len(interests_data)
            }))
            
    async def get_agent_interests(self, profession: str) -> Dict[str, tuple]:
        """Get agent interests for profession."""
        async with self.ReadOnlySession() as session:
            result = await session.execute(
                select(AgentInterests).where(AgentInterests.profession == profession)
            )
            
            interests = {}
            for row in result.scalars().all():
                interests[row.interest_name] = (row.min_value, row.max_value)
                
            return interests
            
    # Batch operations
    async def bulk_update_persons(self, updates: List[Dict[str, Any]]) -> None:
        """Bulk update Person records."""
        if not updates:
            return
        async with self.SessionLocal() as session:
            for update_data in updates:
                stmt = update(Person).where(Person.id == update_data['id']).values(**{k: v for k, v in update_data.items() if k != 'id'})
                await session.execute(stmt)
            await session.commit()
            
    async def bulk_update_simulation_participants(self, updates: List[Dict[str, Any]]) -> None:
        """Bulk update SimulationParticipant records."""
        if not updates:
            return
        async with self.SessionLocal() as session:
            for update_data in updates:
                simulation_id = update_data['simulation_id']
                person_id = update_data['person_id']
                stmt = update(SimulationParticipant).where(
                    SimulationParticipant.simulation_id == simulation_id,
                    SimulationParticipant.person_id == person_id
                ).values(**{k: v for k, v in update_data.items() if k not in ['simulation_id', 'person_id']})
                await session.execute(stmt)
            await session.commit()
            
    async def batch_commit_states(self, updates: List[Dict[str, Any]]) -> None:
        """
        DEPRECATED: This method is now handled by the simulation engine's
        """
        if not updates:
            return
            
        for attempt in range(self._retry_attempts):
            try:
                async with self.SessionLocal() as session:
                    for update_data in updates:
                        table = update_data['table']
                        record_id = update_data['id']
                        fields = update_data['updates']
                        
                        if table == 'persons':
                            stmt = update(Person).where(Person.id == record_id).values(**fields)
                        elif table == 'simulation_participants':
                            simulation_id, person_id = record_id
                            stmt = update(SimulationParticipant).where(
                                SimulationParticipant.simulation_id == simulation_id,
                                SimulationParticipant.person_id == person_id
                            ).values(**fields)
                        else:
                            raise ValueError(f"Unknown table: {table}")
                            
                        await session.execute(stmt)
                        
                    await session.commit()
                    
                    logger.info(json.dumps({
                        "event": "batch_commit_success",
                        "updates_count": len(updates),
                        "attempt": attempt + 1
                    }))
                    return
                    
            except SQLAlchemyError as e:
                logger.warning(json.dumps({
                    "event": "batch_commit_retry",
                    "attempt": attempt + 1,
                    "error": str(e)
                }))
                
                if attempt < self._retry_attempts - 1:
                    import asyncio
                    await asyncio.sleep(self._retry_backoffs[attempt])
                else:
                    logger.error(json.dumps({
                        "event": "batch_commit_failed",
                        "updates_count": len(updates),
                        "error": str(e)
                    }))
                    raise
                    
    def add_to_batch(self, update: Dict[str, Any]) -> None:
        """Add update to batch queue."""
        self._batch_updates.append(update)
        
    async def flush_batch(self) -> None:
        """Flush current batch."""
        if self._batch_updates:
            await self.batch_commit_states(self._batch_updates)
            self._batch_updates.clear()
            
    def should_commit_batch(self) -> bool:
        """Check if batch should be committed."""
        return len(self._batch_updates) >= self._batch_size
        
    # Statistics and queries
    async def get_simulation_stats(self, simulation_id: UUID) -> Dict[str, Any]:
        """Get comprehensive simulation statistics."""
        async with self.ReadOnlySession() as session:
            # Get basic simulation info
            simulation_result = await session.execute(
                select(SimulationRun).where(SimulationRun.run_id == simulation_id)
            )
            simulation = simulation_result.scalar_one_or_none()
            
            if not simulation:
                return {}
                
            # Get participant count
            participants_result = await session.execute(
                select(SimulationParticipant).where(
                    SimulationParticipant.simulation_id == simulation_id
                )
            )
            participants_count = len(participants_result.scalars().all())
            
            # Get events count
            events_result = await session.execute(
                select(Event).where(Event.simulation_id == simulation_id)
            )
            events_count = len(events_result.scalars().all())
            
            # Get trends count
            trends_result = await session.execute(
                select(Trend).where(Trend.simulation_id == simulation_id)
            )
            trends_count = len(trends_result.scalars().all())
            
            return {
                'simulation_id': str(simulation_id),
                'status': simulation.status,
                'num_agents': simulation.num_agents,
                'participants_count': participants_count,
                'events_count': events_count,
                'trends_count': trends_count,
                'start_time': simulation.start_time.isoformat() if simulation.start_time else None,
                'end_time': simulation.end_time.isoformat() if simulation.end_time else None,
                'duration_days': simulation.duration_days
            }
            
    async def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute raw SQL query."""
        async with self.ReadOnlySession() as session:
            result = await session.execute(text(query), params or {})
            return [dict(row._mapping) for row in result]
            
    async def get_profession_attribute_ranges(self) -> Dict[str, Dict[str, tuple]]:
        """Load profession attribute ranges from agents_profession table."""
        async with self.ReadOnlySession() as session:
            result = await session.execute(select(AgentsProfession))
            rows = result.scalars().all()
            if not rows:
                return {}
            ranges: Dict[str, Dict[str, tuple]] = {}
            for row in rows:
                ranges[row.profession] = {
                    "financial_capability": (row.financial_capability_min, row.financial_capability_max),
                    "trend_receptivity": (row.trend_receptivity_min, row.trend_receptivity_max),
                    "social_status": (row.social_status_min, row.social_status_max),
                    "energy_level": (row.energy_level_min, row.energy_level_max),
                    "time_budget": (row.time_budget_min, row.time_budget_max),
                }
            return ranges 