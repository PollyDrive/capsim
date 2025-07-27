# CAPSIM 2.0 - Консолидированная архитектурная документация

## Обзор системы

CAPSIM 2.0 - это агентная дискретно-событийная симуляция социальных взаимодействий, построенная с нуля для поддержки до 5000 агентов с возможностью real-time мониторинга и анализа.

## Архитектурные принципы

### Технологический стек
- **Python 3.11** - основной язык разработки
- **FastAPI** - REST API framework с автоматической OpenAPI документацией
- **SQLAlchemy 2.0** - ORM с async поддержкой
- **PostgreSQL 15** - основная СУБД с JSONB и партиционированием
- **Alembic** - система миграций базы данных
- **Prometheus + Grafana** - мониторинг и метрики
- **Docker + Docker Compose** - контейнеризация

### Архитектурные слои

```
capsim/
├── api/                    # FastAPI routers, REST endpoints
├── engine/                 # SimulationEngine, events, DES core
├── db/                     
│   ├── models.py          # SQLAlchemy models
│   └── repositories.py    # Data access layer
├── domain/                # Person, Trend, Action domain objects
├── common/                # utils, logging, configuration, time_utils
├── cli/                   # Command line interfaces
└── simulation/            # Action system v1.8
    ├── actions/           # Action Factory Pattern
    └── events/            # Event priorities and processing
```

### Схема взаимодействия слоев
**API Layer** → **Engine Layer** → **Domain Layer** → **DB Layer**

- **API Layer**: HTTP запросы, валидация, REST endpoints
- **Engine Layer**: SimulationEngine, очередь событий, планировщик
- **Domain Layer**: бизнес-логика агентов, трендов, действий
- **DB Layer**: persistence, data access, batch operations

## Основные компоненты

### 1. Simulation Engine
- **Дискретно-событийная симуляция** (DES) с приоритетной очередью
- **Batch-commit механизм** для производительности (100 операций или 1 минута)
- **Real-time mode** с настраиваемой скоростью через `SIM_SPEED_FACTOR`
- **Async/await архитектура** для поддержки real-time режима

### 2. Action System v1.8
- **Action Factory Pattern** для унифицированного создания действий
- **YAML конфигурация** (`config/actions.yaml`) для эффектов и cooldowns
- **Система cooldowns**: POST (60 мин), SELFDEV (120 мин)
- **Покупки L1/L2/L3** с финансовыми порогами и эффектами
- **Проверка рабочих часов**: агенты неактивны 00:00-08:00

### 3. Agent System
- **Персоны** с динамическими атрибутами (energy_level, financial_capability, etc.)
- **Матрица интересов** 7x11 профессий vs тем
- **Принятие решений** на основе weighted scoring
- **v1.8 поля**: purchases_today, last_post_ts, last_selfdev_ts, last_purchase_ts

### 4. Event System
Приоритетная система событий:

| Priority | Type | Category | Description |
|----------|------|----------|-------------|
| 100 | SYSTEM | System | Системные события (высший приоритет) |
| 50 | AGENT_ACTION | Agent | Действия агентов |
| 0 | LOW | Various | Низкоприоритетные события |

### 5. Time Management
- **Симуляционное время** в минутах от начала симуляции
- **Human time conversion**: `convert_sim_time_to_human()` (08:00 = начало)
- **Work hours check**: `is_work_hours()` для ограничения активности агентов
- **Real-time clock**: синхронизация с настенными часами

## Схема базы данных

### Основные таблицы
- **simulation_runs**: метаданные симуляций
- **persons**: глобальные агенты с базовыми атрибутами
- **simulation_participants**: участие агентов в конкретных симуляциях
- **trends**: информационные тренды
- **events**: события симуляции с human_time/action_timestamp
- **person_attribute_history**: история изменений атрибутов

### v1.8 Расширения
```sql
-- Новые поля в persons для v1.8
purchases_today SMALLINT DEFAULT 0 CHECK (purchases_today >= 0)
last_post_ts DOUBLE PRECISION NULL
last_selfdev_ts DOUBLE PRECISION NULL  
last_purchase_ts JSONB DEFAULT '{}'::jsonb

-- Индексы для производительности
CREATE INDEX idx_persons_last_purchase_ts ON persons USING GIN (last_purchase_ts jsonb_path_ops);
```

### Статичные справочники
- **agents_profession**: диапазоны атрибутов по профессиям
- **agent_interests**: интересы агентов по профессиям
- **affinity_map**: соответствие профессий к темам трендов
- **topic_interest_mapping**: централизованный маппинг топиков

## API интерфейсы

### REST Endpoints
- `POST /api/v1/simulations` - создание симуляции
- `GET /api/v1/simulations/{id}/status` - статус симуляции
- `GET /api/v1/simulations/{id}/agents` - список агентов
- `GET /api/v1/trends` - активные тренды

### Health & Monitoring
- `/healthz` - health check (интервал 60s)
- `/metrics` - Prometheus метрики
- **Real-time monitoring** через Grafana dashboards

## Конфигурация

### Environment Variables (34+ переменных)
- **Database**: DATABASE_URL, DATABASE_URL_RO
- **Performance**: BATCH_SIZE, SIM_SPEED_FACTOR, CACHE_*
- **v1.8 Actions**: POST_COOLDOWN_MIN, SELF_DEV_COOLDOWN_MIN
- **Monitoring**: ENABLE_METRICS, LOG_LEVEL

### YAML Configuration
- **actions.yaml**: эффекты действий, cooldowns, shop weights
- **simulation.yaml**: параметры профессий и атрибутов
- **trend_affinity.json**: матрица интересов 7x11

## Архитектурные решения (ADR)

### ADR-0001: Stack and Layering
- **Принято**: 4-слойная архитектура с четким разделением ответственности
- **Технологии**: Python 3.11, FastAPI, SQLAlchemy 2.0, PostgreSQL 15
- **Риски**: производительность Python при масштабировании

### ADR-0002: Realtime Clock Architecture
- **Принято**: Clock abstraction с SimClock и RealTimeClock
- **Конфигурация**: SIM_SPEED_FACTOR для управления скоростью
- **Async conversion**: SimulationEngine переведен на async/await

### ADR-0003: Person Schema Extension v1.8
- **Принято**: расширение схемы для системы действий v1.8
- **Поля**: purchases_today, cooldown timestamps, purchase history
- **Производительность**: GIN индексы для JSONB операций

## Производительность и масштабирование

### Целевые метрики
- **P95 latency**: < 10ms для обработки события
- **Throughput**: поддержка 5000 агентов × 43 события/день
- **Queue overflow**: graceful degradation при > 5000 событий
- **Memory**: оптимизация для работы на M1 MacBook Air

### Оптимизации
- **Batch commit**: группировка операций БД
- **JSONB indexing**: быстрый поиск по истории покупок
- **Async processing**: неблокирующая обработка событий
- **Connection pooling**: эффективное использование соединений БД

## Мониторинг и наблюдаемость

### Prometheus метрики
- `capsim_simulations_active` - количество активных симуляций
- `capsim_event_queue_size` - размер очереди событий
- `capsim_http_requests_total` - HTTP запросы к API
- `capsim_event_latency_ms` - латентность обработки событий

### Grafana dashboards
- **CAPSIM Overview**: общая производительность приложения
- **PostgreSQL**: метрики базы данных
- **System Metrics**: производительность хоста
- **Real-time Logs**: потоковые логи операций

### Алерты
- **EventQueueOverload**: очередь > 5000 событий
- **HighAPILatency**: P95 > 10ms
- **CpuTemperatureHigh**: температура > 85°C
- **HighIOWait**: IO wait > 25%

## Безопасность

### Принципы
- **Схема БД**: изоляция через PostgreSQL schema `capsim`
- **Валидация**: строгая типизация через Pydantic
- **Constraints**: проверки целостности на уровне БД
- **Secrets**: управление через environment variables

### Ограничения
- **Rate limiting**: ограничение частоты действий агентов
- **Resource limits**: контроль потребления памяти и CPU
- **Input validation**: проверка всех входных данных
- **Error handling**: graceful degradation при ошибках

## Развертывание

### Docker Compose
- **app**: основное приложение CAPSIM
- **postgres**: база данных PostgreSQL 15
- **prometheus**: сбор метрик
- **grafana**: визуализация и дашборды

### Окружения
- **Development**: полный стек с мониторингом
- **Testing**: изолированная среда для тестов
- **Production**: оптимизированная конфигурация

## Тестирование

### Стратегия тестирования
- **Unit tests**: тестирование отдельных компонентов
- **Integration tests**: тестирование взаимодействий
- **Performance tests**: нагрузочное тестирование
- **A/B testing**: сравнение вариантов поведения

### Реалистичное тестирование
- **Mock vs Reality**: различие между идеальными и реальными условиями
- **Constraint testing**: проверка ограничений и cooldowns
- **Resource depletion**: тестирование истощения ресурсов
- **Failure scenarios**: обработка сбоев и ошибок

## Будущее развитие

### Планируемые улучшения
- **ML адаптация**: машинное обучение для персонализации поведения
- **Масштабирование**: поддержка 10000+ агентов
- **Real-time analytics**: потоковая аналитика событий
- **Advanced monitoring**: предиктивные алерты

### Технический долг
- **Performance optimization**: оптимизация узких мест
- **Code refactoring**: улучшение архитектуры
- **Documentation**: актуализация документации
- **Testing coverage**: расширение покрытия тестами