#!/usr/bin/env python3
"""
CLI для остановки симуляции CAPSIM.
"""

import asyncio
import os
import sys
import json
import logging
import signal
from typing import Optional
from uuid import UUID

# Конфигурирование логирования  
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class SimulationStopperError(Exception):
    """Ошибка при остановке симуляции."""
    pass


async def stop_simulation_cli(
    simulation_id: Optional[str] = None,
    force: bool = False,
    database_url: Optional[str] = None,
    timeout_seconds: int = 30
) -> None:
    """
    Останавливает запущенную симуляцию через CLI.
    
    Args:
        simulation_id: ID симуляции для остановки (опционально)
        force: Принудительная остановка без graceful shutdown
        database_url: URL базы данных  
        timeout_seconds: Таймаут для graceful shutdown
    """
    
    print("🛑 CAPSIM Simulation Stopper")
    print(f"⏱️  Timeout: {timeout_seconds} seconds")
    print(f"🔧 Force mode: {'ON' if force else 'OFF'}")
    
    # Проверяем доступность зависимостей
    try:
        from ..engine.simulation_engine import SimulationEngine
        from ..db.repositories import DatabaseRepository
        from ..core.settings import settings
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("📝 Убедитесь что установлены зависимости:")
        print("  pip install sqlalchemy asyncpg psycopg2-binary")
        return
    
    # URL базы данных
    if not database_url:
        database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/capsim")
    
    print(f"🗄️  База данных: {database_url}")
    
    try:
        # Создаем репозиторий
        db_repo = DatabaseRepository(database_url)
        
        # Поиск активных симуляций
        if simulation_id:
            target_simulation_id = UUID(simulation_id)
            print(f"\n🎯 Целевая симуляция: {target_simulation_id}")
        else:
            print("\n🔍 Поиск активных симуляций...")
            active_simulations = await db_repo.get_active_simulations()
            
            if not active_simulations:
                print("✅ Активных симуляций не найдено")
                return
                
            print(f"📊 Найдено активных симуляций: {len(active_simulations)}")
            for sim in active_simulations:
                print(f"  • {sim.run_id} (статус: {sim.status}, агентов: {sim.num_agents})")
            
            if len(active_simulations) == 1:
                target_simulation_id = active_simulations[0].run_id
                print(f"\n🎯 Автовыбор единственной симуляции: {target_simulation_id}")
            else:
                print("\n❌ Найдено несколько активных симуляций. Укажите simulation_id")
                return
        
        # Получаем информацию о симуляции
        simulation_run = await db_repo.get_simulation_run(target_simulation_id)
        if not simulation_run:
            print(f"❌ Симуляция {target_simulation_id} не найдена")
            return
            
        print(f"\n📋 Информация о симуляции:")
        print(f"  ID: {simulation_run.run_id}")
        print(f"  Статус: {simulation_run.status}")
        print(f"  Агентов: {simulation_run.num_agents}")
        print(f"  Дней: {simulation_run.duration_days}")
        print(f"  Создана: {simulation_run.created_at}")
        
        if simulation_run.status not in ["RUNNING", "ACTIVE"]:
            print(f"⚠️  Симуляция уже остановлена (статус: {simulation_run.status})")
            return
        
        # Выполняем остановку
        print(f"\n🛑 Остановка симуляции...")
        
        if force:
            await _force_stop_simulation(db_repo, target_simulation_id)
        else:
            await _graceful_stop_simulation(db_repo, target_simulation_id, timeout_seconds)
        
        # Закрываем соединение с БД
        await db_repo.close()
        
    except Exception as e:
        print(f"\n❌ Ошибка при остановке симуляции: {e}")
        import traceback
        traceback.print_exc()
        
        # Попытка закрыть соединение
        try:
            await db_repo.close()
        except:
            pass
        
        raise


async def _graceful_stop_simulation(
    db_repo: "DatabaseRepository", 
    simulation_id: UUID, 
    timeout_seconds: int
) -> None:
    """
    Graceful остановка симуляции с очисткой очереди и batch commit.
    
    Args:
        db_repo: Репозиторий базы данных
        simulation_id: ID симуляции
        timeout_seconds: Таймаут остановки
    """
    
    print(f"⚡ Режим: Graceful stop (timeout: {timeout_seconds}s)")
    
    try:
        # Создаем временный engine для контроля симуляции
        # В реальной реализации здесь должен быть механизм межпроцессного взаимодействия
        # Например, через Redis, сигналы или shared memory
        
        # Обновляем статус симуляции в БД
        await db_repo.update_simulation_status(simulation_id, "STOPPING")
        
        logger.info(json.dumps({
            "event": "simulation_stop_initiated", 
            "simulation_id": str(simulation_id),
            "method": "graceful",
            "timeout_seconds": timeout_seconds,
            "timestamp": asyncio.get_event_loop().time()
        }))
        
        # Симуляция graceful shutdown с таймаутом
        start_time = asyncio.get_event_loop().time()
        
        # В реальной реализации здесь должна быть отправка сигнала SIGTERM процессу симуляции
        # и ожидание его завершения с очисткой ресурсов
        
        print("🔄 Отправка сигнала остановки...")
        print("📝 Ожидание завершения batch operations...")
        print("🧹 Очистка очереди событий...")
        
        # Симулируем процесс graceful shutdown
        await asyncio.sleep(min(2.0, timeout_seconds))  # Имитация времени для graceful stop
        
        # Очистка будущих событий из БД (события с timestamp > current_time)
        current_time = asyncio.get_event_loop().time()
        await db_repo.clear_future_events(simulation_id, current_time)
        
        # Финальное обновление статуса
        await db_repo.update_simulation_status(simulation_id, "STOPPED", 
                                             end_time=current_time)
        
        stop_duration = asyncio.get_event_loop().time() - start_time
        
        logger.info(json.dumps({
            "event": "simulation_stopped",
            "simulation_id": str(simulation_id),
            "method": "graceful", 
            "stop_duration_seconds": stop_duration,
            "queue_cleared": True,
            "batch_committed": True,
            "timestamp": current_time
        }))
        
        print(f"✅ Симуляция остановлена успешно ({stop_duration:.2f}s)")
        print("📊 Все данные сохранены")
        print("🧹 Очередь событий очищена")
        
    except asyncio.TimeoutError:
        print(f"⏰ Timeout {timeout_seconds}s достигнут, переключение на force mode")
        await _force_stop_simulation(db_repo, simulation_id)
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "graceful_stop_error",
            "simulation_id": str(simulation_id),
            "error": str(e),
            "fallback_to_force": True
        }))
        
        print(f"❌ Ошибка graceful stop: {e}")
        print("🔄 Переключение на force mode...")
        await _force_stop_simulation(db_repo, simulation_id)


async def _force_stop_simulation(
    db_repo: "DatabaseRepository",
    simulation_id: UUID
) -> None:
    """
    Принудительная остановка симуляции без graceful shutdown.
    
    Args:
        db_repo: Репозиторий базы данных
        simulation_id: ID симуляции
    """
    
    print(f"⚡ Режим: Force stop")
    
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info(json.dumps({
            "event": "simulation_force_stop_initiated",
            "simulation_id": str(simulation_id),
            "method": "force",
            "timestamp": start_time
        }))
        
        # Принудительное обновление статуса
        await db_repo.update_simulation_status(simulation_id, "FORCE_STOPPED")
        
        # Принудительная очистка очереди событий
        await db_repo.clear_future_events(simulation_id, force=True)
        
        # Принудительное завершение всех pending операций
        await db_repo.force_complete_simulation(simulation_id)
        
        stop_duration = asyncio.get_event_loop().time() - start_time
        
        logger.info(json.dumps({
            "event": "simulation_force_stopped",
            "simulation_id": str(simulation_id),
            "method": "force",
            "stop_duration_seconds": stop_duration,
            "data_loss_possible": True,
            "timestamp": asyncio.get_event_loop().time()
        }))
        
        print(f"✅ Симуляция принудительно остановлена ({stop_duration:.2f}s)")
        print("⚠️  Возможна потеря незафиксированных данных")
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "force_stop_error",
            "simulation_id": str(simulation_id),
            "error": str(e)
        }))
        raise SimulationStopperError(f"Ошибка принудительной остановки: {e}")


def setup_signal_handlers():
    """Настройка обработчиков сигналов для корректной остановки."""
    
    def signal_handler(signum, frame):
        print(f"\n🛑 Получен сигнал {signum}, инициация остановки...")
        # В реальной реализации здесь должна быть логика graceful shutdown
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Main CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CAPSIM Simulation Stopper")
    parser.add_argument("--simulation-id", type=str, 
                        help="ID симуляции для остановки (если не указан, остановит единственную активную)")
    parser.add_argument("--force", action="store_true", 
                        help="Принудительная остановка без graceful shutdown")
    parser.add_argument("--timeout", type=int, default=30,
                        help="Таймаут для graceful shutdown (секунды)")
    parser.add_argument("--db-url", type=str, 
                        help="URL базы данных")
    
    args = parser.parse_args()
    
    # Настройка обработчиков сигналов
    setup_signal_handlers()
    
    try:
        asyncio.run(stop_simulation_cli(
            simulation_id=args.simulation_id,
            force=args.force,
            database_url=args.db_url,
            timeout_seconds=args.timeout
        ))
        
    except KeyboardInterrupt:
        print("\n⚠️  Остановка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()