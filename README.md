# CAPSIM 2.0 - Agent-based Discrete Event Simulation

⚡ **Платформа для моделирования социальных взаимодействий между агентами различных профессий под воздействием трендов, законодательных изменений и динамических факторов.**

## ⚡ Быстрый старт

```bash
# 1. Клонируйте репозиторий
git clone <repository-url>
cd capsim

# 2. Настройте окружение
cp .env_example .env
# Отредактируйте .env при необходимости

# 3. Запустите систему
docker-compose up -d

# 4. Проверьте работу
curl http://localhost:8000/healthz
```

## 🏗️ Архитектура

CAPSIM 2.0 построен на модульной 4-слойной архитектуре:

- **API Layer** (FastAPI) - REST endpoints и валидация
- **Engine Layer** - SimulationEngine и очередь событий  
- **Domain Layer** - бизнес-логика агентов и трендов
- **DB Layer** - доступ к данным и persistence

### Основные компоненты

- **SimulationEngine** - центральный координатор DES
- **Person** - агенты с 12 типами профессий
- **TrendProcessor** - управление жизненным циклом трендов
- **PersonInfluence** - обработка социального влияния

## 🎯 Технологический стек

- **Python 3.11** - основной язык
- **FastAPI** - REST API framework
- **SQLAlchemy 2.0** - ORM и работа с БД
- **PostgreSQL 15** - основная СУБД
- **Alembic** - миграции БД
- **Docker** - контейнеризация
- **Prometheus + Grafana** - мониторинг

## 📊 Характеристики производительности

- **Throughput**: до 43 событий на агента в день
- **Latency**: P95 < 10ms для обработки событий
- **Scalability**: поддержка до 5000 агентов
- **Queue Size**: максимум 5000 событий в очереди
- **Batch Commit**: каждые 100 операций или 1 минуту

## 🚀 Основные endpoints

- **POST /api/v1/simulations** - создание симуляции
- **GET /api/v1/simulations/{id}** - статус симуляции
- **GET /api/v1/simulations/{id}/agents** - список агентов
- **GET /api/v1/simulations/{id}/trends** - активные тренды
- **GET /healthz** - health check
- **GET /metrics** - Prometheus метрики

## 🔧 Разработка

### Установка зависимостей

```bash
# Poetry (рекомендуется)
poetry install

# Или pip
pip install -r requirements.txt
```

### Локальная разработка

```bash
# Запуск только БД
docker-compose up postgres -d

# Установка переменных окружения
export DATABASE_URL="postgresql://postgres:postgres_password@localhost:5432/capsim"

# Запуск приложения
python -m capsim.api.main

# Или через uvicorn
uvicorn capsim.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Тестирование

```bash
# Запуск тестов
make test

# Или pytest напрямую
pytest tests/ -v

# Линтинг и типизация
make lint
```

### Makefile команды

```bash
make dev-up      # Запуск в dev режиме
make dev-down    # Остановка dev контейнеров
make test        # Запуск тестов
make lint        # Проверка кода (ruff + mypy)
make bootstrap   # Инициализация системы
```

## 🎮 Использование

### Создание симуляции

```bash
curl -X POST http://localhost:8000/api/v1/simulations \
  -H "Content-Type: application/json" \
  -d '{
    "num_agents": 1000,
    "duration_days": 7,
    "seed": 42
  }'
```

### Получение статуса

```bash
curl http://localhost:8000/api/v1/simulations/{simulation_id}
```

### Мониторинг

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9091
- **API Docs**: http://localhost:8000/docs

## 📈 Мониторинг и метрики

### Prometheus метрики

- `capsim_queue_length` - размер очереди событий
- `capsim_event_latency_ms` - латентность обработки событий
- `capsim_batch_commit_errors_total` - ошибки batch commit
- `capsim_active_agents` - количество активных агентов
- `capsim_active_trends` - количество активных трендов

### Алерты

- **WARNING**: P95 latency > 10ms в течение 3 минут
- **CRITICAL**: Queue size > 5000 событий

## 🗃️ Структура проекта

```
capsim/
├── api/            # FastAPI routers и endpoints
├── engine/         # SimulationEngine и DES core
├── db/             # SQLAlchemy models и repositories
├── domain/         # Domain objects (Person, Trend, Events)
├── common/         # Утилиты, логирование, конфигурация
└── cli/            # Command line interfaces

docs/
├── adr/            # Architecture Decision Records
├── diagrams/       # Mermaid диаграммы
├── architecture_overview.md
└── events.md       # Каталог событий

config/             # YAML конфигурация
scripts/            # Bootstrap и утилиты
monitoring/         # Prometheus и Grafana конфиги
tests/              # Тесты
```

## 🔒 Безопасность

⚠️ **ВАЖНО**: API не защищено авторизацией. Сервис должен работать в изолированной сети или VPN.

## 📝 Конфигурация

Основные параметры в `.env`:

```bash
# Симуляция
DECIDE_SCORE_THRESHOLD=0.25      # Порог принятия решений
TREND_ARCHIVE_THRESHOLD_DAYS=3   # Архивирование трендов
BASE_RATE=43.2                   # События в день на агента
BATCH_SIZE=100                   # Размер batch commit

# Производительность  
SHUTDOWN_TIMEOUT_SEC=30          # Таймаут graceful shutdown
MAX_QUEUE_SIZE=5000              # Максимальный размер очереди
```

## 🤝 Участие в разработке

1. Форкните репозиторий
2. Создайте feature branch
3. Соблюдайте архитектурные границы между слоями  
4. Добавьте тесты для нового функционала
5. Убедитесь что CI проходит (ruff + mypy + pytest)
6. Создайте Pull Request

## 📜 Лицензия

Copyright (c) 2024 CAPSIM Team. All rights reserved.

---

## 🆘 Поддержка

- **Issues**: GitHub Issues для багов и feature requests
- **Documentation**: `/docs` для архитектурной документации
- **API Docs**: `/docs` endpoint когда приложение запущено



