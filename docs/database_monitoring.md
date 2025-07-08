# Database Monitoring - CAPSIM 2.0

## Мониторинг записи в БД

### 1. Метрики Prometheus

#### HTTP-запросы к API
```promql
# Общее количество HTTP запросов
capsim_http_requests_total

# Запросы к healthcheck (теперь раз в минуту)
capsim_http_requests_total{endpoint="/healthz"}

# Запросы к метрикам от Prometheus
capsim_http_requests_total{endpoint="/metrics"}
```

#### Активные симуляции
```promql
# Количество активных симуляций
capsim_simulations_active

# Процент заполнения очереди событий (критический уровень > 5000)
capsim_event_queue_size / capsim_event_queue_max_size * 100
```

### 2. Проверка записи агентов в БД

#### SQL-запросы для мониторинга
```sql
-- Общее количество агентов в schema capsim
SELECT COUNT(*) as total_agents FROM capsim.persons;

-- Агенты по симуляциям
SELECT simulation_id, COUNT(*) as agent_count 
FROM capsim.persons 
GROUP BY simulation_id 
ORDER BY agent_count DESC;

-- Последние созданные агенты
SELECT simulation_id, profession, created_at 
FROM capsim.persons 
ORDER BY created_at DESC 
LIMIT 10;
```

#### Проверка по профессиям
```sql
-- Распределение агентов по профессиям
SELECT profession, COUNT(*) as count, 
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM capsim.persons 
GROUP BY profession 
ORDER BY count DESC;
```

### 3. Мониторинг событий

#### События по симуляциям
```sql
-- Количество событий по симуляциям
SELECT simulation_id, COUNT(*) as event_count
FROM capsim.events 
GROUP BY simulation_id 
ORDER BY event_count DESC;

-- События за последний час
SELECT event_type, COUNT(*) as count
FROM capsim.events 
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY event_type
ORDER BY count DESC;
```

#### Real-time мониторинг
```sql
-- Последние события (real-time)
SELECT simulation_id, agent_id, event_type, created_at
FROM capsim.events 
ORDER BY created_at DESC 
LIMIT 20;
```

### 4. Мониторинг трендов

```sql
-- Количество трендов по симуляциям
SELECT simulation_id, COUNT(*) as trend_count
FROM capsim.trends 
GROUP BY simulation_id 
ORDER BY trend_count DESC;

-- Активные тренды по топикам
SELECT topic, COUNT(*) as count,
       AVG(base_virality_score) as avg_virality
FROM capsim.trends 
GROUP BY topic 
ORDER BY count DESC;
```

### 5. Статус симуляций

```sql
-- Статус всех симуляций
SELECT run_id, status, start_time, end_time, num_agents,
       CASE 
         WHEN end_time IS NULL THEN 'RUNNING'
         ELSE 'COMPLETED'
       END as current_status
FROM capsim.simulation_runs 
ORDER BY start_time DESC;

-- Продолжительность симуляций
SELECT run_id, num_agents,
       EXTRACT(EPOCH FROM (COALESCE(end_time, NOW()) - start_time)) as duration_seconds
FROM capsim.simulation_runs 
ORDER BY start_time DESC;
```

### 6. Grafana Dashboards

#### CAPSIM Overview Dashboard
- **HTTP Request Rate**: `rate(capsim_http_requests_total[5m])`
- **Active Simulations**: `capsim_simulations_active`
- **Total Agents**: Показывает общее количество агентов в БД

#### Real-time Logs Dashboard
- **Agent Actions Stream**: Фильтрует логи по `INSERT.*agent_action`
- **Database Operations**: Мониторит `INSERT|UPDATE|DELETE` операции
- **Error Logs**: Отслеживает логи уровня ERROR

### 7. Алерты

#### Критические алерты
```yaml
# Alert: Высокая нагрузка на очередь событий
- alert: EventQueueOverload
  expr: capsim_event_queue_size > 5000
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "CAPSIM event queue overload"

# Alert: Долгое время ответа API
- alert: HighAPILatency
  expr: histogram_quantile(0.95, rate(capsim_http_request_duration_seconds_bucket[5m])) > 0.01
  for: 3m
  labels:
    severity: warning
  annotations:
    summary: "High API response time"
```

### 8. Troubleshooting

#### Если агенты не появляются в БД:
1. Проверить подключение к БД: `SELECT 1;`
2. Проверить schema: `\dn` в psql
3. Проверить активные симуляции: SQL выше
4. Проверить логи приложения: `docker logs capsim-app-1`

#### Если события не записываются:
1. Проверить структуру таблиц: `\d capsim.events`
2. Проверить ограничения БД: `SELECT * FROM information_schema.table_constraints`
3. Проверить процессы симуляции: `ps aux | grep python`

#### Healthcheck теперь раз в минуту:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
  interval: 60s  # Изменено с 10s на 60s
  timeout: 10s
  retries: 3
```

### 9. Команды для быстрой диагностики

```bash
# Проверка количества агентов
psql postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME} -c "SELECT COUNT(*) FROM capsim.persons;"

# Проверка активных симуляций
psql postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME} -c "SELECT run_id, status, num_agents FROM capsim.simulation_runs ORDER BY start_time DESC LIMIT 5;"

# Проверка последних событий
psql postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME} -c "SELECT COUNT(*) FROM capsim.events WHERE created_at > NOW() - INTERVAL '1 hour';"

# Проверка метрик Prometheus
curl -s http://localhost:8000/metrics | grep capsim_simulations_active

# Проверка статуса targets в Prometheus
curl -s http://localhost:9091/api/v1/targets | jq '.data.activeTargets[].health'
``` 