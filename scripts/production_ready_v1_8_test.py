#!/usr/bin/env python3
"""
Production-Ready CAPSIM v1.8 Simulation Test
Optimized constraints for 30-60% agent participation with multi-hour testing.
"""

import sys
import random
import uuid
import time
from pathlib import Path
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from capsim.domain.person import Person


def test_production_ready_simulation():
    """Run production-ready v1.8 simulation with optimized constraints."""
    
    print('🎯 PRODUCTION-READY v1.8 SIMULATION TEST')
    print('='*60)
    print('Optimized constraints targeting 30-60% agent participation')
    
    # Create simulation
    simulation_id = uuid.uuid4()
    print(f'🎮 Simulation ID: {simulation_id}')
    
    # Create production-ready agents with better starting conditions
    persons = []
    professions = ['Developer', 'Teacher', 'Worker', 'Businessman', 'Doctor', 'Artist', 'Blogger', 'ShopClerk']
    
    for i in range(100):  # Production scale
        person = Person(
            id=uuid.uuid4(),
            simulation_id=simulation_id,
            profession=random.choice(professions),
            # Production-ready attribute ranges (balanced for engagement)
            financial_capability=random.uniform(1.5, 4.5),  # Better starting funds
            trend_receptivity=random.uniform(1.0, 4.0),     # Good receptivity
            social_status=random.uniform(1.0, 4.0),         # Active social agents
            energy_level=random.uniform(2.5, 5.0),          # Good starting energy
            time_budget=random.uniform(2.0, 4.5),           # Adequate time
            interests={
                'Economy': random.uniform(0.2, 0.9),
                'Technology': random.uniform(0.2, 0.9), 
                'Social': random.uniform(0.2, 0.9),
                'Entertainment': random.uniform(0.2, 0.9),
                'Politics': random.uniform(0.1, 0.7),
                'Health': random.uniform(0.2, 0.8),
                'Culture': random.uniform(0.2, 0.8)
            },
            first_name=f'Agent{i+1}',
            last_name='Production',
            # v1.8 fields start at defaults
            purchases_today=0,
            last_post_ts=None,
            last_selfdev_ts=None,
            last_purchase_ts={}
        )
        persons.append(person)
    
    print(f'👥 Created {len(persons)} production-ready agents')
    
    # Create engaging trend
    class ProductionTrend:
        def __init__(self):
            self.topic = 'Technology'
            self.virality_score = 3.2  # Higher virality for engagement
            
    trend = ProductionTrend()
    print(f'📈 Trend: {trend.topic} (virality: {trend.virality_score})')
    
    # Production simulation parameters
    SIM_HOURS = 6  # 6-hour simulation
    SIM_MINUTES = SIM_HOURS * 60  # 360 minutes total
    ACCELERATION = 4  # 4x speed (process 4 sim-minutes per iteration)
    
    actions_performed = defaultdict(int)
    agent_actions = defaultdict(int)
    agent_participation = defaultdict(bool)
    total_actions = 0
    failed_actions = 0
    constraint_violations = defaultdict(int)
    hourly_stats = []
    
    print(f'\n🚀 Starting {SIM_HOURS}-hour simulation with {ACCELERATION}x acceleration...')
    print(f'📊 Processing {SIM_MINUTES} sim-minutes in {SIM_MINUTES//ACCELERATION} iterations\n')
    
    start_time = time.time()
    
    for iteration in range(SIM_MINUTES // ACCELERATION):
        # Process multiple sim-minutes per iteration for acceleration
        for accel_step in range(ACCELERATION):
            current_minute = iteration * ACCELERATION + accel_step
            current_time = float(current_minute)
            minute_actions = 0
            
            # **PRODUCTION-OPTIMIZED RESOURCE MANAGEMENT**
            
            # Moderate resource degradation (not too aggressive)
            for person in persons:
                # Energy decreases moderately
                person.energy_level = max(0.5, person.energy_level - random.uniform(0.005, 0.02))
                # Time budget decreases slowly
                person.time_budget = max(0.3, person.time_budget - random.uniform(0.01, 0.04))
                # Financial capability decreases only with purchases
                if person.purchases_today > 0:
                    person.financial_capability = max(0.2, person.financial_capability - 0.005)
            
            # **PRODUCTION-OPTIMIZED RECOVERY** (More frequent, reasonable rates)
            if current_minute % 5 == 0:  # Every 5 minutes
                for person in persons:
                    person.energy_level = min(5.0, person.energy_level + random.uniform(0.1, 0.3))
                    person.time_budget = min(5.0, person.time_budget + random.uniform(0.05, 0.15))
            
            # Each agent decides and acts
            for person in persons:
                try:
                    # Use v1.8 decision algorithm
                    action = person.decide_action_v18(trend, current_time)
                    
                    if action:
                        # **PRODUCTION-OPTIMIZED CONSTRAINT CHECKING**
                        
                        # Special handling for first-time actions (more lenient)
                        is_first_post = (action.__class__.__name__ == 'PostAction' and person.last_post_ts is None)
                        is_first_selfdev = (action.__class__.__name__ == 'SelfDevAction' and person.last_selfdev_ts is None)
                        is_first_purchase = (action.__class__.__name__.startswith('Purchase') and person.purchases_today == 0)
                        
                        # More lenient thresholds for first actions
                        if is_first_post or is_first_selfdev or is_first_purchase:
                            min_energy = 0.5  # Lower energy requirement for first action
                            min_time = 0.3    # Lower time requirement for first action
                        else:
                            min_energy = 1.0  # Normal energy requirement
                            min_time = 0.5    # Normal time requirement
                        
                        # Check basic resource requirements
                        has_energy = person.energy_level >= min_energy
                        has_time = person.time_budget >= min_time
                        
                        # Production-optimized constraint checking
                        can_execute_result = True
                        failure_reason = None
                        
                        if not has_energy:
                            can_execute_result = False
                            failure_reason = "insufficient_energy"
                        elif not has_time:
                            can_execute_result = False  
                            failure_reason = "insufficient_time"
                        else:
                            # Use built-in can_execute with current constraints
                            try:
                                can_execute_result = action.can_execute(person, current_time)
                                if not can_execute_result:
                                    failure_reason = "cooldown_or_limit"
                            except Exception as e:
                                can_execute_result = False
                                failure_reason = "execution_error"
                        
                        if can_execute_result:
                            # **PRODUCTION SUCCESS RATE** (High but not perfect)
                            if random.random() < 0.92:  # 92% success rate
                                action.execute(person, None)
                                
                                action_name = action.__class__.__name__.replace('Action', '')
                                actions_performed[action_name] += 1
                                agent_actions[person.id] += 1
                                agent_participation[person.id] = True
                                minute_actions += 1
                                total_actions += 1
                            else:
                                failed_actions += 1
                                constraint_violations["system_failure"] += 1
                        else:
                            # Track constraint violation reasons
                            failed_actions += 1
                            constraint_violations[failure_reason] += 1
                            
                except Exception as e:
                    # System errors
                    failed_actions += 1
                    constraint_violations["system_error"] += 1
            
            # Daily reset simulation (every 1440 minutes = 24 hours)
            if current_minute > 0 and current_minute % 1440 == 0:
                reset_count = 0
                for person in persons:
                    if person.purchases_today > 0:
                        reset_count += 1
                    person.purchases_today = 0
                print(f'🔄 Daily reset at hour {current_minute//60}: {reset_count} agents had purchases')
        
        # Progress reporting every hour
        if iteration % (60 // ACCELERATION) == 0:
            current_hour = iteration * ACCELERATION // 60
            hour_actions = sum(actions_performed.values()) - sum(h.get('total_actions', 0) for h in hourly_stats)
            active_this_hour = len([aid for aid, actions in agent_actions.items() if actions > 0]) 
            participation_rate = (active_this_hour / len(persons)) * 100
            
            hourly_stat = {
                'hour': current_hour,
                'total_actions': sum(actions_performed.values()),
                'hour_actions': hour_actions,
                'active_agents': active_this_hour,
                'participation_rate': participation_rate
            }
            hourly_stats.append(hourly_stat)
            
            print(f'⏰ Hour {current_hour}: {hour_actions} actions, {active_this_hour} active agents ({participation_rate:.1f}% participation)')
    
    simulation_time = time.time() - start_time
    
    # **COMPREHENSIVE RESULTS ANALYSIS**
    print(f'\n📊 PRODUCTION-READY SIMULATION RESULTS ({SIM_HOURS} sim-hours):')
    print(f'Real simulation time: {simulation_time:.1f} seconds')
    print(f'Acceleration achieved: {(SIM_MINUTES * 60) / simulation_time:.1f}x real-time')
    
    print(f'\n🎯 CORE METRICS:')
    print(f'Total successful actions: {total_actions}')
    print(f'Total failed attempts: {failed_actions}')
    if total_actions + failed_actions > 0:
        success_rate = total_actions/(total_actions+failed_actions)*100
        print(f'Success rate: {success_rate:.1f}%')
    print(f'Actions per agent: {total_actions/len(persons):.1f}')
    print(f'Actions per sim-hour: {total_actions/SIM_HOURS:.1f}')
    
    # Participation analysis
    active_agents = len([aid for aid, actions in agent_actions.items() if actions > 0])
    posting_agents = len([p for p in persons if p.last_post_ts is not None])
    purchasing_agents = len([p for p in persons if p.purchases_today > 0 or p.last_purchase_ts])
    selfdev_agents = len([p for p in persons if p.last_selfdev_ts is not None])
    
    print(f'\n👥 PARTICIPATION ANALYSIS:')
    print(f'Active agents: {active_agents}/{len(persons)} ({active_agents/len(persons)*100:.0f}%)')
    print(f'Posted: {posting_agents}/{len(persons)} ({posting_agents/len(persons)*100:.0f}%)')
    print(f'Purchased: {purchasing_agents}/{len(persons)} ({purchasing_agents/len(persons)*100:.0f}%)')
    print(f'Self-developed: {selfdev_agents}/{len(persons)} ({selfdev_agents/len(persons)*100:.0f}%)')
    
    # Action breakdown
    if total_actions > 0:
        print(f'\n📈 ACTION BREAKDOWN:')
        for action_type, count in sorted(actions_performed.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_actions * 100)
            print(f'  {action_type}: {count} ({percentage:.1f}%)')
    
    # Constraint violation analysis
    print(f'\n🛑 CONSTRAINT VIOLATIONS ANALYSIS:')
    total_violations = sum(constraint_violations.values())
    for reason, count in sorted(constraint_violations.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_violations * 100) if total_violations > 0 else 0
        print(f'  {reason}: {count} ({percentage:.1f}%)')
    
    # Hourly trends
    print(f'\n📊 HOURLY PARTICIPATION TRENDS:')
    for stat in hourly_stats:
        print(f'  Hour {stat["hour"]}: {stat["hour_actions"]} actions, {stat["participation_rate"]:.1f}% participation')
    
    # Resource state analysis
    avg_energy = sum(p.energy_level for p in persons) / len(persons)
    avg_financial = sum(p.financial_capability for p in persons) / len(persons)
    avg_time = sum(p.time_budget for p in persons) / len(persons)
    
    print(f'\n📈 FINAL RESOURCE STATES:')
    print(f'Average energy: {avg_energy:.2f}/5.0')
    print(f'Average financial capability: {avg_financial:.2f}/5.0')
    print(f'Average time budget: {avg_time:.2f}/5.0')
    
    # **TARGET ACHIEVEMENT ANALYSIS**
    participation_rate = (active_agents/len(persons))*100
    target_met = 30 <= participation_rate <= 60
    
    print(f'\n🎯 PRODUCTION READINESS ASSESSMENT:')
    print(f'Target participation: 30-60%')
    print(f'Achieved participation: {participation_rate:.1f}%')
    print(f'Target met: {"✅ YES" if target_met else "❌ NO"}')
    
    if target_met:
        print(f'🎉 PRODUCTION-READY! Constraint configuration successful.')
    else:
        if participation_rate < 30:
            print(f'⚠️ Under-participation. Recommend: Reduce cooldowns, increase recovery rates')
        else:
            print(f'⚠️ Over-participation. Recommend: Increase cooldowns, reduce recovery rates')
    
    # Sample successful agents analysis
    successful_agents = [(aid, actions) for aid, actions in agent_actions.items() if actions > 0]
    if successful_agents:
        successful_agents.sort(key=lambda x: x[1], reverse=True)
        print(f'\n🏆 TOP PERFORMING AGENTS:')
        for i, (agent_id, action_count) in enumerate(successful_agents[:5]):
            agent = next(p for p in persons if p.id == agent_id)
            print(f'  #{i+1}: {agent.profession} - {action_count} actions (energy: {agent.energy_level:.1f}, funds: {agent.financial_capability:.1f})')
    
    print(f'\n✅ PRODUCTION-READY v1.8 SIMULATION COMPLETE!')
    print(f'Constraint optimization {"successful" if target_met else "needs adjustment"}')


if __name__ == "__main__":
    test_production_ready_simulation() 