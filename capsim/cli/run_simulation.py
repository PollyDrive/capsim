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

# For test mode use in-memory repository
from types import SimpleNamespace

# Конфигурирование логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


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
    
    # Проверяем доступность зависимостей
    # Устанавливаем SIM_SPEED_FACTOR ПЕРЕД импортом движка, чтобы settings подтянули корректное значение
    os.environ["SIM_SPEED_FACTOR"] = str(sim_speed_factor)

    try:
        from ..engine.simulation_engine import SimulationEngine
        from ..db.repositories import DatabaseRepository as _RealRepository
        from ..common.settings import settings
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return
    
    # URL базы данных
    if not database_url:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
    
    print(f"🗄️  База данных: {database_url}")
    
    try:
        # SIM_SPEED_FACTOR уже установлен выше
        
        # Подмена репозитория на in-memory в тестовом режиме
        if database_url and database_url.startswith("sqlite+aiosqlite"):  # тестовый режим
            from reports.demo_simulation import _InMemoryRepo as DatabaseRepository  # type: ignore
        else:
            DatabaseRepository = _RealRepository  # type: ignore
        
        # Создаем репозиторий и движок
        if DatabaseRepository is _RealRepository:
            db_repo = DatabaseRepository(database_url)
        else:
            db_repo = DatabaseRepository()
        engine = SimulationEngine(db_repo)
        
        print("\n🔄 Инициализация симуляции...")
        await engine.initialize(num_agents=num_agents, duration_days=duration_days)
        
        print(f"✅ Создано агентов: {len(engine.agents)}")
        print(f"✅ Системных событий: {len(engine.event_queue)}")
        print(f"✅ Affinity map загружена: {len(engine.affinity_map)} тем")
        
        print(f"\n▶️  Запуск симуляции на {duration_days} дней...")
        
        # Запускаем симуляцию
        await engine.run_simulation()
        
        # Финальная статистика
        final_stats = engine.get_simulation_stats()
        
        print("\n📈 Результаты симуляции:")
        print(f"  Время выполнения: {final_stats['current_time']:.1f} минут")
        print(f"  Активных агентов: {final_stats['active_agents']}/{final_stats['total_agents']}")
        print(f"  Созданных трендов: {final_stats['active_trends']}")
        print(f"  ID симуляции: {final_stats['simulation_id']}")
        
        print("\n✅ Симуляция завершена успешно!")
        
        # Закрываем соединение с БД
        await db_repo.close()
        
    except Exception as e:
        print(f"\n❌ Ошибка во время симуляции: {e}")
        import traceback
        traceback.print_exc()
        
        # Попытка graceful shutdown
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
    parser.add_argument("--speed", type=float, default=1.0, help="Фактор скорости симуляции")
    parser.add_argument("--test", action="store_true", help="Режим тестирования (короткая симуляция)")
    
    args = parser.parse_args()
    
    # Режим тестирования
    if args.test:
        print("🧪 Режим тестирования - мини-симуляция")
        args.agents = 10
        args.days = 60/1440  # 60 минут
    
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