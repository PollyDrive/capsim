#!/usr/bin/env python3
"""
CLI для просмотра статуса симуляций CAPSIM.
"""

import asyncio
import sys
import json
import logging
from typing import Optional
from datetime import datetime, timedelta

# Конфигурирование логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def status_simulation_cli(database_url: Optional[str] = None) -> None:
    """
    Показывает статус всех симуляций.
    
    Args:
        database_url: URL базы данных
    """
    
    print("🔍 CAPSIM - Статус симуляций")
    print("=" * 50)
    
    # Проверяем доступность зависимостей
    try:
        from ..db.repositories import DatabaseRepository
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("📝 Убедитесь что установлены зависимости:")
        print("  pip install sqlalchemy asyncpg psycopg2-binary")
        return
    
    # URL базы данных
    if not database_url:
        import os
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
    
    try:
        # Создаем репозиторий
        db_repo = DatabaseRepository(database_url)
        
        print(f"🗄️  База данных: {database_url}")
        print()
        
        # Получаем активные симуляции
        active_simulations = await db_repo.get_active_simulations()
        
        if not active_simulations:
            print("✅ Нет активных симуляций")
            print("💡 Можно запустить новую симуляцию: python -m capsim run")
        else:
            print(f"🔄 Активных симуляций: {len(active_simulations)}")
            print()
            
            for sim in active_simulations:
                # Рассчитываем время работы
                if sim.start_time:
                    runtime = datetime.utcnow() - sim.start_time
                    runtime_str = str(runtime).split('.')[0]  # Убираем микросекунды
                else:
                    runtime_str = "неизвестно"
                
                # Форматируем вывод
                print(f"📊 ID: {sim.run_id}")
                print(f"   📈 Статус: {sim.status}")
                print(f"   👥 Агентов: {sim.num_agents}")
                print(f"   📅 Продолжительность: {sim.duration_days} дней")
                print(f"   ⏰ Запущена: {sim.start_time}")
                print(f"   ⏱️  Время работы: {runtime_str}")
                
                # Дополнительная информация из конфигурации
                if sim.configuration:
                    config = sim.configuration
                    if 'sim_speed_factor' in config:
                        print(f"   ⚡ Скорость симуляции: {config['sim_speed_factor']}x")
                    if 'batch_size' in config:
                        print(f"   📦 Размер батча: {config['batch_size']}")
                
                print()
                
                # Команды управления
                print(f"💡 Управление:")
                print(f"   🛑 Остановить: python -m capsim stop {sim.run_id}")
                print(f"   🚨 Принудительно: python -m capsim stop {sim.run_id} --force")
                print()
        
        # Статистика БД
        print("📈 Статистика базы данных:")
        
        # Подсчет записей в таблицах
        from ..db.models import SimulationRun, Person as DBPerson, Event, Trend
        from sqlalchemy import select, func
        
        async with db_repo.ReadOnlySession() as session:
            # Общая статистика
            total_sims_result = await session.execute(select(func.count(SimulationRun.run_id)))
            total_sims = total_sims_result.scalar()
            
            total_persons_result = await session.execute(select(func.count(DBPerson.id)))
            total_persons = total_persons_result.scalar()
            
            total_events_result = await session.execute(select(func.count(Event.event_id)))
            total_events = total_events_result.scalar()
            
            total_trends_result = await session.execute(select(func.count(Trend.trend_id)))
            total_trends = total_trends_result.scalar()
            
        print(f"   🎯 Всего симуляций: {total_sims}")
        print(f"   👥 Всего агентов: {total_persons}")
        print(f"   📅 Всего событий: {total_events}")
        print(f"   📊 Всего трендов: {total_trends}")
        
        # Закрываем соединение с БД
        await db_repo.close()
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        
        # Попытка закрыть соединение
        try:
            await db_repo.close()
        except:
            pass
        
        raise


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CAPSIM Status - Просмотр статуса симуляций")
    parser.add_argument("--db-url", type=str, help="URL базы данных")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(status_simulation_cli(
            database_url=args.db_url
        ))
    except KeyboardInterrupt:
        print("\n⚠️  Операция прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 