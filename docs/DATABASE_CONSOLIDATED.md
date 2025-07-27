# CAPSIM 2.0 - Консолидированная документация по базе данных

## Обзор базы данных

CAPSIM 2.0 использует PostgreSQL 15 с схемой `capsim` для хранения данных симуляции. База данных спроектирована для поддержки до 5000 агентов с эффективным хранением временных рядов и JSONB данных.

## Архитектура базы данных

### Технологический стек
- **PostgreSQL 15** - основная СУБД
- **SQLAlchemy 2.0** - ORM с async поддержкой
- **Alembic** - система миграций
- **JSONB** - гибкое хранение структурированных данных
- **UUID** - primary keys для масштабируемости
- **GIN индексы** - быстрый поиск по JSONB

### Схема `capsim`
Все таблицы находятся в отдельной схеме `capsim` для изоляции от других приложений.

## Основные таблицы

### 1. simulation_runs
Метаданные запусков симуляций.

```sql
CREATE TABLE capsim.simulation_runs (
    run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    start_time TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP NULL,
    status VARCHAR(50) DEFAULT 'RUNNING',  -- RUNNING, COMPLETED, FAILED
    num_agents INTEGER NOT NULL,
    duration_days INTEGER NOT NULL,
    configuration JSON NULL
);
```

**Назначение**: Отслеживание всех запусков симуляций с их параметрами и статусом.

### 2. persons
Глобальные агенты симуляции с базовыми атрибутами.

```sql
CREATE TABLE capsim.persons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profession VARCHAR(50) NOT NULL,
    
    -- Personal information (REQUIRED FIELDS)
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    gender VARCHAR(10) NOT NULL,  -- 'male' or 'female'
    date_of_birth DATE NOT NULL,  -- For age calculation (18-65 years)
    
    -- Dynamic attributes (0.0-5.0 scale)
    financial_capability FLOAT DEFAULT 0.0,
    trend_receptivity FLOAT DEFAULT 0.0,
    social_status FLOAT DEFAULT 0.0,
    energy_level FLOAT DEFAULT 5.0,
    
    -- Time and interaction tracking
    time_budget NUMERIC(2,1) DEFAULT 2.5,  -- 0.0-5.0 with 0.5 step
    exposure_history JSON DEFAULT '{}',     -- {trend_id: timestamp}
    interests JSON DEFAULT '{}',            -- {interest_name: value}
    
    -- v1.8 Action tracking fields
    purchases_today SMALLINT DEFAULT 0 CHECK (purchases_today >= 0),
    last_post_ts DOUBLE PRECISION NULL,
    last_selfdev_ts DOUBLE PRECISION NULL,
    last_purchase_ts JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Индексы для производительности
CREATE INDEX idx_persons_profession ON capsim.persons(profession);
CREATE INDEX idx_persons_energy_level ON capsim.persons(energy_level);
CREATE INDEX idx_persons_last_purchase_ts ON capsim.persons USING GIN (last_purchase_ts jsonb_path_ops);
```

**v1.8 Расширения**:
- `purchases_today` - дневной счетчик покупок (лимит 5/день)
- `last_post_ts` - timestamp последнего поста для cooldown
- `last_selfdev_ts` - timestamp саморазвития для cooldown
- `last_purchase_ts` - история покупок по уровням в JSONB

**Структура last_purchase_ts**:
```json
{
  "L1": 1678901234.567,  // timestamp последней покупки L1
  "L2": 1678902345.678,  // timestamp последней покупки L2
  "L3": null             // покупка L3 никогда не совершалась
}
```

### 3. simulation_participants
Участие агентов в конкретных симуляциях с симуляционно-специфичными атрибутами.

```sql
CREATE TABLE capsim.simulation_participants (
    simulation_id UUID REFERENCES capsim.simulation_runs(run_id) ON DELETE CASCADE,
    person_id UUID REFERENCES capsim.persons(id) ON DELETE CASCADE,
    
    -- v1.8: Action tracking and cooldowns (simulation-specific)
    purchases_today SMALLINT DEFAULT 0,
    last_post_ts DOUBLE PRECISION NULL,
    last_selfdev_ts DOUBLE PRECISION NULL,
    last_purchase_ts JSONB DEFAULT '{}'::jsonb,
    
    PRIMARY KEY (simulation_id, person_id)
);
```

**Назначение**: Связь агентов с симуляциями и отслеживание их состояния в рамках конкретной симуляции.

### 4. trends
Информационные тренды в социальной сети.

```sql
CREATE TABLE capsim.trends (
    trend_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id UUID REFERENCES capsim.simulation_runs(run_id) NOT NULL,
    topic VARCHAR(50) NOT NULL,  -- Economic, Health, Spiritual, etc.
    originator_id UUID REFERENCES capsim.persons(id) NOT NULL,
    parent_trend_id UUID REFERENCES capsim.trends(trend_id) NULL,
    
    -- Temporal data
    timestamp_start TIMESTAMP DEFAULT NOW(),
    
    -- Virality metrics
    base_virality_score FLOAT DEFAULT 0.0,  -- 0.0-5.0 scale
    coverage_level VARCHAR(20) DEFAULT 'Low',  -- Low/Middle/High
    total_interactions INTEGER DEFAULT 0,
    
    -- v1.9 sentiment
    sentiment VARCHAR(10) DEFAULT 'Positive' NOT NULL,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_trends_simulation_id ON capsim.trends(simulation_id);
CREATE INDEX idx_trends_topic ON capsim.trends(topic);
CREATE INDEX idx_trends_originator_id ON capsim.trends(originator_id);
```

**Назначение**: Хранение информационных трендов с метриками вирусности и социального влияния.

### 5. events
События симуляции с временными метками.

```sql
CREATE TABLE capsim.events (
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    simulation_id UUID REFERENCES capsim.simulation_runs(run_id) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    priority INTEGER NOT NULL,
    timestamp FLOAT NOT NULL,  -- simulation time in minutes
    action_timestamp VARCHAR(5) NULL,  -- human time format "HH:MM"
    agent_id UUID REFERENCES capsim.persons(id) NULL,
    trend_id UUID REFERENCES capsim.trends(trend_id) NULL,
    event_data JSON NULL,
    processed_at TIMESTAMP NULL,
    processing_duration_ms FLOAT NULL
);

-- Индексы
CREATE INDEX idx_events_simulation_id ON capsim.events(simulation_id);
CREATE INDEX idx_events_timestamp ON capsim.events(timestamp);
CREATE INDEX idx_events_action_timestamp ON capsim.events(action_timestamp);
CREATE INDEX idx_events_event_type ON capsim.events(event_type);
```

**Назначение**: Журнал всех событий симуляции с временными метками и метаданными обработки.

**action_timestamp**: Человеческое время в формате "ЧЧ:ММ", автоматически вычисляется из simulation timestamp.

### 6. person_attribute_history
История изменений атрибутов агентов.

```sql
CREATE TABLE capsim.person_attribute_history (
    id SERIAL PRIMARY KEY,
    simulation_id UUID REFERENCES capsim.simulation_runs(run_id) NOT NULL,
    person_id UUID REFERENCES capsim.persons(id) NOT NULL,
    
    -- Change details
    attribute_name VARCHAR(50) NOT NULL,
    old_value FLOAT NULL,
    new_value FLOAT NOT NULL,
    delta FLOAT NOT NULL,
    
    -- Change context
    reason VARCHAR(100) NOT NULL,  -- TrendInfluence, EnergyRecovery, etc.
    source_trend_id UUID NULL,
    change_timestamp FLOAT NOT NULL,  -- simulation time
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_person_attr_history_person_id ON capsim.person_attribute_history(person_id);
CREATE INDEX idx_person_attr_history_simulation_id ON capsim.person_attribute_history(simulation_id);
CREATE INDEX idx_person_attr_history_attribute_name ON capsim.person_attribute_history(attribute_name);
```

**Назначение**: Аудит всех изменений атрибутов агентов для анализа динамики поведения.

## Статичные справочники

### 7. agents_profession
Статичная таблица диапазонов атрибутов для каждой профессии.

```sql
CREATE TABLE capsim.agents_profession (
    profession VARCHAR(50) PRIMARY KEY,
    
    -- Диапазоны атрибутов
    financial_capability_min FLOAT NOT NULL,
    financial_capability_max FLOAT NOT NULL,
    trend_receptivity_min FLOAT NOT NULL,
    trend_receptivity_max FLOAT NOT NULL,
    social_status_min FLOAT NOT NULL,
    social_status_max FLOAT NOT NULL,
    energy_level_min FLOAT NOT NULL,
    energy_level_max FLOAT NOT NULL,
    time_budget_min FLOAT NOT NULL,
    time_budget_max FLOAT NOT NULL,
    
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Назначение**: Определение диапазонов атрибутов для генерации реалистичных агентов по профессиям.

### 8. agent_interests
Статичная таблица интересов агентов по профессиям.

```sql
CREATE TABLE capsim.agent_interests (
    id SERIAL PRIMARY KEY,
    profession VARCHAR(50) NOT NULL,
    interest_name VARCHAR(50) NOT NULL,  -- Economics, Wellbeing, etc.
    min_value FLOAT NOT NULL,
    max_value FLOAT NOT NULL,
    
    UNIQUE(profession, interest_name)
);
```

**Назначение**: Матрица интересов 7x11 профессий vs категорий интересов.

### 9. affinity_map
Статичная таблица соответствия профессий к темам трендов.

```sql
CREATE TABLE capsim.affinity_map (
    id SERIAL PRIMARY KEY,
    profession VARCHAR(50) NOT NULL,
    topic VARCHAR(50) NOT NULL,  -- Economic, Health, etc.
    affinity_score FLOAT NOT NULL,  -- 1-5 scale
    
    UNIQUE(profession, topic)
);
```

**Назначение**: Определение склонности профессий к различным темам трендов.

### 10. topic_interest_mapping
Централизованная таблица маппинга топиков трендов к категориям интересов.

```sql
CREATE TABLE capsim.topic_interest_mapping (
    id SERIAL PRIMARY KEY,
    topic_code VARCHAR(20) NOT NULL UNIQUE,  -- ECONOMIC, HEALTH, etc.
    topic_display VARCHAR(50) NOT NULL,      -- Economic, Health, etc.
    interest_category VARCHAR(50) NOT NULL,  -- Economics, Wellbeing, etc.
    description TEXT NULL
);
```

**Назначение**: Централизованное управление соответствием между топиками трендов и категориями интересов.

### 11. daily_trend_summary
Агрегированная статистика трендов по дням.

```sql
CREATE TABLE capsim.daily_trend_summary (
    id SERIAL PRIMARY KEY,
    simulation_id UUID REFERENCES capsim.simulation_runs(run_id) NOT NULL,
    simulation_day INTEGER NOT NULL,  -- День симуляции (1, 2, 3...)
    topic VARCHAR(50) NOT NULL,
    
    -- Aggregated metrics
    total_interactions_today INTEGER DEFAULT 0,
    avg_virality_today FLOAT DEFAULT 0.0,
    top_trend_id UUID NULL,
    unique_authors_count INTEGER DEFAULT 0,
    pct_change_virality FLOAT NULL,  -- Compared to previous day
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(simulation_id, simulation_day, topic)
);
```

**Назначение**: Ежедневная агрегация статистики трендов для аналитики.

## Миграции базы данных

### История миграций
- `0001_init_capsim_schema.py` - Инициализация схемы capsim
- `0002_add_person_fields.py` - Добавление полей персон
- `0003_fix_interests_to_tz.py` - Исправление временных зон
- `0004_fix_birth_years_and_time_budget.py` - Исправление дат рождения
- `0005_add_new_person_fields_v1_8.py` - Поля v1.8 для системы действий
- `0006_add_human_time_to_events.py` - Добавление human_time в события
- `0007_rename_human_time_to_action_timestamp.py` - Переименование в action_timestamp

### Текущая версия схемы
Последняя миграция: `0007_rename_human_time_to_action_timestamp`

## Производительность базы данных

### Индексы для оптимизации

#### JSONB индексы
```sql
-- GIN индекс для быстрого поиска по истории покупок
CREATE INDEX idx_persons_last_purchase_ts 
ON capsim.persons USING GIN (last_purchase_ts jsonb_path_ops);

-- Примеры запросов с использованием индекса
SELECT * FROM capsim.persons 
WHERE last_purchase_ts ? 'L1';  -- Быстрый поиск агентов с покупками L1

SELECT * FROM capsim.persons 
WHERE last_purchase_ts @> '{"L2": 1678902345.678}';  -- Точное совпадение
```

#### Составные индексы
```sql
-- Индекс для поиска событий по симуляции и времени
CREATE INDEX idx_events_simulation_timestamp 
ON capsim.events(simulation_id, timestamp);

-- Индекс для поиска трендов по симуляции и топику
CREATE INDEX idx_trends_simulation_topic 
ON capsim.trends(simulation_id, topic);
```

### Оптимизация PostgreSQL

#### Конфигурация для производительности
```sql
-- postgresql.conf оптимизации
shared_buffers = 256MB
work_mem = 4MB
maintenance_work_mem = 64MB
checkpoint_timeout = 10min
checkpoint_completion_target = 0.9
wal_buffers = 16MB
effective_cache_size = 1GB
random_page_cost = 1.1  -- Для SSD
```

#### Партиционирование
```sql
-- Партиционирование таблицы events по месяцам
CREATE TABLE capsim.events_y2025m01 PARTITION OF capsim.events
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE capsim.events_y2025m02 PARTITION OF capsim.events
FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
```

## Мониторинг базы данных

### Ключевые метрики

#### Prometheus метрики
```promql
# Количество подключений к БД
pg_stat_database_numbackends

# Скорость записи WAL
rate(pg_wal_lsn_bytes_total[5m])

# Коэффициент попаданий в кэш
pg_stat_database_blks_hit / (pg_stat_database_blks_hit + pg_stat_database_blks_read)

# Время выполнения запросов
pg_stat_statements_mean_time_ms

# Размер базы данных
pg_database_size_bytes{datname="capsim"}
```

#### SQL запросы для мониторинга
```sql
-- Общее количество агентов
SELECT COUNT(*) as total_agents FROM capsim.persons;

-- Агенты по симуляциям
SELECT simulation_id, COUNT(*) as agent_count 
FROM capsim.simulation_participants 
GROUP BY simulation_id 
ORDER BY agent_count DESC;

-- Распределение агентов по профессиям
SELECT profession, COUNT(*) as count, 
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM capsim.persons 
GROUP BY profession 
ORDER BY count DESC;

-- События за последний час
SELECT event_type, COUNT(*) as count
FROM capsim.events 
WHERE processed_at > NOW() - INTERVAL '1 hour'
GROUP BY event_type
ORDER BY count DESC;

-- Активные тренды по топикам
SELECT topic, COUNT(*) as count,
       AVG(base_virality_score) as avg_virality
FROM capsim.trends 
GROUP BY topic 
ORDER BY count DESC;

-- Статус симуляций
SELECT run_id, status, start_time, end_time, num_agents,
       CASE 
         WHEN end_time IS NULL THEN 'RUNNING'
         ELSE 'COMPLETED'
       END as current_status
FROM capsim.simulation_runs 
ORDER BY start_time DESC;
```

### Grafana дашборды

#### CAPSIM Overview Dashboard
- **Total Agents**: Общее количество агентов в БД
- **Active Simulations**: Количество запущенных симуляций
- **Events Rate**: Скорость создания событий
- **Database Size**: Размер базы данных

#### PostgreSQL Dashboard
- **Connections**: Активные подключения
- **Query Performance**: Производительность запросов
- **Cache Hit Ratio**: Коэффициент попаданий в кэш
- **WAL Activity**: Активность журнала транзакций

### Алерты базы данных

```yaml
# Alert: Высокое количество подключений
- alert: HighDatabaseConnections
  expr: pg_stat_database_numbackends > 80
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "High number of database connections"

# Alert: Низкий коэффициент попаданий в кэш
- alert: LowCacheHitRatio
  expr: pg_stat_database_blks_hit / (pg_stat_database_blks_hit + pg_stat_database_blks_read) < 0.95
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Low database cache hit ratio"

# Alert: Медленные запросы
- alert: SlowQueries
  expr: pg_stat_statements_mean_time_ms > 1000
  for: 3m
  labels:
    severity: warning
  annotations:
    summary: "Slow database queries detected"
```

## Операции с данными

### Batch операции
```python
# Пример batch обновления агентов
async def batch_update_agents(self, updates: List[Dict]):
    """Batch обновление состояния агентов для производительности."""
    
    if not updates:
        return
    
    # Группируем обновления по типу
    person_updates = []
    history_records = []
    
    for update in updates:
        if update["type"] == "person_update":
            person_updates.append(update)
        elif update["type"] == "history_record":
            history_records.append(update)
    
    # Batch обновление persons
    if person_updates:
        await self.session.execute(
            update(DBPerson),
            person_updates
        )
    
    # Batch вставка истории
    if history_records:
        await self.session.execute(
            insert(PersonAttributeHistory),
            history_records
        )
    
    await self.session.commit()
```

### Очистка данных
```sql
-- Очистка старых симуляций (старше 30 дней)
DELETE FROM capsim.simulation_runs 
WHERE start_time < NOW() - INTERVAL '30 days' 
AND status = 'COMPLETED';

-- Архивирование старых событий
CREATE TABLE capsim.events_archive AS 
SELECT * FROM capsim.events 
WHERE processed_at < NOW() - INTERVAL '7 days';

DELETE FROM capsim.events 
WHERE processed_at < NOW() - INTERVAL '7 days';

-- Очистка неактивных агентов
DELETE FROM capsim.persons 
WHERE id NOT IN (
    SELECT DISTINCT person_id 
    FROM capsim.simulation_participants
    WHERE simulation_id IN (
        SELECT run_id FROM capsim.simulation_runs 
        WHERE start_time > NOW() - INTERVAL '30 days'
    )
);
```

## Резервное копирование и восстановление

### Стратегия резервного копирования
```bash
# Ежедневное резервное копирование
pg_dump -h localhost -U capsim_user -d capsim_db \
  --schema=capsim \
  --format=custom \
  --compress=9 \
  --file=backup_$(date +%Y%m%d).dump

# Инкрементальное резервное копирование WAL
pg_basebackup -h localhost -U capsim_user \
  -D /backup/base \
  --wal-method=stream \
  --compress=9
```

### Восстановление
```bash
# Восстановление из дампа
pg_restore -h localhost -U capsim_user -d capsim_db \
  --schema=capsim \
  --clean \
  --if-exists \
  backup_20250127.dump

# Point-in-time recovery
pg_ctl stop -D /var/lib/postgresql/data
cp -R /backup/base/* /var/lib/postgresql/data/
pg_ctl start -D /var/lib/postgresql/data
```

## Безопасность базы данных

### Пользователи и права доступа
```sql
-- Создание пользователей
CREATE USER capsim_rw WITH PASSWORD 'secure_password';
CREATE USER capsim_ro WITH PASSWORD 'readonly_password';

-- Права для read-write пользователя
GRANT USAGE ON SCHEMA capsim TO capsim_rw;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA capsim TO capsim_rw;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA capsim TO capsim_rw;

-- Права для read-only пользователя
GRANT USAGE ON SCHEMA capsim TO capsim_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA capsim TO capsim_ro;
```

### Шифрование и защита
```sql
-- Включение SSL
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'

-- Аудит подключений
log_connections = on
log_disconnections = on
log_statement = 'mod'  -- Логирование изменений данных
```

## Troubleshooting

### Частые проблемы

#### 1. Медленные запросы
```sql
-- Поиск медленных запросов
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Анализ плана выполнения
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM capsim.persons 
WHERE energy_level < 1.0;
```

#### 2. Блокировки
```sql
-- Поиск блокировок
SELECT 
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

#### 3. Проблемы с индексами
```sql
-- Неиспользуемые индексы
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes 
WHERE idx_scan = 0 
AND schemaname = 'capsim';

-- Размер индексов
SELECT schemaname, tablename, indexname, 
       pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes 
WHERE schemaname = 'capsim'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Команды для диагностики
```bash
# Проверка подключения к БД
psql -h localhost -U capsim_user -d capsim_db -c "SELECT 1;"

# Проверка размера БД
psql -h localhost -U capsim_user -d capsim_db -c "
SELECT pg_size_pretty(pg_database_size('capsim_db')) as db_size;"

# Проверка активных подключений
psql -h localhost -U capsim_user -d capsim_db -c "
SELECT count(*) as active_connections FROM pg_stat_activity;"

# Проверка последних событий
psql -h localhost -U capsim_user -d capsim_db -c "
SELECT COUNT(*) FROM capsim.events 
WHERE processed_at > NOW() - INTERVAL '1 hour';"
```

## Заключение

База данных CAPSIM 2.0 обеспечивает:
- **Масштабируемость** до 5000 агентов
- **Производительность** через оптимизированные индексы и batch операции
- **Гибкость** через JSONB поля для динамических данных
- **Надежность** через constraints и транзакционность
- **Мониторинг** через Prometheus метрики и Grafana дашборды
- **Безопасность** через разделение ролей и аудит

Архитектура базы данных поддерживает как быстрые операции чтения для real-time мониторинга, так и эффективные batch операции для высокопроизводительной записи событий симуляции.