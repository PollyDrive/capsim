# CAPSIM v1.8 Implementation Tasks

## Overview

Реализация технических требований v1.8 разбита на задачи для каждой роли. Все изменения должны быть backward-compatible где возможно.

---

## Senior DB Developer Tasks

### 1. Schema Migration for New Fields
```sql
-- Migration: add_new_person_fields_v1_8
ALTER TABLE persons ADD COLUMN purchases_today SMALLINT DEFAULT 0;
ALTER TABLE persons ADD COLUMN last_post_ts DOUBLE PRECISION;
ALTER TABLE persons ADD COLUMN last_selfdev_ts DOUBLE PRECISION;
ALTER TABLE persons ADD COLUMN last_purchase_ts JSONB DEFAULT '{}'::jsonb;

-- Add GIN index for JSONB operations
CREATE INDEX idx_persons_last_purchase_ts 
    ON persons USING GIN (last_purchase_ts jsonb_path_ops);

-- Add constraints
ALTER TABLE persons ADD CONSTRAINT check_purchases_today_positive 
    CHECK (purchases_today >= 0);
```

### 2. Update ORM Models
- Добавить новые поля в `capsim/db/models.py` класс `Person`
- Обновить типы для SQLAlchemy:
  - `purchases_today: Mapped[int] = mapped_column(SmallInteger, default=0)`
  - `last_post_ts: Mapped[Optional[float]] = mapped_column(Double)`
  - `last_selfdev_ts: Mapped[Optional[float]] = mapped_column(Double)`
  - `last_purchase_ts: Mapped[dict] = mapped_column(JSON, default=dict)`

### 3. Database Integrity Checks
- Добавить `CHECK (energy_level >= 0)` constraint если отсутствует
- Проверить все existing constraints на совместимость

---

## Tech Lead Tasks

### 1. Configuration Architecture
```yaml
# config/actions.yaml - новая структура
COOLDOWNS:
  POST_MIN: 60
  SELF_DEV_MIN: 30

LIMITS:
  MAX_PURCHASES_DAY: 5

EFFECTS:
  POST:
    time_budget: -0.20
    energy_level: -0.50
    social_status: 0.10
  SELF_DEV:
    time_budget: -1.00
    energy_level: 0.80
  PURCHASE:
    L1:
      financial_capability: -0.05
      energy_level: 0.20
    L2:
      financial_capability: -0.50
      energy_level: -0.10
      social_status: 0.20
    L3:
      financial_capability: -2.00
      energy_level: -0.15
      social_status: 1.00

SHOP_WEIGHTS:
  Businessman: 1.20
  Worker: 0.80
  Developer: 1.00
  Teacher: 0.90
  Doctor: 1.00
  Blogger: 1.05
  Politician: 1.15
  ShopClerk: 0.85
  Artist: 0.75
  SpiritualMentor: 0.80
  Philosopher: 0.75
  Unemployed: 0.60
```

### 2. Settings Module Update
```python
# capsim/settings.py
from typing import Dict
import yaml

class ActionConfig:
    def __init__(self):
        self.cooldowns = {}
        self.limits = {}
        self.effects = {}
        self.shop_weights = {}
    
    @classmethod
    def load_from_yaml(cls, path: str):
        # Load and parse config/actions.yaml
        pass

# Global instance
action_config = ActionConfig.load_from_yaml("config/actions.yaml")
```

### 3. Action Factory Pattern
```python
# capsim/simulation/actions/factory.py
from abc import ABC, abstractmethod
from enum import Enum

class ActionType(Enum):
    POST = "Post"
    PURCHASE_L1 = "Purchase_L1"
    PURCHASE_L2 = "Purchase_L2"
    PURCHASE_L3 = "Purchase_L3"
    SELF_DEV = "SelfDev"

class BaseAction(ABC):
    @abstractmethod
    def execute(self, person, engine): pass
    
    @abstractmethod
    def can_execute(self, person, current_time): pass

ACTION_FACTORY = {
    "Post": PostAction,
    "Purchase_L1": PurchaseL1Action,
    "Purchase_L2": PurchaseL2Action, 
    "Purchase_L3": PurchaseL3Action,
    "SelfDev": SelfDevAction
}
```

### 4. Event Priority System
```python
# capsim/simulation/events/priorities.py
from enum import IntEnum

class EventPriority(IntEnum):
    SYSTEM = 100       # DailyResetEvent, EnergyRecoveryEvent
    AGENT_ACTION = 50  # PublishPost, Purchase, SelfDev  
    LOW = 0
```

---

## Architect Tasks

### 1. Person Decision Algorithm
```python
# capsim/simulation/person.py
def decide_action(self, trend):
    """Implement v1.8 decision algorithm"""
    now = self.engine.current_time
    actions = []
    
    # POST logic
    if self.can_post(now):
        post_score = (
            trend.virality_score * self.trend_receptivity / 25
            * (1 + self.social_status / 10)
        )
        actions.append(("Post", post_score))
    
    # PURCHASE logic (L1/L2/L3)
    for level in ["L1", "L2", "L3"]:
        if self.can_purchase(now, level):
            score = 0.3 * action_config.shop_weights.get(self.profession, 1.0)
            if trend and trend.topic == "Economic":
                score *= 1.2
            actions.append((f"Purchase_{level}", score))
    
    # SELF_DEV logic  
    if self.can_self_dev(now):
        score = max(0.0, 1 - self.energy_level / 5)
        actions.append(("SelfDev", score))
    
    # Weighted selection
    if not actions or not any(s for _, s in actions):
        return None
        
    name = random.choices([n for n, _ in actions], 
                         [s for _, s in actions])[0]
    return ACTION_FACTORY[name]()
```

### 2. Cooldown Management
```python
# Methods to add to Person class
def can_post(self, current_time: float) -> bool:
    if self.last_post_ts is None:
        return True
    return current_time - self.last_post_ts >= action_config.cooldowns["POST_MIN"]

def can_self_dev(self, current_time: float) -> bool:
    if self.last_selfdev_ts is None:
        return True  
    return current_time - self.last_selfdev_ts >= action_config.cooldowns["SELF_DEV_MIN"]

def can_purchase(self, current_time: float, level: str) -> bool:
    # Check daily limit
    if self.purchases_today >= action_config.limits["MAX_PURCHASES_DAY"]:
        return False
    
    # Check financial capability
    required_capability = action_config.effects["PURCHASE"][level]["financial_capability"]
    return self.financial_capability >= abs(required_capability)
```

### 3. Daily Reset Event
```python
# capsim/simulation/events/system.py
class DailyResetEvent(BaseEvent):
    def execute(self, engine):
        """Reset daily counters at midnight (every 1440 sim minutes)"""
        for person in engine.persons:
            person.purchases_today = 0
        
        # Schedule next daily reset
        next_reset_time = engine.current_time + 1440
        engine.schedule_event(DailyResetEvent(next_reset_time))
```

---

## Developer Tasks

### 1. Action Classes Implementation
```python
# capsim/simulation/actions/purchase.py
class PurchaseL1Action(BaseAction):
    def execute(self, person, engine):
        effects = action_config.effects["PURCHASE"]["L1"]
        person.apply_effects(effects)
        person.purchases_today += 1
        person.last_purchase_ts["L1"] = engine.current_time
        
        # Log metrics
        metrics.actions_total.labels(
            action_type="Purchase", 
            level="L1",
            profession=person.profession
        ).inc()

class PurchaseL2Action(BaseAction):
    # Similar implementation for L2
    pass

class PurchaseL3Action(BaseAction):  
    # Similar implementation for L3
    pass
```

### 2. Post Action Update
```python
# capsim/simulation/actions/post.py
class PostAction(BaseAction):
    def execute(self, person, engine):
        effects = action_config.effects["POST"]
        person.apply_effects(effects)
        person.last_post_ts = engine.current_time
        
        # Create post event
        event = PublishPostEvent(
            timestamp=engine.current_time,
            person_id=person.id,
            trend=engine.current_trend
        )
        engine.schedule_event(event)
```

### 3. Self Development Action
```python
# capsim/simulation/actions/selfdev.py
class SelfDevAction(BaseAction):
    def execute(self, person, engine):
        effects = action_config.effects["SELF_DEV"]
        person.apply_effects(effects)
        person.last_selfdev_ts = engine.current_time
```

---

## DevOps Tasks

### 1. Metrics Implementation
```python
# capsim/metrics.py
from prometheus_client import Counter, Gauge

# New metrics for v1.8
actions_total = Counter(
    'capsim_actions_total',
    'Total actions performed',
    ['action_type', 'level', 'profession']
)

agent_attribute = Gauge(
    'capsim_agent_attribute', 
    'Agent attribute P95 values',
    ['attribute', 'profession']  
)

def record_action(action_type: str, level: str = "", profession: str = ""):
    actions_total.labels(
        action_type=action_type,
        level=level, 
        profession=profession
    ).inc()

def update_agent_attributes(persons):
    """Update P95 metrics for all attributes"""
    by_profession = defaultdict(lambda: defaultdict(list))
    
    for person in persons:
        prof = person.profession
        by_profession[prof]['energy_level'].append(person.energy_level)
        by_profession[prof]['financial_capability'].append(person.financial_capability)
        # ... other attributes
    
    for prof, attributes in by_profession.items():
        for attr_name, values in attributes.items():
            p95_value = np.percentile(values, 95)
            agent_attribute.labels(attribute=attr_name, profession=prof).set(p95_value)
```

### 2. Performance Monitoring
```python
# capsim/monitoring/performance.py
import time
from contextlib import contextmanager

@contextmanager
def measure_performance(operation_name: str):
    start = time.time()
    yield
    duration = time.time() - start
    
    # Log if exceeds threshold
    if duration > 0.05:  # 50ms threshold
        logger.warning(f"{operation_name} took {duration:.3f}s")
```

---

## QA Tasks

### 1. Unit Tests
```python
# tests/test_v1_8_features.py
class TestV18Features:
    def test_purchase_cooldowns(self):
        """Test purchase limits and financial capability checks"""
        pass
        
    def test_daily_reset_event(self):
        """Test purchases_today reset at midnight"""
        pass
        
    def test_action_decision_algorithm(self):
        """Test weighted action selection"""
        pass
        
    def test_shop_weights_application(self):
        """Test profession-based purchase modifiers"""
        pass
        
    def test_jsonb_purchase_tracking(self):
        """Test last_purchase_ts JSONB operations"""
        pass
```

### 2. Integration Tests  
```python
# tests/integration/test_v1_8_simulation.py
def test_24_hour_simulation():
    """Run 24 sim-hours, verify no constraint violations"""
    pass

def test_performance_requirements():
    """Verify ≤50ms per 1000 events with 200 agents"""
    pass

def test_metrics_collection():
    """Verify Prometheus metrics are collected correctly"""
    pass
```

### 3. Database Integrity Tests
```python
# tests/test_database_constraints.py
def test_energy_level_constraint():
    """Verify energy_level >= 0 is maintained"""
    pass

def test_purchase_constraints():
    """Verify purchases_today constraint"""
    pass
```

---

## Migration Plan

### Phase 1: Database & Core
1. Senior DB: Schema migration
2. Tech Lead: Configuration architecture  
3. Developer: Basic action classes

### Phase 2: Logic Implementation
1. Architect: Decision algorithm
2. Developer: Complete action implementations
3. QA: Unit tests

### Phase 3: Integration & Monitoring
1. DevOps: Metrics and monitoring
2. QA: Integration tests
3. All: Performance optimization

### Phase 4: Validation
1. QA: 24-hour simulation tests
2. DevOps: Grafana dashboard updates
3. Tech Lead: Documentation

---

## Success Criteria

- [ ] Unit test coverage ≥ 90%
- [ ] Performance ≤ 50ms per 1000 events (P95)
- [ ] DB constraints maintained over 24 sim-hours
- [ ] Green CI pipeline (pytest + pip-audit + bandit)
- [ ] Grafana CAPSIM Overview dashboard functional
- [ ] All new features working with existing simulations

## Files to Create/Modify

### New Files:
- `config/actions.yaml`
- `capsim/simulation/actions/factory.py`
- `capsim/simulation/actions/purchase.py`
- `capsim/simulation/events/priorities.py`
- `capsim/monitoring/performance.py`

### Modified Files:
- `capsim/db/models.py` (Person model)
- `capsim/settings.py` (ActionConfig)
- `capsim/simulation/person.py` (decide_action)
- `capsim/metrics.py` (new metrics)
- `capsim/simulation/events/system.py` (DailyResetEvent)