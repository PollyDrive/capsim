"""
Тесты для утилит работы с временем.
"""

import pytest
from capsim.common.time_utils import convert_sim_time_to_human, is_work_hours, get_simulation_day


class TestConvertSimTimeToHuman:
    """Тесты функции convert_sim_time_to_human."""
    
    def test_simulation_start(self):
        """Тест начала симуляции (08:00)."""
        assert convert_sim_time_to_human(0) == "08:00"
    
    def test_morning_hours(self):
        """Тест утренних часов."""
        assert convert_sim_time_to_human(120) == "10:00"  # +2 часа
        assert convert_sim_time_to_human(240) == "12:00"  # +4 часа
    
    def test_evening_hours(self):
        """Тест вечерних часов."""
        assert convert_sim_time_to_human(900) == "23:00"  # +15 часов
    
    def test_midnight_transition(self):
        """Тест перехода через полночь."""
        assert convert_sim_time_to_human(960) == "00:00"  # +16 часов = полночь
    
    def test_next_day(self):
        """Тест следующего дня."""
        assert convert_sim_time_to_human(1440) == "08:00"  # +24 часа = 08:00 следующего дня
        assert convert_sim_time_to_human(2400) == "00:00"  # +40 часов = полночь второго дня


class TestIsWorkHours:
    """Тесты функции is_work_hours."""
    
    def test_work_hours_start(self):
        """Тест начала рабочего дня (08:00)."""
        assert is_work_hours(0) is True
    
    def test_work_hours_morning(self):
        """Тест утренних рабочих часов."""
        assert is_work_hours(120) is True   # 10:00
        assert is_work_hours(240) is True   # 12:00
    
    def test_work_hours_afternoon(self):
        """Тест дневных рабочих часов."""
        assert is_work_hours(360) is True   # 14:00
        assert is_work_hours(600) is True   # 18:00
    
    def test_work_hours_evening(self):
        """Тест вечерних рабочих часов."""
        assert is_work_hours(900) is True   # 23:00 - последний рабочий час
    
    def test_non_work_hours_midnight(self):
        """Тест нерабочих часов - полночь."""
        assert is_work_hours(960) is False  # 00:00
    
    def test_non_work_hours_night(self):
        """Тест нерабочих часов - ночь."""
        assert is_work_hours(1020) is False  # 01:00
        assert is_work_hours(1200) is False  # 04:00
        assert is_work_hours(1380) is False  # 07:00
    
    def test_work_hours_next_day(self):
        """Тест рабочих часов следующего дня."""
        assert is_work_hours(1440) is True   # 08:00 второго дня
        assert is_work_hours(1560) is True   # 10:00 второго дня
    
    def test_non_work_hours_next_day(self):
        """Тест нерабочих часов следующего дня."""
        assert is_work_hours(2400) is False  # 00:00 второго дня
        assert is_work_hours(2460) is False  # 01:00 второго дня
        assert is_work_hours(2820) is False  # 07:00 второго дня
    
    def test_boundary_cases(self):
        """Тест граничных случаев."""
        # Последний рабочий час
        assert is_work_hours(900) is True    # 23:00
        
        # Первый нерабочий час
        assert is_work_hours(960) is False   # 00:00
        
        # Последний нерабочий час  
        assert is_work_hours(1380) is False  # 07:00
        
        # Первый рабочий час после ночи
        assert is_work_hours(1440) is True   # 08:00


class TestGetSimulationDay:
    """Тесты функции get_simulation_day."""
    
    def test_day_zero(self):
        """Тест нулевого дня симуляции."""
        assert get_simulation_day(0) == 0      # 08:00 дня 0
        assert get_simulation_day(480) == 0    # 16:00 дня 0
    
    def test_day_transition(self):
        """Тест перехода дня в полночь."""
        assert get_simulation_day(960) == 1    # 00:00 дня 1
        assert get_simulation_day(1440) == 1   # 08:00 дня 1
    
    def test_multiple_days(self):
        """Тест нескольких дней."""
        assert get_simulation_day(2400) == 2   # 00:00 дня 2
        assert get_simulation_day(2880) == 2   # 08:00 дня 2