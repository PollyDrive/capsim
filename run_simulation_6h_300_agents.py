import os
import asyncio
from capsim.engine.simulation_engine import SimulationEngine
from capsim.db.repositories import DatabaseRepository

async def run_6h_simulation():
    # Настройки для 6-часовой симуляции с 300 агентами
    os.environ['ENABLE_REALTIME'] = 'true'
    os.environ['SIM_SPEED_FACTOR'] = '10'  # Скорость x10
    
    db_url = os.environ['DATABASE_URL']
    db_repo = DatabaseRepository(db_url)
    engine = SimulationEngine(db_repo)
    
    print("Starting 6-hour simulation with 300 agents at 10x speed...")
    print("This will test trend chains hypothesis...")
    
    await engine.initialize(num_agents=300)
    await engine.run_simulation(duration_days=6/24)  # 6 часов = 6/24 дня
    
    print("6-hour simulation completed!")
    print("Check database for trend chains and parent_trend_id relationships.")

if __name__ == "__main__":
    asyncio.run(run_6h_simulation()) 