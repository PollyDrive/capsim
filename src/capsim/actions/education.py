from typing import Dict, Any
from .base import Action
from ..models.base import Person

class EducationAction(Action):
    def __init__(
        self,
        level: str,
        cost: float,
        income_boost: float,
        duration_days: int,
        requirements: Dict[str, Any] = None
    ):
        super().__init__(
            name=f"Get {level} Education",
            cost=cost,
            description=f"Complete {level} education to increase income potential",
            requirements=requirements or {}
        )
        self.level = level
        self.income_boost = income_boost
        self.duration_days = duration_days
    
    def is_available(self, person: Person) -> bool:
        # Check if person doesn't already have this level of education
        return not any(
            isinstance(action, EducationAction) and action.level == self.level 
            for action in person.actions_history
        )
    
    def execute(self, person: Person) -> bool:
        if not self.can_execute(person):
            return False
            
        if not self.apply_cost(person):
            return False
            
        person.apply_income(self.income_boost)
        person.actions_history.append(self)
        return True 