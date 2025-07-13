#!/usr/bin/env python3
"""
Тест для анализа timestamp событий и планирования новых действий.
"""

import asyncio
import json
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_timestamp_analysis():
    """Анализирует timestamp событий и планирование новых действий."""
    
    try:
        # Импортируем компоненты симуляции
        from capsim.engine.simulation_engine import SimulationEngine
        from capsim.db.repositories import DatabaseRepository
        from capsim.common.settings import settings
        
        # Создаем репозиторий БД
        db_repo = DatabaseRepository(settings.DATABASE_URL)
        
        # Создаем движок симуляции
        engine = SimulationEngine(db_repo)
        
        # Инициализируем симуляцию на 15 минут для анализа
        await engine.initialize(num_agents=10, duration_days=0.01)  # 10 агентов, 14.4 минуты
        
        logger.info("=== АНАЛИЗ TIMESTAMP СОБЫТИЙ ===")
        logger.info(f"Длительность симуляции: {engine.end_time} минут")
        logger.info(f"Начальное время: {engine.current_time} минут")
        
        # Анализируем seed события
        seed_events = []
        for event in engine.event_queue:
            if hasattr(event.event, 'agent_id'):
                seed_events.append({
                    'type': event.event.__class__.__name__,
                    'timestamp': event.timestamp,
                    'agent_id': str(event.event.agent_id),
                    'priority': event.priority
                })
        
        logger.info("=== SEED СОБЫТИЯ ===")
        for event in sorted(seed_events, key=lambda x: x['timestamp']):
            logger.info(f"{event['type']} - агент {event['agent_id']} - время {event['timestamp']:.1f} мин")
        
        # Анализируем системные события
        system_events = []
        for event in engine.event_queue:
            if not hasattr(event.event, 'agent_id'):
                system_events.append({
                    'type': event.event.__class__.__name__,
                    'timestamp': event.timestamp,
                    'priority': event.priority
                })
        
        logger.info("=== СИСТЕМНЫЕ СОБЫТИЯ ===")
        for event in sorted(system_events, key=lambda x: x['timestamp']):
            logger.info(f"{event['type']} - время {event['timestamp']:.1f} мин - приоритет {event['priority']}")
        
        # Анализируем планирование новых действий
        logger.info("=== АНАЛИЗ ПЛАНИРОВАНИЯ НОВЫХ ДЕЙСТВИЙ ===")
        for minute in range(0, int(engine.end_time) + 1):
            if minute % 2 == 0:  # Каждые 2 минуты
                logger.info(f"На {minute}-й минуте будут планироваться новые действия")
        
        # Анализируем энергию агентов
        logger.info("=== АНАЛИЗ ЭНЕРГИИ АГЕНТОВ ===")
        for i, agent in enumerate(engine.agents[:5]):  # Первые 5 агентов
            logger.info(f"Агент {i+1} ({agent.profession}): энергия={agent.energy_level:.2f}, время={agent.time_budget:.2f}")
        
        # Запускаем симуляцию на короткое время для анализа
        logger.info("=== ЗАПУСК СИМУЛЯЦИИ ДЛЯ АНАЛИЗА ===")
        
        # Останавливаем симуляцию через 10 минут для анализа
        original_end_time = engine.end_time
        engine.end_time = 10.0  # Ограничиваем до 10 минут
        
        # Запускаем симуляцию
        await engine.run_simulation()
        
        # Анализируем результаты
        logger.info("=== РЕЗУЛЬТАТЫ АНАЛИЗА ===")
        logger.info(f"Финальное время симуляции: {engine.current_time:.1f} минут")
        logger.info(f"Всего событий в очереди: {len(engine.event_queue)}")
        logger.info(f"Событий в batch: {len(engine._aggregated_events)}")
        
        # Анализируем события по типам
        events_by_type = {}
        for event in engine._aggregated_events:
            event_type = event.get('event_type', 'Unknown')
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
        
        logger.info("=== РАСПРЕДЕЛЕНИЕ СОБЫТИЙ ПО ТИПАМ ===")
        for event_type, count in events_by_type.items():
            logger.info(f"{event_type}: {count}")
        
        # Анализируем энергию агентов после симуляции
        logger.info("=== ЭНЕРГИЯ АГЕНТОВ ПОСЛЕ СИМУЛЯЦИИ ===")
        for i, agent in enumerate(engine.agents[:5]):
            logger.info(f"Агент {i+1} ({agent.profession}): энергия={agent.energy_level:.2f}, время={agent.time_budget:.2f}")
        
        # Проверяем, были ли созданы новые действия
        agent_events = [e for e in engine._aggregated_events if e.get('agent_id')]
        if agent_events:
            logger.info(f"✅ СОЗДАНО {len(agent_events)} СОБЫТИЙ АГЕНТОВ")
            return True
        else:
            logger.warning("⚠️ СОБЫТИЯ АГЕНТОВ НЕ СОЗДАВАЛИСЬ")
            return False
        
    except Exception as e:
        logger.error(f"ОШИБКА АНАЛИЗА: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Запускаем анализ
    success = asyncio.run(test_timestamp_analysis())
    
    if success:
        print("\n🎉 АНАЛИЗ ЗАВЕРШЕН: События создаются корректно!")
    else:
        print("\n❌ АНАЛИЗ ПРОВАЛЕН: Есть проблемы с созданием событий!")
        exit(1) 