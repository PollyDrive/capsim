"""
Тесты интеграции проверки рабочих часов с планировщиком событий.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from capsim.engine.simulation_engine import SimulationEngine
from capsim.common.time_utils import is_work_hours, convert_sim_time_to_human


class TestWorkHoursIntegration:
    """Тесты интеграции проверки рабочих часов."""
    
    @pytest.fixture
    def mock_engine(self):
        """Создает мок движка симуляции."""
        engine = Mock(spec=SimulationEngine)
        engine.current_time = 0  # 08:00 - рабочее время
        engine.end_time = 1440   # 24 часа симуляции
        engine.agents = []
        engine.active_trends = {}
        engine.affinity_map = {}
        engine.event_queue = []
        engine.add_event = Mock()
        return engine
    
    def test_work_hours_check_during_day(self, mock_engine):
        """Тест что события планируются в рабочие часы."""
        # Рабочее время - 10:00
        mock_engine.current_time = 120
        
        assert is_work_hours(mock_engine.current_time) is True
        human_time = convert_sim_time_to_human(mock_engine.current_time)
        assert human_time == "10:00"
    
    def test_work_hours_check_during_night(self, mock_engine):
        """Тест что события НЕ планируются в ночное время."""
        # Ночное время - 02:00
        mock_engine.current_time = 1080  # 960 (полночь) + 120 (2 часа)
        
        assert is_work_hours(mock_engine.current_time) is False
        human_time = convert_sim_time_to_human(mock_engine.current_time)
        assert human_time == "02:00"
    
    @patch('capsim.engine.simulation_engine.logger')
    def test_seed_actions_skipped_at_night(self, mock_logger, mock_engine):
        """Тест что seed действия пропускаются ночью."""
        from capsim.engine.simulation_engine import SimulationEngine
        
        # Создаем реальный экземпляр для тестирования метода
        engine = SimulationEngine(
            simulation_id="test-id",
            num_agents=1,
            duration_days=1,
            db_repo=Mock()
        )
        engine.current_time = 960  # 00:00 - ночь
        engine.agents = [Mock()]  # Один агент
        engine.active_trends = {}
        engine.affinity_map = {}
        
        # Вызываем метод
        result = await engine._schedule_seed_actions()
        
        # Проверяем результат
        assert result == 0
        
        # Проверяем что было залогировано сообщение о пропуске
        mock_logger.info.assert_called()
        log_call = mock_logger.info.call_args[0][0]
        log_data = eval(log_call)  # Парсим JSON строку
        assert log_data["reason"] == "night_time"
        assert log_data["human_time"] == "00:00"
    
    @patch('capsim.engine.simulation_engine.logger')
    def test_uniform_actions_skipped_at_night(self, mock_logger, mock_engine):
        """Тест что uniform действия пропускаются ночью."""
        from capsim.engine.simulation_engine import SimulationEngine
        
        # Создаем реальный экземпляр для тестирования метода
        engine = SimulationEngine(
            simulation_id="test-id",
            num_agents=1,
            duration_days=1,
            db_repo=Mock()
        )
        engine.current_time = 1200  # 04:00 - ночь
        engine.end_time = 1440
        engine.agents = [Mock()]
        
        # Вызываем метод
        result = await engine._schedule_uniform_agent_actions()
        
        # Проверяем результат
        assert result == 0
        
        # Проверяем что было залогировано сообщение о пропуске
        mock_logger.info.assert_called()
        log_call = mock_logger.info.call_args[0][0]
        log_data = eval(log_call)  # Парсим JSON строку
        assert log_data["reason"] == "night_time"
        assert log_data["human_time"] == "04:00"
    
    @patch('capsim.engine.simulation_engine.logger')
    def test_agent_actions_skipped_at_night(self, mock_logger, mock_engine):
        """Тест что agent действия пропускаются ночью."""
        from capsim.engine.simulation_engine import SimulationEngine
        
        # Создаем реальный экземпляр для тестирования метода
        engine = SimulationEngine(
            simulation_id="test-id",
            num_agents=1,
            duration_days=1,
            db_repo=Mock()
        )
        engine.current_time = 1380  # 07:00 - раннее утро, еще ночь
        engine.end_time = 1440
        engine.agents = [Mock()]
        engine.active_trends = {}
        engine.affinity_map = {}
        
        # Вызываем метод
        result = await engine._schedule_agent_actions()
        
        # Проверяем результат
        assert result == 0
        
        # Проверяем что было залогировано сообщение о пропуске
        mock_logger.info.assert_called()
        log_call = mock_logger.info.call_args[0][0]
        log_data = eval(log_call)  # Парсим JSON строку
        assert log_data["reason"] == "night_time"
        assert log_data["human_time"] == "07:00"
    
    def test_batch_actions_skipped_at_night(self, mock_engine):
        """Тест что batch действия пропускаются ночью."""
        from capsim.engine.simulation_engine import SimulationEngine
        
        # Создаем реальный экземпляр для тестирования метода
        engine = SimulationEngine(
            simulation_id="test-id",
            num_agents=1,
            duration_days=1,
            db_repo=Mock()
        )
        engine.current_time = 960  # 00:00 - полночь
        
        # Создаем тестовый batch
        test_batch = [
            {
                "agent_id": "test-agent",
                "action_type": "PublishPostAction",
                "timestamp": 970
            }
        ]
        
        # Вызываем метод
        result = engine._schedule_actions_batch(test_batch)
        
        # Проверяем результат
        assert result == 0
    
    def test_wellness_actions_skipped_at_night(self, mock_engine):
        """Тест что wellness действия пропускаются ночью."""
        from capsim.engine.simulation_engine import SimulationEngine
        
        # Создаем реальный экземпляр для тестирования метода
        engine = SimulationEngine(
            simulation_id="test-id",
            num_agents=1,
            duration_days=1,
            db_repo=Mock()
        )
        engine.current_time = 1020  # 01:00 - ночь
        engine.agents = [Mock()]
        
        # Вызываем метод
        result = engine._schedule_random_wellness()
        
        # Проверяем результат
        assert result == 0
    
    def test_system_events_not_affected(self, mock_engine):
        """Тест что системные события НЕ затронуты проверкой рабочих часов."""
        from capsim.engine.simulation_engine import SimulationEngine
        
        # Создаем реальный экземпляр для тестирования метода
        engine = SimulationEngine(
            simulation_id="test-id",
            num_agents=1,
            duration_days=1,
            db_repo=Mock()
        )
        engine.current_time = 960  # 00:00 - ночь
        engine.end_time = 1440
        engine.event_queue = []
        engine.add_event = Mock()
        
        # Вызываем планирование системных событий
        engine._schedule_system_events()
        
        # Проверяем что системные события были запланированы
        # (add_event должен был быть вызван для системных событий)
        assert engine.add_event.called
    
    def test_boundary_cases(self):
        """Тест граничных случаев времени."""
        # 07:59 - последняя минута ночи
        assert is_work_hours(1439) is False  # 07:59
        
        # 08:00 - первая минута рабочего дня
        assert is_work_hours(0) is True      # 08:00
        assert is_work_hours(1440) is True   # 08:00 следующего дня
        
        # 23:59 - последняя минута рабочего дня
        assert is_work_hours(959) is True    # 23:59
        
        # 00:00 - первая минута ночи
        assert is_work_hours(960) is False   # 00:00