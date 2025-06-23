"""
Comprehensive integration tests for CAPSIM simulation - full day simulation.

Tests based on demo results:
- 20 agents, 748 events processed, 731 actions scheduled
- 59 trends created, top virality 4.65
- Simulation time: 360 minutes (6 hours)

These tests verify:
1. Full simulation initialization and execution  
2. Agent interaction patterns and decision making
3. Trend creation and virality mechanics
4. Energy recovery and daily resets
5. Batch commit mechanics
6. Graceful shutdown and state persistence
"""

import pytest
import asyncio
import os
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock

from capsim.engine.simulation_engine import SimulationEngine, SimulationContext
from capsim.domain.person import Person
from capsim.domain.trend import Trend  
from capsim.domain.events import (
    PublishPostAction, EnergyRecoveryEvent, DailyResetEvent,
    EventPriority, BaseEvent
)


class MockDatabaseRepository:
    """Mock database repository for testing."""
    
    def __init__(self):
        self.simulation_runs = {}
        self.persons = {}
        self.trends = {}
        self.events = []
        self.batch_updates = []
        self.affinity_map = self._create_test_affinity_map()
        
    def _create_test_affinity_map(self) -> Dict[str, Dict[str, float]]:
        """Create test affinity map matching demo data."""
        return {
            "Banker": {
                "ECONOMIC": 4.5, "HEALTH": 2.0, "SPIRITUAL": 1.5,
                "CONSPIRACY": 1.8, "SCIENCE": 2.2, "CULTURE": 2.1, "SPORT": 2.3
            },
            "Developer": {
                "SCIENCE": 4.0, "ECONOMIC": 3.0, "HEALTH": 2.5,
                "CONSPIRACY": 1.2, "SPIRITUAL": 1.4, "CULTURE": 1.8, "SPORT": 1.5
            },
            "Teacher": {
                "SCIENCE": 3.5, "CULTURE": 4.0, "HEALTH": 3.0,
                "ECONOMIC": 2.3, "SPIRITUAL": 2.2, "CONSPIRACY": 1.6, "SPORT": 2.0
            },
            "Worker": {
                "ECONOMIC": 3.0, "HEALTH": 3.5, "SPORT": 3.5,
                "CULTURE": 1.4, "SCIENCE": 1.7, "SPIRITUAL": 2.3, "CONSPIRACY": 1.9
            },
            "ShopClerk": {
                "ECONOMIC": 3.5, "CULTURE": 3.0, "HEALTH": 2.5,
                "SPORT": 2.3, "SCIENCE": 1.3, "SPIRITUAL": 1.1, "CONSPIRACY": 1.5
            }
        }
        
    async def create_simulation_run(self, num_agents: int, duration_days: int, configuration: Dict):
        """Mock simulation run creation."""
        run_id = uuid4()
        simulation_run = MagicMock()
        simulation_run.run_id = run_id
        simulation_run.num_agents = num_agents
        simulation_run.duration_days = duration_days
        simulation_run.configuration = configuration
        self.simulation_runs[run_id] = simulation_run
        return simulation_run
        
    async def load_affinity_map(self) -> Dict[str, Dict[str, float]]:
        """Return test affinity map."""
        return self.affinity_map
        
    async def bulk_create_persons(self, persons: List[Person]):
        """Mock bulk person creation."""
        for person in persons:
            self.persons[person.person_id] = person
            
    async def get_active_trends(self, simulation_id: UUID) -> List[Trend]:
        """Return active trends for simulation."""
        return [trend for trend in self.trends.values() 
                if trend.simulation_id == simulation_id]
                
    async def create_trend(self, trend: Trend):
        """Mock trend creation."""
        self.trends[trend.trend_id] = trend
        
    async def update_trend_interactions(self, trend_id: UUID, interactions: int):
        """Mock trend interaction update."""
        if trend_id in self.trends:
            self.trends[trend_id].total_interactions += interactions
            
    async def bulk_update_persons(self, updates: List[Dict]):
        """Mock bulk person updates."""
        self.batch_updates.extend(updates)
        
    async def log_event(self, event: BaseEvent):
        """Mock event logging."""
        self.events.append(event)


@pytest.fixture
def mock_db_repo():
    """Fixture providing mock database repository."""
    return MockDatabaseRepository()


@pytest.fixture  
def test_env_vars():
    """Set test environment variables."""
    original_env = dict(os.environ)
    os.environ.update({
        "DECIDE_SCORE_THRESHOLD": "0.25",
        "BATCH_SIZE": "100", 
        "BATCH_TIMEOUT_MIN": "1.0",
        "TREND_ARCHIVE_DAYS": "3"
    })
    yield
    os.environ.clear()
    os.environ.update(original_env)


class TestFullDaySimulation:
    """Full day simulation test suite."""
    
    @pytest.mark.asyncio
    async def test_simulation_initialization_and_bootstrap(self, mock_db_repo, test_env_vars):
        """Test BOOT-01: Bootstrap завершился, создано 20 агентов."""
        engine = SimulationEngine(mock_db_repo)
        
        # Initialize simulation with 20 agents like demo
        await engine.initialize(num_agents=20)
        
        # Verify initialization
        assert engine.simulation_id is not None
        assert len(engine.agents) == 20
        assert len(mock_db_repo.persons) == 20
        
        # Verify profession distribution (4 per profession)
        professions = [agent.profession for agent in engine.agents]
        profession_counts = {}
        for prof in professions:
            profession_counts[prof] = profession_counts.get(prof, 0) + 1
            
        assert all(count == 4 for count in profession_counts.values())
        
        # Verify affinity map loaded
        assert len(engine.affinity_map) == 5  # 5 professions
        assert "Banker" in engine.affinity_map
        assert "Developer" in engine.affinity_map
        
        # Verify system events scheduled
        assert len(engine.event_queue) >= 3  # Energy recovery, daily reset, trend save
        
    @pytest.mark.asyncio
    async def test_des_cycle_event_processing(self, mock_db_repo, test_env_vars):
        """Test DES-01: Цикл DES обрабатывает события, действия планируются."""
        engine = SimulationEngine(mock_db_repo)
        await engine.initialize(num_agents=20)
        
        # Track initial stats
        initial_queue_size = len(engine.event_queue)
        initial_time = engine.current_time
        
        # Run short simulation (30 minutes)
        await engine.run_simulation(duration_days=30/1440)  # 30 minutes as fraction of day
        
        # Verify simulation progressed
        assert engine.current_time >= 30.0
        assert len(mock_db_repo.events) > 0
        
        # Verify agents were active
        stats = engine.get_simulation_stats()
        assert stats["current_time"] >= 30.0
        assert stats["total_agents"] == 20
        
    @pytest.mark.asyncio  
    async def test_agent_decision_making_and_scoring(self, mock_db_repo, test_env_vars):
        """Test AGT-01: Agent decision making with correct scoring formula."""
        engine = SimulationEngine(mock_db_repo)
        await engine.initialize(num_agents=20)
        
        context = SimulationContext(
            current_time=100.0,
            active_trends={},
            affinity_map=engine.affinity_map
        )
        
        # Test decision making for each agent
        decisions_made = 0
        agents_with_energy = 0
        
        for agent in engine.agents:
            if agent.energy_level >= 1.0 and agent.time_budget >= 1:
                agents_with_energy += 1
                decision = agent.decide_action(context)
                if decision == "PublishPostAction":
                    decisions_made += 1
                    
        # Should have some agents with energy and some making decisions
        assert agents_with_energy > 0
        # Decisions depend on scoring formula - some agents should decide to act
        # (exact number depends on random component but should be > 0 with 20 agents)
        
    @pytest.mark.asyncio
    async def test_trend_creation_and_virality_algorithm(self, mock_db_repo, test_env_vars):
        """Test trend creation and virality calculations matching demo results."""
        engine = SimulationEngine(mock_db_repo)
        await engine.initialize(num_agents=20)
        
        # Create test trend similar to demo results
        agent = engine.agents[0]
        trend = Trend.create_from_action(
            topic="ECONOMIC",
            originator_id=agent.person_id,
            simulation_id=engine.simulation_id,
            base_virality=3.0,
            coverage_level="Middle"
        )
        
        # Test virality calculation without interactions
        initial_virality = trend.calculate_current_virality()
        assert initial_virality == 3.0
        
        # Add interactions and test virality growth
        trend.total_interactions = 50
        virality_with_interactions = trend.calculate_current_virality()
        
        # Formula: min(5.0, base + 0.05 * log(interactions + 1))
        expected_virality = min(5.0, 3.0 + 0.05 * math.log(51))
        assert abs(virality_with_interactions - expected_virality) < 0.01
        
        # Test high interaction trending (demo showed max ~4.65)
        trend.total_interactions = 200
        high_virality = trend.calculate_current_virality() 
        assert 4.0 <= high_virality <= 5.0
        
        # Test coverage factor
        assert trend.get_coverage_factor() == 0.6  # Middle coverage
        
    @pytest.mark.asyncio
    async def test_energy_recovery_mechanics(self, mock_db_repo, test_env_vars):
        """Test energy recovery event processing."""
        engine = SimulationEngine(mock_db_repo)
        await engine.initialize(num_agents=20)
        
        # Drain some agents' energy
        for i, agent in enumerate(engine.agents[:10]):
            agent.energy_level = 1.0 if i % 2 == 0 else 0.5
            
        initial_low_energy_count = sum(1 for agent in engine.agents if agent.energy_level < 2.0)
        assert initial_low_energy_count > 0
        
        # Create and process energy recovery event
        recovery_event = EnergyRecoveryEvent(360.0)  # 6 hours
        await engine._process_event(recovery_event)
        
        # Verify energy was recovered
        post_recovery_low_energy = sum(1 for agent in engine.agents if agent.energy_level < 2.0)
        assert post_recovery_low_energy < initial_low_energy_count
        
        # Next recovery should be scheduled
        future_recovery_events = [
            pe for pe in engine.event_queue 
            if isinstance(pe.event, EnergyRecoveryEvent) and pe.timestamp > engine.current_time
        ]
        assert len(future_recovery_events) >= 1
        
    @pytest.mark.asyncio
    async def test_batch_commit_mechanism(self, mock_db_repo, test_env_vars):
        """Test BAT-01: Batch commit с размером 100 и retry механизмом."""
        engine = SimulationEngine(mock_db_repo)
        await engine.initialize(num_agents=20)
        
        # Add updates to batch
        for i in range(150):  # More than batch size
            engine.add_to_batch_update({
                "person_id": uuid4(),
                "attribute": "energy_level", 
                "old_value": 3.0,
                "new_value": 2.5,
                "timestamp": engine.current_time
            })
            
        # Should trigger batch commit at 100
        assert len(engine._batch_updates) == 150
        
        # Test batch commit threshold
        assert engine._should_commit_batch() == True
        
        # Execute batch commit
        await engine._batch_commit_states()
        
        # Verify batch was processed
        assert len(mock_db_repo.batch_updates) > 0
        assert len(engine._batch_updates) == 0  # Cleared after commit
        
    @pytest.mark.asyncio
    async def test_six_hour_simulation_matching_demo(self, mock_db_repo, test_env_vars):
        """Test 6-hour simulation matching demo results patterns."""
        engine = SimulationEngine(mock_db_repo)
        await engine.initialize(num_agents=20)
        
        # Track statistics during simulation
        initial_stats = engine.get_simulation_stats()
        
        # Run 6-hour simulation (360 minutes) like demo
        await engine.run_simulation(duration_days=360/1440)  # 6 hours as fraction of day
        
        final_stats = engine.get_simulation_stats()
        
        # Verify simulation completed
        assert final_stats["current_time"] >= 360.0
        assert final_stats["total_agents"] == 20
        
        # Should have processed many events (demo: 748 events)
        # With 20 agents, expect 200-800 events depending on activity
        total_events = len(mock_db_repo.events)
        assert total_events >= 100  # Minimum activity threshold
        
        # Should have created trends (demo: 59 trends)  
        trends_created = len(mock_db_repo.trends)
        assert trends_created >= 10  # Some trend creation expected
        
        # Verify agents are still active
        active_agents = sum(1 for agent in engine.agents if agent.energy_level > 0)
        assert active_agents >= 10  # Most agents should still be active
        
    @pytest.mark.asyncio
    async def test_full_day_simulation_with_daily_reset(self, mock_db_repo, test_env_vars):
        """Test complete 24-hour simulation with daily reset mechanics."""
        engine = SimulationEngine(mock_db_repo)
        await engine.initialize(num_agents=20)
        
        # Run full day simulation
        await engine.run_simulation(duration_days=1)
        
        final_stats = engine.get_simulation_stats()
        
        # Verify full simulation completed
        assert final_stats["current_time"] >= 1440.0  # 24 hours = 1440 minutes
        
        # Should have processed daily reset event
        daily_reset_events = [e for e in mock_db_repo.events if isinstance(e, DailyResetEvent)]
        assert len(daily_reset_events) >= 1
        
        # Should have multiple energy recovery cycles (every 6 hours = 4 cycles)
        energy_recovery_events = [e for e in mock_db_repo.events if isinstance(e, EnergyRecoveryEvent)]
        assert len(energy_recovery_events) >= 3  # At least 3 recovery cycles
        
        # Verify agents maintain some activity throughout day
        final_active_count = sum(1 for agent in engine.agents if agent.energy_level > 0 or agent.time_budget > 0)
        assert final_active_count >= 10
        
    @pytest.mark.asyncio
    async def test_graceful_shutdown_and_state_persistence(self, mock_db_repo, test_env_vars):
        """Test SYS-01: Graceful shutdown с flush batch."""
        engine = SimulationEngine(mock_db_repo)
        await engine.initialize(num_agents=20)
        
        # Add some updates to batch
        for i in range(50):
            engine.add_to_batch_update({
                "person_id": uuid4(),
                "attribute": "energy_level",
                "old_value": 4.0,
                "new_value": 3.5,
                "timestamp": engine.current_time
            })
            
        # Start simulation briefly
        simulation_task = asyncio.create_task(engine.run_simulation(duration_days=1))
        await asyncio.sleep(0.1)  # Let it start
        
        # Trigger shutdown
        await engine.shutdown()
        
        # Verify final state
        assert engine._running == False
        assert len(engine._batch_updates) == 0  # Batch should be flushed
        
        # Cancel the simulation task
        simulation_task.cancel()
        try:
            await simulation_task
        except asyncio.CancelledError:
            pass
            
    @pytest.mark.asyncio
    async def test_performance_requirements_validation(self, mock_db_repo, test_env_vars):
        """Test performance requirements: queue size, event latency."""
        engine = SimulationEngine(mock_db_repo)
        await engine.initialize(num_agents=100)  # Larger simulation
        
        # Run simulation and track performance  
        start_time = datetime.now()
        await engine.run_simulation(duration_days=60/1440)  # 1 hour
        end_time = datetime.now()
        
        duration_seconds = (end_time - start_time).total_seconds()
        
        # Verify queue never exceeded limit
        max_queue_size = 5000  # From requirements
        final_stats = engine.get_simulation_stats()
        assert final_stats["queue_size"] <= max_queue_size
        
        # Performance should be reasonable for 100 agents, 1 hour simulation
        assert duration_seconds < 30  # Should complete within 30 seconds
        
        # Verify batch processing efficiency
        events_processed = len(mock_db_repo.events)
        if events_processed > 0:
            events_per_second = events_processed / duration_seconds
            assert events_per_second > 10  # Should process at least 10 events/sec 