import pytest
from capsim.models.base import Person

def test_person_creation():
    person = Person(name="John Doe", age=25)
    assert person.name == "John Doe"
    assert person.age == 25
    assert person.income == 0.0
    assert person.savings == 0.0
    assert person.credit_score == 0
    assert len(person.actions_history) == 0

def test_person_validation():
    with pytest.raises(ValueError):
        Person(name="John Doe", age=-1)
    
    with pytest.raises(ValueError):
        Person(name="John Doe", age=25, income=-1000.0)
    
    with pytest.raises(ValueError):
        Person(name="John Doe", age=25, credit_score=1000)

def test_person_money_operations():
    person = Person(name="John Doe", age=25)
    
    # Test income
    person.apply_income(1000.0)
    assert person.income == 1000.0
    
    # Test savings
    person.apply_savings(500.0)
    assert person.savings == 500.0
    
    # Test can_afford
    assert person.can_afford(300.0)
    assert not person.can_afford(600.0)

def test_person_credit_score():
    person = Person(name="John Doe", age=25)
    
    # Test credit score update
    person.update_credit_score(100)
    assert person.credit_score == 100
    
    # Test credit score bounds
    person.update_credit_score(1000)  # Should cap at 850
    assert person.credit_score == 850
    
    person.update_credit_score(-1000)  # Should cap at 0 