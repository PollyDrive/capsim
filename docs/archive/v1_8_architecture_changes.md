# CAPSIM v1.8 Architectural Changes

## Overview

Версия 1.8 привносит значительные изменения в архитектуру CAPSIM для поддержки новой системы действий агентов, улучшенного конфигурирования и оптимизированной производительности.

## Key Changes Summary

### 1. Action System Redesign
- **Factory Pattern**: Централизованное создание и управление действиями
- **Configuration-Driven**: Все эффекты и параметры в YAML файлах
- **Purchase System**: Введены уровни покупок L1/L2/L3
- **Cooldown Management**: Временные ограничения на действия

### 2. Database Schema Extensions
- **New Person Fields**: tracking покупок и активности
- **JSONB Indexing**: оптимизация для поиска истории покупок
- **Constraint Additions**: обеспечение целостности данных

### 3. Event Priority Simplification
- **3-Level System**: SYSTEM (100), AGENT_ACTION (50), LOW (0)
- **Backward Compatibility**: сохранение старых констант

## Detailed Architecture Changes

### Configuration Layer

#### New Files:
```
config/
├── actions.yaml          # NEW: Action configuration
└── existing files...

capsim/
├── simulation/           # NEW: Simulation module
│   ├── actions/         # NEW: Action system
│   │   └── factory.py   # NEW: Action Factory
│   └── events/          # NEW: Event priorities
│       └── priorities.py # NEW: Priority system
└── common/
    └── settings.py      # UPDATED: ActionConfig integration
```

#### YAML Configuration Structure:
```yaml
COOLDOWNS:
  POST_MIN: 60
  SELF_DEV_MIN: 30

LIMITS:
  MAX_PURCHASES_DAY: 5

EFFECTS:
  POST: { time_budget: -0.20, energy_level: -0.50, social_status: 0.10 }
  SELF_DEV: { time_budget: -1.00, energy_level: 0.80 }
  PURCHASE:
    L1: { financial_capability: -0.05, energy_level: 0.20 }
    L2: { financial_capability: -0.50, energy_level: -0.10, social_status: 0.20 }
    L3: { financial_capability: -2.00, energy_level: -0.15, social_status: 1.00 }

SHOP_WEIGHTS:
  Businessman: 1.20
  Developer: 1.00
  Artist: 0.75
  # ... другие профессии
```

### Database Schema Changes

#### New Person Fields:
```sql
-- Migration: add_new_person_fields_v1_8
ALTER TABLE persons ADD COLUMN purchases_today SMALLINT DEFAULT 0;
ALTER TABLE persons ADD COLUMN last_post_ts DOUBLE PRECISION;
ALTER TABLE persons ADD COLUMN last_selfdev_ts DOUBLE PRECISION;
ALTER TABLE persons ADD COLUMN last_purchase_ts JSONB DEFAULT '{}'::jsonb;

-- Performance optimization
CREATE INDEX idx_persons_last_purchase_ts 
    ON persons USING GIN (last_purchase_ts jsonb_path_ops);

-- Data integrity
ALTER TABLE persons ADD CONSTRAINT check_purchases_today_positive 
    CHECK (purchases_today >= 0);
```

#### JSONB Structure for last_purchase_ts:
```json
{
  "L1": 1678901234.567,
  "L2": 1678902345.678,
  "L3": null
}
```

### Action System Architecture

#### Class Hierarchy:
```python
BaseAction (ABC)
├── PostAction
├── PurchaseL1Action
├── PurchaseL2Action
├── PurchaseL3Action
└── SelfDevAction
```

#### Action Factory Pattern:
```python
ACTION_FACTORY = {
    "Post": PostAction(),
    "Purchase_L1": PurchaseL1Action(),
    "Purchase_L2": PurchaseL2Action(),
    "Purchase_L3": PurchaseL3Action(),
    "SelfDev": SelfDevAction()
}
```

### Decision Algorithm v1.8

#### New Person.decide_action():
```python
def decide_action(self, trend):
    now = self.engine.current_time
    actions = []
    
    # POST evaluation
    if self.can_post(now):
        post_score = (
            trend.virality_score * self.trend_receptivity / 25
            * (1 + self.social_status / 10)
        )
        actions.append(("Post", post_score))
    
    # PURCHASE evaluation (L1/L2/L3)
    for level in ["L1", "L2", "L3"]:
        if self.can_purchase(now, level):
            score = 0.3 * action_config.shop_weights.get(self.profession, 1.0)
            if trend and trend.topic == "Economic":
                score *= 1.2
            actions.append((f"Purchase_{level}", score))
    
    # SELF_DEV evaluation
    if self.can_self_dev(now):
        score = max(0.0, 1 - self.energy_level / 5)
        actions.append(("SelfDev", score))
    
    # Weighted selection
    if not actions:
        return None
    return random.choices([n for n, _ in actions], 
                         [s for _, s in actions])[0]
```

#### Cooldown Management:
```python
def can_post(self, current_time: float) -> bool:
    if self.last_post_ts is None:
        return True
    return current_time - self.last_post_ts >= action_config.cooldowns["POST_MIN"]

def can_purchase(self, current_time: float, level: str) -> bool:
    # Check daily limit
    if self.purchases_today >= action_config.limits["MAX_PURCHASES_DAY"]:
        return False
    
    # Check financial capability
    required_capability = action_config.effects["PURCHASE"][level]["financial_capability"]
    return self.financial_capability >= abs(required_capability)
```

### Event System Updates

#### Priority Simplification:
```python
class EventPriority(IntEnum):
    SYSTEM = 100       # DailyResetEvent, EnergyRecoveryEvent
    AGENT_ACTION = 50  # PublishPost, Purchase, SelfDev  
    LOW = 0            # Низкоприоритетные события
```

#### Daily Reset Event Enhancement:
```python
class DailyResetEvent(BaseEvent):
    def execute(self, engine):
        for person in engine.persons:
            person.purchases_today = 0  # NEW: Reset daily purchase counter
        
        next_reset_time = engine.current_time + 1440
        engine.schedule_event(DailyResetEvent(next_reset_time))
```

## Performance Implications

### Positive Impact:
- **YAML Caching**: Конфигурация загружается один раз при старте
- **JSONB Indexing**: Быстрый поиск истории покупок
- **Simplified Priorities**: Меньше сравнений в очереди событий

### Monitoring Considerations:
- **New Metrics**: Покупки по уровням, cooldown violations
- **Memory Usage**: JSONB поля увеличивают размер записей
- **Index Maintenance**: GIN индексы требуют дополнительного места

## Backward Compatibility

### Preserved:
- **Existing API Endpoints**: без изменений
- **Database Schema**: только добавление полей
- **Event Priority Constants**: старые константы сохранены как aliases

### Breaking Changes:
- **Person.decide_action()**: новая сигнатура метода
- **Action System**: требуется обновление вызовов

## Migration Strategy

### Phase 1: Database & Configuration
1. Применить миграцию схемы БД
2. Создать config/actions.yaml
3. Обновить Settings модуль

### Phase 2: Action System
1. Реализовать Action Factory
2. Обновить Person.decide_action()
3. Добавить cooldown методы

### Phase 3: Event System
1. Обновить Event Priorities
2. Модифицировать DailyResetEvent
3. Тестирование интеграции

## Testing Considerations

### Unit Tests:
- Action Factory создание и выполнение
- Cooldown logic корректность
- YAML конфигурация загрузка

### Integration Tests:
- 24-часовая симуляция с новыми действиями
- Performance benchmarks
- Database constraint validation

### Edge Cases:
- Невалидная YAML конфигурация
- JSONB операции с NULL значениями
- Concurrent access to purchase counters

## Documentation Updates

### Updated Files:
- `docs/architecture_overview.md` - новая архитектура действий
- `docs/configuration.md` - YAML конфигурация
- `docs/instructions/v1_8_implementation_tasks.md` - задачи команды

### New Documentation:
- `docs/v1_8_architecture_changes.md` - этот документ
- Action system usage examples
- Migration guide

## Next Steps for Team

### @senior-db.mdc:
- Создать миграцию для новых полей Person
- Обновить ORM модели
- Добавить database constraints

### @dev-rule.mdc:
- Реализовать Action классы (execute методы)
- Обновить Person.decide_action()
- Создать cooldown management методы

### All Team:
- Обновить существующие тесты для новой системы
- Добавить performance benchmarks
- Валидация 24-часовой симуляции 

# RESOURCE MANAGEMENT
- Degradation: 0.01-0.03 каждые 2-3 минуты
- Recovery: 0.1-0.25 каждые 3-5 минут
- Hourly boost: +0.5-1.0 для уставших агентов

# ACTION THRESHOLDS  
- Post: energy 1.2-1.5, time 0.6-1.0
- SelfDev: energy 0.8-1.0, time 1.2-2.0  
- Purchase: energy 1.0-1.2, time 0.4-0.8, funds 1.0-1.5

# COOLDOWN STRATEGY
- First 1-2 actions: skip cooldown
- Subsequent actions: full cooldown enforcement 