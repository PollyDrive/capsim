"""
Тесты для CLI команды остановки симуляции CAPSIM.

Проверяет:
- Graceful и force остановку симуляции
- Очистку очереди событий  
- Сохранение состояния при graceful stop
- Логирование процесса остановки
- Обработку ошибок
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

from capsim.engine.simulation_engine import SimulationEngine
from capsim.cli.stop_simulation import stop_simulation_cli, _graceful_stop_simulation, _force_stop_simulation
from capsim.db.models import SimulationRun


@pytest.fixture
def mock_db_repo():
    """Mock database repository."""
    repo = AsyncMock()
    
    # Mock simulation run
    simulation_run = MagicMock()
    simulation_run.run_id = uuid4()
    simulation_run.status = "RUNNING"
    simulation_run.num_agents = 100
    simulation_run.duration_days = 1
    simulation_run.created_at = "2024-01-01T00:00:00Z"
    
    repo.get_active_simulations.return_value = [simulation_run]
    repo.get_simulation_run.return_value = simulation_run
    repo.update_simulation_status.return_value = None
    repo.clear_future_events.return_value = 50  # 50 events cleared
    repo.force_complete_simulation.return_value = None
    repo.close.return_value = None
    
    return repo


@pytest.fixture
def mock_engine(mock_db_repo):
    """Mock simulation engine."""
    engine = SimulationEngine(mock_db_repo)
    engine.simulation_id = uuid4()
    engine.current_time = 120.5  # 2 hours 30 minutes in simulation
    engine._running = True
    
    # Add some events to queue
    for i in range(10):
        engine.event_queue.append(MagicMock())
        
    # Add some batch updates
    for i in range(5):
        engine._batch_updates.append({
            "person_id": str(uuid4()),
            "attribute": "energy_level", 
            "old_value": 4.0,
            "new_value": 3.5
        })
        
    return engine


class TestSimulationEngineStopMethods:
    """Тесты методов остановки в SimulationEngine."""
    
    def test_clear_event_queue(self, mock_engine):
        """Тест очистки очереди событий."""
        initial_queue_size = len(mock_engine.event_queue)
        assert initial_queue_size == 10
        
        cleared_count = mock_engine.clear_event_queue()
        
        assert cleared_count == 10
        assert len(mock_engine.event_queue) == 0
        
    @pytest.mark.asyncio
    async def test_graceful_stop_simulation(self, mock_engine):
        """Тест graceful остановки симуляции."""
        initial_batch_size = len(mock_engine._batch_updates)
        initial_queue_size = len(mock_engine.event_queue)
        
        await mock_engine.stop_simulation(method="graceful")
        
        # Проверяем что симуляция остановлена
        assert not mock_engine._running
        
        # Проверяем что очередь очищена
        assert len(mock_engine.event_queue) == 0
        
        # Проверяем что batch был выполнен (mock _batch_commit_states)
        mock_engine.db_repo.update_simulation_status.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_force_stop_simulation(self, mock_engine):
        """Тест принудительной остановки симуляции."""
        initial_queue_size = len(mock_engine.event_queue)
        
        await mock_engine.stop_simulation(method="force")
        
        # Проверяем что симуляция остановлена
        assert not mock_engine._running
        
        # Проверяем что очередь очищена
        assert len(mock_engine.event_queue) == 0
        
        # Проверяем что вызван force_complete_simulation
        mock_engine.db_repo.force_complete_simulation.assert_called_once_with(mock_engine.simulation_id)


class TestCLIStopSimulation:
    """Тесты CLI команды остановки симуляции."""
    
    @pytest.mark.asyncio
    async def test_stop_single_active_simulation(self, mock_db_repo):
        """Тест остановки единственной активной симуляции."""
        
        with patch('capsim.cli.stop_simulation.DatabaseRepository', return_value=mock_db_repo):
            await stop_simulation_cli(
                simulation_id=None,  # Автовыбор
                force=False,
                timeout_seconds=30
            )
            
        # Проверяем что была найдена активная симуляция
        mock_db_repo.get_active_simulations.assert_called_once()
        
        # Проверяем что статус был обновлен
        mock_db_repo.update_simulation_status.assert_called()
        
        # Проверяем что были очищены future events
        mock_db_repo.clear_future_events.assert_called()
        
    @pytest.mark.asyncio
    async def test_stop_specific_simulation(self, mock_db_repo):
        """Тест остановки конкретной симуляции по ID."""
        simulation_id = str(uuid4())
        
        with patch('capsim.cli.stop_simulation.DatabaseRepository', return_value=mock_db_repo):
            await stop_simulation_cli(
                simulation_id=simulation_id,
                force=False,
                timeout_seconds=30
            )
            
        # Проверяем что была запрошена конкретная симуляция
        mock_db_repo.get_simulation_run.assert_called_with(UUID(simulation_id))
        
    @pytest.mark.asyncio
    async def test_force_stop_simulation(self, mock_db_repo):
        """Тест принудительной остановки симуляции."""
        simulation_id = str(uuid4())
        
        with patch('capsim.cli.stop_simulation.DatabaseRepository', return_value=mock_db_repo):
            await stop_simulation_cli(
                simulation_id=simulation_id,
                force=True,
                timeout_seconds=30
            )
            
        # В force режиме должен быть вызван force_complete_simulation
        mock_db_repo.force_complete_simulation.assert_called()
        
    @pytest.mark.asyncio
    async def test_no_active_simulations(self, mock_db_repo):
        """Тест когда нет активных симуляций."""
        mock_db_repo.get_active_simulations.return_value = []
        
        with patch('capsim.cli.stop_simulation.DatabaseRepository', return_value=mock_db_repo):
            await stop_simulation_cli(
                simulation_id=None,
                force=False,
                timeout_seconds=30
            )
            
        # Не должно быть вызовов остановки
        mock_db_repo.update_simulation_status.assert_not_called()
        mock_db_repo.clear_future_events.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_multiple_active_simulations_without_id(self, mock_db_repo):
        """Тест когда найдено несколько активных симуляций без указания ID."""
        # Создаем несколько активных симуляций
        sim1 = MagicMock()
        sim1.run_id = uuid4()
        sim1.status = "RUNNING"
        sim1.num_agents = 100
        
        sim2 = MagicMock()  
        sim2.run_id = uuid4()
        sim2.status = "RUNNING"
        sim2.num_agents = 200
        
        mock_db_repo.get_active_simulations.return_value = [sim1, sim2]
        
        with patch('capsim.cli.stop_simulation.DatabaseRepository', return_value=mock_db_repo):
            await stop_simulation_cli(
                simulation_id=None,
                force=False,
                timeout_seconds=30
            )
            
        # Не должно быть попыток остановки без явного ID
        mock_db_repo.update_simulation_status.assert_not_called()


class TestGracefulStop:
    """Тесты graceful остановки."""
    
    @pytest.mark.asyncio
    async def test_graceful_stop_success(self, mock_db_repo):
        """Тест успешной graceful остановки."""
        simulation_id = uuid4()
        
        await _graceful_stop_simulation(mock_db_repo, simulation_id, timeout_seconds=30)
        
        # Проверяем последовательность вызовов
        calls = mock_db_repo.method_calls
        
        # Должен быть вызван update_simulation_status с "STOPPING"
        assert any("update_simulation_status" in str(call) and "STOPPING" in str(call) for call in calls)
        
        # Должна быть очистка future events
        mock_db_repo.clear_future_events.assert_called()
        
        # Финальное обновление статуса
        assert any("update_simulation_status" in str(call) and "STOPPED" in str(call) for call in calls)
        
    @pytest.mark.asyncio 
    async def test_graceful_stop_with_timeout(self, mock_db_repo):
        """Тест graceful остановки с таймаутом."""
        simulation_id = uuid4()
        
        # Имитируем долгую операцию с помощью side_effect
        async def slow_operation(*args, **kwargs):
            await asyncio.sleep(0.1)  # Небольшая задержка
            
        mock_db_repo.clear_future_events.side_effect = slow_operation
        
        # Запускаем с очень коротким таймаутом
        await _graceful_stop_simulation(mock_db_repo, simulation_id, timeout_seconds=1)
        
        # Операция должна завершиться (в реальности может перейти в force mode)
        mock_db_repo.clear_future_events.assert_called()


class TestForceStop:
    """Тесты принудительной остановки."""
    
    @pytest.mark.asyncio
    async def test_force_stop_success(self, mock_db_repo):
        """Тест успешной принудительной остановки."""
        simulation_id = uuid4()
        
        await _force_stop_simulation(mock_db_repo, simulation_id)
        
        # Проверяем что был вызван force_complete_simulation
        mock_db_repo.force_complete_simulation.assert_called_once_with(simulation_id)
        
        # Проверяем что была принудительная очистка событий
        mock_db_repo.clear_future_events.assert_called_with(simulation_id, force=True)
        
    @pytest.mark.asyncio
    async def test_force_stop_with_error(self, mock_db_repo):
        """Тест принудительной остановки с ошибкой."""
        simulation_id = uuid4()
        
        # Имитируем ошибку при force_complete_simulation
        mock_db_repo.force_complete_simulation.side_effect = Exception("Database error")
        
        with pytest.raises(Exception):
            await _force_stop_simulation(mock_db_repo, simulation_id)


class TestLoggingValidation:
    """Тесты логирования в процессе остановки."""
    
    @pytest.mark.asyncio
    async def test_stop_logging_events(self, mock_engine, caplog):
        """Тест что логирование содержит ключевые события."""
        
        await mock_engine.stop_simulation(method="graceful")
        
        # Проверяем что в логах есть ключевые события
        log_records = [record.message for record in caplog.records]
        log_text = " ".join(log_records)
        
        # Должны быть события начала и завершения остановки
        assert "simulation_stop_initiated" in log_text
        assert "simulation_stopped" in log_text
        assert "event_queue_cleared" in log_text
        
    def test_clear_queue_logging(self, mock_engine, caplog):
        """Тест логирования очистки очереди."""
        initial_count = len(mock_engine.event_queue)
        
        mock_engine.clear_event_queue()
        
        # Проверяем что в логах отражено количество очищенных событий
        log_records = [record.message for record in caplog.records]
        log_text = " ".join(log_records)
        
        assert "event_queue_cleared" in log_text
        assert f'"cleared_events":{initial_count}' in log_text


@pytest.mark.integration
class TestStopSimulationIntegration:
    """Интеграционные тесты CLI остановки симуляции."""
    
    @pytest.mark.asyncio
    async def test_stop_simulation_end_to_end(self, mock_db_repo):
        """Тест полного цикла остановки симуляции."""
        
        # Настройка мока для имитации реальной симуляции
        simulation_id = uuid4()
        simulation_run = MagicMock()
        simulation_run.run_id = simulation_id
        simulation_run.status = "RUNNING"
        simulation_run.num_agents = 50
        simulation_run.duration_days = 1
        simulation_run.created_at = "2024-01-01T00:00:00Z"
        
        mock_db_repo.get_active_simulations.return_value = [simulation_run]
        mock_db_repo.get_simulation_run.return_value = simulation_run
        
        # Запуск CLI команды
        with patch('capsim.cli.stop_simulation.DatabaseRepository', return_value=mock_db_repo):
            await stop_simulation_cli(
                simulation_id=str(simulation_id),
                force=False,
                timeout_seconds=30
            )
            
        # Проверяем полную последовательность операций
        mock_db_repo.get_simulation_run.assert_called_with(simulation_id)
        mock_db_repo.update_simulation_status.assert_called()
        mock_db_repo.clear_future_events.assert_called()
        mock_db_repo.close.assert_called()
        
    @pytest.mark.asyncio
    async def test_stop_with_database_error(self, mock_db_repo):
        """Тест обработки ошибок базы данных."""
        simulation_id = uuid4()
        
        # Имитируем ошибку получения симуляции
        mock_db_repo.get_simulation_run.side_effect = Exception("Database connection error")
        
        with patch('capsim.cli.stop_simulation.DatabaseRepository', return_value=mock_db_repo):
            with pytest.raises(Exception):
                await stop_simulation_cli(
                    simulation_id=str(simulation_id),
                    force=False,
                    timeout_seconds=30
                )
                
        # Проверяем что соединение закрыто даже при ошибке
        mock_db_repo.close.assert_called()