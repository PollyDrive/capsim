# CAPSIM 2.0 - Системные требования

## 🚨 КРИТИЧЕСКИЕ ОГРАНИЧЕНИЯ

### 1. ЕДИНСТВЕННАЯ АКТИВНАЯ СИМУЛЯЦИЯ

**Требование**: Система **НЕ ДОЛЖНА** запускать более одной симуляции одновременно.

#### Обоснование
- **Целостность данных**: Параллельные симуляции могут создать конфликты в БД
- **Ресурсы системы**: Симуляция с 1000+ агентами требует значительных вычислительных ресурсов
- **Детерминизм**: Гарантия воспроизводимости результатов
- **Мониторинг**: Упрощение отслеживания производительности

#### Реализация

**Проверка при запуске:**
```python
# В capsim/engine/simulation_engine.py::initialize()
active_simulations = await self.db_repo.get_active_simulations()
if active_simulations:
    raise RuntimeError("Активная симуляция уже запущена!")
```

**Статусы симуляций:**
- `RUNNING` - активная симуляция
- `STOPPING` - процесс остановки
- `COMPLETED` - завершена успешно
- `FAILED` - завершена с ошибкой
- `FORCE_STOPPED` - принудительно остановлена

#### CLI команды

**Проверка статуса:**
```bash
python -m capsim status
```

**Остановка активной симуляции:**
```bash
# Graceful остановка
python -m capsim stop [simulation_id]

# Принудительная остановка
python -m capsim stop [simulation_id] --force
```

**Запуск новой симуляции:**
```bash
# Проверит активные симуляции автоматически
python -m capsim run --agents 100 --days 1
```

#### Поведение при нарушении

При попытке запуска второй симуляции:

1. **Логирование**: WARNING с ID активной симуляции
2. **Исключение**: `RuntimeError` с детальным сообщением
3. **Рекомендации**: Команды для остановки/проверки статуса

Пример вывода:
```
❌ ОТКЛОНЕНО: Активная симуляция уже запущена!
🔄 ID: 2ed1315b-17a1-4b05-bdbc-11187f8270d5
📊 Статус: RUNNING
👥 Агентов: 30
⏰ Запущена: 2025-06-25 13:10:04

💡 Для запуска новой симуляции:
   1. Дождитесь завершения текущей симуляции
   2. Или принудительно остановите: python -m capsim stop 2ed1315b-17a1-4b05-bdbc-11187f8270d5
   3. Затем запустите новую симуляцию
```

---

## 🔧 ТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ

### 2. АРХИТЕКТУРА СИМУЛЯЦИИ

#### База данных
- **PostgreSQL 15+** обязательно
- **Схема**: `capsim` (все таблицы в отдельной схеме)
- **Драйвер**: `asyncpg` для асинхронных операций
- **Подключения**: read-write + read-only сессии

#### Таблицы
- `simulation_runs` - метаданные симуляций
- `persons` - агенты симуляции
- `trends` - информационные тренды
- `events` - история событий
- `affinity_map` - матрица склонностей профессий

### 3. ПРОИЗВОДИТЕЛЬНОСТЬ

#### Временные ограничения
- **Инициализация**: ≤ 10 секунд для 1000 агентов
- **Event latency**: ≤ 10ms P95 в fast-режиме
- **Batch commit**: каждые 100 операций ИЛИ 60 секунд
- **Graceful shutdown**: ≤ 30 секунд

#### Ресурсы
- **Память**: ≤ 1GB для симуляции 1000 агентов
- **CPU**: ≤ 75% одного ядра в realtime-режиме
- **Диск**: ≤ 100MB/час логов и событий

### 4. РЕЖИМЫ РАБОТЫ

#### Fast Mode (по умолчанию)
```bash
SIM_SPEED_FACTOR=60  # 1 сим-минута = 1 реальная секунда
```

#### Realtime Mode
```bash
SIM_SPEED_FACTOR=1   # 1 сим-минута = 1 реальная минута
```

#### Development Mode
```bash
SIM_SPEED_FACTOR=3600  # 1 сим-минута = 1мс (для тестов)
```

---

## 🚨 МОНИТОРИНГ И АЛЕРТЫ

### 5. КРИТИЧЕСКИЕ МЕТРИКИ

#### Prometheus метрики
- `capsim_active_simulations_total` - количество активных симуляций
- `capsim_event_latency_ms` - время обработки событий
- `capsim_queue_length` - размер очереди событий
- `capsim_agents_total` - общее количество агентов

#### Алерты Grafana

**CRITICAL**: Нарушение единственности симуляции
```yaml
- alert: MultipleActiveSimulations
  expr: capsim_active_simulations_total > 1
  for: 0s
  annotations:
    summary: "Обнаружено {{ $value }} активных симуляций!"
```

**WARNING**: Высокая латентность
```yaml
- alert: HighEventLatency
  expr: histogram_quantile(0.95, capsim_event_latency_ms_bucket) > 10
  for: 3m
  annotations:
    summary: "Латентность событий: {{ $value }}ms"
```

**WARNING**: Переполнение очереди
```yaml
- alert: QueueOverflow  
  expr: capsim_queue_length > 5000
  for: 1m
  annotations:
    summary: "Очередь событий: {{ $value }} элементов"
```

### 6. ЛОГИРОВАНИЕ

#### Структура логов
```json
{
  "timestamp": "2025-06-25T13:10:04.123Z",
  "level": "INFO",
  "event": "simulation_rejected_active_exists",
  "active_simulation_id": "uuid",
  "active_status": "RUNNING",
  "total_active_simulations": 1
}
```

#### Ключевые события
- `simulation_initializing` - начало инициализации
- `simulation_rejected_active_exists` - отклонение из-за активной симуляции
- `simulation_started` - симуляция запущена
- `simulation_completed` - симуляция завершена
- `simulation_force_stopped` - принудительная остановка

---

## 📋 ОПЕРАЦИОННЫЕ ПРОЦЕДУРЫ

### 7. ЭКСТРЕННЫЕ СИТУАЦИИ

#### Зависшая симуляция
```bash
# 1. Проверить статус
python -m capsim status

# 2. Принудительная остановка
python -m capsim stop --force

# 3. Очистка БД (если нужно)
docker exec capsim-postgres-1 psql -U postgres -d capsim_db -c \
  "UPDATE capsim.simulation_runs SET status='FORCE_STOPPED', end_time=NOW() WHERE end_time IS NULL;"
```

#### Проблемы с БД
```bash
# Проверка подключения
docker exec capsim-postgres-1 psql -U postgres -d capsim_db -c "SELECT 1;"

# Проверка активных симуляций
docker exec capsim-postgres-1 psql -U postgres -d capsim_db -c \
  "SELECT run_id, status, start_time, num_agents FROM capsim.simulation_runs WHERE end_time IS NULL;"
```

### 8. РАЗВЕРТЫВАНИЕ

#### Требования к окружению
- Docker Compose с сервисами: `app`, `postgres`, `prometheus`, `grafana`
- Переменные окружения в `.env` файле
- Сетевые порты: `8000` (API), `5432` (PostgreSQL), `9090` (Prometheus), `3000` (Grafana)

#### Проверка развертывания
```bash
# Healthcheck
curl localhost:8000/healthz

# Статус симуляций
python -m capsim status

# Метрики
curl localhost:9090/api/v1/query?query=capsim_active_simulations_total
```

---

## ⚠️ ПРЕДУПРЕЖДЕНИЯ

### 9. ОГРАНИЧЕНИЯ

- ❌ **НЕ** запускайте симуляции напрямую через API в продакшене
- ❌ **НЕ** изменяйте статус симуляций вручную в БД без критической необходимости
- ❌ **НЕ** удаляйте записи из `simulation_runs` во время выполнения
- ⚠️ **ВСЕГДА** используйте graceful остановку перед принудительной
- ⚠️ **ПРОВЕРЯЙТЕ** статус перед запуском новой симуляции

### 10. ИЗВЕСТНЫЕ ПРОБЛЕМЫ

- При некорректном завершении процесса статус может остаться `RUNNING`
- В Docker могут возникнуть проблемы с SIGTERM обработкой
- PostgreSQL требует время на инициализацию после старта контейнера

---

**Дата документа**: 2025-06-25  
**Версия**: 1.0  
**Автор**: Архитектор CAPSIM 2.0 