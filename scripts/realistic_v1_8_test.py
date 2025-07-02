#!/usr/bin/env python3
"""
Realistic CAPSIM v1.8 Simulation Test 
Demonstrates realistic behavior vs mock test results.
"""

import sys
import random
import uuid
from pathlib import Path
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from capsim.domain.person import Person


def test_realistic_simulation():
    """Run realistic v1.8 simulation test."""
    
    print('🧪 REALISTIC v1.8 SIMULATION TEST')
    print('='*50)
    print('Testing with realistic conditions and constraints')
    
    # Create simulation
    simulation_id = uuid.uuid4()
    print(f'🎮 Simulation ID: {simulation_id}')
    
    # Create realistic test agents (smaller number, realistic attributes)
    persons = []
    professions = ['Developer', 'Teacher', 'Worker', 'Businessman', 'Doctor', 'Artist']
    
    for i in range(50):  # Smaller realistic population
        person = Person(
            id=uuid.uuid4(),
            simulation_id=simulation_id,
            profession=random.choice(professions),
            # More realistic attribute ranges (not always high)
            financial_capability=random.uniform(0.5, 3.5),  # Lower average
            trend_receptivity=random.uniform(0.5, 3.0),     # More variation
            social_status=random.uniform(0.5, 3.0),         # Not everyone is social
            energy_level=random.uniform(1.5, 4.0),          # Starting tired
            time_budget=random.uniform(1.0, 3.5),           # Limited time
            interests={
                'Economy': random.uniform(0.1, 0.8),
                'Technology': random.uniform(0.1, 0.8), 
                'Social': random.uniform(0.1, 0.8),
                'Entertainment': random.uniform(0.1, 0.8),
                'Politics': random.uniform(0.1, 0.6),
                'Health': random.uniform(0.1, 0.7),
                'Culture': random.uniform(0.1, 0.6)
            },
            first_name=f'Agent{i+1}',
            last_name='Realistic',
            # v1.8 fields start at defaults
            purchases_today=0,
            last_post_ts=None,
            last_selfdev_ts=None,
            last_purchase_ts={}
        )
        persons.append(person)
    
    print(f'👥 Created {len(persons)} realistic agents')
    
    # Create simple trend
    class MockTrend:
        def __init__(self):
            self.topic = 'Technology'
            self.virality_score = 2.8
            
    trend = MockTrend()
    print(f'📈 Trend: {trend.topic} (virality: {trend.virality_score})')
    
    # Realistic simulation parameters
    SIM_MINUTES = 60  # 1 hour simulation
    actions_performed = defaultdict(int)
    agent_actions = defaultdict(int)
    total_actions = 0
    failed_actions = 0
    
    print(f'\n🚀 Starting {SIM_MINUTES}-minute realistic simulation...')
    
    for minute in range(SIM_MINUTES):
        current_time = float(minute)
        minute_actions = 0
        
        # Realistic resource degradation
        for person in persons:
            # Energy decreases with activity
            person.energy_level = max(0.2, person.energy_level - random.uniform(0.01, 0.05))
            # Time budget decreases
            person.time_budget = max(0.1, person.time_budget - random.uniform(0.02, 0.08))
            # Financial capability may decrease with purchases
            if person.purchases_today > 0:
                person.financial_capability = max(0.1, person.financial_capability - 0.01)
        
        # Each agent decides and acts (with failure rate)
        for person in persons:
            try:
                # Use v1.8 decision algorithm
                action = person.decide_action_v18(trend, current_time)
                
                if action:
                    # Real-world constraint checking
                    if action.can_execute(person, current_time):
                        # Simulate occasional failures (DB issues, network, etc.)
                        if random.random() < 0.95:  # 95% success rate
                            action.execute(person, None)
                            
                            action_name = action.__class__.__name__.replace('Action', '')
                            actions_performed[action_name] += 1
                            agent_actions[person.id] += 1
                            minute_actions += 1
                            total_actions += 1
                        else:
                            failed_actions += 1
                    else:
                        # Action blocked by cooldowns/constraints
                        failed_actions += 1
                        
            except Exception as e:
                # Realistic error handling
                failed_actions += 1
        
        # Periodic energy recovery (realistic - not every step)
        if minute % 10 == 0:  # Every 10 minutes
            for person in persons:
                person.energy_level = min(5.0, person.energy_level + random.uniform(0.05, 0.15))
                person.time_budget = min(5.0, person.time_budget + random.uniform(0.02, 0.08))
        
        # Daily reset simulation (every 60 minutes = 1 day)
        if minute % 60 == 0 and minute > 0:
            for person in persons:
                person.purchases_today = 0
            print(f'🔄 Daily reset at minute {minute}')
        
        # Progress updates
        if minute % 15 == 0:
            print(f'⏱️  Minute {minute}: {minute_actions} actions, {failed_actions} total failures')
    
    # Calculate results
    print(f'\n📊 REALISTIC SIMULATION RESULTS ({SIM_MINUTES} sim-minutes):')
    print(f'Total successful actions: {total_actions}')
    print(f'Total failed attempts: {failed_actions}')
    if total_actions + failed_actions > 0:
        print(f'Success rate: {total_actions/(total_actions+failed_actions)*100:.1f}%')
    print(f'Actions per agent: {total_actions/len(persons):.1f}')
    print(f'Actions per minute: {total_actions/SIM_MINUTES:.1f}')
    
    if total_actions > 0:
        print(f'\n📈 Action breakdown:')
        for action_type, count in sorted(actions_performed.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_actions * 100)
            print(f'  {action_type}: {count} ({percentage:.1f}%)')
    
    # Participation analysis
    active_agents = len([aid for aid, actions in agent_actions.items() if actions > 0])
    posting_agents = len([p for p in persons if p.last_post_ts is not None])
    purchasing_agents = len([p for p in persons if p.purchases_today > 0])
    selfdev_agents = len([p for p in persons if p.last_selfdev_ts is not None])
    
    print(f'\n👥 Agent participation analysis:')
    print(f'  Active agents: {active_agents}/{len(persons)} ({active_agents/len(persons)*100:.0f}%)')
    print(f'  Posted: {posting_agents}/{len(persons)} ({posting_agents/len(persons)*100:.0f}%)')
    print(f'  Purchased: {purchasing_agents}/{len(persons)} ({purchasing_agents/len(persons)*100:.0f}%)')
    print(f'  Self-developed: {selfdev_agents}/{len(persons)} ({selfdev_agents/len(persons)*100:.0f}%)')
    
    # Compare with mock results
    print(f'\n🔍 COMPARISON WITH MOCK TEST:')
    print(f'  Mock test (60 min): 728 actions, 7.28 per agent, 100% participation')
    print(f'  Real test (60 min): {total_actions} actions, {total_actions/len(persons):.1f} per agent, {active_agents/len(persons)*100:.0f}% participation')
    
    if total_actions > 0:
        realism_factor = 728 / total_actions
        print(f'  Mock was {realism_factor:.1f}x more active than realistic conditions')
    
    # Resource state analysis
    avg_energy = sum(p.energy_level for p in persons) / len(persons)
    avg_financial = sum(p.financial_capability for p in persons) / len(persons)
    avg_time = sum(p.time_budget for p in persons) / len(persons)
    
    print(f'\n📈 Final resource states:')
    print(f'  Average energy: {avg_energy:.2f}/5.0')
    print(f'  Average financial capability: {avg_financial:.2f}/5.0')
    print(f'  Average time budget: {avg_time:.2f}/5.0')
    
    print(f'\n✅ REALISTIC v1.8 SIMULATION COMPLETE!')
    print(f'This shows expected production behavior vs unrealistic mock test results.')


if __name__ == "__main__":
    test_realistic_simulation() 