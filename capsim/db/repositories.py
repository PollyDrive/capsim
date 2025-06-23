"""
Database repositories for CAPSIM 2.0 - CRUD operations and batch processing.
"""

import json
import logging
from typing import List, Dict, Optional, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, insert, update, delete, text
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    SimulationRun, Person, Trend, Event, 
    PersonAttributeHistory, AgentInterests, AffinityMap, DailyTrendSummary
)

logger = logging.getLogger(__name__)


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
                                     end_time: Optional[str] = None) -> None:
        """Update simulation status."""
        async with self.SessionLocal() as session:
            stmt = update(SimulationRun).where(
                SimulationRun.run_id == simulation_id
            ).values(status=status)
            
            if end_time:
                stmt = stmt.values(end_time=end_time)
                
            await session.execute(stmt)
            await session.commit()
            
    # Person operations  
    async def create_person(self, person: Person) -> None:
        """Create new person/agent."""
        async with self.SessionLocal() as session:
            session.add(person)
            await session.commit()
            
    async def bulk_create_persons(self, persons: List[Person]) -> None:
        """Bulk create persons for better performance."""
        async with self.SessionLocal() as session:
            session.add_all(persons)
            await session.commit()
            
            logger.info(json.dumps({
                "event": "bulk_persons_created",
                "count": len(persons),
                "simulation_id": str(persons[0].simulation_id) if persons else None
            }))
            
    async def get_persons_by_simulation(self, simulation_id: UUID) -> List[Person]:
        """Get all persons for a simulation."""
        async with self.ReadOnlySession() as session:
            result = await session.execute(
                select(Person).where(Person.simulation_id == simulation_id)
            )
            return result.scalars().all()
            
    async def get_person(self, person_id: UUID) -> Optional[Person]:
        """Get person by ID."""
        async with self.ReadOnlySession() as session:
            result = await session.execute(
                select(Person).where(Person.id == person_id)
            )
            return result.scalar_one_or_none()
            
    # Trend operations
    async def create_trend(self, trend: Trend) -> None:
        """Create new trend."""
        async with self.SessionLocal() as session:
            session.add(trend)
            await session.commit()
            
    async def get_active_trends(self, simulation_id: UUID) -> List[Trend]:
        """Get active trends for simulation (created in last 3 days)."""
        async with self.ReadOnlySession() as session:
            # In production, use timestamp filtering
            result = await session.execute(
                select(Trend).where(Trend.simulation_id == simulation_id)
            )
            return result.scalars().all()
            
    async def increment_trend_interactions(self, trend_id: UUID) -> None:
        """Increment trend interaction count."""
        async with self.SessionLocal() as session:
            stmt = update(Trend).where(
                Trend.trend_id == trend_id
            ).values(total_interactions=Trend.total_interactions + 1)
            
            await session.execute(stmt)
            await session.commit()
            
    # Event operations
    async def create_event(self, event: Event) -> None:
        """Create new event."""
        async with self.SessionLocal() as session:
            session.add(event)
            await session.commit()
            
    # Affinity Map operations  
    async def load_affinity_map(self) -> Dict[str, Dict[str, float]]:
        """Load affinity map from database."""
        async with self.ReadOnlySession() as session:
            result = await session.execute(
                select(AffinityMap.profession, AffinityMap.topic, AffinityMap.affinity_score)
            )
            
            affinity_map = {}
            for profession, topic, score in result:
                if topic not in affinity_map:
                    affinity_map[topic] = {}
                affinity_map[topic][profession] = score
                
            return affinity_map
            
    async def bulk_insert_affinity_map(self, affinity_data: Dict[str, Dict[str, float]]) -> None:
        """Bulk insert affinity map data."""
        records = []
        for topic, professions in affinity_data.items():
            for profession, score in professions.items():
                records.append({
                    'profession': profession,
                    'topic': topic,
                    'affinity_score': score
                })
                
        async with self.SessionLocal() as session:
            stmt = insert(AffinityMap)
            await session.execute(stmt, records)
            await session.commit()
            
            logger.info(json.dumps({
                "event": "affinity_map_loaded",
                "records_count": len(records)
            }))
            
    # Agent Interests operations
    async def bulk_insert_agent_interests(self, interests_data: List[Dict]) -> None:
        """Bulk insert agent interests data."""
        async with self.SessionLocal() as session:
            stmt = insert(AgentInterests)
            await session.execute(stmt, interests_data)
            await session.commit()
            
            logger.info(json.dumps({
                "event": "agent_interests_loaded", 
                "records_count": len(interests_data)
            }))
            
    async def get_agent_interests(self, profession: str) -> Dict[str, tuple]:
        """Get interest ranges for profession."""
        async with self.ReadOnlySession() as session:
            result = await session.execute(
                select(AgentInterests).where(AgentInterests.profession == profession)
            )
            
            interests = {}
            for record in result.scalars():
                interests[record.interest_name] = (record.min_value, record.max_value)
                
            return interests
            
    # Batch operations
    async def batch_commit_states(self, updates: List[Dict[str, Any]]) -> None:
        """
        Batch commit agent state changes with retry logic.
        
        Args:
            updates: List of state change dictionaries
        """
        if not updates:
            return
            
        for attempt in range(self._retry_attempts):
            try:
                async with self.SessionLocal() as session:
                    # Group updates by type for efficiency
                    person_updates = []
                    history_records = []
                    
                    for update in updates:
                        if update['type'] == 'person_state':
                            person_updates.append({
                                'id': update['person_id'],
                                **{k: v for k, v in update.items() 
                                   if k not in ['type', 'person_id', 'reason', 'timestamp']}
                            })
                            
                        elif update['type'] == 'attribute_history':
                            history_records.append(update)
                            
                    # Bulk update persons
                    if person_updates:
                        await session.execute(
                            update(Person),
                            person_updates
                        )
                        
                    # Bulk insert history
                    if history_records:
                        await session.execute(
                            insert(PersonAttributeHistory),
                            history_records
                        )
                        
                    await session.commit()
                    
                    logger.info(json.dumps({
                        "event": "batch_commit_success",
                        "updates_count": len(updates),
                        "attempt": attempt + 1
                    }))
                    
                    return  # Success
                    
            except SQLAlchemyError as e:
                wait_time = self._retry_backoffs[min(attempt, len(self._retry_backoffs) - 1)]
                
                logger.warning(json.dumps({
                    "event": "batch_commit_retry",
                    "attempt": attempt + 1,
                    "error": str(e),
                    "wait_seconds": wait_time
                }))
                
                if attempt < self._retry_attempts - 1:
                    import asyncio
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(json.dumps({
                        "event": "batch_commit_failed",
                        "updates_lost": len(updates),
                        "error": str(e)
                    }))
                    raise
                    
    def add_to_batch(self, update: Dict[str, Any]) -> None:
        """Add update to batch queue."""
        self._batch_updates.append(update)
        
    async def flush_batch(self) -> None:
        """Force flush current batch."""
        if self._batch_updates:
            await self.batch_commit_states(self._batch_updates)
            self._batch_updates.clear()
            
    def should_commit_batch(self) -> bool:
        """Check if batch should be committed."""
        return len(self._batch_updates) >= self._batch_size
        
    # Statistics and monitoring
    async def get_simulation_stats(self, simulation_id: UUID) -> Dict[str, Any]:
        """Get simulation statistics."""
        async with self.ReadOnlySession() as session:
            # Person count
            persons_result = await session.execute(
                select(Person.id).where(Person.simulation_id == simulation_id)
            )
            person_count = len(persons_result.scalars().all())
            
            # Trends count  
            trends_result = await session.execute(
                select(Trend.trend_id).where(Trend.simulation_id == simulation_id)
            )
            trends_count = len(trends_result.scalars().all())
            
            # Events count
            events_result = await session.execute(
                select(Event.event_id).where(Event.simulation_id == simulation_id)
            )
            events_count = len(events_result.scalars().all())
            
            return {
                "simulation_id": str(simulation_id),
                "persons_count": person_count,
                "trends_count": trends_count,
                "events_count": events_count,
                "batch_pending": len(self._batch_updates)
            } 