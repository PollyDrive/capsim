"""
Shared test configuration and fixtures for CAPSIM test suite.

Provides common fixtures, mock objects, and test utilities used across
all test modules. Ensures consistent test environment and reduces
code duplication.
"""

import pytest
import os
import asyncio
import logging
from typing import Dict, List, Any
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# Set test environment variables
os.environ.update({
    "DECIDE_SCORE_THRESHOLD": "0.25",
    "BATCH_SIZE": "100",
    "BATCH_TIMEOUT_MIN": "1.0",
    "TREND_ARCHIVE_DAYS": "3",
    "BASE_RATE": "43.2",
    "SHUTDOWN_TIMEOUT_SEC": "30",
    "CACHE_TTL_MIN": "2880",
    "CACHE_MAX_SIZE": "10000"
})

# Import project modules
import sys
sys.path.append('.')

try:
    from capsim.domain.person import Person
    from capsim.domain.trend import Trend
    from capsim.domain.events import (
        PublishPostAction, EnergyRecoveryEvent, DailyResetEvent,
        BaseEvent, EventPriority
    )
    from capsim.engine.simulation_engine import SimulationEngine, SimulationContext
    from capsim.common.topic_mapping import get_all_topic_codes
    CAPSIM_AVAILABLE = True
except ImportError:
    CAPSIM_AVAILABLE = False

# Configure test logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise during tests
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Disable verbose loggers during tests
logging.getLogger('capsim').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)


class MockDatabaseRepository:
    """
    Mock database repository for testing.
    
    Provides in-memory storage and realistic async behavior
    without requiring actual database connections.
    """
    
    def __init__(self):
        self.simulation_runs = {}
        self.persons = {}
        self.trends = {}
        self.events = []
        self.batch_updates = []
        self.affinity_map = self._create_test_affinity_map()
        self.agent_interests = self._create_test_agent_interests()
        
        # Performance tracking
        self.operation_counts = {}
        self.batch_commit_count = 0
        
    def _create_test_affinity_map(self) -> Dict[str, Dict[str, float]]:
        """Create comprehensive test affinity map."""
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
        
    def _create_test_agent_interests(self) -> Dict[str, Dict[str, tuple]]:
        """Create test agent interest ranges."""
        return {
            "Banker": {
                "Economics": (3.0, 5.0), "Wellbeing": (1.5, 3.0),
                "Religion": (0.5, 2.0), "Politics": (2.0, 4.0),
                "Education": (1.5, 3.5), "Entertainment": (2.0, 4.0)
            },
            "Developer": {
                "Economics": (2.0, 4.0), "Wellbeing": (1.5, 3.5),
                "Religion": (0.5, 2.5), "Politics": (1.0, 3.0),
                "Education": (3.5, 5.0), "Entertainment": (2.5, 4.5)
            },
            "Teacher": {
                "Economics": (1.5, 3.5), "Wellbeing": (2.5, 4.5),
                "Religion": (1.0, 3.0), "Politics": (2.0, 4.5),
                "Education": (4.0, 5.0), "Entertainment": (3.0, 5.0)
            },
            "Worker": {
                "Economics": (2.0, 4.0), "Wellbeing": (2.0, 4.0),
                "Religion": (1.5, 3.5), "Politics": (1.5, 3.5),
                "Education": (1.0, 3.0), "Entertainment": (2.5, 4.5)
            },
            "ShopClerk": {
                "Economics": (2.5, 4.5), "Wellbeing": (1.5, 3.5),
                "Religion": (0.5, 2.5), "Politics": (1.0, 3.0),
                "Education": (1.5, 3.5), "Entertainment": (2.5, 4.5)
            }
        }
        
    def _track_operation(self, operation_name: str):
        """Track operation for testing metrics."""
        self.operation_counts[operation_name] = self.operation_counts.get(operation_name, 0) + 1
        
    async def create_simulation_run(self, num_agents: int, duration_days: int, configuration: Dict):
        """Mock simulation run creation."""
        self._track_operation('create_simulation_run')
        
        run_id = uuid4()
        simulation_run = MagicMock()
        simulation_run.run_id = run_id
        simulation_run.num_agents = num_agents
        simulation_run.duration_days = duration_days
        simulation_run.configuration = configuration
        simulation_run.status = "initialized"
        simulation_run.created_at = datetime.utcnow()
        
        self.simulation_runs[run_id] = simulation_run
        return simulation_run
        
    async def load_affinity_map(self) -> Dict[str, Dict[str, float]]:
        """Return test affinity map."""
        self._track_operation('load_affinity_map')
        return self.affinity_map
        
    async def bulk_create_persons(self, persons: List):
        """Mock bulk person creation."""
        self._track_operation('bulk_create_persons')
        
        for person in persons:
            self.persons[person.person_id] = person
        
    async def get_active_trends(self, simulation_id: UUID) -> List:
        """Return active trends for simulation."""
        self._track_operation('get_active_trends')
        
        return [trend for trend in self.trends.values() 
                if trend.simulation_id == simulation_id]
                
    async def create_trend(self, trend):
        """Mock trend creation."""
        self._track_operation('create_trend')
        self.trends[trend.trend_id] = trend
        
    async def update_trend_interactions(self, trend_id: UUID, interactions: int):
        """Mock trend interaction update."""
        self._track_operation('update_trend_interactions')
        
        if trend_id in self.trends:
            self.trends[trend_id].total_interactions += interactions
            
    async def bulk_update_persons(self, updates: List[Dict]):
        """Mock bulk person updates."""
        self._track_operation('bulk_update_persons')
        
        self.batch_updates.extend(updates)
        self.batch_commit_count += 1
        
    async def log_event(self, event):
        """Mock event logging."""
        self._track_operation('log_event')
        self.events.append(event)
        
    async def get_agent_interests(self, profession: str) -> Dict[str, tuple]:
        """Get interest ranges for profession."""
        self._track_operation('get_agent_interests')
        return self.agent_interests.get(profession, {})
        
    async def get_persons_count(self):
        return 0

    async def get_available_persons(self, num_agents):
        return []

    async def get_persons_for_simulation(self, simulation_id, limit):
        return []

    async def get_profession_attribute_ranges(self):
        return {
            "ShopClerk": {"financial_capability": (2, 4), "trend_receptivity": (1, 3), "social_status": (1, 3), "energy_level": (2, 5), "time_budget": (3, 5)},
            "Worker": {"financial_capability": (2, 4), "trend_receptivity": (1, 3), "social_status": (1, 2), "energy_level": (2, 5), "time_budget": (3, 5)},
            "Developer": {"financial_capability": (3, 5), "trend_receptivity": (3, 5), "social_status": (2, 4), "energy_level": (2, 5), "time_budget": (2, 4)},
            "Politician": {"financial_capability": (3, 5), "trend_receptivity": (3, 5), "social_status": (4, 5), "energy_level": (2, 5), "time_budget": (2, 4)},
            "Blogger": {"financial_capability": (2, 4), "trend_receptivity": (4, 5), "social_status": (3, 5), "energy_level": (2, 5), "time_budget": (3, 5)},
            "Businessman": {"financial_capability": (4, 5), "trend_receptivity": (2, 4), "social_status": (4, 5), "energy_level": (2, 5), "time_budget": (2, 4)},
            "SpiritualMentor": {"financial_capability": (1, 3), "trend_receptivity": (2, 5), "social_status": (2, 4), "energy_level": (3, 5), "time_budget": (2, 4)},
            "Philosopher": {"financial_capability": (1, 3), "trend_receptivity": (1, 3), "social_status": (1, 3), "energy_level": (2, 5), "time_budget": (2, 4)},
            "Unemployed": {"financial_capability": (1, 2), "trend_receptivity": (3, 5), "social_status": (1, 2), "energy_level": (3, 5), "time_budget": (3, 5)},
            "Teacher": {"financial_capability": (1, 3), "trend_receptivity": (1, 3), "social_status": (2, 4), "energy_level": (2, 5), "time_budget": (2, 4)},
            "Artist": {"financial_capability": (1, 3), "trend_receptivity": (2, 4), "social_status": (2, 4), "energy_level": (4, 5), "time_budget": (3, 5)},
            "Doctor": {"financial_capability": (2, 4), "trend_receptivity": (1, 3), "social_status": (3, 5), "energy_level": (2, 5), "time_budget": (1, 2)},
        }

    # Test utility methods
    def reset(self):
        """Reset all mock data."""
        self.simulation_runs.clear()
        self.persons.clear()
        self.trends.clear()
        self.events.clear()
        self.batch_updates.clear()
        self.operation_counts.clear()
        self.batch_commit_count = 0
        
    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics for testing."""
        return {
            "simulation_runs": len(self.simulation_runs),
            "persons": len(self.persons),
            "trends": len(self.trends),
            "events": len(self.events),
            "batch_updates": len(self.batch_updates),
            "batch_commits": self.batch_commit_count,
            "operations": self.operation_counts.copy()
        }


@pytest.fixture
def mock_db_repo():
    """Fixture providing mock database repository."""
    repo = MockDatabaseRepository()
    yield repo
    # Cleanup after test
    repo.reset()


@pytest.fixture
def test_agents():
    """Fixture providing pre-configured test agents."""
    if not CAPSIM_AVAILABLE:
        pytest.skip("CAPSIM modules not available")
        
    agents = []
    # Правильный список из 12 профессий согласно ТЗ
    professions = ["ShopClerk", "Worker", "Developer", "Politician", "Blogger", 
                  "Businessman", "SpiritualMentor", "Philosopher", "Unemployed", 
                  "Teacher", "Artist", "Doctor"]
    simulation_id = uuid4()
    
    # Create 4 agents per profession (48 total for testing)
    for profession in professions:
        for i in range(4):
            agent = Person.create_random_agent(profession, simulation_id)
            agents.append(agent)
            
    return agents, simulation_id


@pytest.fixture
def test_trends():
    """Fixture providing pre-configured test trends."""
    if not CAPSIM_AVAILABLE:
        pytest.skip("CAPSIM modules not available")
        
    simulation_id = uuid4()
    agent_id = uuid4()
    
    trends = []
    
    # Create sample trends with different characteristics
    trend_configs = [
        ("ECONOMIC", 3.0, "High", 200),    # High virality trend
        ("HEALTH", 2.5, "Middle", 120),    # Medium virality  
        ("SCIENCE", 2.0, "Low", 50),       # Low virality
        ("CULTURE", 3.5, "Middle", 180),   # High-medium virality
    ]
    
    for topic, base_virality, coverage, interactions in trend_configs:
        trend = Trend.create_from_action(
            topic=topic,
            originator_id=agent_id,
            simulation_id=simulation_id,
            base_virality=base_virality,
            coverage_level=coverage
        )
        trend.total_interactions = interactions
        trends.append(trend)
        
    return trends, simulation_id


@pytest.fixture
def simulation_context():
    """Fixture providing simulation context for testing."""
    if not CAPSIM_AVAILABLE:
        pytest.skip("CAPSIM modules not available")
        
    affinity_map = {
        "ShopClerk": {"ECONOMIC": 3, "HEALTH": 2, "SPIRITUAL": 2, "CONSPIRACY": 3, "SCIENCE": 1, "CULTURE": 2, "SPORT": 2},
        "Worker": {"ECONOMIC": 3, "HEALTH": 3, "SPIRITUAL": 2, "CONSPIRACY": 3, "SCIENCE": 1, "CULTURE": 2, "SPORT": 3},
        "Developer": {"ECONOMIC": 3, "HEALTH": 2, "SPIRITUAL": 1, "CONSPIRACY": 2, "SCIENCE": 5, "CULTURE": 3, "SPORT": 2},
        "Teacher": {"ECONOMIC": 3, "HEALTH": 4, "SPIRITUAL": 3, "CONSPIRACY": 2, "SCIENCE": 4, "CULTURE": 4, "SPORT": 3}
    }
    
    return SimulationContext(
        current_time=100.0,
        active_trends={},
        affinity_map=affinity_map
    )


@pytest.fixture
def performance_config():
    """Fixture providing performance test configuration."""
    return {
        "max_latency_ms": 10.0,
        "max_queue_size": 5000,
        "batch_size": 100,
        "target_throughput": 43.2,  # events per agent per day
        "shutdown_timeout": 30.0,
    }


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def demo_results():
    """Fixture providing demo simulation results for validation."""
    return {
        "agents": 20,
        "simulation_minutes": 360,  # 6 hours
        "events_processed": 748,
        "actions_scheduled": 731,
        "trends_created": 59,
        "top_virality_scores": [4.65, 4.61, 4.55],
        "professions": ["ShopClerk", "Worker", "Developer", "Politician", "Blogger", 
                       "Businessman", "SpiritualMentor", "Philosopher", "Unemployed", 
                       "Teacher", "Artist", "Doctor"],
        "profession_count": 4,  # 4 agents per profession
    }


# Test utilities
def assert_agent_valid(agent):
    """Assert agent has valid attributes."""
    if not CAPSIM_AVAILABLE:
        return
        
    assert agent.person_id is not None
    assert agent.simulation_id is not None
    assert agent.profession in ["ShopClerk", "Worker", "Developer", "Politician", "Blogger", 
                               "Businessman", "SpiritualMentor", "Philosopher", "Unemployed", 
                               "Teacher", "Artist", "Doctor"]
    assert 0.0 <= agent.financial_capability <= 5.0
    assert 0.0 <= agent.social_status <= 5.0
    assert 0.0 <= agent.trend_receptivity <= 5.0
    assert 0.0 <= agent.energy_level <= 5.0
    assert 0 <= agent.time_budget <= 5
    assert isinstance(agent.interests, dict)
    assert len(agent.interests) > 0


def assert_trend_valid(trend):
    """Assert trend has valid attributes."""
    if not CAPSIM_AVAILABLE:
        return
        
    assert trend.trend_id is not None
    assert trend.simulation_id is not None
    assert trend.originator_id is not None
    # Validate topic is canonical
    assert trend.topic in get_all_topic_codes()
    assert 0.0 <= trend.base_virality_score <= 5.0
    assert trend.coverage_level in ["Low", "Middle", "High"]
    assert trend.total_interactions >= 0
    
    # Test virality calculation
    calculated_virality = trend.calculate_current_virality()
    assert 0.0 <= calculated_virality <= 5.0


def create_test_events(num_events: int = 10):
    """Create test events for simulation."""
    if not CAPSIM_AVAILABLE:
        return []
        
    events = []
    
    for i in range(num_events):
        if i % 3 == 0:
            event = PublishPostAction(
                agent_id=uuid4(),
                topic="ECONOMIC",
                timestamp=float(i * 10)
            )
        elif i % 3 == 1:
            event = EnergyRecoveryEvent(float(i * 60))
        else:
            event = DailyResetEvent(float(i * 1440))
            
        events.append(event)
        
    return events


# Markers for test categorization
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.performance = pytest.mark.performance
pytest.mark.slow = pytest.mark.slow 