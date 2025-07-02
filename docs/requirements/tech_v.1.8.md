# CAPSIM · Техническое задание v 1.8 (FINAL)

---

## 1 Схема данных (PostgreSQL 15)

### 1.1 Таблица `persons`

```sql
CREATE TABLE persons (
    id                  UUID         PRIMARY KEY,
    first_name          TEXT         NOT NULL,
    last_name           TEXT         NOT NULL,
    profession          TEXT         NOT NULL,
    -- mutable state
    financial_capability REAL        NOT NULL,
    trend_receptivity    REAL        NOT NULL,
    social_status        REAL        NOT NULL,
    energy_level         REAL        NOT NULL,
    time_budget          REAL        NOT NULL,
    purchases_today      SMALLINT    DEFAULT 0,
    last_post_ts         DOUBLE PRECISION,      --  unix-секунды
    last_selfdev_ts      DOUBLE PRECISION,
    last_purchase_ts     JSONB        DEFAULT '{}'::jsonb,
    simulation_id        UUID         NOT NULL
);

-- ➊  ускоряем фильтры по времени последней покупки любого уровня
CREATE INDEX idx_persons_last_purchase_ts
    ON persons USING GIN (last_purchase_ts jsonb_path_ops);

```

`*last_purchase_ts` хранит пары `"L1": 1.689e9`, `"L2": …`.
Если понадобится жёсткая колонка — добавьте миграцию.*

### 1.2 Таблица `events` (без изменений)

```sql
CREATE TABLE events (
    event_id   UUID PRIMARY KEY,
    timestamp  DOUBLE PRECISION NOT NULL,   -- сим-минуты
    event_type TEXT  NOT NULL,
    payload    JSONB NOT NULL,
    simulation_id UUID NOT NULL
);

```

---

## 2 Конфигурация действий (`config/actions.yaml`)

```yaml
# cooldowns (реальные минуты сим-времени)
COOLDOWNS:
  POST_MIN:         60
  SELF_DEV_MIN:     30

# дневные лимиты
LIMITS:
  MAX_PURCHASES_DAY: 5

# эффекты и «стоимость ресурсов»
EFFECTS:
  POST:
    time_budget:        -0.20   # 12 минут
    energy_level:       -0.50
    social_status:      +0.10
  SELF_DEV:
    time_budget:        -1.00
    energy_level:       +0.80
  PURCHASE:
    L1:
      financial_capability: -0.05     # порог = 0.05
      energy_level:          +0.20
    L2:
      financial_capability: -0.50     # порог = 0.50
      energy_level:          -0.10
      social_status:         +0.20
    L3:
      financial_capability: -2.00     # порог = 2.00
      energy_level:          -0.15
      social_status:         +1.00

# мотивация покупок по профессиям
SHOP_WEIGHTS:        # default = 1.0
  Businessman: 1.20
  Worker:      0.80
  Developer:   1.00
  Teacher:     0.90
  Doctor:      1.00
  Blogger:     1.05
  Politician:  1.15
  ShopClerk:   0.85
  Artist:      0.75
  SpiritualMentor: 0.80
  Philosopher: 0.75
  Unemployed:  0.60

```

---

## 3 Базовые константы (импортируются из `settings.py`)

| Ключ ENV | Значение по-умолчанию | Назначение |
| --- | --- | --- |
| `SIM_SPEED_FACTOR` | `60` | 1 сим-мин = 1 / 60 реальной секунды |
| `POST_COOLDOWN_MIN` | `60` | переопределяет YAML |
| `SELF_DEV_COOLDOWN_MIN` | `30` | — |

---

## 4 События и приоритеты

```python
class EventPriority(IntEnum):
    SYSTEM       = 100   # DailyResetEvent, EnergyRecoveryEvent
    AGENT_ACTION =  50   # PublishPost, Purchase, SelfDev
    LOW          =   0

```

`*timestamp` — симуляционные минуты с начала `simulation_id`;`priority` вторым ключом в очереди.*

`DailyResetEvent` генерируется движком при `current_time % 1440 == 0`.

---

## 5 Алгоритм `Person.decide_action`

```python
def decide_action(self, trend):
    now = self.engine.current_time
    actions = []

    # POST / REPLY
    if self.can_post(now):
        post_score = (
            trend.virality_score * self.trend_receptivity / 25
            * (1 + self.social_status / 10)
        )
        actions.append(("Post", post_score))

    # PURCHASE (L1/L2/L3)
    if self.can_purchase(now, "L1"):
        score = 0.3 * self.settings.shop_weight[self.profession]
        if trend and trend.topic == "Economic":
            score *= 1.2
        actions.append(("Purchase_L1", score))

    # SELF-DEV
    if self.can_self_dev(now):
        actions.append(("SelfDev", max(0.0, 1 - self.energy_level / 5)))

    # взвешенный выбор
    if not actions or not any(s for _, s in actions):
        return None
    name = random.choices([n for n, _ in actions],
                          [s for _, s in actions])[0]
    return ACTION_FACTORY[name]()

```

---

## 6 Метрики Prometheus

| Metric | Labels | Описание |
| --- | --- | --- |
| `capsim_actions_total` | `action_type`, `level`, `profession` | инкремент при каждом AgentAction |
| `capsim_agent_attribute` (Gauge) | `attribute`, `profession` | периодический snapshot P95 |

Объявить счётчики в `capsim/metrics.py`.

---

## 7 Критерии приёмки / тест-ориентир

| Категория | Минимум |
| --- | --- |
| **Unit-cover** | ≥ 90 % строк (`pytest --cov`) |
| **Performance** | ≤ 50 ms на 1 000 событий (P95, SIM_SPEED_FACTOR=60, 200 агентов) |
| **DB integrity** | `CHECK (energy_level >= 0)` не нарушается за 24 сим-часа |
| **CI** | green pipeline (pytest + pip-audit + bandit) |
| **Grafana** | дашборд *CAPSIM Overview* рендерит графики без ошибок |