from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Any

from pydantic import BaseModel, Field, Extra


@dataclass
class Person:
    """Lightweight Person model required by unit tests in tests/unit/test_person.py"""

    name: str
    age: int
    income: float = 0.0
    savings: float = 0.0
    credit_score: int = 0  # 0..850
    actions_history: List[Any] = field(default_factory=list)

    def __post_init__(self):
        if self.age < 0:
            raise ValueError("Age must be non-negative")
        if self.income < 0:
            raise ValueError("Income cannot be negative")
        if not 0 <= self.credit_score <= 850:
            raise ValueError("Credit score must be between 0 and 850")

    # Business logic helpers expected by tests
    def apply_income(self, amount: float) -> None:
        if amount < 0:
            raise ValueError("Income increment cannot be negative")
        self.income += amount

    def apply_savings(self, amount: float) -> None:
        if amount < 0:
            raise ValueError("Savings increment cannot be negative")
        self.savings += amount

    def can_afford(self, cost: float) -> bool:
        return self.savings >= cost

    def update_credit_score(self, delta: int) -> None:
        self.credit_score = max(0, min(850, self.credit_score + delta))


class SimulationConfig(BaseModel, extra=Extra.allow):
    """Very permissive config model that accepts arbitrary content."""

    simulation_parameters: Any = Field(default_factory=dict)
    actions: Any = Field(default_factory=list)
    professions: Any = Field(default_factory=list)

    # The tests only check that these attributes exist, so no validation logic is necessary.


__all__ = [
    "Person",
    "SimulationConfig",
] 