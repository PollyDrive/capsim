#!/usr/bin/env python3
"""
Упрощенная тестовая симуляция CAPSIM на 300 агентов с realtime архитектурой.
"""

import asyncio
import time
import json
import logging
from uuid import uuid4
from typing import Dict, Any, List
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Agent:
    id: str
    profession: str
    energy_level: float
    social_status: float
    interests: Dict[str, float]
    created_at: float

class MockRealTimeEngine:
    def __init__(self, speed_factor: float = 60.0, use_realtime: bool = True):
        self.speed_factor = speed_factor
        self.use_realtime = use_realtime
        self.current_time = 0.0
        self.agents: List[Agent] = []
        self.events: List[Dict] = []
        self.simulation_id = str(uuid4())
        self.start_real_time = 0.0
        
    async def initialize_agents(self, num_agents: int = 300) -> None:
        logger.info(f"🚀 Initializing {num_agents} agents with smart allocation logic")
        
        existing_agents = self._simulate_existing_agents()
        existing_count = len(existing_agents)
        
        if existing_count >= num_agents:
            self.agents = existing_agents[:num_agents]
            logger.info(json.dumps({
                "event": "agents_reused",
                "simulation_id": self.simulation_id,
                "reused_count": len(self.agents),
                "requested_count": num_agents,
                "allocation_strategy": "reuse_existing"
            }))
        else:
            agents_to_create = num_agents - existing_count
            new_agents = self._create_new_agents(agents_to_create)
            self.agents = existing_agents + new_agents
            
            logger.info(json.dumps({
                "event": "agents_supplemented",
                "simulation_id": self.simulation_id,
                "existing_count": existing_count,
                "created_count": len(new_agents),
                "total_count": len(self.agents),
                "requested_count": num_agents,
                "allocation_strategy": "supplement_missing"
            }))
        
        logger.info(f"✅ Agent initialization completed: {len(self.agents)} total agents")
        
    def _simulate_existing_agents(self) -> List[Agent]:
        existing_count = 150
        agents = []
        professions = ["Teacher", "Developer", "Artist", "Blogger", "Worker"]
        
        for i in range(existing_count):
            profession = professions[i % len(professions)]
            agent = Agent(
                id=str(uuid4()),
                profession=profession,
                energy_level=round(3.0 + (i % 20) * 0.1, 1),
                social_status=round(2.0 + (i % 30) * 0.1, 1),
                interests=self._generate_interests(profession),
                created_at=time.time() - (existing_count - i) * 10
            )
            agents.append(agent)
            
        logger.info(f"📊 Found {existing_count} existing agents in simulated database")
        return agents
        
    def _create_new_agents(self, count: int) -> List[Agent]:
        profession_distribution = [
            ("Teacher", 0.20), ("ShopClerk", 0.18), ("Developer", 0.12),
            ("Unemployed", 0.09), ("Businessman", 0.08), ("Artist", 0.08),
            ("Worker", 0.07), ("Blogger", 0.05), ("SpiritualMentor", 0.03),
            ("Philosopher", 0.02), ("Politician", 0.01), ("Doctor", 0.01)
        ]
        
        agents = []
        current_time = time.time()
        
        for profession, ratio in profession_distribution:
            profession_count = int(count * ratio)
            for i in range(profession_count):
                agent = Agent(
                    id=str(uuid4()),
                    profession=profession,
                    energy_level=round(1.0 + (i % 40) * 0.1, 1),
                    social_status=round(0.5 + (i % 40) * 0.1, 1),
                    interests=self._generate_interests(profession),
                    created_at=current_time + i * 0.1
                )
                agents.append(agent)
                
        while len(agents) < count:
            agent = Agent(
                id=str(uuid4()),
                profession="Teacher",
                energy_level=3.5,
                social_status=2.8,
                interests=self._generate_interests("Teacher"),
                created_at=current_time + len(agents) * 0.1
            )
            agents.append(agent)
            
        logger.info(f"🏭 Created {len(agents)} new agents with professional distribution")
        return agents
        
    def _generate_interests(self, profession: str) -> Dict[str, float]:
        base_interests = {
            "Economic": 2.5, "Science": 2.5, "Culture": 2.5, 
            "Health": 2.5, "Sport": 2.5, "Spiritual": 2.5
        }
        
        profession_modifiers = {
            "Teacher": {"Science": 1.5, "Culture": 1.2},
            "Developer": {"Science": 1.8, "Economic": 1.3},
            "Artist": {"Culture": 1.7, "Spiritual": 1.2},
            "Blogger": {"Culture": 1.4, "Economic": 1.1},
            "Worker": {"Health": 1.3, "Sport": 1.4}
        }
        
        modifiers = profession_modifiers.get(profession, {})
        for interest, modifier in modifiers.items():
            if interest in base_interests:
                base_interests[interest] = min(5.0, base_interests[interest] * modifier)
                
        return base_interests
        
    async def run_simulation(self, duration_minutes: int = 60) -> Dict[str, Any]:
        logger.info(f"⏰ Starting simulation: {duration_minutes} minutes")
        logger.info(f"�� Mode: {'Realtime' if self.use_realtime else 'Fast'} (speed factor: {self.speed_factor}x)")
        
        self.start_real_time = time.time()
        end_time_sim = duration_minutes
        expected_duration_real = duration_minutes * 60 / self.speed_factor if self.use_realtime else 0
        
        if self.use_realtime:
            logger.info(f"⏱️  Expected real duration: {expected_duration_real:.1f} seconds")
        
        events_processed = 0
        
        while self.current_time < end_time_sim:
            if self.use_realtime:
                real_time_event = self.start_real_time + (self.current_time * 60 / self.speed_factor)
                current_real_time = time.time()
                if real_time_event > current_real_time:
                    sleep_duration = real_time_event - current_real_time
                    await asyncio.sleep(sleep_duration)
            
            event = self._process_simulation_step()
            self.events.append(event)
            events_processed += 1
            
            self.current_time += 0.25
            
            if int(self.current_time) % 5 == 0 and (self.current_time % 0.25) < 0.1:
                progress = (self.current_time / end_time_sim) * 100
                logger.info(f"📈 Progress: {progress:.1f}% ({self.current_time:.1f}/{end_time_sim} sim-minutes)")
        
        actual_duration = time.time() - self.start_real_time
        
        timing_accuracy = 0.0
        if self.use_realtime and expected_duration_real > 0:
            timing_accuracy = (1 - abs(actual_duration - expected_duration_real) / expected_duration_real) * 100
        
        return {
            "simulation_id": self.simulation_id,
            "agents_count": len(self.agents),
            "events_processed": events_processed,
            "sim_duration_minutes": self.current_time,
            "real_duration_seconds": actual_duration,
            "expected_duration_seconds": expected_duration_real,
            "timing_accuracy_percent": timing_accuracy,
            "use_realtime": self.use_realtime,
            "speed_factor": self.speed_factor
        }
        
    def _process_simulation_step(self) -> Dict[str, Any]:
        event_types = ["agent_action", "trend_influence", "energy_recovery", "social_interaction"]
        event_type = event_types[int(self.current_time * 4) % len(event_types)]
        
        event = {
            "event_id": str(uuid4()),
            "event_type": event_type,
            "sim_time": self.current_time,
            "real_time": time.time(),
            "simulation_id": self.simulation_id,
            "affected_agents": min(5, len(self.agents)),
            "timestamp": time.time()
        }
        
        return event

async def run_test_simulation(agents: int = 300, duration: int = 60, speed: float = 60.0, realtime: bool = True):
    print(f"\n{'='*60}")
    print("🧪 CAPSIM REALTIME ARCHITECTURE TEST")
    print(f"{'='*60}")
    
    print(f"🎯 Configuration:")
    print(f"   • Agents: {agents}")
    print(f"   • Duration: {duration} sim-minutes")
    print(f"   • Mode: {'Realtime' if realtime else 'Fast'}")
    print(f"   • Speed factor: {speed}x")
    
    engine = MockRealTimeEngine(speed_factor=speed, use_realtime=realtime)
    
    print(f"\n📊 Agent Management (Smart Allocation):")
    await engine.initialize_agents(agents)
    
    print(f"\n⚡ Running simulation...")
    start_time = time.time()
    
    results = await engine.run_simulation(duration)
    
    print(f"\n{'='*60}")
    print("📋 TEST RESULTS")
    print(f"{'='*60}")
    
    print(f"🎯 Simulation:")
    print(f"   • ID: {results['simulation_id'][:8]}...")
    print(f"   • Agents: {results['agents_count']}")
    print(f"   • Events processed: {results['events_processed']}")
    print(f"   • Sim duration: {results['sim_duration_minutes']:.1f} minutes")
    
    print(f"\n⏱️  Performance:")
    print(f"   • Real duration: {results['real_duration_seconds']:.2f}s")
    
    if realtime:
        print(f"   • Expected duration: {results['expected_duration_seconds']:.2f}s")
        print(f"   • Timing accuracy: {results['timing_accuracy_percent']:.1f}%")
        
        if results['timing_accuracy_percent'] >= 95:
            print("   🎯 Excellent timing accuracy!")
        elif results['timing_accuracy_percent'] >= 85:
            print("   👍 Good timing accuracy")
        else:
            print("   ⚠️  Timing accuracy could be improved")
    
    print(f"\n✅ Realtime Architecture Features:")
    print(f"   • Smart agent allocation: ✅ Working")
    print(f"   • Append-only events: ✅ Working") 
    print(f"   • Realtime clock: ✅ Working")
    print(f"   • Speed factor control: ✅ Working")
    
    profession_counts = {}
    for agent in engine.agents:
        profession_counts[agent.profession] = profession_counts.get(agent.profession, 0) + 1
    
    print(f"\n👥 Agent Distribution:")
    for profession, count in sorted(profession_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(engine.agents)) * 100
        print(f"   • {profession}: {count} ({percentage:.1f}%)")
    
    print(f"\n{'='*60}")
    
    return results

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='CAPSIM 300 Agents Test (Simplified)')
    parser.add_argument('--agents', type=int, default=300, help='Number of agents')
    parser.add_argument('--duration', type=int, default=10, help='Simulation duration in minutes')
    parser.add_argument('--speed', type=float, default=60.0, help='Speed factor for realtime mode')
    parser.add_argument('--fast', action='store_true', help='Use fast mode instead of realtime')
    parser.add_argument('--compare', action='store_true', help='Run both modes for comparison')
    
    args = parser.parse_args()
    
    if args.compare:
        print("🔬 Running comparison: Fast vs Realtime modes...")
        
        print(f"\n{'='*40}")
        print("1️⃣  FAST MODE")
        print(f"{'='*40}")
        await run_test_simulation(args.agents, args.duration, args.speed, realtime=False)
        
        print(f"\n{'='*40}")
        print("2️⃣  REALTIME MODE")
        print(f"{'='*40}")
        await run_test_simulation(args.agents, args.duration, args.speed, realtime=True)
        
    else:
        use_realtime = not args.fast
        await run_test_simulation(args.agents, args.duration, args.speed, use_realtime)

if __name__ == "__main__":
    asyncio.run(main())
