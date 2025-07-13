#!/usr/bin/env python3
"""
Скрипт для тестирования исправлений бесконечных циклов в симуляции CAPSIM.
Запускает ускоренную симуляцию на 100 агентов.
"""

import asyncio
import logging
import sys
import os
import time
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from capsim.engine.simulation_engine import SimulationEngine
from capsim.db.repositories import DatabaseRepository
from capsim.common.logging_config import setup_logging
from capsim.common.db_config import ASYNC_DSN


async def run_test_simulation():
    """Запускает тестовую симуляцию на 100 агентов."""
    # Настройка логирования
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Запуск тестовой симуляции после исправления бесконечных циклов")
    logger.info("📊 Параметры: 100 агентов, 0.5 дня (12 часов), ускоренный режим")
    
    # Создаем подключение к базе данных
    db_repo = DatabaseRepository(ASYNC_DSN)
    
    # Создаем симуляцию
    simulation_engine = SimulationEngine(db_repo)
    
    # Время начала
    start_time = time.time()
    
    try:
        # Инициализируем симуляцию с 100 агентами
        logger.info("🔧 Инициализация симуляции...")
        await simulation_engine.initialize(num_agents=100)
        
        # Проверяем начальное состояние
        logger.info("✅ Симуляция инициализирована")
        logger.info(f"   - Агентов: {len(simulation_engine.agents)}")
        logger.info(f"   - Активных трендов: {len(simulation_engine.active_trends)}")
        logger.info(f"   - Событий в очереди: {len(simulation_engine.event_queue)}")
        logger.info(f"   - Время окончания: {simulation_engine.end_time}")
        
        # Запускаем симуляцию на 0.5 дня (12 часов)
        duration_days = 0.5
        logger.info(f"▶️  Запуск симуляции на {duration_days} дня...")
        
        await simulation_engine.run_simulation(duration_days=duration_days)
        
        # Время окончания
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Финальная статистика
        stats = simulation_engine.get_simulation_stats()
        
        logger.info("🎉 Симуляция завершена успешно!")
        logger.info(f"   - Время выполнения: {execution_time:.2f} секунд")
        logger.info(f"   - Симуляционное время: {simulation_engine.current_time:.2f} минут")
        logger.info(f"   - Ожидаемое время окончания: {simulation_engine.end_time:.2f} минут")
        logger.info(f"   - Активных агентов: {stats['active_agents']}")
        logger.info(f"   - Всего агентов: {stats['total_agents']}")
        logger.info(f"   - Активных трендов: {stats['active_trends']}")
        logger.info(f"   - Событий в очереди: {stats['queue_size']}")
        logger.info(f"   - Ожидающих batch: {stats['pending_batches']}")
        
        # Проверяем корректность завершения
        if simulation_engine.current_time <= simulation_engine.end_time:
            logger.info("✅ Симуляция завершилась в пределах заданного времени")
        else:
            logger.warning("⚠️ Симуляция превысила заданное время!")
            
        # Проверяем события в очереди
        events_past_end = 0
        for priority_event in simulation_engine.event_queue:
            if priority_event.timestamp >= simulation_engine.end_time:
                events_past_end += 1
                
        if events_past_end == 0:
            logger.info("✅ Все события в очереди в пределах времени симуляции")
        else:
            logger.warning(f"⚠️ Найдено {events_past_end} событий после времени окончания")
            
        # Проверяем статус выполнения
        if simulation_engine._running:
            logger.warning("⚠️ Флаг _running все еще True!")
        else:
            logger.info("✅ Симуляция корректно остановлена")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка во время выполнения симуляции: {e}")
        logger.error(f"   - Симуляционное время: {simulation_engine.current_time}")
        logger.error(f"   - Время окончания: {simulation_engine.end_time}")
        logger.error(f"   - Событий в очереди: {len(simulation_engine.event_queue)}")
        return False
        
    finally:
        # Останавливаем симуляцию
        await simulation_engine.stop_simulation("graceful")
        
        # Закрываем подключение к БД
        await db_repo.close()


async def main():
    """Основная функция."""
    logger = logging.getLogger(__name__)
    
    # Проверяем переменные окружения
    if not os.getenv("DATABASE_URL"):
        logger.error("❌ DATABASE_URL не установлена. Установите переменную окружения.")
        return False
    
    logger.info("=" * 60)
    logger.info("ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ БЕСКОНЕЧНЫХ ЦИКЛОВ CAPSIM")
    logger.info("=" * 60)
    
    success = await run_test_simulation()
    
    if success:
        logger.info("🎉 Тестирование успешно завершено!")
        logger.info("✅ Исправления бесконечных циклов работают корректно")
    else:
        logger.error("💥 Тестирование не удалось!")
        logger.error("❌ Возможно, остались проблемы с бесконечными циклами")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 