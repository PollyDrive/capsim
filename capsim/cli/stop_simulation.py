#!/usr/bin/env python3
"""
CLI для остановки симуляций CAPSIM.
"""

import asyncio
import sys
import json
import logging
from typing import Optional
from datetime import datetime
from uuid import UUID

# Конфигурирование логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def stop_simulation_cli(
    simulation_id: Optional[str] = None,
    force: bool = False,
    database_url: Optional[str] = None
) -> None:
    """
    Останавливает активную симуляцию.
    
    Args:
        simulation_id: ID симуляции для остановки (если не указан, останавливает первую активную)
        force: Принудительная остановка
        database_url: URL базы данных
    """
    
    print("🛑 CAPSIM - Остановка симуляции")
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
        print(f"⚙️  Режим: {'принудительный' if force else 'graceful'}")
        print()
        
        # Получаем активные симуляции
        active_simulations = await db_repo.get_active_simulations()
        
        if not active_simulations:
            print("✅ Нет активных симуляций для остановки")
            print("💡 Проверить статус: python -m capsim status")
            await db_repo.close()
            return
        
        # Выбираем симуляцию для остановки
        target_simulation = None
        
        if simulation_id:
            # Ищем конкретную симуляцию
            try:
                target_id = UUID(simulation_id)
                for sim in active_simulations:
                    if sim.run_id == target_id:
                        target_simulation = sim
                        break
                
                if not target_simulation:
                    print(f"❌ Симуляция {simulation_id} не найдена среди активных")
                    print("\n🔄 Активные симуляции:")
                    for sim in active_simulations:
                        print(f"   - {sim.run_id} (статус: {sim.status})")
                    await db_repo.close()
                    return
                    
            except ValueError:
                print(f"❌ Неверный формат ID симуляции: {simulation_id}")
                print("💡 ID должен быть в формате UUID, например: 2ed1315b-17a1-4b05-bdbc-11187f8270d5")
                await db_repo.close()
                return
        else:
            # Берем первую активную симуляцию
            target_simulation = active_simulations[0]
            print(f"🎯 Будет остановлена первая активная симуляция: {target_simulation.run_id}")
        
        # Отображаем информацию о симуляции
        print(f"📊 Остановка симуляции:")
        print(f"   🔄 ID: {target_simulation.run_id}")
        print(f"   📈 Статус: {target_simulation.status}")
        print(f"   👥 Агентов: {target_simulation.num_agents}")
        print(f"   ⏰ Запущена: {target_simulation.start_time}")
        
        if target_simulation.start_time:
            runtime = datetime.utcnow() - target_simulation.start_time
            runtime_str = str(runtime).split('.')[0]  # Убираем микросекунды
            print(f"   ⏱️  Время работы: {runtime_str}")
        
        print()
        
        # Подтверждение для принудительной остановки
        if force:
            print("⚠️  ВНИМАНИЕ: Принудительная остановка!")
            print("   - Данные могут быть потеряны")
            print("   - События в очереди будут отброшены")
            print("   - Агенты могут остаться в неконсистентном состоянии")
            print()
            
            confirm = input("❓ Продолжить принудительную остановку? (yes/no): ")
            if confirm.lower() not in ['yes', 'y', 'да', 'д']:
                print("❌ Операция отменена")
                await db_repo.close()
                return
        
        # Остановка симуляции
        print("🔄 Остановка симуляции...")
        
        if force:
            # Принудительная остановка
            await db_repo.force_complete_simulation(target_simulation.run_id)
            
            # Очистка событий в очереди
            cleared_events = await db_repo.clear_future_events(
                target_simulation.run_id, 
                force=True
            )
            
            print(f"🚨 Принудительная остановка выполнена")
            print(f"   🗑️  Очищено событий: {cleared_events}")
            
        else:
            # Graceful остановка
            await db_repo.update_simulation_status(
                target_simulation.run_id,
                "STOPPING"
            )
            
            # Очистка будущих событий
            cleared_events = await db_repo.clear_future_events(
                target_simulation.run_id,
                current_time=None,  # Текущее время симуляции (если доступно)
                force=False
            )
            
            # Обновляем статус на завершено
            await db_repo.update_simulation_status(
                target_simulation.run_id,
                "COMPLETED",
                datetime.utcnow()
            )
            
            print(f"✅ Graceful остановка выполнена")
            print(f"   🗑️  Очищено будущих событий: {cleared_events}")
        
        # Обновляем метрику Prometheus
        try:
            from ..common.metrics import SIMULATION_COUNT
            remaining_active = await db_repo.get_active_simulations()
            SIMULATION_COUNT.set(len(remaining_active))
        except ImportError:
            pass  # Метрики недоступны
        
        print()
        print("✅ Симуляция успешно остановлена")
        print("💡 Проверить статус: python -m capsim status")
        print("🚀 Запустить новую: python -m capsim run --agents 100")
        
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
    
    parser = argparse.ArgumentParser(description="CAPSIM Stop - Остановка симуляций")
    parser.add_argument('simulation_id', nargs='?', help='ID симуляции для остановки (опционально)')
    parser.add_argument("--force", action="store_true", help="Принудительная остановка")
    parser.add_argument("--db-url", type=str, help="URL базы данных")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(stop_simulation_cli(
            simulation_id=args.simulation_id,
            force=args.force,
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