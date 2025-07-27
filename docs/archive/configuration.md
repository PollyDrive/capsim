# Configuration Guide - CAPSIM 2.0

## Environment Variables

### Database Configuration
- `DATABASE_URL` - основная строка подключения к PostgreSQL
- `DATABASE_URL_RO` - read-only подключение для отчетов
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB` - параметры БД

### Simulation Configuration
- `DECIDE_SCORE_THRESHOLD=0.25` - минимальный score для действия агента
- `TREND_ARCHIVE_THRESHOLD_DAYS=3` - дни неактивности до архивирования тренда
- `BASE_RATE=43.2` - базовая частота событий на агента в день
- `BATCH_SIZE=100` - размер batch для commit операций

### **NEW: v1.8 Action Configuration**
- `POST_COOLDOWN_MIN=60` - cooldown для публикации постов (минуты)
- `SELF_DEV_COOLDOWN_MIN=30` - cooldown для саморазвития (минуты)

### **Realtime Mode Configuration**
- `SIM_SPEED_FACTOR=60` - коэффициент скорости симуляции
  - `1` = реальное время (1 сим-минута = 1 реальная минута)
  - `60` = ускорение в 60 раз (1 сим-минута = 1 реальная секунда) [DEFAULT]
  - `0.5` = замедление в 2 раза (1 сим-минута = 2 реальные минуты)

### Performance Configuration
- `BATCH_RETRY_ATTEMPTS=3` - количество повторов batch-commit
- `BATCH_RETRY_BACKOFFS=1,2,4` - секунды задержки между повторами
- `SHUTDOWN_TIMEOUT_SEC=30` - таймаут graceful shutdown
- `MAX_QUEUE_SIZE=5000` - максимальный размер очереди событий

### Cache Configuration  
- `CACHE_TTL_MIN=2880` - TTL кэша трендов (2 дня)
- `CACHE_MAX_SIZE=10000` - максимальный размер кэша

### Monitoring
- `ENABLE_METRICS=true` - включение Prometheus метрик
- `METRICS_PORT=9090` - порт для /metrics endpoint

### Logging
- `LOG_LEVEL=INFO` - уровень логирования
- `ENABLE_JSON_LOGS=true` - JSON формат логов

## YAML Configuration Files

### Actions Configuration (v1.8)

Файл `config/actions.yaml` содержит настройки для новой системы действий:

```yaml
COOLDOWNS:
  POST_MIN: 60        # Минуты между публикациями постов
  SELF_DEV_MIN: 30    # Минуты между действиями саморазвития

LIMITS:
  MAX_PURCHASES_DAY: 5  # Максимум покупок в день

EFFECTS:
  POST:
    time_budget: -0.20      # Трата времени на пост
    energy_level: -0.50     # Трата энергии на пост
    social_status: 0.10     # Прирост социального статуса
  SELF_DEV:
    time_budget: -1.00      # Трата времени на саморазвитие
    energy_level: 0.80      # Восстановление энергии
  PURCHASE:
    L1:                     # Покупки уровня L1 (threshold: 0.05)
      financial_capability: -0.05
      energy_level: 0.20
    L2:                     # Покупки уровня L2 (threshold: 0.50)
      financial_capability: -0.50
      energy_level: -0.10
      social_status: 0.20
    L3:                     # Покупки уровня L3 (threshold: 2.00)
      financial_capability: -2.00
      energy_level: -0.15
      social_status: 1.00

SHOP_WEIGHTS:             # Склонность профессий к покупкам
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

**Важные особенности:**
- ENV переменные `POST_COOLDOWN_MIN` и `SELF_DEV_COOLDOWN_MIN` переопределяют значения из YAML
- L1/L2/L3 представляют "цену" покупки - L3 доступна только при financial_capability >= 4.5
- SHOP_WEIGHTS влияют на вероятность покупок независимо от темы тренда

## Usage Examples

### Basic Setup
```bash
# Копирование конфига
cp .env.example .env

# Основные настройки
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/capsim"
export SIM_SPEED_FACTOR=60
export ENABLE_METRICS=true
```

### Action System v1.8
```python
from capsim.common.settings import action_config

# Получение cooldown
post_cooldown = action_config.cooldowns.get('POST_MIN', 60)

# Получение shop weight
weight = action_config.shop_weights.get('Developer', 1.0)

# Получение эффектов покупки
l1_effects = action_config.effects['PURCHASE']['L1']
```

### Performance Tuning
```env
# Высокая производительность
BATCH_SIZE=200
SIM_SPEED_FACTOR=120
CACHE_MAX_SIZE=20000

# Отладка
SIM_SPEED_FACTOR=1
LOG_LEVEL=DEBUG
ENABLE_JSON_LOGS=false
```

## Performance Considerations

| SIM_SPEED_FACTOR | Use Case | Expected Latency | Queue Behavior |
|------------------|----------|------------------|----------------|
| 60+ | Testing, Analysis | P95 < 10ms | Fast processing |
| 10-59 | Demo, Debug | P95 < 50ms | Moderate queue |
| 1-9 | Realtime monitor | P95 < 100ms | Real-time sync |
| <1 | Detailed analysis | P95 < 200ms | Slow sync |

## Batch Commit Timing

Batch commit occurs when EITHER condition is met:
- **Size limit**: 100 operations accumulated  
- **Time limit**: `60/SIM_SPEED_FACTOR` real seconds elapsed

Examples:
- `SIM_SPEED_FACTOR=60`: commit every 1 real second
- `SIM_SPEED_FACTOR=1`: commit every 60 real seconds  
- `SIM_SPEED_FACTOR=0.5`: commit every 120 real seconds 