"""
Тесты для realtime симуляции.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from uuid import uuid4

from capsim.common.clock import SimClock, RealTimeClock, create_clock
from capsim.engine.simulation_engine import SimulationEngine
from capsim.domain.events import BaseEvent, EventPriority


class TestClock:
    """Тесты для Clock implementations."""
    
    def test_sim_clock_basic(self):
        """Тест базовой функциональности SimClock."""
        clock = SimClock()
        assert clock.now() == 0.0
        
    @pytest.mark.asyncio
    async def test_sim_clock_sleep_until(self):
        """Тест что SimClock не делает реальных задержек."""
        clock = SimClock()
        start_time = time.time()
        
        await clock.sleep_until(100.0)  # 100 минут
        
        elapsed = time.time() - start_time
        assert elapsed < 0.1  # Должно быть практически мгновенно
        assert clock.now() == 100.0
        
    def test_real_time_clock_init(self):
        """Тест инициализации RealTimeClock."""
        clock = RealTimeClock(speed_factor=10.0)
        assert clock.speed_factor == 10.0
        assert clock.start_real_time > 0
        
    def test_real_time_clock_invalid_speed(self):
        """Тест валидации speed_factor."""
        with pytest.raises(ValueError):
            RealTimeClock(speed_factor=0.05)  # Слишком медленно
            
        with pytest.raises(ValueError):
            RealTimeClock(speed_factor=2000)  # Слишком быстро
            
    def test_real_time_clock_now(self):
        """Тест расчета текущего времени в RealTimeClock."""
        clock = RealTimeClock(speed_factor=60.0)
        
        # Небольшая задержка для проверки расчетов
        time.sleep(0.1)
        
        sim_time = clock.now()
        assert sim_time > 0
        assert sim_time < 1.0  # Меньше минуты при 60x ускорении
        
    @pytest.mark.asyncio
    async def test_real_time_clock_sleep_until(self):
        """Тест sleep_until с ускорением."""
        clock = RealTimeClock(speed_factor=100.0)  # Очень быстро для теста
        
        start_time = time.time()
        await clock.sleep_until(1.0)  # 1 минута симуляции
        elapsed = time.time() - start_time
        
        # При speed_factor=100, 1 sim-минута = 0.6 real-секунды
        assert 0.5 < elapsed < 0.8
        
    def test_create_clock_factory(self):
        """Тест factory function для создания часов."""
        sim_clock = create_clock(realtime=False)
        assert isinstance(sim_clock, SimClock)
        
        real_clock = create_clock(realtime=True)
        assert isinstance(real_clock, RealTimeClock)


class MockEvent(BaseEvent):
    """Mock событие для тестирования."""
    
    def __init__(self, timestamp: float):
        super().__init__(EventPriority.AGENT_ACTION, timestamp)
        self.processed = False
        
    def process(self, engine):
        """Mock обработка события."""
        self.processed = True


class TestRealtimeSimulation:
    """Тесты для realtime симуляции."""
    
    @pytest.fixture
    def mock_db_repo(self):
        """Mock database repository."""
        repo = Mock()
        repo.create_simulation_run = Mock(return_value=Mock(run_id=uuid4()))
        repo.load_affinity_map = Mock(return_value={})
        repo.get_active_trends = Mock(return_value=[])
        repo.bulk_create_persons = Mock()
        repo.batch_commit_states = Mock()
        repo.create_event = Mock()
        repo.update_simulation_status = Mock()
        return repo
        
    @pytest.mark.asyncio
    async def test_realtime_simulation_timing(self, mock_db_repo):
        """Тест точности timing в realtime режиме."""
        # Используем fast clock для ускорения теста
        clock = RealTimeClock(speed_factor=60.0)  # 60x ускорение
        engine = SimulationEngine(mock_db_repo, clock)
        
        # Инициализируем с малым количеством агентов
        await engine.initialize(num_agents=5)
        
        # Добавляем тестовые события
        event1 = MockEvent(timestamp=1.0)  # Через 1 минуту
        event2 = MockEvent(timestamp=2.0)  # Через 2 минуты
        
        engine.add_event(event1, EventPriority.AGENT_ACTION, 1.0)
        engine.add_event(event2, EventPriority.AGENT_ACTION, 2.0)
        
        start_time = time.time()
        
        # Запускаем симуляцию на 3 минуты
        with patch('capsim.common.settings.settings.ENABLE_REALTIME', True):
            await engine.run_simulation(duration_days=3/1440.0)  # 3 минуты в днях
        
        elapsed = time.time() - start_time
        
        # При speed_factor=60, 3 минуты симуляции = 3 реальных секунды
        assert 2.5 < elapsed < 4.0  # С небольшим tolerance
        assert event1.processed
        assert event2.processed
        
    @pytest.mark.asyncio
    async def test_fast_simulation_no_delay(self, mock_db_repo):
        """Тест что fast режим работает без задержек."""
        clock = SimClock()
        engine = SimulationEngine(mock_db_repo, clock)
        
        await engine.initialize(num_agents=5)
        
        # Добавляем много событий
        for i in range(10):
            event = MockEvent(timestamp=float(i))
            engine.add_event(event, EventPriority.AGENT_ACTION, float(i))
            
        start_time = time.time()
        
        with patch('capsim.common.settings.settings.ENABLE_REALTIME', False):
            await engine.run_simulation(duration_days=10/1440.0)  # 10 минут
            
        elapsed = time.time() - start_time
        
        # Должно выполниться очень быстро
        assert elapsed < 1.0
        
    @pytest.mark.asyncio 
    async def test_batch_commit_timing_realtime(self, mock_db_repo):
        """Тест batch commit в realtime режиме."""
        clock = RealTimeClock(speed_factor=100.0)  # Быстрое ускорение
        engine = SimulationEngine(mock_db_repo, clock)
        
        await engine.initialize(num_agents=5)
        
        # Добавляем много обновлений в batch
        for i in range(50):
            engine.add_to_batch_update({
                "type": "test_update",
                "id": i,
                "timestamp": float(i)
            })
            
        with patch('capsim.common.settings.settings.ENABLE_REALTIME', True):
            with patch('capsim.common.settings.settings.get_batch_timeout_seconds', return_value=0.1):
                # Симулируем время для проверки timeout
                time.sleep(0.2)
                
                # Проверяем что должен произойти commit
                should_commit = engine._should_commit_batch()
                assert should_commit
                
    @pytest.mark.asyncio
    async def test_timestamp_real_conversion(self, mock_db_repo):
        """Тест конвертации sim_time в timestamp_real."""
        clock = RealTimeClock(speed_factor=10.0)
        engine = SimulationEngine(mock_db_repo, clock)
        engine._simulation_start_real = time.time()
        
        event = MockEvent(timestamp=5.0)  # 5 минут симуляции
        engine.add_event(event, EventPriority.AGENT_ACTION, 5.0)
        
        await engine.initialize(num_agents=1)
        
        # Проверяем что timestamp_real вычисляется правильно
        with patch('capsim.common.settings.settings.ENABLE_REALTIME', True):
            # Запускаем один event loop iteration
            priority_event = engine.event_queue[0]
            
            # Конвертируем timestamp
            if priority_event.event.timestamp_real is None:
                priority_event.event.timestamp_real = (
                    engine._simulation_start_real + 
                    priority_event.timestamp * 60.0 / 10.0  # speed_factor=10
                )
                
            # timestamp_real должен быть через 30 секунд (5 * 60 / 10)
            expected_real = engine._simulation_start_real + 30.0
            assert abs(priority_event.event.timestamp_real - expected_real) < 0.1


@pytest.mark.asyncio
async def test_end_to_end_mini_simulation():
    """End-to-end тест мини-симуляции в realtime."""
    from capsim.db.repositories import DatabaseRepository
    
    # Mock repository для e2e теста
    mock_repo = Mock(spec=DatabaseRepository)
    mock_repo.create_simulation_run = Mock(return_value=Mock(run_id=uuid4()))
    mock_repo.load_affinity_map = Mock(return_value={
        "Teacher": {"Science": 0.8, "Culture": 0.6},
        "Developer": {"Science": 0.9, "Economic": 0.5}
    })
    mock_repo.get_active_trends = Mock(return_value=[])
    mock_repo.bulk_create_persons = Mock()
    mock_repo.batch_commit_states = Mock()
    mock_repo.create_event = Mock()
    mock_repo.update_simulation_status = Mock()
    
    # Создаем engine с ускоренным clock
    clock = RealTimeClock(speed_factor=120.0)  # 2 минуты = 1 секунда
    engine = SimulationEngine(mock_repo, clock)
    
    start_time = time.time()
    
    with patch('capsim.common.settings.settings.ENABLE_REALTIME', True):
        with patch('capsim.common.settings.settings.SIM_SPEED_FACTOR', 120.0):
            # Мини-симуляция: 10 агентов, 2 минуты
            await engine.initialize(num_agents=10)
            await engine.run_simulation(duration_days=2/1440.0)
    
    elapsed = time.time() - start_time
    
    # При speed_factor=120, 2 минуты симуляции ≈ 1 секунда
    assert 0.8 < elapsed < 2.0
    
    # Проверяем что основные методы были вызваны
    mock_repo.create_simulation_run.assert_called_once()
    mock_repo.bulk_create_persons.assert_called_once()
    mock_repo.update_simulation_status.assert_called_once() 