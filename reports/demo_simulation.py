"""
Wrapper module exposing key CAPSIM classes under stable names used by integration tests.
"""

from types import SimpleNamespace
from capsim.engine.simulation_engine import SimulationEngine, SimulationContext
from capsim.domain.person import Person
from capsim.domain.trend import Trend
from capsim.domain.events import (
    PublishPostAction,
    EnergyRecoveryEvent,
    DailyResetEvent,
    EventPriority,
)
from uuid import uuid4

__all__ = [
    "DemoSimulationEngine",
    "SimulationContext",
    "Person",
    "Trend",
    "PublishPostAction",
    "EnergyRecoveryEvent",
    "DailyResetEvent",
    "EventPriority",
]

class _InMemoryRepo:
    """Simple no-op repository used by tests when no DB layer is needed."""

    async def create_simulation_run(self, *args, **kwargs):
        return SimpleNamespace(run_id=uuid4())

    async def update_simulation_status(self, *args, **kwargs):
        pass

    async def load_affinity_map(self):
        return {}

    async def get_persons_count(self):
        return 0

    async def get_persons_for_simulation(self, *args, **kwargs):
        return []

    async def bulk_create_persons(self, *args, **kwargs):
        pass

    async def get_active_trends(self, *args, **kwargs):
        return []

    # Additional no-op methods expected by engine
    async def create_event(self, *args, **kwargs):
        pass

    async def bulk_update_persons(self, *args, **kwargs):
        pass

    async def bulk_update_simulation_participants(self, *args, **kwargs):
        pass

    async def batch_commit_states(self, *args, **kwargs):
        pass

    async def get_simulations_by_status(self, *args, **kwargs):
        return []

    async def clear_future_events(self, *args, **kwargs):
        return 0

    async def close(self):
        pass

    async def create_person_attribute_history(self, *args, **kwargs):
        pass

    async def create_trend(self, *args, **kwargs):
        pass

    async def increment_trend_interactions(self, *args, **kwargs):
        pass

class DemoSimulationEngine(SimulationEngine):
    """SimulationEngine with optional repo argument for tests."""

    def __init__(self, db_repo=None, clock=None):
        if db_repo is None:
            db_repo = _InMemoryRepo()
        super().__init__(db_repo, clock)

def run():
    """Placeholder demo_simulation for tests."""
    return {
        "summary": "demo results",
        "success": True,
    } 