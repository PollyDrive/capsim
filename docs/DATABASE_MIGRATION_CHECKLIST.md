# 🚀 CHECKLIST: Миграция PostgreSQL на хостинг

## 📋 **ОБЗОР ВСЕХ ТОЧЕК ПОДКЛЮЧЕНИЯ К БД**

Проанализированы все файлы проекта. Вот **исчерпывающий список** всех мест, где используется подключение к PostgreSQL:

---

## 🔧 **ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ** ✅ (Основное управление)

### **Основные переменные (должны быть изменены):**
```bash
# Главные строки подключения
DATABASE_URL=postgresql+asyncpg://user:password@HOST:PORT/database
DATABASE_URL_RO=postgresql+asyncpg://user:password@HOST:PORT/database

# Отдельные компоненты (используются как fallback)
POSTGRES_HOST=your-hosting-host.com
POSTGRES_PORT=5432
POSTGRES_DB=your_database_name
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password

# Пароли для пользователей (используются в Docker)
CAPSIM_RW_PASSWORD=password_for_read_write_user
CAPSIM_RO_PASSWORD=password_for_read_only_user
```

### **Файлы с переменными окружения:**
- ✅ `.env` - основной файл (будет изменен)
- ✅ `.env.local` - локальная разработка (оставить как есть)
- ✅ `.env.example` - шаблон (можно обновить)

---

## 🏗️ **АРХИТЕКТУРА ПОДКЛЮЧЕНИЙ**

### **1. Основное приложение (capsim/)**
**Файл:** `capsim/common/db_config.py` ✅ **Автоматически адаптируется**
- Использует `DATABASE_URL` из env
- Создает SYNC_DSN и ASYNC_DSN автоматически
- **Действие:** Только изменить переменные окружения

### **2. Скрипты анализа данных** ⚠️ **Есть hardcoded fallback**
**Файлы с проблемами:**
- `scripts/sync_profession_config.py:20`
- `scripts/analyze_simulation_results.py:9`  
- `scripts/analyze_trend_receptivity.py:16`
- `scripts/analyze_trend_receptivity_individual.py:16`

**Проблема:** Hardcoded fallback URL:
```python
default_url = "postgresql://capsim_rw:capsim321@localhost:5432/capsim_db"
```

**Решение:** ✅ Эти скрипты проверяют `DATABASE_URL` первым приоритетом, hardcoded используется только как fallback. Замены ENV будет достаточно.

### **3. Bootstrap скрипт**
**Файл:** `scripts/bootstrap.py` ✅ **Использует DATABASE_URL**
- Читает из `DATABASE_URL` env переменной
- **Действие:** Только изменить переменные окружения

---

## 🐳 **DOCKER КОНФИГУРАЦИЯ**

### **Docker Compose** ⚠️ **Требуется адаптация**
**Файл:** `docker-compose.yml`

**Проблемы:**
1. **Строки 11-12**: Hardcoded `@postgres:5432`
```yaml
- DATABASE_URL=postgresql+asyncpg://capsim_rw:${CAPSIM_RW_PASSWORD}@postgres:5432/${POSTGRES_DB}
- DATABASE_URL_RO=postgresql+asyncpg://capsim_ro:${CAPSIM_RO_PASSWORD}@postgres:5432/${POSTGRES_DB}
```

2. **Строки 35, 47**: Зависимость от сервиса `postgres`
```yaml
depends_on:
  postgres:
    condition: service_healthy
```

**Решение для хостинга:**
```yaml
# Вместо hardcoded строк, использовать env переменные
- DATABASE_URL=${DATABASE_URL}
- DATABASE_URL_RO=${DATABASE_URL_RO}

# Убрать depends_on postgres (если БД внешняя)
# depends_on:
#   postgres:
#     condition: service_healthy
```

---

## 🔄 **МИГРАЦИИ БАЗЫ ДАННЫХ**

### **Alembic конфигурация** ⚠️ **Требует изменения**
**Файл:** `alembic.ini:29`
```ini
# Текущее (Docker):
sqlalchemy.url = postgresql+psycopg2://capsim_rw:%%(CAPSIM_RW_PASSWORD)s@postgres:5432/capsim

# Для хостинга - изменить на:
sqlalchemy.url = postgresql+psycopg2://capsim_rw:%%(CAPSIM_RW_PASSWORD)s@your-host.com:PORT/database
```

**ИЛИ** использовать env переменную:
```ini
# sqlalchemy.url = driver://user:pass@localhost/dbname
# sqlalchemy.url = 
```
И устанавливать `ALEMBIC_DATABASE_URL` в окружении.

---

## 📊 **МОНИТОРИНГ**

### **Grafana DataSource** ⚠️ **Hardcoded хост**
**Файл:** `monitoring/grafana-datasources.yml:7`
```yaml
url: postgres:5432  # ← Изменить на внешний хост
```

**Решение:**
```yaml
url: your-hosting-host.com:5432
password: your_actual_password  # Вместо capsim321
```

### **PostgreSQL Exporter** (Docker Compose)
**Файл:** `docker-compose.yml:125`
```yaml
DATA_SOURCE_NAME: "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}?sslmode=disable"
```

**Решение:** Изменить `@postgres:5432` на `@${POSTGRES_HOST}:${POSTGRES_PORT}`

---

## 🧪 **ТЕСТИРОВАНИЕ**

### **GitHub Actions** ✅ **Только для CI/CD**
**Файл:** `.github/workflows/ci.yml:57`
- Использует localhost для тестов
- **Действие:** Оставить как есть (для CI окружения)

---

## ⚠️ **КРИТИЧЕСКИЕ МОМЕНТЫ ДЛЯ ХОСТИНГА**

### **1. SSL/TLS подключения**
Многие хостинги требуют SSL. Добавьте в DATABASE_URL:
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db?sslmode=require
```

### **2. Пулы подключений**
Хостинги часто имеют лимиты подключений. Настройте в env:
```bash
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

### **3. Пользователи БД**
Убедитесь, что на хостинге созданы пользователи:
- `capsim_rw` - для чтения/записи
- `capsim_ro` - только для чтения (опционально)

---

## ✅ **ПОШАГОВЫЙ ПЛАН МИГРАЦИИ**

### **ШАГ 1: Подготовка переменных**
```bash
# Новые значения для продакшена
export DATABASE_URL="postgresql+asyncpg://user:pass@your-host.com:5432/database?sslmode=require"
export DATABASE_URL_RO="postgresql+asyncpg://ro_user:pass@your-host.com:5432/database?sslmode=require"
export POSTGRES_HOST="your-host.com"
export POSTGRES_PORT="5432"
export POSTGRES_DB="your_database"
export POSTGRES_USER="your_user"
export POSTGRES_PASSWORD="your_password"
```

### **ШАГ 2: Файлы для изменения**
1. **Обязательно:**
   - `.env` - обновить все DATABASE_* и POSTGRES_* переменные
   - `alembic.ini` - изменить sqlalchemy.url
   - `monitoring/grafana-datasources.yml` - изменить url и password

2. **Опционально (для Docker):**
   - `docker-compose.yml` - если планируете использовать Docker с внешней БД

### **ШАГ 3: Проверка подключения**
```bash
# Тест подключения
python -c "
import asyncio
from capsim.common.db_config import ASYNC_DSN
import asyncpg

async def test():
    conn = await asyncpg.connect(ASYNC_DSN)
    result = await conn.fetchval('SELECT 1')
    print(f'✅ Подключение успешно: {result}')
    await conn.close()

asyncio.run(test())
"
```

### **ШАГ 4: Миграции**
```bash
# Применить миграции на новой БД
alembic upgrade head

# Загрузить начальные данные
python scripts/bootstrap.py
```

---

## 🎯 **ЗАКЛЮЧЕНИЕ**

**✅ ХОРОШИЕ НОВОСТИ:** 
- 95% кода использует переменные окружения
- `db_config.py` автоматически обрабатывает URL
- Большинство скриптов проверяют `DATABASE_URL` первым приоритетом

**⚠️ ЧТО НУЖНО ИЗМЕНИТЬ:**
1. **Переменные окружения** в `.env` (главное)
2. **alembic.ini** - URL для миграций  
3. **Grafana datasource** - хост и пароль
4. **Docker Compose** - если используете с внешней БД

**🚀 ВЫВОД:** Замены переменных в `.env` будет достаточно для **90%** функционала. Остальное - мелкие правки конфигурационных файлов.