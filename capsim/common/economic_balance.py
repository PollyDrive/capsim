"""
Система экономического баланса CAPSIM v2.0

Реализует механизмы доходов, расходов и восстановления ресурсов
для решения проблемы дисбаланса атрибутов агентов.
"""

import logging
import os
from typing import Dict, Optional, TYPE_CHECKING
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

if TYPE_CHECKING:
    from ..domain.person import Person

logger = logging.getLogger(__name__)


class EconomicBalanceConfig:
    """Конфигурация экономического баланса."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация конфигурации.
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "economic_balance.yaml"
        
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path: Path) -> Dict:
        """Загрузка конфигурации из YAML файла."""
        if not HAS_YAML:
            logger.warning("YAML module not available, using default economic balance config")
            return self._get_default_config()
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Economic balance config not found at {config_path}, using defaults")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading economic balance config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Конфигурация по умолчанию."""
        return {
            "INCOME_COEFFICIENTS": {
                "Unemployed": 0.0,
                "Developer": 1.0,
                "Teacher": 0.6,
                "Businessman": 1.3
            },
            "DAILY_EXPENSES": {
                "Unemployed": 0.5,
                "Developer": 2.0,
                "Teacher": 1.2,
                "Businessman": 2.5
            },
            "ENERGY_COSTS": {
                "base_activity": 0.3,
                "stress_actions": 0.5,
                "post_action": 0.2,
                "purchase_action": 0.1,
                "selfdev_action": 0.4
            },
            "NIGHT_RECOVERY": {
                "energy_bonus": 1.2,
                "financial_bonus": 1.0,
                "time_full_restore": True
            },
            "BALANCE_SETTINGS": {
                "enable_income_system": True,
                "enable_daily_expenses": True,
                "enable_energy_costs": True,
                "enable_night_recovery": True
            }
        }
    
    @property
    def income_coefficients(self) -> Dict[str, float]:
        """Коэффициенты доходов по профессиям."""
        return self.config.get("INCOME_COEFFICIENTS", {})
    
    @property
    def daily_expenses(self) -> Dict[str, float]:
        """Ежедневные расходы по профессиям."""
        return self.config.get("DAILY_EXPENSES", {})
    
    @property
    def energy_costs(self) -> Dict[str, float]:
        """Затраты энергии на действия."""
        return self.config.get("ENERGY_COSTS", {})
    
    @property
    def night_recovery(self) -> Dict:
        """Параметры ночного восстановления."""
        return self.config.get("NIGHT_RECOVERY", {})
    
    @property
    def max_time_budget(self) -> Dict[str, float]:
        """Максимальный time_budget по профессиям."""
        return self.config.get("MAX_TIME_BUDGET", {})
    
    @property
    def balance_settings(self) -> Dict[str, bool]:
        """Настройки включения/выключения систем."""
        return self.config.get("BALANCE_SETTINGS", {})


class EconomicBalanceManager:
    """Менеджер экономического баланса агентов."""
    
    def __init__(self, config: Optional[EconomicBalanceConfig] = None):
        """
        Инициализация менеджера.
        
        Args:
            config: Конфигурация экономического баланса
        """
        self.config = config or EconomicBalanceConfig()
        self._daily_status_changes = {}  # Отслеживание изменений статуса за день
        
    def calculate_daily_income(self, person: "Person") -> float:
        """
        Вычисляет дневной доход агента.
        
        Args:
            person: Агент
            
        Returns:
            Размер дохода
        """
        if not self.config.balance_settings.get("enable_income_system", True):
            return 0.0
            
        # Базовый доход = начальная финансовая способность × коэффициент профессии
        profession_coeff = self.config.income_coefficients.get(person.profession, 0.0)
        financial_capability = person.financial_capability or 0.0
        social_status = person.social_status or 0.0
        
        base_income = financial_capability * profession_coeff
        
        # Бонус за социальный статус
        status_bonus = base_income * (social_status / 5.0)
        
        total_income = base_income + status_bonus
        
        logger.debug(f"Daily income for {person.profession}: base={base_income:.2f}, "
                    f"status_bonus={status_bonus:.2f}, total={total_income:.2f}")
        
        # Записываем метрику дохода
        try:
            from .metrics import record_daily_income
            record_daily_income(person.profession, total_income)
        except ImportError:
            pass
        
        return total_income
    
    def calculate_daily_expenses(self, person: "Person") -> float:
        """
        Вычисляет ежедневные расходы агента.
        
        Args:
            person: Агент
            
        Returns:
            Размер расходов
        """
        if not self.config.balance_settings.get("enable_daily_expenses", True):
            return 0.0
            
        expenses = self.config.daily_expenses.get(person.profession, 1.0)
        
        logger.debug(f"Daily expenses for {person.profession}: {expenses:.2f}")
        
        # Записываем метрику расходов
        try:
            from .metrics import record_daily_expenses
            record_daily_expenses(person.profession, expenses)
        except ImportError:
            pass
        
        return expenses
    
    def apply_energy_cost(self, person: "Person", action_type: str) -> float:
        """
        Применяет затраты энергии за действие.
        
        Args:
            person: Агент
            action_type: Тип действия
            
        Returns:
            Размер затрат энергии
        """
        if not self.config.balance_settings.get("enable_energy_costs", True):
            return 0.0
            
        # Базовая трата за любое действие
        base_cost = self.config.energy_costs.get("base_activity", 0.3)
        
        # Дополнительные траты по типу действия
        action_cost = 0.0
        if action_type.lower() == "post":
            action_cost = self.config.energy_costs.get("post_action", 0.2)
        elif action_type.lower().startswith("purchase"):
            action_cost = self.config.energy_costs.get("purchase_action", 0.1)
        elif action_type.lower() == "selfdev":
            action_cost = self.config.energy_costs.get("selfdev_action", 0.4)
        
        total_cost = base_cost + action_cost
        
        # Применяем затраты
        current_energy = person.energy_level or 0.0
        person.energy_level = max(0.0, current_energy - total_cost)
        
        logger.debug(f"Energy cost for {action_type}: base={base_cost:.2f}, "
                    f"action={action_cost:.2f}, total={total_cost:.2f}")
        
        return total_cost
    
    def perform_night_recovery(self, person: "Person") -> Dict[str, float]:
        """
        Выполняет ночное восстановление ресурсов агента.
        
        Args:
            person: Агент
            
        Returns:
            Словарь с примененными изменениями
        """
        if not self.config.balance_settings.get("enable_night_recovery", True):
            return {}
            
        changes = {}
        
        # 1. Восстановление времени
        if self.config.night_recovery.get("time_full_restore", True):
            max_time = self.config.max_time_budget.get(person.profession, 3.0)
            old_time = person.time_budget or 0.0
            person.time_budget = max_time
            changes["time_budget"] = max_time - old_time
        
        # 2. Восстановление энергии
        energy_bonus = self.config.night_recovery.get("energy_bonus", 1.2)
        current_energy = person.energy_level or 0.0
        energy_recovery = energy_bonus * (5.0 - current_energy)
        old_energy = current_energy
        person.energy_level = min(5.0, current_energy + energy_recovery)
        changes["energy_level"] = person.energy_level - old_energy
        
        # 3. Начисление дохода (если был рост социального статуса)
        person_id = str(person.id)
        status_delta = self._daily_status_changes.get(person_id, 0.0)
        
        if status_delta > 0 and hasattr(person, 'actions_today') and person.actions_today >= 3:
            income = self.calculate_daily_income(person)
            financial_bonus = self.config.night_recovery.get("financial_bonus", 1.0)
            total_income = income * financial_bonus
            
            old_financial = person.financial_capability or 0.0
            person.financial_capability = old_financial + total_income
            changes["financial_capability"] = total_income
        
        # 4. Списание обязательных расходов
        expenses = self.calculate_daily_expenses(person)
        old_financial = person.financial_capability or 0.0
        person.financial_capability = max(0.0, old_financial - expenses)
        changes["daily_expenses"] = old_financial - person.financial_capability
        
        # 5. Сброс дневных счетчиков
        if hasattr(person, 'purchases_today'):
            person.purchases_today = 0
        if hasattr(person, 'actions_today'):
            person.actions_today = 0
        
        # Сброс отслеживания изменений статуса
        if person_id in self._daily_status_changes:
            del self._daily_status_changes[person_id]
        
        logger.info(f"Night recovery for {person.profession}: {changes}")
        
        # Записываем метрики ночного восстановления
        try:
            from .metrics import record_night_recovery
            if changes:
                if "time_budget" in changes:
                    record_night_recovery("time_budget")
                if "energy_level" in changes:
                    record_night_recovery("energy_level")
                if "financial_capability" in changes:
                    record_night_recovery("financial_capability")
        except ImportError:
            pass
        
        return changes
    
    def track_status_change(self, person: "Person", delta: float) -> None:
        """
        Отслеживает изменения социального статуса за день.
        
        Args:
            person: Агент
            delta: Изменение статуса
        """
        person_id = str(person.id)
        if person_id not in self._daily_status_changes:
            self._daily_status_changes[person_id] = 0.0
        self._daily_status_changes[person_id] += delta
        
        # Записываем метрику изменения социального статуса
        try:
            from .metrics import record_social_status_change
            change_type = "positive" if delta > 0 else "negative"
            record_social_status_change(change_type, person.profession)
        except ImportError:
            pass
    
    def is_night_time(self, current_time: float) -> bool:
        """
        Проверяет, является ли текущее время ночным.
        
        Args:
            current_time: Текущее время симуляции в минутах
            
        Returns:
            True если ночное время (00:00-08:00)
        """
        day_time = current_time % 1440  # минуты в дне
        return 0 <= day_time < 480  # 00:00 - 08:00 (8 часов = 480 минут)
    
    def should_trigger_night_recovery(self, current_time: float, last_recovery_time: float) -> bool:
        """
        Определяет, нужно ли запустить ночное восстановление.
        
        Args:
            current_time: Текущее время симуляции
            last_recovery_time: Время последнего восстановления
            
        Returns:
            True если нужно запустить восстановление
        """
        # Проверяем, прошли ли сутки с последнего восстановления
        time_diff = current_time - last_recovery_time
        return time_diff >= 1440  # 24 часа = 1440 минут


# Глобальный экземпляр менеджера
economic_balance_manager = EconomicBalanceManager()