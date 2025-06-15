from typing import Dict, Any
from .base import Action
from ..models.base import Person

class WorkAction(Action):
    def __init__(
        self,
        job_title: str,
        base_salary: float,
        experience_required: int,
        requirements: Dict[str, Any] = None
    ):
        super().__init__(
            name=f"Work as {job_title}",
            cost=0.0,  # No cost to work
            description=f"Work as {job_title} to earn income",
            requirements=requirements or {}
        )
        self.job_title = job_title
        self.base_salary = base_salary
        self.experience_required = experience_required
    
    def is_available(self, person: Person) -> bool:
        # Check if person has required experience
        work_experience = sum(
            1 for action in person.actions_history 
            if isinstance(action, WorkAction)
        )
        return work_experience >= self.experience_required
    
    def execute(self, person: Person) -> bool:
        if not self.is_available(person):
            return False
            
        # Calculate salary with experience bonus
        work_experience = sum(
            1 for action in person.actions_history 
            if isinstance(action, WorkAction)
        )
        experience_bonus = 1.0 + (work_experience * 0.1)  # 10% bonus per year
        salary = self.base_salary * experience_bonus
        
        person.update_financial_capability(salary)
        person.actions_history.append(self)
        return True 