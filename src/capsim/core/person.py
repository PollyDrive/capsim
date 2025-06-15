from dataclasses import dataclass
from typing import List, Optional
from uuid import UUID, uuid4

@dataclass
class Person:
    id: UUID = uuid4()
    name: str = ""
    age: int = 0
    income: float = 0.0
    savings: float = 0.0
    credit_score: int = 0
    actions_history: List['Action'] = None
    
    def __post_init__(self):
        if self.actions_history is None:
            self.actions_history = []
    
    def can_afford(self, cost: float) -> bool:
        return self.savings >= cost
    
    def apply_income(self, amount: float) -> None:
        self.income += amount
    
    def apply_savings(self, amount: float) -> None:
        self.savings += amount
    
    def update_credit_score(self, change: int) -> None:
        self.credit_score = max(0, min(850, self.credit_score + change)) 