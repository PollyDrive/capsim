#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправленной логики создания событий в CAPSIM.
Проверяет, что агенты создают разнообразные события: Post, Purchase, SelfDev.
"""

import asyncio
import json
import logging
from datetime import datetime
from uuid import uuid4

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_simulation_events():
    """Тестирует создание событий в симуляции."""
    
    try:
        # Импортируем компоненты симуляции
        from capsim.engine.simulation_engine import SimulationEngine
        from capsim.db.repositories import DatabaseRepository
        from capsim.common.settings import settings
        
        # Создаем репозиторий БД
        db_repo = DatabaseRepository(settings.DATABASE_URL)
        
        # Создаем движок симуляции
        engine = SimulationEngine(db_repo)
        
        # Инициализируем симуляцию с небольшим количеством агентов для тестирования
        await engine.initialize(num_agents=50, duration_days=0.1)  # 50 агентов, 2.4 часа
        
        logger.info("=== НАЧАЛО ТЕСТИРОВАНИЯ СОЗДАНИЯ СОБЫТИЙ ===")
        
        # Запускаем симуляцию
        await engine.run_simulation()
        
        # Получаем статистику симуляции
        stats = engine.get_simulation_stats()
        
        logger.info("=== СТАТИСТИКА СОБЫТИЙ ===")
        logger.info(f"Всего событий: {stats.get('total_events', 0)}")
        logger.info(f"Событий агентов: {stats.get('agent_events', 0)}")
        logger.info(f"Системных событий: {stats.get('system_events', 0)}")
        logger.info(f"Созданных трендов: {stats.get('trends_created', 0)}")
        
        # Проверяем, что создались разные типы событий
        events_by_type = {}
        for event in engine._aggregated_events:
            event_type = event.get('event_type', 'Unknown')
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
        
        logger.info("=== РАСПРЕДЕЛЕНИЕ СОБЫТИЙ ПО ТИПАМ ===")
        for event_type, count in events_by_type.items():
            logger.info(f"{event_type}: {count}")
        
        # Проверяем наличие ключевых типов событий
        required_events = ['PublishPostAction', 'PurchaseAction', 'SelfDevAction']
        missing_events = []
        
        for event_type in required_events:
            if event_type not in events_by_type or events_by_type[event_type] == 0:
                missing_events.append(event_type)
        
        if missing_events:
            logger.error(f"ОТСУТСТВУЮТ СОБЫТИЯ: {missing_events}")
            return False
        else:
            logger.info("✅ ВСЕ ТИПЫ СОБЫТИЙ СОЗДАЮТСЯ КОРРЕКТНО")
        
        # Проверяем, что тренды создаются
        if stats.get('trends_created', 0) > 0:
            logger.info("✅ ТРЕНДЫ СОЗДАЮТСЯ КОРРЕКТНО")
        else:
            logger.warning("⚠️ ТРЕНДЫ НЕ СОЗДАЮТСЯ")
        
        # Проверяем состояние агентов
        active_agents = sum(1 for agent in engine.agents if agent.energy_level > 0)
        logger.info(f"Активных агентов: {active_agents}/{len(engine.agents)}")
        
        # Показываем примеры событий
        logger.info("=== ПРИМЕРЫ СОБЫТИЙ ===")
        for i, event in enumerate(engine._aggregated_events[:5]):
            logger.info(f"Событие {i+1}: {event.get('event_type')} - агент {event.get('agent_id', 'N/A')}")
        
        logger.info("=== ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===")
        return True
        
    except Exception as e:
        logger.error(f"ОШИБКА ТЕСТИРОВАНИЯ: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Запускаем тест
    success = asyncio.run(test_simulation_events())
    
    if success:
        print("\n🎉 ТЕСТ ПРОЙДЕН: Логика создания событий работает корректно!")
    else:
        print("\n❌ ТЕСТ ПРОВАЛЕН: Есть проблемы с созданием событий!")
        exit(1) 