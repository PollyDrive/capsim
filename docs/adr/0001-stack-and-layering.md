# ADR-0001: Stack and Layering

## Status
Accepted

## Context
CAPSIM 2.0 строится с нуля как агентная дискретно-событийная симуляция социальных взаимодействий. Legacy-репозиторий остается только «золотым мастером» для внешнего поведения. Необходимо выбрать технологический стэк и архитектурную схему слоев для обеспечения масштабируемости до 5000 агентов и поддержки симуляций без ограничения общей длительности.

## Decision

### Технологический стэк:
- **Python 3.11** - основной язык разработки
- **FastAPI** - REST API framework с автоматической OpenAPI документацией
- **SQLAlchemy 2.0** - ORM для работы с базой данных
- **Alembic** - система миграций базы данных  
- **PostgreSQL 15** - основная СУБД с поддержкой JSONB и партиционирования
- **Prometheus + Grafana** - мониторинг метрик производительности
- **Docker + Docker Compose** - контейнеризация и локальная разработка

### Архитектурные слои:

```
capsim/
├── api/            # FastAPI routers, REST endpoints
├── engine/         # SimulationEngine, events, DES core
├── db/            
│   ├── models.py   # SQLAlchemy models
│   └── repositories.py  # Data access layer
├── domain/         # Person, Trend, Action domain objects
├── common/         # utils, logging, configuration
├── cli/            # Command line interfaces
└── __init__.py
```

### Схема взаимодействия слоев:
- **API Layer** → **Engine Layer** → **Domain Layer** → **DB Layer**
- **API Layer** только обрабатывает HTTP запросы и валидацию
- **Engine Layer** содержит SimulationEngine и очередь событий
- **Domain Layer** содержит бизнес-логику агентов и трендов
- **DB Layer** обеспечивает persistence и data access

## Consequences

### Положительные:
- Четкое разделение ответственности между слоями
- FastAPI обеспечивает автоматическую OpenAPI документацию
- SQLAlchemy 2.0 поддерживает современные async/await паттерны
- PostgreSQL JSONB подходит для хранения exposure_history и interests
- Docker обеспечивает консистентную среду разработки

### Отрицательные:
- Python может стать узким местом при масштабировании до 5000+ агентов
- Дополнительная сложность от 4-слойной архитектуры
- Требуется дисциплина команды для соблюдения границ между слоями

### Риски:
- Производительность Python для real-time симуляций
- Сложность отладки циркулярных зависимостей между TrendProcessor и SimulationEngine

### Митигация:
- Профилирование производительности на каждом этапе
- Использование Dependency Injection для разрешения циркулярных зависимостей
- Мониторинг P95 латентности обработки событий (цель < 10ms) 