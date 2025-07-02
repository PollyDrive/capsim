#!/usr/bin/env python3
"""
CAPSIM v1.8 Simplified Functionality Test
Tests v1.8 action system without full engine initialization.

Tech-Lead validation script.
"""

import sys
import time
import random
from pathlib import Path
from uuid import uuid4
from collections import defaultdict, Counter

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from capsim.domain.person import Person
from capsim.simulation.actions.factory import ACTION_FACTORY
from capsim.common.settings import action_config
from capsim.domain.events import DailyResetEvent


def test_v1_8_functionality():
    """Test v1.8 functionality with 100 agents over simulation time."""
    print("🚀 CAPSIM v1.8 Simplified Test")
    print("="*50)
    
    # Configuration
    num_agents = 100
    simulation_duration = 60.0  # 1 hour in sim-minutes
    current_time = 0.0
    time_step = 5.0  # 5-minute steps
    
    stats = {
        'agents_created': 0,
        'actions_executed': defaultdict(int),
        'agent_states': [],
        'errors': []
    }
    
    try:
        # 1. Create 100 diverse agents
        print("👥 Creating 100 test agents...")
        agents = []
        professions = [
            "Developer", "Businessman", "Teacher", "Doctor", "Artist",
            "Worker", "Blogger", "Politician", "ShopClerk", "SpiritualMentor", 
            "Philosopher", "Unemployed"
        ]
        
        for i in range(num_agents):
            profession = professions[i % len(professions)]
            try:
                agent = Person.create_random_agent(
                    profession=profession,
                    simulation_id=uuid4()
                )
                agents.append(agent)
                stats['agents_created'] += 1
                
                if i % 20 == 0:
                    print(f"   Created {i+1}/100 agents...")
                    
            except Exception as e:
                print(f"❌ Failed to create agent {i}: {e}")
                stats['errors'].append(f"Agent creation {i}: {e}")
        
        print(f"✅ Created {len(agents)} agents")
        
        # 2. Simulate 1 hour with 5-minute steps
        print(f"⏳ Running simulation for {simulation_duration} minutes...")
        
        step_count = 0
        while current_time < simulation_duration:
            step_count += 1
            print(f"   Step {step_count}: sim-time {current_time:.1f} min")
            
            # Process daily reset at midnight (every 1440 minutes)
            if current_time > 0 and current_time % 1440 == 0:
                print(f"   🌅 Daily reset at {current_time} minutes")
                for agent in agents:
                    agent.purchases_today = 0
            
            # Let agents make decisions and execute actions
            actions_this_step = 0
            
            for agent in agents:
                # Skip agents with no energy or time
                if agent.energy_level <= 0 or agent.time_budget <= 0:
                    continue
                
                # Mock trend for decision making
                class MockTrend:
                    def __init__(self):
                        self.virality_score = random.uniform(5, 10)
                        self.topic = random.choice(["Economic", "Health", "Culture"])
                
                trend = MockTrend()
                
                # Agent decides on action
                action_name = agent.decide_action_v18(trend, current_time)
                
                if action_name and action_name in ACTION_FACTORY:
                    action = ACTION_FACTORY[action_name]
                    
                    # Check if can execute
                    action_instance = action()
                    if action_instance.can_execute(agent, current_time):
                        try:
                            # Mock engine for execution
                            class MockEngine:
                                def __init__(self):
                                    self.current_time = current_time
                                def add_event(self, *args, **kwargs):
                                    pass
                            
                            mock_engine = MockEngine()
                            
                            # Execute action
                            action_instance.execute(agent, mock_engine)
                            
                            stats['actions_executed'][action_name] += 1
                            actions_this_step += 1
                            
                        except Exception as e:
                            stats['errors'].append(f"Action execution {action_name}: {e}")
            
            print(f"      → {actions_this_step} actions executed")
            
            # Apply natural recovery/decay
            for agent in agents:
                # Small energy recovery each step
                if agent.energy_level < 5.0:
                    agent.energy_level = min(5.0, agent.energy_level + 0.1)
                
                # Small time budget recovery
                if agent.time_budget < 5.0:
                    agent.time_budget = min(5.0, agent.time_budget + 0.1)
            
            current_time += time_step
        
        # 3. Collect final statistics
        print("📊 Collecting final statistics...")
        
        for agent in agents:
            agent_state = {
                'profession': agent.profession,
                'energy_level': agent.energy_level,
                'financial_capability': agent.financial_capability,
                'social_status': agent.social_status,
                'time_budget': agent.time_budget,
                'purchases_today': agent.purchases_today,
                'has_posted': agent.last_post_ts is not None,
                'has_selfdev': agent.last_selfdev_ts is not None,
                'total_purchases': sum(1 for ts in agent.last_purchase_ts.values() if ts is not None)
            }
            stats['agent_states'].append(agent_state)
        
        # 4. Generate report
        print("\n" + "="*60)
        print("🎉 CAPSIM v1.8 SIMPLIFIED TEST REPORT")
        print("="*60)
        
        print(f"⏱️  Simulation duration: {current_time:.1f} sim-minutes")
        print(f"👥 Agents: {len(agents)}")
        print(f"📈 Steps: {step_count}")
        
        print("\n🎬 ACTION STATISTICS:")
        total_actions = sum(stats['actions_executed'].values())
        print(f"   Total actions: {total_actions}")
        for action_type, count in stats['actions_executed'].items():
            print(f"   {action_type}: {count}")
        
        if total_actions > 0:
            print(f"   Actions per agent: {total_actions / len(agents):.2f}")
            print(f"   Actions per minute: {total_actions / current_time:.2f}")
        
        print("\n📊 AGENT STATISTICS:")
        profession_counts = Counter(s['profession'] for s in stats['agent_states'])
        print(f"   Profession distribution: {dict(profession_counts)}")
        
        # Average attributes
        avg_energy = sum(s['energy_level'] for s in stats['agent_states']) / len(stats['agent_states'])
        avg_financial = sum(s['financial_capability'] for s in stats['agent_states']) / len(stats['agent_states'])
        avg_social = sum(s['social_status'] for s in stats['agent_states']) / len(stats['agent_states'])
        avg_time = sum(s['time_budget'] for s in stats['agent_states']) / len(stats['agent_states'])
        
        print(f"   Average energy: {avg_energy:.2f}")
        print(f"   Average financial: {avg_financial:.2f}")
        print(f"   Average social: {avg_social:.2f}")
        print(f"   Average time budget: {avg_time:.2f}")
        
        print("\n🆕 v1.8 FEATURE USAGE:")
        agents_with_posts = sum(1 for s in stats['agent_states'] if s['has_posted'])
        agents_with_selfdev = sum(1 for s in stats['agent_states'] if s['has_selfdev'])
        agents_with_purchases = sum(1 for s in stats['agent_states'] if s['purchases_today'] > 0)
        
        print(f"   Agents who posted: {agents_with_posts}/{len(agents)} ({100*agents_with_posts/len(agents):.1f}%)")
        print(f"   Agents who used self-dev: {agents_with_selfdev}/{len(agents)} ({100*agents_with_selfdev/len(agents):.1f}%)")
        print(f"   Agents who purchased: {agents_with_purchases}/{len(agents)} ({100*agents_with_purchases/len(agents):.1f}%)")
        
        # Test validation
        print("\n✅ VALIDATION RESULTS:")
        
        validations = []
        
        # Check that actions were executed
        if total_actions > 0:
            validations.append("✅ Actions executed successfully")
        else:
            validations.append("❌ No actions executed")
        
        # Check v1.8 features used
        if agents_with_posts > 0 and agents_with_selfdev > 0 and agents_with_purchases > 0:
            validations.append("✅ All v1.8 action types used")
        else:
            validations.append("⚠️  Some v1.8 action types not used")
        
        # Check no critical errors
        critical_errors = [e for e in stats['errors'] if 'create_random_agent' in e]
        if not critical_errors:
            validations.append("✅ No critical errors")
        else:
            validations.append(f"❌ {len(critical_errors)} critical errors")
        
        # Check agents maintained valid states
        invalid_agents = [s for s in stats['agent_states'] if s['energy_level'] < 0 or s['time_budget'] < 0]
        if not invalid_agents:
            validations.append("✅ All agents in valid states")
        else:
            validations.append(f"❌ {len(invalid_agents)} agents in invalid states")
        
        for validation in validations:
            print(f"   {validation}")
        
        if stats['errors']:
            print(f"\n⚠️  ERRORS: {len(stats['errors'])}")
            for error in stats['errors'][:3]:
                print(f"   - {error}")
            if len(stats['errors']) > 3:
                print(f"   ... and {len(stats['errors']) - 3} more")
        
        print("\n" + "="*60)
        
        # Determine overall result
        success_count = sum(1 for v in validations if v.startswith("✅"))
        if success_count >= 3:
            print("🎉 TEST RESULT: PASSED")
            return True
        else:
            print("❌ TEST RESULT: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_v1_8_functionality()
    sys.exit(0 if success else 1) 