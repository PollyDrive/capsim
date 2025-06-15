from pydantic import BaseModel, Field, validator
from uuid import UUID, uuid4
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class Gender(str, Enum):
    MALE = "Male"
    FEMALE = "Female"

class Cluster(str, Enum):
    WORKER = "Worker"
    SOCIAL = "Social"
    SPIRITUAL = "Spiritual"
    OTHER = "Other"

class Profession(str, Enum):
    SHOP_CLERK = "ShopClerk"
    ARTISAN = "Artisan"
    DEVELOPER = "Developer"
    POLITICIAN = "Politician"
    BLOGGER = "Blogger"
    MARKETER = "Marketer"
    BUSINESSMAN = "Businessman"
    SPIRITUAL_MENTOR = "SpiritualMentor"
    PHILOSOPHER = "Philosopher"
    STUDENT = "Student"
    UNEMPLOYED = "Unemployed"
    ATHLETE = "Athlete"
    FRAUDSTER = "Fraudster"

class Action(BaseModel):
    # Forward declaration stub
    pass

class Person(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    age: int
    gender: Gender
    cluster: Cluster
    profession: Profession
    financial_capability: float
    trend_receptivity: float
    social_status: float
    energy_level: float
    time_budget: float
    actions_history: List['Action'] = Field(default_factory=list, exclude=True)
    created_at: datetime = Field(default_factory=datetime.now)
    
    @validator('age')
    def validate_age(cls, v):
        if v < 0 or v > 120:
            raise ValueError('Age must be between 0 and 120')
        return v
    
    @validator('financial_capability')
    def validate_money(cls, v):
        if v < 0:
            raise ValueError('Money values cannot be negative')
        return v
    
    def can_afford(self, cost: float) -> bool:
        return self.financial_capability >= cost
    
    def update_financial_capability(self, amount: float):
        self.financial_capability += amount

# Now that Person is defined, we can resolve the forward reference in Action
from ..actions.base import Action as ConcreteAction
Person.model_rebuild()

class SimulationConfig(BaseModel):
    initial_population: int = 100
    simulation_days: int = 365
    random_seed: Optional[int] = None
    
    @validator('initial_population', 'simulation_days')
    def validate_positive_int(cls, v):
        if v <= 0:
            raise ValueError('Value must be positive')
        return v 