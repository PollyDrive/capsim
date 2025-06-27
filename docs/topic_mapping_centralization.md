# Централизация маппинга топиков трендов ↔ категорий интересов

## Проблема

До рефакторинга маппинг топиков трендов к категориям интересов был размножен по разным модулям и тестам, что приводило к:

1. **Дублированию кода** - одинаковые словари в разных файлах
2. **Расхождениям в данных** - разные модули использовали разные маппинги
3. **Сложности поддержки** - изменения нужно было вносить в несколько мест
4. **Ошибкам в тестах** - тесты проверяли устаревшие маппинги

### Примеры расхождений:

```python
# В Person.py (устаревший)
topic_mapping = {
    "SPIRITUAL": "Religion",      # НЕПРАВИЛЬНО
    "CONSPIRACY": "Politics",     # НЕПРАВИЛЬНО  
    "SCIENCE": "Education",       # НЕПРАВИЛЬНО
    "CULTURE": "Entertainment",   # НЕПРАВИЛЬНО
}

# В тестах (правильный)
topic_mapping = {
    "SPIRITUAL": "Spirituality",  # ПРАВИЛЬНО
    "CONSPIRACY": "Society",      # ПРАВИЛЬНО
    "SCIENCE": "Knowledge",       # ПРАВИЛЬНО  
    "CULTURE": "Creativity",      # ПРАВИЛЬНО
}
```

## Решение

### 1. База данных как источник истины

Создана таблица `capsim.topic_interest_mapping` с каноническими маппингами:

```sql
CREATE TABLE capsim.topic_interest_mapping (
    id INTEGER PRIMARY KEY,
    topic_code VARCHAR(20) UNIQUE NOT NULL,     -- ECONOMIC, HEALTH, etc.
    topic_display VARCHAR(50) NOT NULL,         -- Economic, Health, etc.
    interest_category VARCHAR(50) NOT NULL,     -- Economics, Wellbeing, etc.
    description TEXT
);
```

**Данные (7 строк):**
| topic_code | topic_display | interest_category | description |
|------------|---------------|-------------------|-------------|
| ECONOMIC   | Economic      | Economics         | Economic trends and financial topics |
| HEALTH     | Health        | Wellbeing         | Health, wellness and medical topics |
| SPIRITUAL  | Spiritual     | Spirituality      | Spiritual, religious and philosophical topics |
| CONSPIRACY | Conspiracy    | Society           | Conspiracy theories and social distrust topics |
| SCIENCE    | Science       | Knowledge         | Scientific discoveries and educational content |
| CULTURE    | Culture       | Creativity        | Cultural events, arts and creative expression |
| SPORT      | Sport         | Society           | Sports events and physical activities |

### 2. Централизованный модуль

Создан модуль `capsim.common.topic_mapping` с функциями:

```python
from capsim.common.topic_mapping import (
    get_all_topic_codes,           # → ['ECONOMIC', 'HEALTH', ...]
    get_all_interest_categories,   # → ['Economics', 'Wellbeing', ...]
    topic_to_interest_category,    # ECONOMIC → Economics
    topic_to_display_name,         # ECONOMIC → Economic
    validate_topic_code,           # Проверка валидности
    get_topic_mapping,             # Простой словарь для legacy кода
)
```

**Особенности:**
- **Кэширование** для производительности
- **Fallback к константам** если БД недоступна
- **Обратная совместимость** с legacy кодом

### 3. Миграция базы данных

```bash
alembic revision -m "create_topic_interest_mapping"
alembic upgrade head
```

Миграция создаёт таблицу и заполняет её 7 каноническими записями.

## Изменения в коде

### Обновлённые модули:

1. **`capsim/domain/person.py`**
   ```python
   # Было:
   topic_mapping = {"ECONOMIC": "Economics", ...}
   
   # Стало:
   from capsim.common.topic_mapping import topic_to_interest_category
   interest_category = topic_to_interest_category(topic)
   ```

2. **Все скрипты** (`scripts/*.py`)
   ```python
   # Было:
   topics = ["Economic", "Health", "Spiritual", ...]
   
   # Стало:
   from capsim.common.topic_mapping import get_display_mapping
   topics = list(get_display_mapping().values())
   ```

3. **Все тесты** (`tests/*.py`)
   ```python
   # Было:
   all_topics = ["ECONOMIC", "HEALTH", ...]
   
   # Стало:
   from capsim.common.topic_mapping import get_all_topic_codes
   all_topics = get_all_topic_codes()
   ```

## Проверка работы

### Тест централизованного маппинга:

```python
from capsim.domain.person import Person
from capsim.common.topic_mapping import topic_to_interest_category
from uuid import uuid4

agent = Person.create_random_agent('Developer', uuid4())

# Проверяем что Person использует тот же маппинг
assert topic_to_interest_category('SCIENCE') == 'Knowledge'
science_interest = agent.get_interest_in_topic('SCIENCE')
knowledge_value = agent.interests['Knowledge']
assert science_interest == knowledge_value  # Теперь работает!
```

### Результат:
```
✅ Agent interests: ['Economics', 'Wellbeing', 'Spirituality', 'Knowledge', 'Creativity', 'Society']
✅ Knowledge interest value: 4.238
✅ SCIENCE topic → get_interest_in_topic: 4.238  # Раньше было 2.5 (fallback)
✅ SPIRITUAL topic → get_interest_in_topic: 0.738  # Раньше мапилось в Religion
```

## Преимущества

### ✅ Единый источник истины
- Все модули читают маппинг из одного места
- Нет расхождений между компонентами
- Изменения вносятся в одном месте

### ✅ Производительность  
- Кэширование предотвращает повторные запросы к БД
- Fallback к константам если БД недоступна
- Минимальный overhead

### ✅ Надёжность
- Валидация топиков и категорий
- Обработка ошибок
- Обратная совместимость

### ✅ Тестируемость
- Все тесты используют актуальные маппинги
- Функция очистки кэша для изоляции тестов
- Комплексные проверки целостности

## Миграция legacy кода

Для упрощения миграции предоставлены compatibility функции:

```python
# Legacy код продолжает работать:
from capsim.common.topic_mapping import get_topic_mapping
topic_mapping = get_topic_mapping()
interest = topic_mapping.get("ECONOMIC", "Economics")  # ✅ Работает
```

## Файлы изменений

### Новые файлы:
- `alembic/versions/2bebdbfef5d5_create_topic_interest_mapping.py`
- `capsim/common/topic_mapping.py`
- `docs/topic_mapping_centralization.md`

### Изменённые файлы:
- `capsim/db/models.py` - добавлена модель TopicInterestMapping
- `capsim/domain/person.py` - использует централизованный маппинг
- `scripts/*.py` - все скрипты обновлены
- `tests/*.py` - все тесты обновлены

### База данных:
- Таблица `capsim.topic_interest_mapping` с 7 записями
- Все маппинги синхронизированы с ТЗ

## Заключение

Централизация маппинга топиков устранила дублирование кода, исправила расхождения в данных и упростила поддержку системы. Все модули теперь используют единый источник истины, что гарантирует консистентность данных во всей симуляции. 