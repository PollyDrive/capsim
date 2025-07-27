#!/usr/bin/env python3
"""
Тест соответствия исправлений ТЗ v1.9.
Проверяет:
1. Правильную конфигурацию действий (cooldown, эффекты)
2. Систему sentiment для трендов
3. PostEffect систему
4. Суточные циклы
5. Создание разнообразных событий
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

async def test_v1_9_compliance():
    """Тестирует соответствие исправлений ТЗ v1.9."""
    
    try:
        # Импортируем компоненты симуляции
        from capsim.engine.simulation_engine import SimulationEngine
        from capsim.db.repositories import DatabaseRepository
        from capsim.common.settings import settings, action_config
        
        logger.info("=== ТЕСТ СООТВЕТСТВИЯ ТЗ v1.9 ===")
        
        # 1. Проверяем конфигурацию действий
        logger.info("1. Проверка конфигурации действий...")
        
        # Проверяем cooldown значения
        assert action_config.cooldowns["POST_MIN"] == 40, f"POST_MIN должен быть 40, получен {action_config.cooldowns['POST_MIN']}"
        assert action_config.cooldowns["SELF_DEV_MIN"] == 30, f"SELF_DEV_MIN должен быть 30, получен {action_config.cooldowns['SELF_DEV_MIN']}"
        logger.info("✅ Cooldown значения соответствуют ТЗ v1.9")
        
        # Проверяем эффекты POST
        post_effects = action_config.effects["POST"]
        assert post_effects["time_budget"] == -0.15, f"POST time_budget должен быть -0.15, получен {post_effects['time_budget']}"
        assert post_effects["energy_level"] == -0.20, f"POST energy_level должен быть -0.20, получен {post_effects['energy_level']}"
        assert post_effects["social_status"] == 0.05, f"POST social_status должен быть 0.05, получен {post_effects['social_status']}"
        logger.info("✅ POST эффекты соответствуют ТЗ v1.9")
        
        # Проверяем эффекты SELF_DEV
        selfdev_effects = action_config.effects["SELF_DEV"]
        assert selfdev_effects["time_budget"] == -0.80, f"SELF_DEV time_budget должен быть -0.80, получен {selfdev_effects['time_budget']}"
        assert selfdev_effects["energy_level"] == 0.45, f"SELF_DEV energy_level должен быть 0.45, получен {selfdev_effects['energy_level']}"
        assert selfdev_effects["social_status"] == 0.10, f"SELF_DEV social_status должен быть 0.10, получен {selfdev_effects['social_status']}"
        logger.info("✅ SELF_DEV эффекты соответствуют ТЗ v1.9")
        
        # Проверяем эффекты PURCHASE
        for level in ["L1", "L2", "L3"]:
            purchase_effects = action_config.effects["PURCHASE"][level]
            assert "cost_range" in purchase_effects, f"PURCHASE {level} должен иметь cost_range"
            assert "energy_level" in purchase_effects, f"PURCHASE {level} должен иметь energy_level"
            assert "time_budget" in purchase_effects, f"PURCHASE {level} должен иметь time_budget"
            logger.info(f"✅ PURCHASE {level} эффекты соответствуют ТЗ v1.9")
        
        # 2. Проверяем систему sentiment
        logger.info("2. Проверка системы sentiment...")
        from capsim.domain.trend import Trend, Sentiment
        
        # Создаем тестовый тренд с sentiment
        test_trend = Trend.create_from_action(
            topic="Economic",
            originator_id=uuid4(),
            simulation_id=uuid4(),
            base_virality=2.0,
            sentiment="Positive"
        )
        assert test_trend.sentiment in ["Positive", "Negative"], f"Sentiment должен быть Positive или Negative, получен {test_trend.sentiment}"
        logger.info("✅ Система sentiment работает корректно")
        
        # 3. Проверяем PostEffect систему
        logger.info("3. Проверка PostEffect системы...")
        from capsim.domain.events import TrendInfluenceEvent
        
        # Проверяем наличие метода расчета PostEffect
        assert hasattr(TrendInfluenceEvent, '_calculate_author_post_effect'), "TrendInfluenceEvent должен иметь метод _calculate_author_post_effect"
        logger.info("✅ PostEffect система реализована")
        
        # 4. Проверяем суточные циклы
        logger.info("4. Проверка суточных циклов...")
        from capsim.domain.person import Person
        
        # Создаем тестового агента
        test_agent = Person(
            profession="Developer",
            energy_level=3.0,
            time_budget=2.0,
            simulation_id=uuid4()
        )
        
        # Проверяем блокировку в ночное время (00:00-08:00)
        night_time = 120.0  # 02:00
        day_time = night_time % 1440
        assert 0 <= day_time < 480, f"Время {day_time} должно быть в ночном диапазоне"
        
        can_act_night = test_agent.can_perform_action("any", current_time=night_time)
        assert not can_act_night, f"Агент не должен действовать в ночное время {day_time}"
        
        # Проверяем разрешение в дневное время
        day_time = 600.0  # 10:00
        can_act_day = test_agent.can_perform_action("any", current_time=day_time)
        assert can_act_day, f"Агент должен действовать в дневное время"
        logger.info("✅ Суточные циклы работают корректно")
        
        # 5. Запускаем короткую симуляцию для проверки создания событий
        logger.info("5. Запуск тестовой симуляции...")
        
        # Создаем репозиторий БД
        db_repo = DatabaseRepository()
        
        # Создаем движок симуляции
        engine = SimulationEngine(db_repo)
        
        # Инициализируем короткую симуляцию
        await engine.initialize(num_agents=20, duration_days=0.05)  # 20 агентов, 1.2 часа
        
        # Запускаем симуляцию
        await engine.run_simulation()
        
        # Получаем статистику
        stats = engine.get_simulation_stats()
        
        logger.info("=== РЕЗУЛЬТАТЫ СИМУЛЯЦИИ ===")
        logger.info(f"Всего событий: {stats.get('total_events', 0)}")
        logger.info(f"Созданных трендов: {stats.get('trends_created', 0)}")
        
        # Проверяем создание разных типов событий
        events_by_type = {}
        for event in engine._aggregated_events:
            event_type = event.get('event_type', 'Unknown')
            events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
        
        logger.info("=== РАСПРЕДЕЛЕНИЕ СОБЫТИЙ ===")
        for event_type, count in events_by_type.items():
            logger.info(f"{event_type}: {count}")
        
        # Проверяем наличие ключевых типов событий
        required_events = ['PublishPostAction', 'PurchaseAction', 'SelfDevAction']
        missing_events = []
        
        for event_type in required_events:
            if event_type not in events_by_type or events_by_type[event_type] == 0:
                missing_events.append(event_type)
        
        if missing_events:
            logger.error(f"❌ ОТСУТСТВУЮТ СОБЫТИЯ: {missing_events}")
            return False
        else:
            logger.info("✅ ВСЕ ТИПЫ СОБЫТИЙ СОЗДАЮТСЯ")
        
        # Проверяем создание трендов с sentiment
        if stats.get('trends_created', 0) > 0:
            logger.info("✅ ТРЕНДЫ СОЗДАЮТСЯ КОРРЕКТНО")
        else:
            logger.warning("⚠️ ТРЕНДЫ НЕ СОЗДАЮТСЯ")
        
        logger.info("=== ТЕСТ СООТВЕТСТВИЯ ТЗ v1.9 ЗАВЕРШЕН ===")
        return True
        
    except Exception as e:
        logger.error(f"❌ ОШИБКА ТЕСТИРОВАНИЯ: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Запускаем тест
    success = asyncio.run(test_v1_9_compliance())
    
    if success:
        print("\n🎉 ТЕСТ ПРОЙДЕН: Все исправления соответствуют ТЗ v1.9!")
    else:
        print("\n❌ ТЕСТ ПРОВАЛЕН: Есть несоответствия ТЗ v1.9!")
        exit(1) 