
from typing import List

import asyncio
import pytest
from uuid import UUID
from types import SimpleNamespace

from capsim.engine.simulation_engine import SimulationEngine
from capsim.db.repositories import DatabaseRepository
from capsim.domain.events import EnergyRecoveryEvent

@pytest.mark.asyncio
async def test_night_activity(mock_db_repo):
    """
    Verifies that agent actions are processed during the "night" hours (00:00 - 08:00).
    """
    engine = SimulationEngine(mock_db_repo)
    await engine.initialize(num_agents=50, duration_days=1)
    night_actions = 0
    original_process_event = engine._process_event
    async def patched_process_event(event):
        nonlocal night_actions
        if event.__class__.__name__ in ["PublishPostAction", "PurchaseAction", "SelfDevAction"]:
            day_time = event.timestamp % 1440
            if 0 <= day_time < 480:
                night_actions += 1
        await original_process_event(event)
    engine._process_event = patched_process_event
    await engine.run_simulation()
    assert night_actions > 0, "No actions were processed during the night."

@pytest.mark.asyncio
async def test_minimum_activity(mock_db_repo):
    """
    Verifies that each agent performs at least 20 actions in 24 hours.
    """
    engine = SimulationEngine(mock_db_repo)
    await engine.initialize(num_agents=50, duration_days=1)
    agent_action_counts = {agent.id: 0 for agent in engine.agents}
    original_process_event = engine._process_event
    async def patched_process_event(event):
        if hasattr(event, 'agent_id') and event.agent_id in agent_action_counts:
            agent_action_counts[event.agent_id] += 1
        await original_process_event(event)
    engine._process_event = patched_process_event
    await engine.run_simulation()
    for agent_id, count in agent_action_counts.items():
        assert count >= 20, f"Agent {agent_id} performed only {count} actions."

@pytest.mark.asyncio
async def test_energy_recovery(mock_db_repo):
    """
    Verifies that EnergyRecoveryEvent occurs every 20 minutes.
    """
    engine = SimulationEngine(mock_db_repo)
    await engine.initialize(num_agents=1, duration_days=1)
    energy_recovery_timestamps = []
    original_process_event = engine._process_event
    async def patched_process_event(event):
        if isinstance(event, EnergyRecoveryEvent):
            energy_recovery_timestamps.append(event.timestamp)
        await original_process_event(event)
    engine._process_event = patched_process_event
    await engine.run_simulation()
    for i in range(1, len(energy_recovery_timestamps)):
        time_diff = energy_recovery_timestamps[i] - energy_recovery_timestamps[i-1]
        assert time_diff == 20, f"Time difference between energy recovery events is {time_diff} instead of 20."
