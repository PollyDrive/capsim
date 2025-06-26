# CAPSIM 2.0 Operations Guide

## Мониторинг и управление

### Grafana Dashboard Configuration

#### PostgreSQL Datasource
Grafana подключается напрямую к PostgreSQL для мониторинга статистики таблиц:

```yaml
# monitoring/grafana-datasources.yml
datasources:
  - name: Postgres
    type: postgres
    url: postgres:5432
    user: ${POSTGRES_USER}
    password: ${POSTGRES_PASSWORD}
    database: ${POSTGRES_DB}

```

#### Loki Datasource
Loki используется для централизованного сбора логов:

```yaml
datasources:
  - name: Loki
    type: loki
    url: http://loki:3100
```

### PostgreSQL Configuration for Real-time Monitoring

PostgreSQL настроен для детального логирования операций INSERT/UPDATE/DELETE в таблицу `events`:

```yaml
# monitoring/postgresql.conf
log_statement = 'mod'                    # Логирует все операции изменения данных
log_min_duration_statement = 0           # Логирует все запросы независимо от времени выполнения  
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_connections = on
log_disconnections = on
log_error_verbosity = verbose

# Performance monitoring
log_parser_stats = on
log_planner_stats = on
log_executor_stats = on
```

Эта конфигурация позволяет в реальном времени видеть все INSERT операции в таблицу `events` со всеми параметрами в панели Grafana "Events Real-time Monitoring".

### Дашборды

#### PostgreSQL Table Counts (`pg-counts`)
Показывает количество записей в основных таблицах:
- `capsim.persons` - количество агентов
- `capsim.events` - количество событий
- `capsim.trends` - количество трендов

#### Events Real-time Monitoring (`events-realtime`)
Real-time панель для мониторинга INSERT операций в таблицу `events`:
- Полные логи INSERT операций с параметрами
- Разобранные параметры событий (event_type, agent_id, simulation_id)
- Счетчик INSERT операций в минуту
- Форматированный вывод деталей событий

SQL запросы:
```sql
SELECT count(*) FROM capsim.persons;
SELECT count(*) FROM capsim.events;
SELECT count(*) FROM capsim.trends;
```

#### Logs Dashboard (`logs-dashboard`)
Три панели для просмотра логов:
- Application Logs: `{container_name="capsim-app-1"}`
- PostgreSQL Logs: `{container_name="capsim-postgres-1"}`
- Error Logs: `{container_name=~"capsim-.+"} |= "ERROR"`

### Добавление новых дашбордов

1. Создайте JSON файл в `monitoring/grafana/dashboards/`
2. Перезапустите Grafana: `docker compose restart grafana`
3. Дашборд автоматически загрузится через provisioning

### Изменение конфигурации Loki

Для изменения настроек сбора логов:

1. Отредактируйте `monitoring/promtail-config.yml`
2. Перезапустите Promtail: `docker compose restart promtail`

#### Promtail Configuration for PostgreSQL Logs

Promtail настроен для парсинга логов PostgreSQL и извлечения параметров INSERT операций:

```yaml
# Парсинг INSERT операций в таблицу events
- match:
    selector: '{service_name="postgres"} |~ "INSERT INTO.*events"'
    stages:
      - regex:
          expression: '.*INSERT INTO (?P<schema>\w+)\.(?P<table>\w+).*VALUES\s*\((?P<values>.*)\).*'
      - labels:
          operation: "INSERT"
          schema: schema
          table: table
          log_type: "events_insert"

# Извлечение параметров событий
- match:
    selector: '{log_type="events_insert"}'
    stages:
      - regex:
          expression: '.*event_type.*?[\'"](.*?)[\'"].*'
      - labels:
          event_type: event_type
```

Эта конфигурация автоматически распознает и маркирует INSERT операции в таблицу `events`, что позволяет создавать детальные фильтры в Grafana.

### Backup и Restore

#### Database Backup
```bash
# Создание backup
docker exec capsim-postgres-1 pg_dump -U postgres -d capsim_db > backup_$(date +%Y%m%d).sql

# Restore из backup
docker exec -i capsim-postgres-1 psql -U postgres -d capsim_db < backup_20250624.sql
```

#### Logs Backup
Логи Loki хранятся в volume `loki_data`. Для backup:
```bash
docker run --rm -v loki_data:/data -v $(pwd):/backup alpine tar czf /backup/loki_backup.tar.gz /data
```

### Troubleshooting

#### Grafana не видит данные
1. Проверьте подключение к PostgreSQL:
   ```bash
   docker exec capsim-postgres-1 psql -U postgres -d capsim_db -c "SELECT 1"
   ```

2. Проверьте права пользователя:
   ```bash
   docker exec capsim-postgres-1 psql -U postgres -d capsim_db -c "SELECT current_user"
   ```

#### Loki не собирает логи
1. Проверьте статус Promtail:
   ```bash
   docker logs capsim-promtail-1
   ```

2. Проверьте доступность Loki:
   ```bash
   curl http://localhost:3100/ready
   ```

#### Медленные запросы к БД
1. Включите логирование медленных запросов в PostgreSQL
2. Мониторинг через Grafana панель "PostgreSQL Logs"
3. Анализ через `EXPLAIN ANALYZE` для проблемных запросов

### Performance Tuning

#### PostgreSQL Configuration
Для высоких нагрузок отредактируйте `postgresql.conf`:
```conf
shared_buffers = 256MB
max_connections = 200
work_mem = 4MB
```

#### Grafana Performance  
Для больших datasets настройте:
```ini
[database]
max_open_conns = 300
max_idle_conns = 50
```

### Security

#### Database Security
- Используйте сильные пароли в `.env`
- Ограничьте доступ к PostgreSQL только из контейнеров
- Регулярно обновляйте образы PostgreSQL

#### Grafana Security
- Измените дефолтный пароль admin/admin
- Настройте HTTPS для production
- Ограничьте доступ к дашбордам по ролям

### Monitoring Checklist

- [ ] PostgreSQL контейнер запущен и доступен
- [ ] Grafana показывает корректные числа в дашбордах
- [ ] Loki собирает логи всех сервисов
- [ ] Promtail отправляет логи в Loki
- [ ] Нет ошибок в логах контейнеров
- [ ] Достаточно места на диске для логов и данных 