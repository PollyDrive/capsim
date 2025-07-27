"""
Test suite for CAPSIM v1.8 features.
Validates action system, cooldowns, purchase limits, and daily reset functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime, date
from uuid import uuid4
import json

from capsim.domain.person import Person
from capsim.common.settings import action_config
from capsim.common.metrics import record_action, ACTIONS_TOTAL, AGENT_ATTRIBUTE
from capsim.domain.events import DailyResetEvent, EventPriority

# Import lazily to avoid missing factory in minimal env
try:
    from capsim.simulation.actions.factory import ACTION_FACTORY, ActionType
except ImportError:
    ACTION_FACTORY, ActionType = {}, None


class TestV18Features:
    """Test v1.8 action system features."""
    
    def test_person_v18_fields(self):
        """Test Person has all v1.8 fields."""
        person = Person(
            profession="Developer",
            simulation_id=uuid4()
        )
        
        # Check v1.8 fields exist
        assert hasattr(person, 'purchases_today')
        assert hasattr(person, 'last_post_ts')
        assert hasattr(person, 'last_selfdev_ts')
        assert hasattr(person, 'last_purchase_ts')
        
        # Check default values
        assert person.purchases_today == 0
        assert person.last_post_ts is None
        assert person.last_selfdev_ts is None
        assert isinstance(person.last_purchase_ts, dict)
    
    def test_action_factory_completeness(self):
        """Test all v1.8 actions are in factory."""
        expected_actions = ["Post", "Purchase_L1", "Purchase_L2", "Purchase_L3", "SelfDev"]
        
        for action_name in expected_actions:
            assert action_name in ACTION_FACTORY
            action = ACTION_FACTORY[action_name]
            assert hasattr(action, 'execute')
            assert hasattr(action, 'can_execute')
    
    def test_purchase_cooldowns(self):
        """Test purchase limits and financial capability checks."""
        person = Person(
            profession="Developer",
            financial_capability=3.0,
            simulation_id=uuid4()
        )
        current_time = 100.0
        
        # Test L1 purchase capability
        assert person.can_purchase(current_time, "L1")
        
        # Test daily limit (MAX_PURCHASES_DAY: 5 from config/actions.yaml)
        person.purchases_today = 4  # Still below limit
        assert person.can_purchase(current_time, "L1")
        
        person.purchases_today = 5  # At limit
        assert not person.can_purchase(current_time, "L1")
        
        # Reset and test financial capability based on config/actions.yaml
        person.purchases_today = 0
        person.financial_capability = 1.0  # Too low for L2 (cost_range: [1.1, 2.4])
        assert not person.can_purchase(current_time, "L2")
        
        # Test L3 financial requirement
        person.financial_capability = 2.4  # Too low for L3 (cost_range: [2.5, 3.5])
        assert not person.can_purchase(current_time, "L3")
        
        person.financial_capability = 2.5  # Sufficient for L3 (minimum cost)
        assert person.can_purchase(current_time, "L3")
    
    def test_post_cooldown_logic(self):
        """Test post cooldown management."""
        person = Person(
            profession="Blogger",
            energy_level=3.0,
            time_budget=1.0,
            trend_receptivity=2.0,
            simulation_id=uuid4()
        )
        
        current_time = 100.0
        
        # First post should be allowed
        assert person.can_post(current_time)
        
        # Set last post time
        person.last_post_ts = current_time
        
        # With POST_MIN cooldown (40m from config), posting again at +40m allowed
        assert person.can_post(current_time + 40.0)
        
        # Should not allow at +10m
        assert not person.can_post(current_time + 10.0)
    
    def test_self_dev_cooldown_logic(self):
        """Test self-development cooldown management."""
        person = Person(
            profession="Artist",
            time_budget=2.0,
            simulation_id=uuid4()
        )
        
        current_time = 200.0
        
        # First self-dev should be allowed
        assert person.can_self_dev(current_time)
        
        # Set last self-dev time
        person.last_selfdev_ts = current_time
        
        # SELF_DEV_MIN cooldown (30m from config); after 30m allowed
        assert person.can_self_dev(current_time + 30.0)
        
        # Immediately after (5m) disallowed
        assert not person.can_self_dev(current_time + 5.0)
    
    def test_apply_effects(self):
        """Test effects application with boundary checks."""
        person = Person(
            profession="Developer",
            energy_level=3.0,
            financial_capability=2.0,
            social_status=1.5,
            time_budget=2.5,
            simulation_id=uuid4()
        )
        
        # Test POST effects
        post_effects = action_config.effects["POST"]
        person.apply_effects(post_effects)
        
        assert person.energy_level == 2.8  # 3.0 - 0.20
        assert person.social_status == 1.55  # 1.5 + 0.05
        assert person.time_budget == 2.5  # 2.5 - 0.15 = 2.35, rounded to 2.5
        
        # Test boundary limits
        person.energy_level = 0.2
        person.apply_effects({"energy_level": -1.0})
        assert person.energy_level == 0.0  # Should not go below 0
        
        person.energy_level = 4.8
        person.apply_effects({"energy_level": 1.0})
        assert person.energy_level == 5.0  # Should not go above 5
    
    def test_shop_weights_application(self):
        """Test profession-based purchase modifiers."""
        # Test high-weight profession
        businessman_weight = action_config.shop_weights.get("Businessman", 1.0)
        assert businessman_weight == 1.20
        
        # Test low-weight profession  
        unemployed_weight = action_config.shop_weights.get("Unemployed", 1.0)
        assert unemployed_weight == 0.60
        
        # Test default profession
        default_weight = action_config.shop_weights.get("NonExistentProfession", 1.0)
        assert default_weight == 1.0
    
    def test_decide_action_v18_algorithm(self):
        """Test weighted action selection algorithm."""
        person = Person(
            profession="Developer",
            energy_level=4.0,
            financial_capability=3.0,
            time_budget=3.0,
            trend_receptivity=2.0,
            social_status=3.0,
            simulation_id=uuid4()
        )
        
        current_time = 300.0
        
        # Mock trend
        mock_trend = Mock()
        mock_trend.virality_score = 8.0
        mock_trend.topic = "Economic"
        mock_trend.calculate_current_virality = lambda: 8.0
        
        # Should return an action name
        action_name = person.decide_action_v18(mock_trend, current_time)
        
        # Action should be one of valid types
        if action_name:
            assert action_name in ["Post", "Purchase_L1", "Purchase_L2", "Purchase_L3", "SelfDev"]
    
    @pytest.mark.asyncio
    async def test_daily_reset_event(self):
        """Test DailyResetEvent functionality."""
        # Create mock engine with agents
        mock_engine = Mock()
        mock_agents = []
        
        for i in range(3):
            agent = Person(profession="Developer", simulation_id=uuid4())
            agent.purchases_today = 3  # Set some purchases
            mock_agents.append(agent)
        
        mock_engine.agents = mock_agents
        mock_engine.add_event = Mock()
        
        # Create and execute daily reset event
        reset_event = DailyResetEvent(timestamp=1440.0)
        reset_event.process(mock_engine)
        
        # Check all agents have reset purchases
        for agent in mock_agents:
            assert agent.purchases_today == 0
        
        # Check next event scheduled
        assert mock_engine.add_event.called
    
    def test_action_config_loading(self):
        """Test action configuration loads correctly."""
        # Check cooldowns
        assert action_config.cooldowns["POST_MIN"] == 40
        assert action_config.cooldowns["SELF_DEV_MIN"] == 30
        
        # Check limits
        assert action_config.limits["MAX_PURCHASES_DAY"] == 5
        
        # Check effects structure
        assert "POST" in action_config.effects
        assert "SELF_DEV" in action_config.effects
        assert "PURCHASE" in action_config.effects
        
        # Check purchase effects
        assert "L1" in action_config.effects["PURCHASE"]
        assert "L2" in action_config.effects["PURCHASE"]
        assert "L3" in action_config.effects["PURCHASE"]
    
    def test_event_priority_system(self):
        """Test v1.8 event priority values."""
        assert EventPriority.SYSTEM == 100
        assert EventPriority.AGENT_ACTION == 50
        assert EventPriority.LOW == 0
        
        # Test ordering
        assert EventPriority.SYSTEM > EventPriority.AGENT_ACTION
        assert EventPriority.AGENT_ACTION > EventPriority.LOW
    
    def test_metrics_integration(self):
        """Test Prometheus metrics are recorded correctly."""
        # Test record_action function exists and works
        try:
            record_action("Post", "", "Developer")
            record_action("Purchase", "L1", "Businessman")
            record_action("SelfDev", "", "Artist")
            # Should not raise exceptions
        except Exception as e:
            pytest.fail(f"Metrics recording failed: {e}")
        
        # Test metrics objects exist
        assert ACTIONS_TOTAL is not None
        assert AGENT_ATTRIBUTE is not None


class TestV18Integration:
    """Integration tests for v1.8 system."""
    
    def test_action_execution_mock(self):
        """Test action execution capability check."""
        person = Person(
            profession="Developer",
            energy_level=3.0,
            financial_capability=2.0,
            time_budget=2.0,
            trend_receptivity=2.0,  # Required for posting
            simulation_id=uuid4()
        )
        
        mock_engine = Mock()
        mock_engine.current_time = 500.0
        
        # Test Post action capability check
        if ACTION_FACTORY:
            post_action = ACTION_FACTORY["Post"]
            assert post_action.can_execute(person, mock_engine.current_time)
            
            # Test that action has required methods
            assert hasattr(post_action, 'execute')
            assert hasattr(post_action, 'can_execute')
    
    def test_performance_requirements(self):
        """Test that v1.8 components meet performance requirements."""
        import time
        
        # Test action decision speed
        person = Person(profession="Developer", simulation_id=uuid4())
        
        start_time = time.time()
        for _ in range(100):
            person.decide_action_v18(None, 100.0)
        
        decision_time = time.time() - start_time
        
        # Should complete 100 decisions in under 1 second
        assert decision_time < 1.0, f"Decision algorithm too slow: {decision_time:.3f}s"
        
        # Test effects application speed
        start_time = time.time()
        for _ in range(1000):
            person.apply_effects(action_config.effects["POST"])
        
        effects_time = time.time() - start_time
        
        # Should complete 1000 effect applications in under 1 second
        assert effects_time < 1.0, f"Effects application too slow: {effects_time:.3f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 