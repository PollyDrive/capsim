# CAPSIM 2.0: DevOps Requirements & Infrastructure

## Status: ✅ PRODUCTION READY
**Version**: 1.0  
**Last Updated**: 2025-06-24  
**Document Owner**: DevOps Team  

---

## Executive Summary

Данный документ консолидирует все требования к DevOps инфраструктуре CAPSIM 2.0, включая мониторинг, деплоймент, автоматизацию и операционные процедуры.

---

## 1. Container Infrastructure ✅

### 1.1 Docker Compose Stack

**Services Configuration**:
```yaml
services:
  app:
    build: .
    ports: ["8000:8000", "9090:9090"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 30s
    depends_on:
      postgres: { condition: service_healthy }

  postgres:
    image: postgres:15
    ports: ["5432:5432"]
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sh:/docker-entrypoint-initdb.d/init-db.sh:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  prometheus:
    image: prom/prometheus:v2.40.0
    ports: ["9091:9090"]
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/alerts.yml:/etc/prometheus/alerts.yml

  grafana:
    image: grafana/grafana:9.2.0
    ports: ["3000:3000"]
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana-datasources.yml:/etc/grafana/provisioning/datasources/
```

### 1.2 Health Checks & Dependencies

**Service Health Matrix**:
| Service | Health Endpoint | Interval | Dependencies |
|---------|----------------|----------|--------------|
| app | /healthz | 60s | postgres |
| postgres | pg_isready | 5s | none |
| prometheus | /-/healthy | 30s | none |
| grafana | /api/health | 30s | prometheus |

---

## 2. Monitoring & Observability ✅

### 2.1 Prometheus Metrics

**Application Metrics**:
```
capsim_http_requests_total{endpoint, method, status}
capsim_simulations_active
capsim_queue_length
capsim_event_latency_ms (histogram)
capsim_batch_commit_errors_total
capsim_agents_total{simulation_id}
capsim_trends_active{topic}
```

**System Metrics**:
```
process_cpu_seconds_total
process_memory_bytes
process_open_fds
go_memstats_*
```

### 2.2 Grafana Dashboards

**Dashboard 1: CAPSIM Overview**
- HTTP request metrics
- Active simulations count
- Queue length monitoring
- Error rate tracking

**Dashboard 2: Real-time Logs**
- Agent activity streams
- Database operation logs
- Error rate by component
- Performance bottlenecks

**Dashboard 3: Database Monitoring**
- Connection pool status
- Query performance
- Batch commit metrics
- Schema migration status

### 2.3 Alert Rules

```yaml
# monitoring/alerts.yml
groups:
  - name: capsim-alerts
    rules:
      - alert: HighEventLatency
        expr: histogram_quantile(0.95, capsim_event_latency_ms) > 10
        for: 3m
        labels:
          severity: warning
        annotations:
          description: "Event processing P95 latency > 10ms for 3 minutes"

      - alert: QueueOverflow
        expr: capsim_queue_length > 5000
        for: 1m
        labels:
          severity: critical
        annotations:
          description: "Event queue length > 5000 events"

      - alert: BatchCommitErrors
        expr: increase(capsim_batch_commit_errors_total[5m]) > 3
        for: 0m
        labels:
          severity: critical
        annotations:
          description: "Multiple batch commit errors detected"
```

---

## 3. Database Operations ✅

### 3.1 PostgreSQL Configuration

**Database Setup**:
```sql
-- Create application users
CREATE USER capsim_rw WITH PASSWORD 'secure_rw_password';
CREATE USER capsim_ro WITH PASSWORD 'secure_ro_password';

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA capsim TO capsim_rw;
GRANT SELECT ON ALL TABLES IN SCHEMA capsim TO capsim_ro;
GRANT USAGE ON SCHEMA capsim TO capsim_ro;
```

**Connection Strings**:
```env
DATABASE_URL=postgresql://capsim_rw:password@postgres:5432/capsim_db
DATABASE_URL_RO=postgresql://capsim_ro:password@postgres:5432/capsim_db
```

### 3.2 Migration Management

**Alembic Configuration**:
```bash
# Apply migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"

# Rollback migration
alembic downgrade -1
```

**Migration Versions**:
- **0001**: Initial schema (persons, trends, events, simulation_runs)
- **0002**: Person demographics (first_name, last_name, gender, date_of_birth)
- **0003**: Interests/Topics separation (agent_interests, affinity_map)
- **0004**: Birth years fix (1960-2007) + time_budget FLOAT

### 3.3 Database Monitoring

**Real-time Monitoring Queries**:
```sql
-- Agent distribution per simulation
SELECT simulation_id, COUNT(*) as agents 
FROM capsim.persons 
GROUP BY simulation_id;

-- Event processing rate (last hour)
SELECT COUNT(*) as events_last_hour
FROM capsim.events 
WHERE created_at > NOW() - INTERVAL '1 hour';

-- Simulation status overview
SELECT run_id, status, num_agents, start_time, 
       EXTRACT(EPOCH FROM (NOW() - start_time))/60 as runtime_minutes
FROM capsim.simulation_runs 
ORDER BY start_time DESC;

-- Database size monitoring
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'capsim'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 4. Automation & CLI Tools ✅

### 4.1 Makefile Targets

```makefile
# Development lifecycle
dev-up:           # Start development environment
dev-down:         # Stop development environment
dev-restart:      # Restart development environment

# Health & monitoring
check-health:     # Check all services health
monitor-db:       # Real-time database monitoring
metrics:          # Show current metrics
status:           # Show system status

# Logs & debugging
compose-logs:     # View service logs
app-logs:         # View application logs only
db-logs:          # View database logs only
tail-logs:        # Tail all logs in real-time

# Maintenance
clean-logs:       # Clean Docker logs and volumes
backup-db:        # Backup database
restore-db:       # Restore database from backup
migrate:          # Apply database migrations

# Grafana operations
grafana-reload:   # Reload Grafana configuration
grafana-import:   # Import dashboards
```

### 4.2 Health Check Commands

```bash
# Service health verification
make check-health

# Output format:
# ✅ API: http://localhost:8000/healthz → 200 OK
# ✅ Prometheus: http://localhost:9091/-/healthy → 200 OK
# ✅ Grafana: http://localhost:3000/api/health → 200 OK
# ✅ Database: PostgreSQL responsive
```

### 4.3 Database Administration

```bash
# Real-time monitoring
make monitor-db

# Manual queries
docker exec -it capsim-postgres-1 psql -U postgres -d capsim_db

# Backup operations
make backup-db DATE=$(date +%Y%m%d)
make restore-db BACKUP_FILE=backup_20250624.sql
```

---

## 5. Configuration Management ✅

### 5.1 Environment Variables

**Core Configuration**:
```env
# Application
LOG_LEVEL=INFO
ENABLE_JSON_LOGS=true
ENABLE_METRICS=true

# Database
POSTGRES_DB=capsim_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_postgres_password
CAPSIM_RW_PASSWORD=secure_rw_password
CAPSIM_RO_PASSWORD=secure_ro_password

# Performance
BATCH_SIZE=100
DECIDE_SCORE_THRESHOLD=0.25
TREND_ARCHIVE_THRESHOLD_DAYS=3
BASE_RATE=86.4

# Monitoring
GRAFANA_PASSWORD=secure_grafana_password
```

**Realtime Configuration**:
```env
# Clock Management
SIM_SPEED_FACTOR=60
REALTIME_MODE=false

# Performance Tuning
SHUTDOWN_TIMEOUT_SEC=30
CACHE_TTL_MIN=2880
CACHE_MAX_SIZE=10000
BATCH_RETRY_ATTEMPTS=3
BATCH_RETRY_BACKOFFS=1,2,4
```

### 5.2 Configuration Files

**Prometheus Config** (`monitoring/prometheus.yml`):
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alerts.yml"

scrape_configs:
  - job_name: 'capsim-api'
    static_configs:
      - targets: ['app:9090']
    scrape_interval: 15s
    metrics_path: /metrics
```

**Grafana Datasources** (`monitoring/grafana-datasources.yml`):
```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
  - name: PostgreSQL
    type: postgres
    url: postgres:5432
    database: capsim_db
    user: capsim_ro
    secureJsonData:
      password: secure_ro_password
```

---

## 6. Log Management ✅

### 6.1 Log Format Standards

**JSON Log Format**:
```json
{
  "ts": "2025-06-24T14:00:00Z",
  "level": "INFO",
  "sim_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_id": "event-1234",
  "phase": "PROCESS",
  "duration_ms": 7,
  "msg": "PublishPost processed successfully"
}
```

**Log Levels**:
- **CRITICAL**: System failures requiring immediate attention
- **ERROR**: Component errors with recovery capability
- **WARN**: Performance degradation or unusual conditions
- **INFO**: Normal operation events and state changes
- **DEBUG**: Detailed debugging information (dev only)

### 6.2 Log Aggregation

**Loki Configuration**:
```yaml
# monitoring/loki-config.yml
auth_enabled: false
server:
  http_listen_port: 3100
ingester:
  lifecycler:
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h
```

**Promtail Configuration**:
```yaml
# monitoring/promtail-config.yml
server:
  http_listen_port: 9080
positions:
  filename: /tmp/positions.yaml
clients:
  - url: http://loki:3100/loki/api/v1/push
scrape_configs:
  - job_name: containers
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
    relabel_configs:
      - source_labels: [__meta_docker_container_label_logging]
        target_label: job
        regex: promtail
      - source_labels: [__meta_docker_container_label_service_name]
        target_label: service
```

---

## 7. Security & Network ✅

### 7.1 Network Security

**Docker Network Configuration**:
```yaml
networks:
  default:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

**Port Exposure Policy**:
- **8000**: Application API (external)
- **5432**: PostgreSQL (internal/external for dev)
- **9091**: Prometheus (external for monitoring)
- **3000**: Grafana (external for dashboards)
- **3100**: Loki (internal only)

### 7.2 Security Considerations

**Database Security**:
- Separate RW/RO users with minimal privileges
- Password-based authentication
- Connection limits per user
- Query timeout protection

**Application Security**:
- No external authentication (trusted network only)
- Internal service mesh communication
- Rate limiting at infrastructure level
- Input validation on all endpoints

### 7.3 Backup & Recovery

**Backup Strategy**:
```bash
# Daily automated backup
docker exec capsim-postgres-1 pg_dump -U postgres capsim_db > backup_$(date +%Y%m%d).sql

# Retention policy: 7 daily, 4 weekly, 12 monthly
find ./backups -name "backup_*.sql" -mtime +7 -delete
```

**Recovery Procedures**:
```bash
# Database recovery
docker exec -i capsim-postgres-1 psql -U postgres -d capsim_db < backup_20250624.sql

# Service recovery
docker-compose down && docker-compose up -d
make check-health
```

---

## 8. Performance & Scaling ✅

### 8.1 Performance KPIs

**Target Metrics**:
- **API Response Time**: P95 < 200ms
- **Event Processing**: P95 < 10ms (fast mode), P95 < 100ms (realtime mode)
- **Database Query Time**: P95 < 50ms
- **Batch Commit**: 100 operations or 1 simulation minute
- **Memory Usage**: < 2GB for 1000 agents
- **CPU Usage**: < 80% during normal operations

### 8.2 Scaling Configuration

**Horizontal Scaling Readiness**:
```yaml
# Future multi-instance support
app:
  deploy:
    replicas: 3
    update_config:
      parallelism: 1
      delay: 10s
  environment:
    - INSTANCE_ID={{.Task.Slot}}
```

**Database Connection Pooling**:
```env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

### 8.3 Resource Limits

**Container Resource Limits**:
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
  
  postgres:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 2G
          cpus: '1.0'
```

---

## 9. Deployment & CI/CD ✅

### 9.1 CI/CD Pipeline

**GitHub Actions Workflow**:
```yaml
name: CAPSIM CI/CD
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Lint with ruff
        run: ruff check .
      - name: Type check with mypy
        run: mypy --strict capsim
      - name: Run tests
        run: pytest
      - name: Build Docker image
        run: docker build -t capsim:${{ github.sha }} .
```

### 9.2 Deployment Strategies

**Development Deployment**:
```bash
# Local development
cp .env.example .env
docker-compose up -d
make migrate
make check-health
```

**Production Deployment**:
```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d
make migrate
make backup-db
make check-health
```

### 9.3 Rollback Procedures

**Quick Rollback**:
```bash
# Service rollback
docker-compose down
docker-compose up -d --force-recreate

# Database rollback
make restore-db BACKUP_FILE=backup_$(date -d yesterday +%Y%m%d).sql
```

---

## 10. Operational Procedures ✅

### 10.1 Startup Procedures

**System Startup Checklist**:
1. ✅ Start PostgreSQL container
2. ✅ Wait for database health check
3. ✅ Apply pending migrations
4. ✅ Start application container
5. ✅ Start monitoring stack (Prometheus, Grafana)
6. ✅ Verify all health checks
7. ✅ Validate metrics collection

### 10.2 Shutdown Procedures

**Graceful Shutdown**:
```bash
# SIGTERM handling with 30s timeout
SHUTDOWN_TIMEOUT_SEC=30

# Shutdown sequence:
# 1. Stop accepting new requests
# 2. Finish processing current events
# 3. Flush pending batch commits
# 4. Close database connections
# 5. Exit application
```

### 10.3 Maintenance Windows

**Weekly Maintenance Tasks**:
- Database vacuum and analyze
- Log rotation and cleanup
- Metrics retention cleanup
- Backup verification
- Performance review

**Monthly Maintenance Tasks**:
- Security updates
- Dependency updates
- Capacity planning review
- Disaster recovery testing

---

## Implementation Checklist

### ✅ Completed
- [x] Docker Compose infrastructure
- [x] Prometheus metrics collection
- [x] Grafana dashboards
- [x] Database monitoring
- [x] Health checks
- [x] Log aggregation
- [x] Backup procedures
- [x] CLI automation tools
- [x] Alert rules
- [x] Documentation

### 🟡 In Progress
- [ ] Multi-instance scaling
- [ ] Advanced alerting
- [ ] Automated testing
- [ ] Performance profiling

### ❌ Planned
- [ ] Kubernetes migration
- [ ] External monitoring integration
- [ ] Advanced security features
- [ ] Automated capacity scaling

---

**DevOps Team Sign-off**: ✅  
**Production Readiness**: ✅  
**Monitoring Coverage**: ✅  
**Documentation Complete**: ✅ 