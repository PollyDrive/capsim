#!/usr/bin/env python3
"""
Скрипт для отладки сохранения изменений trend_receptivity.
Создает минимальную симуляцию и проверяет, сохраняются ли изменения в базу данных.
"""

import asyncio
import json
import logging
from datetime import datetime, date
from uuid import uuid4
from capsim.common.logging_config import get_logger
from capsim.engine.simulation_engine import SimulationEngine
from capsim.domain.person import Person
from capsim.domain.trend import Trend
from capsim.domain.events import TrendInfluenceEvent

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = get_logger(__name__)

class MockDBRepository:
    """Мок-репозиторий для тестирования без реальной базы данных."""
    
    def __init__(self):
        self.history_records = []
        self.simulation_runs = []
        self.persons = []
        self.trends = []
    
    async def create_simulation_run(self, **kwargs):
        run_id = uuid4()
        self.simulation_runs.append({"run_id": run_id, **kwargs})
        return type('SimulationRun', (), {"run_id": run_id})()
    
    async def get_persons_count(self):
        return len(self.persons)
    
    async def get_available_persons(self, count):
        return self.persons[:count]
    
    async def get_latest_agent_attributes(self, person_ids):
        return {}
    
    async def bulk_create_persons(self, persons):
        self.persons.extend(persons)
    
    async def load_affinity_map(self):
        """Возвращает тестовую карту аффинности."""
        return {
            ("Blogger", "Economic"): 4.0,
            ("Developer", "Economic"): 2.0,
        }
    
    async def load_profession_ranges(self):
        """Возвращает тестовые диапазоны профессий."""
        return {}
    
    async def cleanup_stale_simulations(self):
        """Очистка устаревших симуляций."""
        pass
    
    async def get_profession_attribute_ranges(self):
        """Возвращает диапазоны атрибутов профессий."""
        return {}
    
    async def get_persons_for_simulation(self, simulation_id, count):
        """Возвращает персон для симуляции."""
        return []
    
    async def bulk_create_person_attribute_history(self, history_records):
        """Сохраняем записи истории и логируем их."""
        for record in history_records:
            record_dict = {
                "simulation_id": record.simulation_id,
                "person_id": record.person_id,
                "attribute_name": record.attribute_name,
                "old_value": record.old_value,
                "new_value": record.new_value,
                "delta": record.delta,
                "reason": record.reason,
                "source_trend_id": record.source_trend_id,
                "change_timestamp": record.change_timestamp
            }
            self.history_records.append(record_dict)
            
            if record.attribute_name == "trend_receptivity":
                logger.info(json.dumps({
                    "event": "mock_db_saved_trend_receptivity",
                    "person_id": str(record.person_id),
                    "old_value": record.old_value,
                    "new_value": record.new_value,
                    "delta": record.delta,
                    "reason": record.reason
                }, default=str))
        
        logger.info(f"Mock DB: Saved {len(history_records)} history records")
        logger.info(f"Mock DB: Total trend_receptivity records: {len([r for r in self.history_records if r['attribute_name'] == 'trend_receptivity'])}")
    
    async def bulk_create_trends(self, trends):
        self.trends.extend(trends)
    
    async def bulk_update_simulation_participants(self, updates):
        pass
    
    async def update_simulation_run_status(self, run_id, status, end_time=None):
        pass

async def test_trend_receptivity_saving():
    """Тестирует сохранение изменений trend_receptivity."""
    
    logger.info("🚀 Начинаем тест сохранения trend_receptivity")
    
    # Создаем мок-репозиторий
    mock_repo = MockDBRepository()
    
    # Создаем движок симуляции
    engine = SimulationEngine(db_repo=mock_repo)
    
    # Минимальная инициализация без создания агентов
    engine.simulation_id = uuid4()
    engine.duration_minutes = 144.0
    engine.current_time = 0.0
    engine.running = True
    engine._aggregated_history = []
    engine._aggregated_trends = []
    engine._aggregated_updates = {}
    
    # Добавляем карту аффинности
    engine.affinity_map = {
        ("Blogger", "Economic"): 4.0,
        ("Developer", "Economic"): 2.0,
    }
    
    # Создаем тестовых агентов с высокими значениями для гарантированного влияния
    agent1 = Person(
        id=uuid4(),
        profession="Blogger",
        first_name="Тест",
        last_name="Блогеров",
        gender="male",
        date_of_birth=date(1990, 1, 1),
        financial_capability=3.0,
        trend_receptivity=4.0,  # Высокая восприимчивость
        social_status=3.0,
        energy_level=5.0,  # Максимальная энергия
        time_budget=5.0,   # Максимальный бюджет времени
        interests={"Economics": 5.0},  # Максимальный интерес
        simulation_id=engine.simulation_id
    )
    
    agent2 = Person(
        id=uuid4(),
        profession="Developer",
        first_name="Тест",
        last_name="Разработчиков",
        gender="male",
        date_of_birth=date(1985, 1, 1),
        financial_capability=4.0,
        trend_receptivity=3.0,  # Высокая восприимчивость
        social_status=2.0,
        energy_level=5.0,  # Максимальная энергия
        time_budget=5.0,   # Максимальный бюджет времени
        interests={"Economics": 4.0},  # Высокий интерес
        simulation_id=engine.simulation_id
    )
    
    engine.agents = [agent1, agent2]
    
    # Создаем тестовый тренд с высоким охватом
    trend = Trend(
        trend_id=uuid4(),
        simulation_id=engine.simulation_id,
        topic="Economic",
        originator_id=agent1.id,
        base_virality_score=3.0,
        sentiment="Positive"
    )
    trend.coverage_level = "High"  # Максимальный охват
    
    engine.trends = [trend]
    engine.active_trends = {str(trend.trend_id): trend}
    
    logger.info(f"Начальные значения trend_receptivity:")
    logger.info(f"  Agent1 (Blogger): {agent1.trend_receptivity}")
    logger.info(f"  Agent2 (Developer): {agent2.trend_receptivity}")
    
    # Создаем событие влияния тренда
    influence_event = TrendInfluenceEvent(timestamp=10.0, trend_id=trend.trend_id)
    
    # Выполняем событие
    influence_event.process(engine)
    
    logger.info(f"Значения trend_receptivity после влияния тренда:")
    logger.info(f"  Agent1 (Blogger): {agent1.trend_receptivity}")
    logger.info(f"  Agent2 (Developer): {agent2.trend_receptivity}")
    
    # Принудительно сохраняем изменения
    await engine._batch_commit_states()
    
    # Проверяем результаты
    trend_receptivity_records = [r for r in mock_repo.history_records if r['attribute_name'] == 'trend_receptivity']
    
    logger.info(f"📊 Результаты теста:")
    logger.info(f"  Всего записей истории: {len(mock_repo.history_records)}")
    logger.info(f"  Записей trend_receptivity: {len(trend_receptivity_records)}")
    
    for record in trend_receptivity_records:
        logger.info(f"  📝 Запись: person_id={str(record['person_id'])[:8]}..., "
                   f"old={record['old_value']}, new={record['new_value']}, "
                   f"delta={record['delta']}, reason={record['reason']}")
    
    if len(trend_receptivity_records) > 0:
        logger.info("✅ УСПЕХ: Изменения trend_receptivity сохраняются в историю!")
    else:
        logger.error("❌ ОШИБКА: Изменения trend_receptivity НЕ сохраняются в историю!")
    
    return len(trend_receptivity_records) > 0

if __name__ == "__main__":
    success = asyncio.run(test_trend_receptivity_saving())
    exit(0 if success else 1)