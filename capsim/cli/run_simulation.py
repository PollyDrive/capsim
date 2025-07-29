#!/usr/bin/env python3
"""
CLI для запуска симуляции CAPSIM.
"""

import asyncio
import os
import sys
import json
import logging
from typing import Optional
import yaml

# For test mode use in-memory repository
from types import SimpleNamespace

# Конфигурирование логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def load_simulation_config():
    """Loads simulation configuration from config/simulation.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'simulation.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

async def run_simulation_cli(
    num_agents: int = 100,
    duration_days: float = 1.0,
    database_url: Optional[str] = None,
    sim_speed_factor: float = 1.0
) -> None:
    """
    Запускает симуляцию через CLI.
    
    Args:
        num_agents: Количество агентов
        duration_days: Продолжительность в днях
        database_url: URL базы данных
        sim_speed_factor: Фактор скорости симуляции (1.0 = реальное время)
    """
    
    print("🚀 Запуск CAPSIM Simulation Engine")
    print(f"📊 Агентов: {num_agents}")
    print(f"⏱️  Продолжительность: {duration_days} дней")
    print(f"⚡ Скорость симуляции: {sim_speed_factor}x")
    
    os.environ["SIM_SPEED_FACTOR"] = str(sim_speed_factor)

    try:
        from ..engine.simulation_engine import SimulationEngine
        from ..db.repositories import DatabaseRepository as _RealRepository
        from ..common.settings import settings
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return
    
    if not database_url:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
    
    print(f"🗄️  База данных: {database_url}")
    
    try:
        if database_url and database_url.startswith("sqlite+aiosqlite"): 
            from reports.demo_simulation import _InMemoryRepo as DatabaseRepository
        else:
            DatabaseRepository = _RealRepository
        
        if DatabaseRepository is _RealRepository:
            db_repo = DatabaseRepository(database_url)
        else:
            db_repo = DatabaseRepository()
        
        simulation_config = load_simulation_config()
        engine = SimulationEngine(db_repo)
        
        print("\n🔄 Инициализация симуляции...")
        await engine.initialize(num_agents=num_agents, duration_days=duration_days, config=simulation_config)
        
        print(f"✅ Создано агентов: {len(engine.agents)}")
        print(f"✅ Системных событий: {len(engine.event_queue)}")
        print(f"✅ Affinity map загружена: {len(engine.affinity_map)} тем")
        
        print(f"\n▶️  Запуск симуляции на {duration_days} дней...")
        
        await engine.run_simulation()
        
        final_stats = engine.get_simulation_stats()
        
        from ..common.time_utils import convert_sim_time_to_human, format_simulation_time_detailed
        
        print("\n📈 Результаты симуляции:")
        print(f"  Время выполнения: {final_stats['current_time']:.1f} минут ({format_simulation_time_detailed(final_stats['current_time'])})")
        print(f"  Активных агентов: {final_stats['active_agents']}/{final_stats['total_agents']}")
        print(f"  Созданных трендов: {final_stats['active_trends']}")
        print(f"  Среднее действий/агент/час: {final_stats.get('avg_actions_per_agent_per_hour', 0):.2f}")
        print(f"  Всего покупок: {final_stats.get('total_purchases', 0)}")
        print(f"  Всего саморазвитий: {final_stats.get('total_selfdev', 0)}")
        print(f"  ID симуляции: {final_stats['simulation_id']}")
        
        print("\n✅ Симуляция завершена успешно!")
        
        await db_repo.close()
        
    except Exception as e:
        print(f"\n❌ Ошибка во время симуляции: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await engine.shutdown()
            await db_repo.close()
        except:
            pass
        
        raise

def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CAPSIM Simulation Engine")
    parser.add_argument("--agents", type=int, default=100, help="Количество агентов")
    parser.add_argument("--days", type=float, default=1, help="Продолжительность в днях")
    parser.add_argument("--db-url", type=str, help="URL базы данных")
    parser.add_argument("--speed", type=float, default=240.0, help="Фактор скорости симуляции (240x = быстро, 1x = реальное время)")
    parser.add_argument("--240x", action="store_const", const=240.0, dest="speed", help="Быстрая симуляция (эквивалент --speed 240)")
    parser.add_argument("--test", action="store_true", help="Режим тестирования (короткая симуляция)")
    
    args = parser.parse_args()
    
    if args.test:
        print("🧪 Режим тестирования - мини-симуляция")
        args.agents = 10
        args.days = 60/1440
    
    try:
        asyncio.run(run_simulation_cli(
            num_agents=args.agents,
            duration_days=args.days,
            database_url=args.db_url,
            sim_speed_factor=args.speed
        ))
    except KeyboardInterrupt:
        print("\n⚠️  Симуляция прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()