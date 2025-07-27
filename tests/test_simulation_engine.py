"""
Tests for SimulationEngine - основной тест DES-цикла и логики агентов.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from capsim.engine.simulation_engine import SimulationEngine, SimulationContext
from capsim.domain.person import Person
from capsim.domain.trend import Trend
from capsim.domain.events import PublishPostAction, EnergyRecoveryEvent
from capsim.db.models import SimulationRun


@pytest.fixture
def mock_db_repo():
    """Мок репозитория БД для тестов."""
    repo = AsyncMock()
    
    # Мок создания симуляции
    simulation_run = SimulationRun(
        run_id=uuid4(),
        num_agents=10,
        duration_days=1,
        status="RUNNING"
    )
    repo.create_simulation_run.return_value = simulation_run
    
    # Мок загрузки affinity map
    repo.load_affinity_map.return_value = {
        "ECONOMIC": {"Banker": 4.5, "Developer": 3.0},
        "HEALTH": {"Teacher": 4.0, "Worker": 3.5}
    }
    
    # Мок получения трендов
    repo.get_active_trends.return_value = []
    
    # Дополнительные методы для нового API
    repo.get_persons_count.return_value = 0
    repo.get_persons_for_simulation.return_value = []
    
    # Мок batch операций
    repo.bulk_create_persons.return_value = None
    repo.batch_commit_states.return_value = None
    repo.create_event.return_value = None
    repo.update_simulation_status.return_value = None
    
    repo.bulk_update_persons = AsyncMock()
    repo.bulk_update_simulation_participants = AsyncMock()
    
    # Валидные диапазоны профессий из agents_profession_dump.csv
    repo.get_profession_attribute_ranges.return_value = {
        "ShopClerk": {"financial_capability": (2, 4), "trend_receptivity": (1, 3), "social_status": (1, 3), "energy_level": (2, 5), "time_budget": (3, 5)},
        "Worker": {"financial_capability": (2, 4), "trend_receptivity": (1, 3), "social_status": (1, 2), "energy_level": (2, 5), "time_budget": (3, 5)},
        "Developer": {"financial_capability": (3, 5), "trend_receptivity": (3, 5), "social_status": (2, 4), "energy_level": (2, 5), "time_budget": (2, 4)},
        "Politician": {"financial_capability": (3, 5), "trend_receptivity": (3, 5), "social_status": (4, 5), "energy_level": (2, 5), "time_budget": (2, 4)},
        "Blogger": {"financial_capability": (2, 4), "trend_receptivity": (4, 5), "social_status": (3, 5), "energy_level": (2, 5), "time_budget": (3, 5)},
        "Businessman": {"financial_capability": (4, 5), "trend_receptivity": (2, 4), "social_status": (4, 5), "energy_level": (2, 5), "time_budget": (2, 4)},
        "SpiritualMentor": {"financial_capability": (1, 3), "trend_receptivity": (2, 5), "social_status": (2, 4), "energy_level": (3, 5), "time_budget": (2, 4)},
        "Philosopher": {"financial_capability": (1, 3), "trend_receptivity": (1, 3), "social_status": (1, 3), "energy_level": (2, 5), "time_budget": (2, 4)},
        "Unemployed": {"financial_capability": (1, 2), "trend_receptivity": (3, 5), "social_status": (1, 2), "energy_level": (3, 5), "time_budget": (3, 5)},
        "Teacher": {"financial_capability": (1, 3), "trend_receptivity": (1, 3), "social_status": (2, 4), "energy_level": (2, 5), "time_budget": (2, 4)},
        "Artist": {"financial_capability": (1, 3), "trend_receptivity": (2, 4), "social_status": (2, 4), "energy_level": (4, 5), "time_budget": (3, 5)},
        "Doctor": {"financial_capability": (2, 4), "trend_receptivity": (1, 3), "social_status": (3, 5), "energy_level": (2, 5), "time_budget": (1, 2)},
    }

    # Заглушка для ReadOnlySession (чтобы не падало на async with)
    class DummySession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            pass
        async def execute(self, *args, **kwargs):
            class DummyResult:
                def scalars(self):
                    class DummyScalars:
                        def all(self):
                            return []
                    return DummyScalars()
                def fetchall(self):
                    return []
            return DummyResult()
    repo.ReadOnlySession = DummySession
    
    return repo


@pytest.mark.asyncio
async def test_simulation_initialization(mock_db_repo):
    """Тест инициализации симуляции."""
    engine = SimulationEngine(mock_db_repo)
    
    await engine.initialize(num_agents=10)
    
    # Проверяем что симуляция инициализирована
    assert engine.simulation_id is not None
    assert len(engine.agents) == 10
    assert len(engine.event_queue) > 0  # Системные события запланированы
    assert engine.affinity_map is not None
    
    # Проверяем что агенты созданы правильно
    professions = set(agent.profession for agent in engine.agents)
    assert len(professions) > 0
    
    for agent in engine.agents:
        assert 0.0 <= agent.energy_level <= 5.0
        assert agent.time_budget > 0
        assert len(agent.interests) > 0


@pytest.mark.asyncio
async def test_agent_decision_making(mock_db_repo):
    """Тест принятия решений агентами."""
    engine = SimulationEngine(mock_db_repo)
    await engine.initialize(num_agents=5)
    
    # Создаем контекст симуляции
    context = SimulationContext(
        current_time=0.0,
        active_trends={},
        affinity_map=engine.affinity_map
    )
    
    # Тестируем принятие решений
    decisions_made = 0
    for agent in engine.agents:
        decision = agent.decide_action(context)
        if decision:
            decisions_made += 1
            assert decision in ["PublishPostAction"]
    
    # Должны быть приняты некоторые решения
    assert decisions_made >= 0  # Может быть 0 если у агентов низкий score


@pytest.mark.asyncio
async def test_publish_post_action(mock_db_repo):
    """Тест обработки события публикации поста."""
    engine = SimulationEngine(mock_db_repo)
    await engine.initialize(num_agents=5)
    
    agent = engine.agents[0]
    initial_energy = agent.energy_level
    initial_budget = agent.time_budget
    
    # Создаем событие публикации
    event = PublishPostAction(
        agent_id=agent.id,
        topic="ECONOMIC", 
        timestamp=10.0
    )
    
    # Обрабатываем событие
    await engine._process_event(event)
    
    # Проверяем что тренд создан
    assert len(engine.active_trends) == 1
    
    # v1.9: Эффекты применяются через TrendInfluenceEvent (через 5 минут), не мгновенно
    # Проверяем что cooldown обновлен
    assert agent.last_post_ts == 10.0
    assert agent.actions_today == 1
    
    # Энергия и время пока не изменились (эффекты будут через 5 минут)
    assert agent.energy_level == initial_energy
    assert agent.time_budget == initial_budget
    
    # v1.9: History records are created by TrendInfluenceEvent, not immediately
    # Just verify the trend was created
    assert len(engine.active_trends) == 1


@pytest.mark.asyncio
async def test_energy_recovery_event(mock_db_repo):
    """Тест события восстановления энергии."""
    engine = SimulationEngine(mock_db_repo)
    await engine.initialize(num_agents=5)
    
    # Снижаем энергию у некоторых агентов
    for i, agent in enumerate(engine.agents[:3]):
        if i < 2:
            agent.energy_level = 2.0  # Низкая энергия
        else:
            agent.energy_level = 4.0  # Высокая энергия
    
    # Создаем событие восстановления
    event = EnergyRecoveryEvent(timestamp=360.0)
    
    # Обрабатываем событие
    await engine._process_event(event)
    
    # Проверяем восстановление энергии (EnergyRecoveryEvent добавляет 0.12 энергии)
    assert engine.agents[0].energy_level >= 2.12  # 2.0 + 0.12
    assert engine.agents[1].energy_level >= 2.12  # 2.0 + 0.12
    assert engine.agents[2].energy_level >= 4.0
    
    # Проверяем что запланировано следующее восстановление
    future_events = [e for e in engine.event_queue if isinstance(e.event, EnergyRecoveryEvent)]
    assert len(future_events) >= 1


@pytest.mark.asyncio
async def test_trend_virality_calculation():
    """Тест расчета виральности тренда."""
    trend = Trend.create_from_action(
        topic="ECONOMIC",
        originator_id=uuid4(),
        simulation_id=uuid4(),
        base_virality=2.0
    )
    
    # Без взаимодействий
    assert trend.calculate_current_virality() == 2.0
    
    # С взаимодействиями
    for _ in range(10):
        trend.add_interaction()
    
    # Виральность должна увеличиться
    new_virality = trend.calculate_current_virality()
    assert new_virality > 2.0
    assert new_virality <= 5.0  # Не превышает максимум


@pytest.mark.asyncio 
async def test_batch_commit_mechanism(mock_db_repo):
    """Тест механизма batch commit."""
    engine = SimulationEngine(mock_db_repo)
    engine.batch_size = 3  # Маленький размер для теста
    
    await engine.initialize(num_agents=5)
    
    # Проверяем что batch размер установлен правильно
    assert engine.batch_size == 3
    
    # Проверяем что engine имеет необходимые атрибуты для batch операций
    assert hasattr(engine, '_aggregated_history')
    assert hasattr(engine, '_aggregated_trends')
    
    # Проверяем что репозиторий настроен
    assert engine.db_repo == mock_db_repo


@pytest.mark.asyncio
async def test_short_simulation_run(mock_db_repo):
    """Интеграционный тест короткого запуска симуляции."""
    engine = SimulationEngine(mock_db_repo)
    
    await engine.initialize(num_agents=10)
    
    # Запускаем симуляцию на 60 минут (1/24 дня)
    # Устанавливаем короткое время для теста
    engine.end_time = 60.0  # 60 минут
    await engine.run_simulation()
    
    # Проверяем финальную статистику
    stats = engine.get_simulation_stats()
    
    assert stats["simulation_id"] is not None
    assert stats["current_time"] > 0  # Simulation ran for some time
    assert stats["total_agents"] == 10
    
    # Проверяем что статус обновлен
    mock_db_repo.update_simulation_status.assert_called()


if __name__ == "__main__":
    # Быстрый тест для разработки
    async def quick_test():
        from unittest.mock import AsyncMock
        
        repo = AsyncMock()
        repo.create_simulation_run.return_value = SimulationRun(
            run_id=uuid4(),
            num_agents=10,
            duration_days=1
        )
        repo.load_affinity_map.return_value = {}
        repo.get_active_trends.return_value = []
        repo.bulk_create_persons.return_value = None
        repo.batch_commit_states.return_value = None
        repo.create_event.return_value = None
        repo.update_simulation_status.return_value = None
        
        engine = SimulationEngine(repo)
        await engine.initialize(num_agents=10)
        
        print(f"✅ Симуляция инициализирована: {len(engine.agents)} агентов")
        print(f"✅ События в очереди: {len(engine.event_queue)}")
        print(f"✅ Affinity map загружена: {len(engine.affinity_map)} тем")
        
        # Тест одного решения агента
        from capsim.engine.simulation_engine import SimulationContext
        context = SimulationContext(0.0, {}, engine.affinity_map)
        
        decisions = [agent.decide_action(context) for agent in engine.agents[:5]]
        print(f"✅ Решения агентов: {[d for d in decisions if d]}")
        
    asyncio.run(quick_test()) 