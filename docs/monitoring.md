# CAPSIM 2.0 Monitoring & Logging

## Overview

CAPSIM 2.0 включает комплексную систему мониторинга и логирования на базе Prometheus, Grafana и структурированных логов в JSON формате.

## Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   CAPSIM API    │───▶│  Prometheus  │───▶│   Grafana   │
│                 │    │              │    │             │
│ • HTTP Metrics  │    │ • Scraping   │    │ • Dashboards│
│ • Event Metrics │    │ • Storage    │    │ • Alerts    │
│ • Queue Metrics │    │ • Rules      │    │ • Viz       │
│ • DB Metrics    │    │              │    │             │
└─────────────────┘    └──────────────┘    └─────────────┘
         │
         ▼
    JSON Logs
  (stdout/stderr)
```

## Logging

### Structured JSON Logging

Все логи выводятся в JSON формате для упрощения парсинга и агрегации:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "logger": "capsim.api.main",
  "message": "HTTP request completed",
  "method": "GET",
  "url": "/healthz",
  "status_code": 200,
  "duration_ms": 12.34,
  "correlation_id": "uuid-1234-5678-9abc",
  "module": "main",
  "function": "health_check",
  "line": 45
}
```

### Correlation IDs

Каждый HTTP запрос получает уникальный correlation ID для трейсинга через систему:

- Автоматически генерируется для каждого запроса
- Добавляется в заголовок ответа `X-Correlation-ID`
- Логируется во всех связанных операциях

### Configuration

```env
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
ENABLE_JSON_LOGS=true            # true/false - JSON vs text format
```

### Usage Example

```python
from structlog import get_logger
from capsim.common.logging_config import setup_logging, bind_correlation_id

# Setup logging
setup_logging(level="INFO", enable_json=True)
logger = get_logger(__name__)

# Use correlation ID
correlation_id = bind_correlation_id()
logger.info("Processing started", user_id=123, correlation_id=correlation_id)
```

## Metrics

### HTTP Request Metrics

- `capsim_http_requests_total` - Total HTTP requests by method, endpoint, status
- `capsim_http_request_duration_seconds` - Request duration histogram

### Event Processing Metrics

- `capsim_event_latency_ms` - Event processing latency (P50, P95, P99)
- `capsim_events_processed_total` - Total events processed by type and status
- `capsim_queue_length` - Current event queue length
- `capsim_queue_wait_time_seconds` - Time events spend in queue

### Batch Processing Metrics

- `capsim_batch_size` - Size of processed batches
- `capsim_batch_commit_errors_total` - Total batch commit errors
- `capsim_batch_processing_seconds` - Time to process batches

### Database Metrics

- `capsim_db_connections_active` - Active database connections
- `capsim_db_query_duration_seconds` - Database query duration by type

### Simulation Metrics

- `capsim_simulations_active` - Number of active simulations
- `capsim_agents_total` - Total number of agents by simulation
- `capsim_simulation_step_duration_seconds` - Simulation step duration

### Resource Metrics

- `capsim_memory_usage_bytes` - Memory usage by type (RSS, VMS)
- `capsim_cpu_usage_percent` - CPU usage percentage

### Using Metrics Decorators

```python
from capsim.common.metrics import track_event_processing, track_batch_processing

@track_event_processing("agent_decision")
async def process_agent_decision(agent_id: str, context: dict):
    # Processing logic here
    pass

@track_batch_processing
async def commit_batch(batch: list):
    # Batch processing logic
    pass
```

## Prometheus Configuration

### Scraping Configuration

```yaml
# monitoring/prometheus.yml
scrape_configs:
  - job_name: 'capsim-api'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

### Alert Rules

```yaml
# monitoring/alerts.yml
groups:
  - name: capsim_alerts
    rules:
      - alert: HighEventLatency
        expr: histogram_quantile(0.95, capsim_event_latency_ms) > 10
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "High event processing latency"
```

## Grafana Dashboards

### Main Dashboard: CAPSIM 2.0 Overview

- **HTTP Request Rate** - Requests per second by endpoint
- **HTTP Request Duration** - P50/P95 latency
- **Event Processing Latency** - P95 event processing time
- **Queue Length** - Current queue size
- **Active Simulations** - Number of running simulations
- **Database Connections** - Active DB connections
- **Error Rate** - HTTP error rate
- **Memory Usage** - RSS/VMS memory usage
- **CPU Usage** - CPU utilization

### Access

- URL: http://localhost:3000
- Default credentials: admin/admin
- Dashboard auto-imported at startup

## Docker Compose Integration

```yaml
services:
  app:
    environment:
      - ENABLE_METRICS=true
      - LOG_LEVEL=INFO
      - ENABLE_JSON_LOGS=true
    ports:
      - "8000:8000"  # API endpoint

  prometheus:
    ports:
      - "9091:9090"  # Prometheus UI
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/alerts.yml:/etc/prometheus/alerts.yml

  grafana:
    ports:
      - "3000:3000"  # Grafana UI
    volumes:
      - ./monitoring/grafana-datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml
      - ./monitoring/grafana/provisioning.yml:/etc/grafana/provisioning/dashboards/dashboards.yml
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
```

## Quick Start

1. **Start monitoring stack:**
   ```bash
   make dev-up
   ```

2. **Verify metrics endpoint:**
   ```bash
   curl http://localhost:8000/metrics
   ```

3. **Access Grafana:**
   - URL: http://localhost:3000
   - Login: admin/admin
   - Navigate to CAPSIM folder → CAPSIM 2.0 Overview

4. **View Prometheus:**
   - URL: http://localhost:9091
   - Query examples:
     - `rate(capsim_http_requests_total[5m])`
     - `histogram_quantile(0.95, capsim_event_latency_ms)`

## Log Aggregation

For production environments, consider adding log aggregation:

```yaml
# Future enhancement: Loki integration
services:
  loki:
    image: grafana/loki:2.9.0
    # ... configuration
```

## Alerting

### Slack Integration (Example)

```yaml
# alertmanager.yml
global:
  slack_api_url: 'YOUR_SLACK_WEBHOOK_URL'

route:
  receiver: 'capsim-alerts'

receivers:
  - name: 'capsim-alerts'
    slack_configs:
      - channel: '#capsim-alerts'
        title: 'CAPSIM Alert'
        text: '{{ range .Alerts }}{{ .Description }}{{ end }}'
```

## Performance Considerations

- **Metrics Storage**: Prometheus retention set to 200h (8+ days)
- **Scrape Interval**: 5s for API, 30s for database
- **Log Rotation**: Handled by Docker log driver
- **Resource Limits**: Set in docker-compose for all services

## Troubleshooting

### Common Issues

1. **Metrics endpoint not accessible:**
   - Check `ENABLE_METRICS=true` in environment
   - Verify app is running on correct port

2. **Grafana dashboard not loading:**
   - Check Prometheus connectivity: http://prometheus:9090
   - Verify dashboard provisioning volumes

3. **High memory usage:**
   - Monitor `capsim_memory_usage_bytes` metrics
   - Adjust batch sizes if needed

4. **Missing correlation IDs:**
   - Ensure middleware is properly configured
   - Check logging configuration

### Debug Commands

```bash
# Check metrics availability
curl -s http://localhost:8000/metrics | grep capsim

# View structured logs
docker logs capsim-app-1 | jq .

# Test Prometheus queries
curl 'http://localhost:9091/api/v1/query?query=up{job="capsim-api"}'
```

## Real-time Log Monitoring Stack

### 🎯 **Что реализовано:**

### 📊 **Real-time Log Monitoring Stack**
- **Loki**: Хранение и индексация логов
- **Promtail**: Сбор Docker логов с парсингом
- **JSON Pipeline**: Парсинг INSERT операций агентов
- **Grafana Integration**: Real-time визуализация

### 🔍 **Детальное логирование INSERT операций**
```json
{
  "operation": "INSERT",
  "table_name": "agent_actions", 
  "entity_type": "agent_action",
  "agent_id": "agent_5",
  "simulation_id": "sim_1750715895",
  "action_type": "move|interact|decide|communicate",
  "timestamp": "2025-06-23T21:58:15.016811Z"
}
```

### 🚀 **Как использовать:**

1. **Запустить демо:**
   ```bash
   curl -X POST http://localhost:8000/simulate/demo
   ```

2. **Открыть Grafana:**
   - URL: http://localhost:3000 (admin/admin)
   - Navigate: **Explore** → **Loki**

3. **Запросы для мониторинга:**
   ```logql
   # Все INSERT операции агентов
   {service_name="app"} |~ "INSERT.*agent_action"
   
   # Действия конкретного агента
   {service_name="app", entity_type="agent"} |~ "agent_1"
   
   # События симуляции
   {service_name="app", entity_type="simulation"}
   ```

4. **Смотреть в real-time** как появляются новые действия агентов!

### 📁 **Ключевые файлы:**
- `monitoring/promtail-config.yml` - Конфигурация сбора логов
- `capsim/common/db_logger.py` - Детальное логирование INSERT
- `docs/logs_realtime.md` - Полная документация
- `docker-compose.yml` - Loki + Promtail сервисы

**Результат**: Теперь каждая INSERT операция агента в БД — это структурированная лог-запись, видимая в Grafana в реальном времени! 🎉 