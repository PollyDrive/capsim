"""
Тесты для системы экономического баланса CAPSIM v2.0.

Проверяет корректность работы механизмов доходов, расходов и восстановления ресурсов.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from uuid import uuid4
from datetime import date

from capsim.common.economic_balance import EconomicBalanceConfig, EconomicBalanceManager
from capsim.domain.person import Person


class TestEconomicBalanceConfig:
    """Тесты конфигурации экономического баланса."""
    
    def test_load_default_config(self):
        """Тест загрузки конфигурации по умолчанию."""
        config = EconomicBalanceConfig()
        
        assert "Unemployed" in config.income_coefficients
        assert config.income_coefficients["Unemployed"] == 0.0
        assert config.income_coefficients["Developer"] == 1.0
        
    def test_load_custom_config(self):
        """Тест загрузки пользовательской конфигурации."""
        custom_config = {
            "INCOME_COEFFICIENTS": {
                "TestProfession": 2.0
            },
            "DAILY_EXPENSES": {
                "TestProfession": 1.5
            },
            "BALANCE_SETTINGS": {
                "enable_income_system": False
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(custom_config, f)
            config_path = f.name
        
        try:
            config = EconomicBalanceConfig(config_path)
            assert config.income_coefficients["TestProfession"] == 2.0
            assert config.daily_expenses["TestProfession"] == 1.5
            assert config.balance_settings["enable_income_system"] is False
        finally:
            Path(config_path).unlink()


class TestEconomicBalanceManager:
    """Тесты менеджера экономического баланса."""
    
    @pytest.fixture
    def manager(self):
        """Создает менеджер с тестовой конфигурацией."""
        return EconomicBalanceManager()
    
    @pytest.fixture
    def test_person(self):
        """Создает тестового агента."""
        return Person(
            id=uuid4(),
            profession="Developer",
            first_name="Test",
            last_name="Person",
            gender="male",
            date_of_birth=date(1990, 1, 1),
            financial_capability=3.0,
            social_status=2.5,
            energy_level=4.0,
            time_budget=2.0,
            actions_today=5
        )
    
    def test_calculate_daily_income(self, manager, test_person):
        """Тест расчета дневного дохода."""
        income = manager.calculate_daily_income(test_person)
        
        # Базовый доход = 3.0 * 1.0 = 3.0 (Developer coefficient)
        # Бонус за статус = 3.0 * (2.5 / 5.0) = 1.5
        # Итого = 3.0 + 1.5 = 4.5
        expected_income = 3.0 + (3.0 * 2.5 / 5.0)
        assert abs(income - expected_income) < 0.01
    
    def test_calculate_daily_income_unemployed(self, manager):
        """Тест расчета дохода для безработного."""
        unemployed = Person(
            id=uuid4(),
            profession="Unemployed",
            financial_capability=1.0,
            social_status=1.0
        )
        
        income = manager.calculate_daily_income(unemployed)
        assert income == 0.0  # Безработные не получают доход
    
    def test_calculate_daily_expenses(self, manager, test_person):
        """Тест расчета ежедневных расходов."""
        expenses = manager.calculate_daily_expenses(test_person)
        
        # Developer должен тратить 2.0 согласно конфигурации
        assert expenses == 2.0
    
    def test_apply_energy_cost(self, manager, test_person):
        """Тест применения затрат энергии."""
        initial_energy = test_person.energy_level
        
        cost = manager.apply_energy_cost(test_person, "post")
        
        # Базовая трата (0.3) + трата за пост (0.2) = 0.5
        expected_cost = 0.5
        assert abs(cost - expected_cost) < 0.01
        assert test_person.energy_level == initial_energy - expected_cost
    
    def test_apply_energy_cost_minimum_zero(self, manager):
        """Тест что энергия не может стать отрицательной."""
        low_energy_person = Person(
            id=uuid4(),
            profession="Developer",
            energy_level=0.1
        )
        
        manager.apply_energy_cost(low_energy_person, "post")
        assert low_energy_person.energy_level == 0.0
    
    def test_perform_night_recovery(self, manager, test_person):
        """Тест ночного восстановления."""
        # Устанавливаем начальные значения
        test_person.time_budget = 1.0
        test_person.energy_level = 2.0
        test_person.financial_capability = 2.0
        test_person.purchases_today = 3
        test_person.actions_today = 5
        
        # Отслеживаем изменение статуса (положительное)
        manager.track_status_change(test_person, 0.5)
        
        changes = manager.perform_night_recovery(test_person)
        
        # Проверяем восстановление времени
        assert test_person.time_budget == 4.0  # Максимум для Developer
        assert "time_budget" in changes
        
        # Проверяем восстановление энергии
        assert test_person.energy_level > 2.0
        assert "energy_level" in changes
        
        # Проверяем начисление дохода (был рост статуса и достаточно действий)
        assert test_person.financial_capability > 2.0
        assert "financial_capability" in changes
        
        # Проверяем списание расходов
        assert "daily_expenses" in changes
        
        # Проверяем сброс счетчиков
        assert test_person.purchases_today == 0
        assert test_person.actions_today == 0
    
    def test_perform_night_recovery_no_income(self, manager, test_person):
        """Тест ночного восстановления без начисления дохода."""
        # Нет роста статуса или недостаточно действий
        test_person.actions_today = 1
        
        changes = manager.perform_night_recovery(test_person)
        
        # Доход не должен начисляться
        assert "financial_capability" not in changes or changes["financial_capability"] <= 0
    
    def test_track_status_change(self, manager, test_person):
        """Тест отслеживания изменений социального статуса."""
        person_id = str(test_person.id)
        
        manager.track_status_change(test_person, 0.3)
        manager.track_status_change(test_person, 0.2)
        
        # Проверяем что изменения накапливаются
        assert manager._daily_status_changes[person_id] == 0.5
    
    def test_is_night_time(self, manager):
        """Тест определения ночного времени."""
        # 02:00 (120 минут) - ночь
        assert manager.is_night_time(120.0) is True
        
        # 10:00 (600 минут) - день
        assert manager.is_night_time(600.0) is False
        
        # 07:59 (479 минут) - ночь
        assert manager.is_night_time(479.0) is True
        
        # 08:00 (480 минут) - день
        assert manager.is_night_time(480.0) is False
    
    def test_should_trigger_night_recovery(self, manager):
        """Тест определения необходимости ночного восстановления."""
        current_time = 1500.0  # Больше суток
        last_recovery = 50.0   # Давно было
        
        assert manager.should_trigger_night_recovery(current_time, last_recovery) is True
        
        # Недавно было восстановление
        recent_recovery = 1450.0
        assert manager.should_trigger_night_recovery(current_time, recent_recovery) is False


class TestEconomicBalanceIntegration:
    """Интеграционные тесты экономической модели."""
    
    def test_full_day_cycle(self):
        """Тест полного дневного цикла агента."""
        manager = EconomicBalanceManager()
        
        # Создаем агента
        agent = Person(
            id=uuid4(),
            profession="Businessman",
            financial_capability=4.0,
            social_status=3.0,
            energy_level=5.0,
            time_budget=3.0,
            actions_today=0,
            purchases_today=0
        )
        
        initial_financial = agent.financial_capability
        
        # Симулируем дневную активность
        for _ in range(5):
            # Действия тратят энергию
            manager.apply_energy_cost(agent, "post")
            agent.actions_today += 1
            
            # Отслеживаем рост статуса
            manager.track_status_change(agent, 0.1)
        
        # Ночное восстановление
        changes = manager.perform_night_recovery(agent)
        
        # Проверяем что агент получил доход
        assert agent.financial_capability > initial_financial
        
        # Проверяем что энергия восстановилась
        assert agent.energy_level > 3.0
        
        # Проверяем что время восстановилось
        assert agent.time_budget == 3.0  # Максимум для Businessman
        
        # Проверяем что счетчики сброшены
        assert agent.actions_today == 0
        assert agent.purchases_today == 0
    
    def test_profession_differentiation(self):
        """Тест дифференциации по профессиям."""
        manager = EconomicBalanceManager()
        
        # Создаем агентов разных профессий
        businessman = Person(
            id=uuid4(),
            profession="Businessman",
            financial_capability=3.0,
            social_status=2.0,
            actions_today=5
        )
        
        unemployed = Person(
            id=uuid4(),
            profession="Unemployed",
            financial_capability=3.0,
            social_status=2.0,
            actions_today=5
        )
        
        # Отслеживаем рост статуса для обоих
        manager.track_status_change(businessman, 0.5)
        manager.track_status_change(unemployed, 0.5)
        
        # Ночное восстановление
        businessman_changes = manager.perform_night_recovery(businessman)
        unemployed_changes = manager.perform_night_recovery(unemployed)
        
        # Бизнесмен должен получить доход
        businessman_income = businessman_changes.get("financial_capability", 0)
        assert businessman_income > 0
        
        # Безработный не должен получить доход
        unemployed_income = unemployed_changes.get("financial_capability", 0)
        assert unemployed_income == 0
        
        # Расходы должны отличаться
        businessman_expenses = businessman_changes.get("daily_expenses", 0)
        unemployed_expenses = unemployed_changes.get("daily_expenses", 0)
        assert businessman_expenses > unemployed_expenses
    
    def test_energy_balance(self):
        """Тест баланса энергии в течение дня."""
        manager = EconomicBalanceManager()
        
        agent = Person(
            id=uuid4(),
            profession="Developer",
            energy_level=5.0
        )
        
        # Симулируем активность в течение дня
        total_cost = 0
        for action_type in ["post", "purchase_L1", "selfdev", "post"]:
            cost = manager.apply_energy_cost(agent, action_type)
            total_cost += cost
        
        # Энергия должна уменьшиться
        assert agent.energy_level < 5.0
        assert agent.energy_level == 5.0 - total_cost
        
        # Ночное восстановление
        initial_energy = agent.energy_level
        changes = manager.perform_night_recovery(agent)
        
        # Энергия должна восстановиться
        assert agent.energy_level > initial_energy
        assert changes["energy_level"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])