#!/usr/bin/env python3
"""
Тест для проверки продвижения времени и автоматического завершения симуляции.
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
from capsim.common.logging_config import setup_logging
from capsim.common.db_config import ASYNC_DSN

# Простая заглушка для тестирования
class MockRepository:
    async def create_simulation_run(self, *args, **kwargs):
        from uuid import uuid4
        from dataclasses import dataclass
        @dataclass
        class SimulationRun:
            run_id: str = str(uuid4())
        return SimulationRun()
    
    async def update_simulation_status(self, *args, **kwargs):
        pass
    
    async def get_simulations_by_status(self, *args, **kwargs):
        return []
    
    async def load_affinity_map(self, *args, **kwargs):
        return {}
    
    async def get_profession_attribute_ranges(self, *args, **kwargs):
        return {}
    
    async def get_persons_count(self, *args, **kwargs):
        return 0
    
    async def get_persons_for_simulation(self, *args, **kwargs):
        return []
    
    async def get_available_persons(self, *args, **kwargs):
        return []
    
    async def create_persons(self, *args, **kwargs):
        return []
    
    async def bulk_create_persons(self, *args, **kwargs):
        return []
    
    async def get_active_trends(self, *args, **kwargs):
        return []
    
    async def create_event(self, *args, **kwargs):
        pass
    
    async def bulk_update_persons(self, *args, **kwargs):
        pass
    
    async def bulk_update_simulation_participants(self, *args, **kwargs):
        pass
    
    async def create_person_attribute_history(self, *args, **kwargs):
        pass
    
    async def create_trend(self, *args, **kwargs):
        pass
    
    async def increment_trend_interactions(self, *args, **kwargs):
        pass
    
    async def clear_future_events(self, *args, **kwargs):
        pass
    
    async def close(self, *args, **kwargs):
        pass


async def test_time_advance():
    """Тест корректного продвижения времени."""
    # Настройка логирования
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Создаем тестовый репозиторий
    test_repo = MockRepository()
    
    # Создаем симуляцию
    engine = SimulationEngine(test_repo)
    
    try:
        # Инициализируем симуляцию с 10 агентами
        await engine.initialize(num_agents=10)
        
        logger.info("🚀 Запуск КОРОТКОЙ симуляции для тестирования продвижения времени...")
        
        # Запускаем симуляцию на 0.1 дня (144 минуты = 2.4 часа)
        start_time = time.time()
        await engine.run_simulation(duration_days=0.1)
        end_time = time.time()
        
        # Проверяем результат
        duration = end_time - start_time
        final_sim_time = engine.current_time
        
        logger.info(f"✅ Симуляция завершена автоматически!")
        logger.info(f"📊 Результаты теста:")
        logger.info(f"   - Реальное время: {duration:.2f} секунд")
        logger.info(f"   - Симуляционное время: {final_sim_time:.2f} минут")
        logger.info(f"   - Целевое время: {0.1 * 1440:.2f} минут")
        logger.info(f"   - Время продвинулось: {'✅ ДА' if final_sim_time > 10 else '❌ НЕТ'}")
        logger.info(f"   - Завершение в срок: {'✅ ДА' if abs(final_sim_time - 144) < 10 else '❌ НЕТ'}")
        
        # Проверяем что симуляция завершилась корректно
        if final_sim_time > 10:
            logger.info("✅ УСПЕХ: Время симуляции продвигается корректно!")
            return True
        else:
            logger.error("❌ ОШИБКА: Время симуляции не продвигается!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании симуляции: {e}")
        return False
    finally:
        # Очистка
        await engine.shutdown()


if __name__ == "__main__":
    success = asyncio.run(test_time_advance())
    sys.exit(0 if success else 1) 