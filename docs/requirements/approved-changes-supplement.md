# CAPSIM 2.0: Approved Changes Supplement to Tech v.1.5

## Status: ✅ APPROVED
**Version**: 1.0  
**Last Updated**: 2025-06-24  
**Document Owner**: Tech-Lead

---

## Executive Summary

Данный документ консолидирует все архитектурные решения и требования, которые были аппрувлены в ходе разработки CAPSIM 2.0, но не вошли в исходное техническое задание v.1.5. Все изменения проверены, протестированы и внедрены в production-ready код.

---

## 1. Database Schema Enhancements ✅

### 1.1 Personal Identity Fields (CRITICAL)
```sql
-- Добавлены обязательные поля для агентов
first_name VARCHAR(100) NOT NULL    -- Русские имена (Александр, София, etc.)
last_name VARCHAR(100) NOT NULL     -- Русские фамилии с правильными окончаниями по полу
gender VARCHAR(10) NOT NULL         -- 'male' или 'female' 
date_of_birth DATE NOT NULL         -- Для расчета возраста агентов (18-65 лет)
```

**Обоснование**: Требование реалистичности агентов с демографическими характеристиками.

### 1.2 Time Budget Type Correction
```sql
-- Исправлено противоречие в документации
time_budget FLOAT NOT NULL DEFAULT 2.5  -- 0.0-5.0 (было INTEGER)
```

**Обоснование**: Унификация спецификации согласно tech v.1.5 Table 2.4.

### 1.3 Agent Interests vs Trend Topics Separation

**Agent Interests (6 categories)**: Economics, Wellbeing, Spirituality, Knowledge, Creativity, Society  
**Trend Topics (7 categories)**: Economic, Health, Spiritual, Conspiracy, Science, Culture, Sport

**Matrix Coverage**:
- agent_interests: 72 records (12 professions × 6 interests)
- affinity_map: 84 records (12 professions × 7 topics)

**Обоснование**: Устранение путаницы между интересами агентов и темами трендов.

### 1.4 Migration Versioning
Внедрена система миграций Alembic:
- **0001**: Initial schema
- **0002**: Person demographics + Agent interests
- **0003**: Interests/Topics separation
- **0004**: Birth years (1960-2007) + Time budget float

---

## 2. Architecture Decision Records (ADR) ✅

### 2.1 ADR-0002: Realtime Clock Architecture

**Problem**: Необходимость realtime наблюдения за симуляцией  
**Solution**: Clock abstraction с двумя реализациями:

```python
class Clock(Protocol):
    def now(self) -> float: ...
    async def sleep_until(self, timestamp: float) -> None: ...
```

**Implementations**:
- `SimClock` — максимальная скорость (legacy)
- `RealTimeClock` — синхронизация с wall-clock time

**Configuration**:
```env
SIM_SPEED_FACTOR=1     # реальное время
SIM_SPEED_FACTOR=60    # ускорение в 60 раз
SIM_SPEED_FACTOR=0.5   # замедление в 2 раза
```

**Impact**: Async conversion SimulationEngine, realtime monitoring capability.

---

## 3. DevOps & Infrastructure ✅

### 3.1 Enhanced Monitoring Stack

**Prometheus Metrics**:
```
capsim_http_requests_total{endpoint}
capsim_simulations_active
capsim_queue_length
capsim_event_latency_ms (histogram)
capsim_batch_commit_errors_total
```

**Grafana Dashboards**:
- CAPSIM Overview (HTTP metrics, active simulations)
- Real-time Logs (agent activity, DB operations, errors)

### 3.2 Database Monitoring Protocol

**Real-time Queries**:
```sql
-- Agent distribution per simulation
SELECT simulation_id, COUNT(*) as agents FROM capsim.persons GROUP BY simulation_id;

-- Event processing rate
SELECT COUNT(*) FROM capsim.events WHERE created_at > NOW() - INTERVAL '1 hour';

-- Simulation status
SELECT run_id, status, num_agents, start_time FROM capsim.simulation_runs ORDER BY start_time DESC;
```

### 3.3 Enhanced Docker Compose

**Improvements**:
- Healthcheck frequency: 60s interval (было frequent)
- Proper service dependencies
- Volume management for persistent data
- Log rotation configuration

**Services**: app, postgres, prometheus, grafana, loki, promtail

### 3.4 Makefile DevOps Targets

```makefile
check-health     # проверка всех сервисов
monitor-db       # мониторинг БД в реальном времени
compose-logs     # просмотр логов
clean-logs       # очистка Docker
metrics          # текущие метрики
grafana-reload   # перезагрузка Grafana
```

---

## 4. CLI & Automation ✅

### 4.1 Simulation Management Commands

```bash
# Остановка симуляции
capsim-cli simulation stop <simulation_id>

# Мониторинг статуса
capsim-cli simulation status <simulation_id>

# Batch операции
capsim-cli agents recreate --count 100 --proper-attributes
```

### 4.2 Agent Recreation Protocol

**Approved Process**:
1. Clear existing agents: `DELETE FROM capsim.persons`
2. Generate with proper demographics (Russian names, birth years 1960-2007)
3. Apply profession-specific attribute distributions
4. Validate age ranges and attribute precision

---

## 5. Configuration Management ✅

### 5.2 Configuration File Structure
```yaml
# config/default.yml
simulation:
  max_agents: 1000
  max_events_per_agent_per_day: 43
  
database:
  batch_commit_size: 100
  retry_attempts: 3
  
monitoring:
  metrics_interval: 15
  healthcheck_interval: 60
```

---

## 6. API Extensions ✅

### 6.1 Enhanced REST Endpoints

**Simulation Management**:
```
POST /api/v1/simulations
GET /api/v1/simulations/{id}
POST /api/v1/simulations/{id}/start
POST /api/v1/simulations/{id}/stop
```

**Real-time Monitoring**:
```
GET /api/v1/simulations/{id}/agents
GET /api/v1/simulations/{id}/trends
GET /api/v1/simulations/{id}/events/stream
```

**Health & Metrics**:
```
GET /healthz
GET /metrics
GET /api/v1/status
```

### 6.2 Response Format Standardization

```json
{
  "simulation_id": "uuid",
  "status": "RUNNING|STOPPED|COMPLETED",
  "num_agents": 100,
  "duration_days": 1,
  "created_at": "2025-06-24T10:00:00Z",
  "updated_at": "2025-06-24T10:05:00Z"
}
```

---

## 7. Data Quality & Validation ✅

### 7.1 Agent Demographics Standards

**Russian Names**:
- Male: ['Александр', 'Дмитрий', 'Максим', 'Сергей', ...]
- Female: ['София', 'Мария', 'Анна', 'Виктория', ...]

**Surnames with Gender Matching**:
- Male endings: Петров, Иванов, Сидоров
- Female endings: Петрова, Иванова, Сидорова

**Age Distribution**:
- Range: 18-65 years (birth years 1960-2007)
- Professional minimums: Politicians ≥35, Teachers/Doctors ≥30

### 7.2 Attribute Precision Requirements

```python
# Все числовые атрибуты округляются до 3 знаков после запятой
financial_capability = round(value, 3)  # 0.0-5.0
trend_receptivity = round(value, 3)     # 0.0-5.0
social_status = round(value, 3)         # 0.0-4.5
energy_level = round(value, 3)          # 0.0-5.0
time_budget = round(value, 3)           # 0.0-5.0
```

---

## 8. Testing & Quality Assurance ✅

### 8.1 Verification Queries

```sql
-- Demographics coverage
SELECT 
  COUNT(*) as total_agents,
  COUNT(first_name) as with_names,
  COUNT(DISTINCT gender) as gender_variants,
  MIN(EXTRACT(YEAR FROM date_of_birth)) as min_year,
  MAX(EXTRACT(YEAR FROM date_of_birth)) as max_year
FROM capsim.persons;

-- Agent interests coverage
SELECT 
  profession,
  COUNT(*) as interest_count,
  CASE WHEN COUNT(*) = 6 THEN '✅' ELSE '❌' END as status
FROM capsim.agent_interests 
GROUP BY profession;
```

### 8.2 Performance KPIs

- **Event Processing**: P95 < 10ms (fast mode), P95 < 100ms (realtime mode)
- **Batch Commit**: 100 operations or 1 simulation minute
- **Database Recording**: 1000 agents successfully written
- **API Response Time**: < 200ms for standard endpoints
- **Memory Usage**: < 2GB for 1000 agents simulation

---

## 9. Security & Operations ✅

### 9.1 Database Users

```sql
-- Read-write user for application
CREATE USER capsim_rw WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON SCHEMA capsim TO capsim_rw;

-- Read-only user for monitoring/analytics
CREATE USER capsim_ro WITH PASSWORD 'readonly_password';
GRANT SELECT ON ALL TABLES IN SCHEMA capsim TO capsim_ro;
```

### 9.2 Network Security

- **Internal Network Only**: No external authentication required
- **Service Mesh**: Docker Compose internal networking
- **Port Exposure**: Only necessary ports (5432, 8000, 9091, 3000)

---

## 10. Documentation Standards ✅

### 10.1 ADR Format (MADR)
- Title / Status / Context / Decision / Consequences
- Mermaid diagrams in separate .mmd files
- Version control for architectural decisions

### 10.2 Code Documentation
- Google-style docstrings
- Type hints (PEP 604 format)
- API documentation with OpenAPI/Swagger

---

## Implementation Status

| Component | Status | Migration | Testing |
|-----------|--------|-----------|---------|
| Database Schema | ✅ | 0004 | ✅ |
| Personal Demographics | ✅ | 0002 | ✅ |
| Interests/Topics | ✅ | 0003 | ✅ |
| Realtime Clock | 🟡 | N/A | 🟡 |
| DevOps Stack | ✅ | N/A | ✅ |
| API Extensions | ✅ | N/A | ✅ |
| CLI Tools | ✅ | N/A | ✅ |
| Monitoring | ✅ | N/A | ✅ |

**Legend**: ✅ Complete, 🟡 In Progress, ❌ Not Started

---

## Approval Chain

✅ **Database Schema**: @senior-db  
✅ **DevOps Infrastructure**: @devops  
✅ **Architecture**: @tech-lead  
✅ **Testing**: @qa  

**Final Approval**: Tech-Lead  
**Effective Date**: 2025-06-24 