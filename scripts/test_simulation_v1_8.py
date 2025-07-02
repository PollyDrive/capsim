#!/usr/bin/env python3
"""
CAPSIM v1.8 Intermediate Simulation Test
Runs a 1-hour simulation with 100 agents to validate v1.8 functionality.

Tech-Lead validation script.
"""

import asyncio
import logging
import json
import time
from datetime import datetime
from pathlib import Path
import sys
import os

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from capsim.engine.simulation_engine import SimulationEngine
from capsim.db.repositories import DatabaseRepository
from capsim.domain.person import Person
from capsim.simulation.actions.factory import ACTION_FACTORY
from capsim.common.settings import action_config
from capsim.common.clock import SimClock
from uuid import uuid4
from collections import defaultdict, Counter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimulationTester:
    """Test harness for v1.8 simulation validation."""
    
    def __init__(self):
        self.simulation_id = uuid4()
        self.start_time = None
        self.end_time = None
        self.stats = {
            'agents_created': 0,
            'events_processed': 0,
            'actions_executed': defaultdict(int),
            'agent_final_states': [],
            'performance_metrics': {},
            'errors': []
        }
        
    async def run_test_simulation(self):
        """Run the complete test simulation."""
        logger.info("🚀 Starting CAPSIM v1.8 Intermediate Simulation Test")
        logger.info(f"📊 Configuration: 100 agents, 1 hour simulation")
        logger.info(f"🆔 Simulation ID: {self.simulation_id}")
        
        self.start_time = time.time()
        
        try:
            # 1. Setup
            await self._setup_simulation()
            
            # 2. Create agents
            await self._create_test_agents()
            
            # 3. Run simulation
            await self._run_simulation()
            
            # 4. Collect results
            await self._collect_final_stats()
            
            # 5. Generate report
            self._generate_report()
            
        except Exception as e:
            logger.error(f"❌ Simulation failed: {e}")
            self.stats['errors'].append(str(e))
            raise
        finally:
            self.end_time = time.time()
    
    async def _setup_simulation(self):
        """Setup simulation environment."""
        logger.info("⚙️ Setting up simulation environment...")
        
        # Mock database repository for testing
        class MockDatabaseRepository:
            def __init__(self):
                self.simulation_id = None
                
            async def create_simulation(self, *args, **kwargs):
                return self.simulation_id
            
            async def create_simulation_run(self, *args, **kwargs):
                return self.simulation_id
            
            async def create_person(self, person):
                return person
            
            async def create_event(self, event):
                pass
                
            async def update_simulation_status(self, *args, **kwargs):
                pass
                
            async def create_trend(self, trend):
                return trend
                
            async def get_simulations_by_status(self, *args, **kwargs):
                return []  # No stale simulations
                
            async def delete_simulation(self, *args, **kwargs):
                pass
                
            async def get_persons_by_simulation(self, *args, **kwargs):
                return []
                
            async def update_person_state(self, *args, **kwargs):
                pass
                
            async def bulk_insert_events(self, *args, **kwargs):
                pass
                
            async def bulk_update_persons(self, *args, **kwargs):  
                pass
        
        self.db_repo = MockDatabaseRepository()
        self.db_repo.simulation_id = self.simulation_id
        
        # Initialize engine with mock repo
        self.engine = SimulationEngine(
            db_repo=self.db_repo,
            clock=SimClock()
        )
        
        await self.engine.initialize(num_agents=0)  # We'll create manually
        
        logger.info("✅ Simulation environment ready")
    
    async def _create_test_agents(self):
        """Create 100 test agents with diverse professions."""
        logger.info("👥 Creating 100 test agents...")
        
        professions = [
            "Developer", "Businessman", "Teacher", "Doctor", "Artist",
            "Worker", "Blogger", "Politician", "ShopClerk", "SpiritualMentor",
            "Philosopher", "Unemployed"
        ]
        
        for i in range(100):
            profession = professions[i % len(professions)]
            
            try:
                person = Person.create_random_agent(
                    profession=profession,
                    simulation_id=self.simulation_id
                )
                
                # Add to engine
                self.engine.agents.append(person)
                self.stats['agents_created'] += 1
                
                if i % 20 == 0:
                    logger.info(f"👤 Created {i+1}/100 agents...")
                    
            except Exception as e:
                logger.error(f"❌ Failed to create agent {i}: {e}")
                self.stats['errors'].append(f"Agent creation {i}: {e}")
        
        logger.info(f"✅ Created {self.stats['agents_created']} agents")
    
    async def _run_simulation(self):
        """Run the 1-hour simulation."""
        logger.info("⏳ Starting 1-hour simulation (60 sim-minutes)...")
        
        # Track performance
        sim_start = time.time()
        
        try:
            # Run for 1 hour simulation time (60 minutes)
            await self.engine.run_simulation(duration_days=1/24)  # 1 hour = 1/24 day
            
        except Exception as e:
            logger.error(f"❌ Simulation execution failed: {e}")
            raise
        
        sim_duration = time.time() - sim_start
        self.stats['performance_metrics']['simulation_duration_real'] = sim_duration
        self.stats['performance_metrics']['simulation_duration_sim'] = self.engine.current_time
        
        logger.info(f"✅ Simulation completed in {sim_duration:.2f} real seconds")
        logger.info(f"📊 Simulated time: {self.engine.current_time:.1f} minutes")
    
    async def _collect_final_stats(self):
        """Collect final statistics from the simulation."""
        logger.info("📊 Collecting final statistics...")
        
        # Agent statistics
        for agent in self.engine.agents:
            agent_state = {
                'id': str(agent.id),
                'profession': agent.profession,
                'energy_level': agent.energy_level,
                'financial_capability': agent.financial_capability,
                'social_status': agent.social_status,
                'time_budget': agent.time_budget,
                'purchases_today': agent.purchases_today,
                'last_post_ts': agent.last_post_ts,
                'last_selfdev_ts': agent.last_selfdev_ts,
                'last_purchase_ts': agent.last_purchase_ts
            }
            self.stats['agent_final_states'].append(agent_state)
        
        # Count v1.8 actions that occurred
        action_counts = defaultdict(int)
        for agent in self.engine.agents:
            if agent.last_post_ts is not None:
                action_counts['Post'] += 1
            if agent.last_selfdev_ts is not None:
                action_counts['SelfDev'] += 1
            if agent.purchases_today > 0:
                action_counts['Purchase'] += agent.purchases_today
        
        self.stats['actions_executed'] = dict(action_counts)
        
        logger.info("✅ Statistics collected")
    
    def _generate_report(self):
        """Generate final test report."""
        total_duration = self.end_time - self.start_time
        
        print("\n" + "="*60)
        print("🎉 CAPSIM v1.8 SIMULATION TEST REPORT")
        print("="*60)
        
        print(f"🆔 Simulation ID: {self.simulation_id}")
        print(f"⏱️  Total Duration: {total_duration:.2f} seconds")
        print(f"🎯 Simulation Time: {self.stats['performance_metrics'].get('simulation_duration_sim', 0):.1f} minutes")
        
        print("\n📊 AGENT STATISTICS:")
        print(f"   Created: {self.stats['agents_created']}")
        print(f"   Final count: {len(self.stats['agent_final_states'])}")
        
        # Profession distribution
        profession_counts = Counter(agent['profession'] for agent in self.stats['agent_final_states'])
        print(f"   Professions: {dict(profession_counts)}")
        
        print("\n🎬 ACTION STATISTICS:")
        total_actions = sum(self.stats['actions_executed'].values())
        print(f"   Total actions: {total_actions}")
        for action_type, count in self.stats['actions_executed'].items():
            print(f"   {action_type}: {count}")
        
        print("\n⚡ PERFORMANCE METRICS:")
        sim_real_time = self.stats['performance_metrics'].get('simulation_duration_real', 0)
        sim_sim_time = self.stats['performance_metrics'].get('simulation_duration_sim', 0)
        if sim_real_time > 0 and sim_sim_time > 0:
            speed_factor = sim_sim_time / sim_real_time * 60  # minutes per real second
            print(f"   Speed factor: {speed_factor:.1f}x (sim-minutes per real-second)")
            print(f"   Actions per second: {total_actions / sim_real_time:.1f}")
        
        print("\n🧮 AGENT ATTRIBUTE AVERAGES:")
        if self.stats['agent_final_states']:
            avg_energy = sum(a['energy_level'] for a in self.stats['agent_final_states']) / len(self.stats['agent_final_states'])
            avg_financial = sum(a['financial_capability'] for a in self.stats['agent_final_states']) / len(self.stats['agent_final_states'])
            avg_social = sum(a['social_status'] for a in self.stats['agent_final_states']) / len(self.stats['agent_final_states'])
            avg_time = sum(a['time_budget'] for a in self.stats['agent_final_states']) / len(self.stats['agent_final_states'])
            
            print(f"   Energy Level: {avg_energy:.2f}")
            print(f"   Financial Capability: {avg_financial:.2f}")
            print(f"   Social Status: {avg_social:.2f}")
            print(f"   Time Budget: {avg_time:.2f}")
        
        # v1.8 specific metrics
        agents_with_purchases = sum(1 for a in self.stats['agent_final_states'] if a['purchases_today'] > 0)
        agents_with_posts = sum(1 for a in self.stats['agent_final_states'] if a['last_post_ts'] is not None)
        agents_with_selfdev = sum(1 for a in self.stats['agent_final_states'] if a['last_selfdev_ts'] is not None)
        
        print("\n🆕 v1.8 FEATURE USAGE:")
        print(f"   Agents with purchases: {agents_with_purchases}/100")
        print(f"   Agents with posts: {agents_with_posts}/100")
        print(f"   Agents with self-dev: {agents_with_selfdev}/100")
        
        if self.stats['errors']:
            print("\n⚠️ ERRORS:")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                print(f"   - {error}")
            if len(self.stats['errors']) > 5:
                print(f"   ... and {len(self.stats['errors']) - 5} more")
        else:
            print("\n✅ No errors detected!")
        
        print("\n" + "="*60)
        
        # Determine test result
        if self.stats['errors']:
            print("❌ TEST RESULT: FAILED (errors detected)")
            return False
        elif total_actions == 0:
            print("⚠️  TEST RESULT: WARNING (no actions executed)")
            return False
        else:
            print("✅ TEST RESULT: PASSED")
            return True


async def main():
    """Main test execution."""
    tester = SimulationTester()
    
    try:
        success = await tester.run_test_simulation()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 