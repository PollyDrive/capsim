import os
from capsim.engine.simulation_engine import SimulationEngine
from capsim.db.repositories import DatabaseRepository
import asyncio

async def run_test():
    db_url = os.environ['DATABASE_URL']
    db_repo = DatabaseRepository(db_url)
    engine = SimulationEngine(db_repo)
    await engine.initialize(num_agents=200)
    await engine.run_simulation(duration_days=2/24)  # 2 часа
    print('Final simulation completed with all fixes')

if __name__ == "__main__":
    asyncio.run(run_test()) 