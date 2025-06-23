# CAPSIM 2.0 - Real-time Logs Monitoring

## Overview

Система real-time мониторинга логов с использованием **Loki + Promtail** для отслеживания действий агентов и INSERT операций в БД в режиме реального времени.

## Architecture

```
┌─────────────┐    ┌──────────┐    ┌─────────┐    ┌──────────┐
│  CAPSIM API │───▶│ Promtail │───▶│  Loki   │───▶│ Grafana  │
│             │    │          │    │         │    │          │
│ • JSON Logs │    │ • Docker │    │ • Store │    │ • Explore│
│ • INSERT    │    │ • Parse  │    │ • Query │    │ • Visual │
│ • Agents    │    │ • Label  │    │ • Index │    │ • Alert  │
└─────────────┘    └──────────┘    └─────────┘    └──────────┘
```

## Components

### 🗂️ Loki
- **Port**: 3100
- **Function**: Log aggregation and storage
- **Config**: Default Loki configuration
- **Data**: Stored in `loki_data` volume

### 📡 Promtail
- **Function**: Log collection from Docker containers
- **Config**: `monitoring/promtail-config.yml`
- **Targets**: Containers with `logging: promtail` label
- **Pipeline**: JSON parsing, label extraction, filtering

### 📊 Database Logger
- **Module**: `capsim.common.db_logger`
- **Purpose**: Structured logging of database operations
- **Format**: JSON with detailed metadata

## Log Format

### Agent Action Log
```json
{
  "level": "INFO",
  "message": "INSERT agent_action into agent_actions",
  "timestamp": "2025-06-23T21:58:15.016811Z",
  "operation": "INSERT",
  "table_name": "agent_actions",
  "entity_type": "agent_action",
  "entity_id": "agent_5_1750715895",
  "service": "capsim-db",
  "simulation_id": "sim_1750715895",
  "data_size": 208,
  "fields": ["agent_id", "action_type", "action_timestamp", "position", "energy", "score"]
}
```

### Simulation Event Log
```json
{
  "level": "INFO", 
  "message": "INSERT simulation_event into simulation_events",
  "timestamp": "2025-06-23T21:58:15.012345Z",
  "operation": "INSERT",
  "table_name": "simulation_events",
  "entity_type": "simulation_event",
  "entity_id": "sim_1750715895_simulation_started_1750715895",
  "simulation_id": "sim_1750715895",
  "data_size": 156,
  "fields": ["simulation_id", "event_type", "event_timestamp", "agent_count", "start_time"]
}
```

## Promtail Configuration

### Docker SD Config
```yaml
scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
        filters:
          - name: label
            values: ["logging=promtail"]
```

### Pipeline Stages
1. **JSON Parsing**: Extract structured log fields
2. **SQL Parsing**: Parse INSERT operations with regex
3. **Agent Parsing**: Extract agent IDs from logs
4. **Label Assignment**: Add metadata labels

## Grafana Queries

### Basic Queries

```logql
# All INSERT operations
{service_name="app"} |~ "INSERT"

# Agent actions only  
{service_name="app"} |~ "INSERT.*agent_action"

# Specific simulation
{service_name="app", simulation_id="sim_1750715895"}

# Agent-related logs
{service_name="app", entity_type="agent"}

# Error logs
{service_name="app", level="ERROR"}
```

### Advanced Queries

```logql
# Count INSERT operations per minute
sum(count_over_time({service_name="app"} |~ "INSERT" [1m])) by (table_name)

# Agent actions by type
sum by (action_type) (count_over_time({service_name="app"} |~ "action_type" [5m]))

# Simulation events rate
rate({service_name="app", entity_type="simulation"}[5m])
```

## Demo API

### Generate Sample Data

```bash
# Generate agent actions and logs
curl -X POST http://localhost:8000/simulate/demo
```

Response:
```json
{
  "status": "demo_completed",
  "simulation_id": "sim_1750715895", 
  "agent_count": 8,
  "actions_generated": 8,
  "message": "Check Grafana logs to see real-time agent actions!"
}
```

## Real-time Monitoring

### Step-by-Step Guide

1. **Start Services**
   ```bash
   docker-compose up -d
   ```

2. **Access Grafana**
   - URL: http://localhost:3000
   - Login: admin/admin

3. **Open Log Explorer**
   - Navigate to **Explore**
   - Select **Loki** as data source

4. **Query Logs**
   ```logql
   {service_name="app"} |~ "INSERT.*agent_action"
   ```

5. **Generate Demo Data**
   ```bash
   curl -X POST http://localhost:8000/simulate/demo
   ```

6. **Watch Real-time Updates**
   - Set refresh to **5s**
   - See new INSERT operations appear instantly

## Dashboard Features

### Panels Available
- **Agent Actions Stream**: Real-time log stream
- **INSERT Operations Count**: Metrics over time
- **Active Agents**: Count of unique agents
- **Simulation Events**: Event tracking
- **Log Levels**: Distribution pie chart
- **Database Operations Timeline**: All DB ops

### Auto-refresh
- **Interval**: 5 seconds
- **Time Range**: Last 15 minutes
- **Variables**: Dynamic simulation filtering

## Docker Labels

### Required Labels
```yaml
services:
  app:
    labels:
      logging: "promtail"
      service.name: "capsim-app"
      
  postgres:
    labels:
      logging: "promtail" 
      service.name: "capsim-postgres"
```

## Environment Variables

```env
# Logging configuration
LOG_LEVEL=INFO
ENABLE_JSON_LOGS=true

# Monitoring
ENABLE_METRICS=true
```

## Troubleshooting

### Common Issues

1. **No logs in Loki**
   - Check Promtail targets: `docker-compose logs promtail`
   - Verify container labels
   - Check Loki readiness: `curl http://localhost:3100/ready`

2. **JSON parsing errors**
   - Verify log format in app logs
   - Check pipeline configuration
   - Test regex patterns

3. **Performance issues**
   - Reduce log retention in Loki
   - Limit pipeline stages
   - Increase query timeout

### Debug Commands

```bash
# Check Loki health
curl http://localhost:3100/ready

# Check Promtail targets
curl http://localhost:9080/targets

# View raw logs
docker-compose logs app | tail -20

# Test log queries
curl -G -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={service_name="app"}' \
  --data-urlencode 'limit=10'
```

## Performance Optimization

### Loki Configuration
- **Retention**: 7 days by default
- **Compression**: gzip enabled
- **Indexing**: Optimized for time-series queries

### Promtail Configuration
- **Batch Size**: 1MB maximum
- **Timeout**: 10s client timeout
- **Positions**: Tracked in `/tmp/positions.yaml`

## Use Cases

### 1. Real-time Agent Monitoring
Watch agents perform actions in real-time during simulation runs.

### 2. Database Operation Tracking
Monitor all INSERT/UPDATE/DELETE operations with full context.

### 3. Performance Analysis
Analyze log patterns to identify bottlenecks and optimization opportunities.

### 4. Debugging
Correlate application logs with database operations using correlation IDs.

### 5. Audit Trail
Maintain detailed audit trail of all system operations with timestamps.

## Integration with Metrics

### Combined Monitoring
- **Logs**: Detailed operation tracking (Loki)
- **Metrics**: Performance indicators (Prometheus)
- **Visualization**: Unified dashboards (Grafana)

### Alert Rules
```yaml
# Log-based alerts (future enhancement)
groups:
  - name: log_alerts
    rules:
      - alert: HighErrorRate
        expr: sum(rate({service_name="app", level="ERROR"}[5m])) > 0.1
        for: 2m
        annotations:
          summary: "High error rate in logs"
```

## Quick Reference

| Component | URL | Purpose |
|-----------|-----|---------|
| Loki | http://localhost:3100 | Log storage & querying |
| Promtail | http://localhost:9080 | Log collection status |
| Grafana | http://localhost:3000 | Log exploration & dashboards |
| Demo API | http://localhost:8000/simulate/demo | Generate test data |

**Start monitoring**: Generate demo data → Open Grafana Explore → Query `{service_name="app"} |~ "INSERT"` → Watch real-time updates! 🚀 