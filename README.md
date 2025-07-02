# CAPSIM 2.0 - Agent-Based Social Simulation Platform

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL 15](https://img.shields.io/badge/postgresql-15-blue.svg)](https://www.postgresql.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100.0-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-compose-blue.svg)](https://docs.docker.com/compose/)

Система дискретно-событийного моделирования социальных взаимодействий между агентами различных профессий с поддержкой трендов, внешних факторов и realtime мониторинга.

## ⚡ Quick Start

```bash
# Clone repository
git clone <repository-url>
cd capsim

# Setup environment
cp .env.example .env

# Start infrastructure
docker-compose up -d

# Apply database migrations
make migrate

# Verify system health
make check-health

# Access services
# API: http://localhost:8000
# Grafana: http://localhost:3000 (admin:admin)
# Loki: http://localhost:3100
```

## 🏗 Architecture Overview

CAPSIM 2.0 построена на модульной архитектуре с центральным компонентом `SimulationEngine` и восемью взаимодействующими подсистемами:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │ SimulationEngine│    │   PostgreSQL    │
│   REST API      │◄──►│   Coordinator   │◄──►│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Grafana +     │    │   EventQueue    │    │ TrendProcessor  │
│   Loki Logs     │    │   Prioritized   │    │   Virality      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Ключевые компоненты:

- **SimulationEngine**: Центральный координатор событий и состояний
- **Person**: Агенты с 12 типами профессий и динамическими атрибутами
- **TrendProcessor**: Управление жизненным циклом трендов и виральности
- **PersonInfluence**: Обработка социального влияния между агентами
- **EventQueue**: Приоритетная очередь с 5 уровнями приоритета
- **DatabaseRepository**: Абстракция доступа к данным с batch-commit
- **ExternalFactor/God**: Источники внешних событий (погода, законы)

## 🎯 Core Features

### Agent Modeling
- **12 профессий**: Artist, Businessman, Developer, Doctor, SpiritualMentor, Teacher, ShopClerk, Worker, Politician, Blogger, Unemployed, Philosopher
- **Демографические данные**: Русские имена, пол, возраст (18-65 лет)
- **Динамические атрибуты**: financial_capability, trend_receptivity, social_status, energy_level, time_budget
- **Интересы**: 6 категорий (Economics, Wellbeing, Spirituality, Knowledge, Creativity, Society)

### Trend System
- **7 топиков трендов**: Economic, Health, Spiritual, Conspiracy, Science, Culture, Sport
- **Уровни охвата**: Low/Middle/High на основе социального статуса
- **Виральность**: Динамический расчет с учетом социального влияния
- **Архивирование**: Автоматическое удаление неактивных трендов (3+ дня)

### Event Processing
- **5 приоритетов**: LAW=1, WEATHER=2, TREND=3, AGENT_ACTION=4, SYSTEM=5
- **До 43 событий** на агента в день
- **Batch-commit**: 100 операций или 1 минута симулированного времени
- **Graceful degradation** при сбоях компонентов

### Monitoring & Observability
- **PostgreSQL мониторинг**: Прямое подключение к БД для статистики таблиц
- **Grafana дашборды**: Database counts, Real-time logs, Error tracking
- **Loki логирование**: Централизованный сбор логов всех сервисов
- **Healthchecks**: Автоматические проверки всех сервисов
- **Structured logging**: JSON-формат с trace ID

## 📊 System Capabilities

| Параметр | Значение | Описание |
|----------|----------|----------|
| **Макс. агентов** | 1,000 | На одну симуляцию |
| **Событий/день** | 43 на агента | Настраиваемая частота |
| **Event latency** | P95 < 10ms | Fast mode |
| **Realtime mode** | P95 < 100ms | С синхронизацией времени |
| **Очередь событий** | < 5,000 | Порог переполнения |
| **Batch size** | 100 операций | Или 1 мин. сим-времени |

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (для разработки)
- PostgreSQL 15+ (в контейнере)
- 4GB RAM (рекомендуется 8GB)

### Installation

1. **Настройка окружения**:
```bash
# Создание .env файла
cp .env.example .env

# Настройка паролей (опционально)
nano .env
```

2. **Запуск инфраструктуры**:
```bash
# Полный стек с мониторингом
docker-compose up -d

# Только приложение и БД
docker-compose up -d app postgres
```

3. **Инициализация базы данных**:
```bash
# Применение миграций
make migrate

# Создание тестовых агентов
python scripts/recreate_100_agents_proper.py
```

4. **Проверка системы**:
```bash
# Проверка health endpoints
make check-health

# Просмотр метрик
make metrics

# Мониторинг БД
make monitor-db
```

### First Simulation

```bash
# Создание симуляции через API
curl -X POST "http://localhost:8000/api/v1/simulations" \
  -H "Content-Type: application/json" \
  -d '{"num_agents": 100, "duration_days": 1}'

# Получение статуса
curl "http://localhost:8000/api/v1/simulations/{simulation_id}"

# Просмотр агентов
curl "http://localhost:8000/api/v1/simulations/{simulation_id}/agents"
```

## 🛠 Development

### Local Development

```bash
# Установка зависимостей
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Запуск только БД
docker-compose up -d postgres

# Локальный запуск приложения
export DATABASE_URL="postgresql://capsim_rw:password@localhost:5432/capsim_db"
python -m capsim.api.main

# Тестирование
pytest
make lint
make type-check
```

### Database Operations

```bash
# Создание новой миграции
alembic revision --autogenerate -m "description"

# Откат на предыдущую версию
alembic downgrade -1

# Прямое подключение к БД
docker exec -it capsim-postgres-1 psql -U postgres -d capsim_db

# Backup/Restore
make backup-db
make restore-db BACKUP_FILE=backup_20250624.sql
```

### Code Quality

```bash
# Линтинг и форматирование
ruff check .
ruff format .

# Типизация
mypy --strict capsim

# Тестирование
pytest --cov=capsim tests/
```

## 📈 Monitoring & Operations

### Service Health

```bash
# Общий статус системы
make check-health

# Логи в реальном времени
make compose-logs

# Проверка Loki
curl http://localhost:3100/ready
```

### Database Monitoring

```bash
# Текущий статус агентов
make monitor-db

# Проверка симуляций
SELECT run_id, status, num_agents, start_time 
FROM capsim.simulation_runs 
ORDER BY start_time DESC;

# Статистика событий
SELECT COUNT(*) as events_last_hour
FROM capsim.events 
WHERE created_at > NOW() - INTERVAL '1 hour';
```

### Grafana Dashboards

- **PostgreSQL Table Counts**: http://localhost:3000/d/pg-counts
  - Persons table count (capsim.persons)
  - Events table count (capsim.events)  
  - Trends table count (capsim.trends)

- **Events Real-time Monitoring**: http://localhost:3000/d/events-realtime
  - Real-time INSERT operations into events table
  - Detailed event parameters (event_type, agent_id, simulation_id)
  - Events INSERT rate per minute
  - Formatted event details with full context
  
- **Logs Dashboard**: http://localhost:3000/d/logs-dashboard
  - Application logs (capsim-app-1)
  - PostgreSQL logs (capsim-postgres-1)
  - Error logs across all services

### Performance Tuning

```env
# .env конфигурация для производительности
BATCH_SIZE=100                    # Размер batch-commit
SIM_SPEED_FACTOR=60              # Ускорение симуляции
DECIDE_SCORE_THRESHOLD=0.25      # Порог принятия решений
TREND_ARCHIVE_THRESHOLD_DAYS=3   # Архивирование трендов

# v1.8 Action System
POST_COOLDOWN_MIN=60             # Cooldown для постов
SELF_DEV_COOLDOWN_MIN=30         # Cooldown для саморазвития
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | - | PostgreSQL connection string |
| `LOG_LEVEL` | INFO | Logging level (DEBUG/INFO/WARN/ERROR) |
| `BATCH_SIZE` | 100 | Batch commit size |
| `SIM_SPEED_FACTOR` | 60 | Simulation speed multiplier |
| `ENABLE_METRICS` | true | Prometheus metrics export |
| `REALTIME_MODE` | false | Real-time simulation mode |
| `POST_COOLDOWN_MIN` | 60 | **v1.8** Post action cooldown (minutes) |
| `SELF_DEV_COOLDOWN_MIN` | 30 | **v1.8** Self-development cooldown (minutes) |

### Scaling Configuration

```yaml
# Horizontal scaling (будущая версия)
services:
  app:
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

### v1.8 Action Configuration

**Новая система действий** через YAML конфигурацию в `config/actions.yaml`:

```yaml
SHOP_WEIGHTS:                 # Профессиональные модификаторы покупок
  Businessman: 1.20           # +20% склонность к покупкам
  Developer: 1.00             # Базовая склонность
  Artist: 0.75                # -25% склонность к покупкам

PURCHASE:                     # Уровни покупок
  L1: { financial_capability: -0.05, energy_level: 0.20 }    # Порог: 0.05
  L2: { financial_capability: -0.50, energy_level: -0.10 }   # Порог: 0.50
  L3: { financial_capability: -2.00, social_status: 1.00 }   # Порог: 2.00
```

**Ключевые особенности v1.8**:
- Покупки L1/L2/L3 с разными финансовыми порогами
- Cooldown система для ограничения частоты действий  
- Shop weights по профессиям (независимо от темы тренда)
- Дневной лимит покупок (5 в день)

## 📚 API Documentation

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/simulations` | Создать симуляцию |
| `GET` | `/api/v1/simulations/{id}` | Получить статус |
| `POST` | `/api/v1/simulations/{id}/start` | Запустить симуляцию |
| `POST` | `/api/v1/simulations/{id}/stop` | Остановить симуляцию |
| `GET` | `/api/v1/simulations/{id}/agents` | Список агентов |
| `GET` | `/api/v1/simulations/{id}/trends` | Активные тренды |

### System Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/healthz` | Health check |
| `GET` | `/api/v1/status` | System status |

### Response Examples

```json
{
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "RUNNING",
  "num_agents": 100,
  "duration_days": 1,
  "created_at": "2025-06-24T10:00:00Z",
  "current_time": 45.5,
  "events_processed": 1250
}
```

Полная документация API: http://localhost:8000/docs

## 🔄 Migration & Upgrade

### Database Migrations

Текущие миграции:
- **0001**: Initial schema (persons, trends, events, simulation_runs)
- **0002**: Person demographics (first_name, last_name, gender, date_of_birth)
- **0003**: Interests/Topics separation (agent_interests, affinity_map)
- **0004**: Birth years fix (1960-2007) + time_budget FLOAT

### System Upgrade

```bash
# Backup перед обновлением
make backup-db

# Обновление кода
git pull origin main

# Применение новых миграций
make migrate

# Перезапуск сервисов
docker-compose down && docker-compose up -d

# Проверка после обновления
make check-health
```

## 🧪 Testing

### Unit Tests

```bash
# Запуск всех тестов
pytest

# Тесты с покрытием кода
pytest --cov=capsim --cov-report=html

# Тесты определенного компонента
pytest tests/test_simulation_engine.py
```

### Integration Tests

```bash
# Тестирование API
pytest tests/api/

# Тестирование базы данных
pytest tests/db/

# End-to-end тесты
pytest tests/e2e/
```

### Performance Tests

```bash
# Нагрузочное тестирование
pytest tests/performance/test_load.py

# Benchmark агентов
python scripts/benchmark_agents.py
```

## 🔧 Troubleshooting

### Common Issues

**База данных недоступна**:
```bash
# Проверка контейнера
docker ps | grep postgres

# Проверка логов
docker logs capsim-postgres-1

# Пересоздание контейнера
docker-compose down postgres && docker-compose up -d postgres
```

**Медленная обработка событий**:
```bash
# Проверка логов приложения
make app-logs

# Анализ статистики БД
make monitor-db
```

**Ошибки batch-commit**:
```bash
# Проверка логов приложения
make app-logs

# Мониторинг БД соединений
make monitor-db
```

### Debug Mode

```bash
# Включение debug логов
export LOG_LEVEL=DEBUG

# Запуск с подробными логами
docker-compose up -d && docker-compose logs -f app
```

## 📖 Documentation

### Technical Documentation

- **Architecture**: `docs/architecture_overview.md`
- **Database Schema**: `docs/database-schema-requirements.md`
- **API Specification**: `docs/api-specification.md`
- **DevOps Guide**: `docs/devops-requirements.md`
- **Configuration**: `docs/configuration.md`

### Decision Records (ADR)

- **ADR-0001**: Stack and Layering (`docs/adr/0001-stack-and-layering.md`)
- **ADR-0002**: Realtime Clock Architecture (`docs/adr/0002-realtime-clock.md`)

### Reports

All implementation reports and analysis are in `docs/reports/`:
- Sprint summaries
- Technical analysis
- Performance reports
- Development decisions

## 🤝 Contributing

### Development Workflow

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Run tests: `make test`
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Open Pull Request

### Code Standards

- **Python**: PEP 8, type hints, Google docstrings
- **SQL**: Lowercase with underscores
- **Git**: Conventional commits
- **Testing**: Minimum 80% coverage

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Links

- **API Documentation**: http://localhost:8000/docs
- **Monitoring Dashboard**: http://localhost:3000
- **Logs Aggregation**: http://localhost:3100
- **Technical Specification**: `docs/requirements/tech v.1.5.md`

---

**CAPSIM 2.0** - Production Ready Social Simulation Platform 🚀



