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

### **NEW: Realtime Mode Configuration**
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

## Usage Examples

### Fast Simulation (Legacy Mode)
```bash
export SIM_SPEED_FACTOR=60  # или не устанавливать (default)
python -m capsim.cli run --minutes 1440  # завершится за ~2 минуты
```

### Real-time Simulation  
```bash
export SIM_SPEED_FACTOR=1
python -m capsim.cli run --minutes 120  # займет ровно 2 часа
```

### Demo Mode (10x acceleration)
```bash
export SIM_SPEED_FACTOR=10  
python -m capsim.cli run --minutes 60  # займет 6 минут
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