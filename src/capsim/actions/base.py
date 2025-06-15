from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from ..models.base import Person

class Action(BaseModel, ABC):
    id: UUID = Field(default_factory=uuid4)
    name: str
    cost: float
    description: str
    requirements: Dict[str, Any] = Field(default_factory=dict)
    
    @abstractmethod
    def is_available(self, person: Person) -> bool:
        """Check if action is available for the person"""
        pass
    
    @abstractmethod
    def execute(self, person: Person) -> bool:
        """Execute the action for the person"""
        pass
    
    def can_execute(self, person: Person) -> bool:
        """Check if person can execute this action"""
        return self.is_available(person) and person.can_afford(self.cost)
    
    def apply_cost(self, person: Person) -> bool:
        """Apply the cost of the action to person's savings"""
        if not person.can_afford(self.cost):
            return False
        person.update_financial_capability(-self.cost)
        return True 