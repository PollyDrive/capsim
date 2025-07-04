# v.1.5

# Техническое задание для системы CAPSIM

# Цель и задачи

Основной целью системы CAPSIM является создание платформы для моделирования социальных взаимодействий между агентами различных профессий в условиях воздействия трендов, законодательных изменений, погодных факторов и динамического изменения состояний.

Ключевые задачи симуляции:

- моделирование поведения агентов с различными социально-экономическими характеристиками
- симуляцию распространения трендов через социальные сети
- генерацию таблиц с данными о действиях агентов в симуляции
- анализ влияния внешних факторов на принятие решений агентами и исследование динамики энергетических ресурсов и временных бюджетов агентов.

## Область применения (Scope)

## Что входит в функционал системы

- Моделирование агентов с 12 типами профессий и их социальных взаимодействий
- Обработку пяти типов событий с приоритизацией (LAW, WEATHER, TREND, AGENT_ACTION, SYSTEM)
- Управление трендами по семи тематическим категориям (Economic, Health, Spiritual, Conspiracy, Science, Culture, Sport)
- Систему энергетического восстановления и временных бюджетов
- Дискретно-событийную симуляцию с поддержкой до 1000 агентов
- Механизмы архивирования и batch-обработки данных
- Дискретно-событийную симуляцию с поддержкой до 43 событий на агента в день без ограничения общей длительности симуляции .

## Что не входит в функционал системы

Система не предназначена для:

- Реального взаимодействия с внешними социальными сетями
- Обработки персональных данных реальных пользователей
- Предоставления финансовых или медицинских консультаций
- Долгосрочного прогнозирования реальных экономических процессов
- Интеграции с системами государственного управления

# Функциональные требования

## Use Case 1: Создание и запуск симуляции (Приоритет: Высокий)

**Актор:** Исследователь

**Описание:** Пользователь создает новую симуляцию с заданными параметрами и запускает ее выполнение.

**Предусловия:** Система доступна и база данных инициализирована

**Основной сценарий:**

1. Пользователь указывает количество агентов (до 1000) и продолжительность (не ограничена, но рекомендуется до 14 дней)
2. Система создает агентов с случайным распределением профессий и характеристик
3. Инициализируются базовые тренды через TrendProcessor
4. Запускается основной цикл дискретно-событийной симуляции

## Use Case 2: Обработка действия PublishPostAction (Приоритет: Высокий)

**Актор:**

Агент системы

**Описание:**

1. SimulationEngine вызывает decideAction у агента, 
2. агент возвращает PublishPostAction с указанием темы, 
3. PersonInfluence обрабатывает публикацию,
4. TrendProcessor создает или модифицирует тренд, 
5. Система обновляет состояние автора (energyLevel -1.5, timeBudget -2)
6. Аудитория получает обновления влияния на их trendReceptivity

**Предусловия:**

Агент имеет достаточный энергетический уровень (>0) и временной бюджет (≥2)

## Use Case 3: Восстановление энергии агентов (Приоритет: Средний)

**Актор:** Системный планировщик

**Описание:** Каждые 24 часа симуляции происходит автоматическое восстановление энергии всех агентов

**Основной сценарий:**

1. EnergyRecoveryEvent запускается в полночь симулированного времени
2. Для агентов с energyLevel ≥ 3.0 устанавливается значение 5.0
3. Для остальных агентов добавляется 2.0 единицы энергии (максимум 5.0)
4. Изменения фиксируются через batch-commit

# Нефункциональные требования

## Производительность

- Обработка симуляции должна поддерживать до 43 и не более событий на агента в день.
- P95 времени обработки событий не должно превышать 10 миллисекунд
- Размер очереди событий не должен превышать 5000 элементов
- Batch-commit должен происходить при накоплении 100 обновлений или каждую минуту симулированного времени

## Надежность

- Система должна поддерживать graceful degradation при сбоях компонентов
- Критические ошибки базы данных должны приводить к корректной остановке симуляции
- Все транзакции должны использовать простой batch-commit без трехфазного протокола
- Система должна автоматически восстанавливаться после сетевых ошибок с экспоненциальной задержкой

## Масштабируемость

- Архитектура должна поддерживать горизонтальное масштабирование для обработки до 5000 агентов
- База данных должна использовать партиционирование по simulation_id
- Система должна поддерживать параллельную обработку независимых симуляций

## Архитектура системы

Система построена на основе модульной архитектуры с центральным компонентом SimulationEngine и восемью взаимодействующими подсистемами. 

- **SimulationEngine** - центральный координатор всех операций
- **Person** - агенты с атрибутами и поведением
- **TrendProcessor** - управление жизненным циклом трендов
- **PersonInfluence** - обработка социального влияния
- **DatabaseRepository** - абстракция доступа к данным
- **ExternalFactor** и **God** - источники внешних событий
- **EventQueue** - приоритетная очередь событий

## Решение циркулярных зависимостей

Система использует паттерн Dependency Injection для устранения циркулярных зависимостей между TrendProcessor и SimulationEngine . Каждый процессор получает ссылку на SimulationEngine через метод `set_simulation_engine()` после инициализации .

# Основные классы и компоненты

## SimulationEngine

Центральный класс координирует выполнение симуляции и содержит:

- **`agents: List[Person]`** - список всех агентов
- **`current_time: float`** - текущее время симуляции в минутах
- **`event_queue: List[PriorityEvent]`** - приоритетная очередь событий
- **`active_trends: Dict[str, Trend]`** - активные тренды по ID
- **`affinity_map: Dict[str, Dict[str, float]]`** - соответствие профессий темам

Ключевые методы включают **`initialize()`**, **`run_simulation()`**, **`process_event()`**, и **`batch_commit_agent_states()`**

Ключевые методы включают `initialize()`, `run_simulation()`, `process_event()` и `batch_commit_agent_states()` с упрощенной логикой без трехфазного протокола .

## Person

Класс агента содержит атрибуты:

- **`id: UUID`**,
- **`profession: str`**,
- **`financial_capability: float (0.0-5.0)`**
- **`trend_receptivity: float (0.0-5.0)`**,
- **`social_status: float (0.0-5.0)`**
- **`energy_level: float (0.0-5.0)`**,
- **`time_budget: float (0.0-5.0)`**
- **`exposure_history: Dict[str, datetime]`**,
- **`interests: Dict[str, float]`**

Методы **`decide_action()`** и **`update_state()`** реализуют логику принятия решений и обновления состояния.

### Список профессий агентов

ShopClerk, Worker, Developer, Politician, Blogger, Businessman, Doctor, Teacher, Unemployed, Artist, SpiritualMentor, Philosopher.

### Распределение персонажей по профессиям

Ниже приведена таблица с 12 профессиями, количеством агентов и долей от общего населения (1 000), распределённых более реалистично:

| Profession | Cluster | Count | Share (%) |
| --- | --- | --- | --- |
| ShopClerk | Worker | 180 | 18.0 |
| Worker | Worker | 70 | 7.0 |
| Developer | Worker | 120 | 12.0 |
| Politician | Social | 10 | 1.0 |
| Blogger | Social | 50 | 5.0 |
| Businessman | Social | 80 | 8.0 |
| SpiritualMentor | Spiritual | 30 | 3.0 |
| Philosopher | Spiritual | 20 | 2.0 |
| Unemployed | Other | 90 | 9.0 |
| Teacher | Other | 200 | 20.0 |
| Artist | Other | 80 | 8.0 |
| Doctor | Other | 10 | 1.0 |

### 2.4. Диапазоны распределения атрибутов по профессиям

Для каждой профессии задаём минимальные и максимальные значения ключевых атрибутов персонажа.

| Profession | financial_capability | trend_receptivity | social_status | energy_level | time_budget |
| --- | --- | --- | --- | --- | --- |
| ShopClerk | 2–4 | 1–3 | 1–3 | 2–5 | 3–5 |
| Worker | 2–4 | 1–3 | 1–2 | 2–5 | 3–5 |
| Developer | 3–5 | 3–5 | 2–4 | 2–5 | 2–4 |
| Politician | 3–5 | 3–5 | 4–5 | 2–5 | 2–4 |
| Blogger | 2–4 | 4–5 | 3–5 | 2–5 | 3–5 |
| Businessman | 4–5 | 2–4 | 4–5 | 2–5 | 2–4 |
| SpiritualMentor | 1–3 | 2–5 | 2–4 | 3–5 | 2–4 |
| Philosopher | 1–3 | 1–3 | 1–3 | 2–5 | 2–4 |
| Unemployed | 1–2 | 3–5 | 1–2 | 3–5 | 3–5 |
| Teacher | 1–3 | 1–3 | 2–4 | 2–5 | 2–4 |
| Artist | 1–3 | 2–4 | 2–4 | 4–5 | 3–5 |
| Doctor | 2–4 | 1–3 | 3–5 | 2–5 | 1–2 |


### Trend
Содержит информацию об отдельных информационных волнах (Trend):

| Поле | Тип | Описание |
| --- | --- | --- |
| `trend_id` | UUID | Уникальный идентификатор тренда |
| `topic` | TEXT | Тема (Economic, Health и др.) |
| `originator_id` | UUID | ID агента-инициатора |
| `parent_trend_id` | UUID ? | Ссылка на родительский тренд (если ответ на другой пост) |
| `timestamp_start` | TIMESTAMP | Время создания тренда |
| `base_virality_score` | REAL | Исходная виральность |
| `coverage_level` | TEXT | Уровень охвата (Low/Middle/High) |
| `total_interactions` | INTEGER | Счётчик всех реакций агентов на данный тренд |
| `simulation_id` | UUID | Ссылка на `run_id` из `simulation_runs` |

### Доступные темы (topic) для трендов:

| Economic | Health | Spiritual | Conspiracy | Science | Culture | Sport |
| --- | --- | --- | --- | --- | --- | --- |

**Хранение**: каждый новый тренд записывается сразу при публикации, а поле `total_interactions` инкрементируется при каждом влиянии.

## Расчёт «средней социальной значимости тем» для `coverage_level`

При старте базовых трендов в `TrendProcessor` для каждой темы `topic` рассчитывается средний социальный статус группы, склонной к теме:

1. Из всех агентов, чья `profession` участвует в `affinity_map[topic]`, выбираются значения `social_status`.
2. Среднее арифметическое этих значений нормируется к шкале 0–1:SS=N×5∑SSi
    
    SS‾=∑SSiN×5  \overline{SS} = \frac{\sum SS_i}{N \times 5}
    
3. По порогам SS‾<0.33\overline{SS}<0.33SS<0.33, 0.33≤SS‾<0.660.33\le \overline{SS}<0.660.33≤SS<0.66, SS‾≥0.66\overline{SS}\ge0.66SS≥0.66 определяется `coverage_level`: `Low`, `Middle` или `High`.

### Список интересов, доступный агентам:

- Economics
- Wellbeing
- Spirituality
- Knowledge
- Creativity
- Society

## Таблица с диапазонами значений **интересов (AgentInterests)** по профессиям.

Таблица статичная, генерируется при создании симуляции, хранится в основной базе и является источником данных для генерации свойства **`interests`** у агентов**.**

В текущей версии системы интересы и их значения создаются в соответствии с **AgentInterests**, но не изменяются в процессе симуляции.

| Profession | Economics | Wellbeing | Spirituality | Knowledge | Creativity | Society |
| --- | --- | --- | --- | --- | --- | --- |
| **ShopClerk** | [4.59, 5.0] | [0.74, 1.34] | [0.64, 1.24] | [1.15, 1.75] | [1.93, 2.53] | [2.70, 3.30] |
| **Worker** | [3.97, 4.57] | [1.05, 1.65] | [1.86, 2.46] | [1.83, 2.43] | [0.87, 1.47] | [0.69, 1.29] |
| **Developer** | [1.82, 2.42] | [1.15, 1.75] | [0.72, 1.32] | [4.05, 4.65] | [2.31, 2.91] | [1.59, 2.19] |
| **Politician** | [0.51, 1.11] | [1.63, 2.23] | [0.32, 0.92] | [2.07, 2.67] | [1.73, 2.33] | [3.57, 4.17] |
| **Blogger** | [1.32, 1.92] | [1.01, 1.61] | [1.20, 1.80] | [1.23, 1.83] | [3.27, 3.87] | [2.43, 3.03] |
| **Businessman** | [4.01, 4.61] | [0.76, 1.36] | [0.91, 1.51] | [1.35, 1.95] | [2.04, 2.64] | [2.42, 3.02] |
| **Doctor** | [1.02, 1.62] | [3.97, 4.57] | [1.37, 1.97] | [2.01, 2.61] | [1.58, 2.18] | [2.45, 3.05] |
| **Teacher** | [1.32, 1.92] | [2.16, 2.76] | [1.40, 2.00] | [3.61, 4.21] | [1.91, 2.51] | [2.24, 2.84] |
| **Unemployed** | [0.72, 1.32] | [1.38, 1.98] | [3.69, 4.29] | [2.15, 2.75] | [2.33, 2.93] | [2.42, 3.02] |
| **Artist** | [0.86, 1.46] | [0.91, 1.51] | [2.01, 2.61] | [1.82, 2.42] | [3.72, 4.32] | [1.94, 2.54] |
| **SpiritualMentor** | [0.62, 1.22] | [2.04, 2.64] | [3.86, 4.46] | [2.11, 2.71] | [2.12, 2.72] | [1.95, 2.55] |
| **Philosopher** | [1.06, 1.66] | [2.22, 2.82] | [3.71, 4.31] | [3.01, 3.61] | [2.21, 2.81] | [1.80, 2.40] |

### Формула генерации интересов для агента

При создании нового агента:

1. Определяется его профессия `P`
2. Из таблицы **AgentInterests** берутся диапазоны интересов `InterestRange[P][InterestName]`
3. Для каждого интереса:
    
    ```python
    
    interest_value = random.uniform(low, high)
    ```
    
    где `low` и `high` — значения из диапазона.
    

## Изменения атрибутов агентов от влияния трендов

При распространении тренда через механизм **PersonInfluence**, каждому затронутому агенту формируется пакет `UpdateState`, описывающий изменения его атрибутов. Ниже представлена структура и правила расчёта этих изменений.

---

## Структура пакета UpdateState

Каждый элемент пакета содержит:

- **agent_id** – идентификатор агента.
- **attribute_changes** – словарь `{имя_атрибута: delta}`, где `delta` — величина изменения.
- **reason** – строка, поясняющая причину изменения (например, `TrendInfluence`).
- **source_trend_id** – идентификатор тренда, вызвавшего изменение.

```python
json{
  "agent_id": "UUID",
  "attribute_changes": {
    "trend_receptivity": { "delta": +0.1 },
    "social_status":     { "delta": +0.05 }
  },
  "reason": "TrendInfluence",
  "source_trend_id": "trend-1234"
}
```

---

## Основные атрибуты и их динамика

## 1 Trend Receptivity

- **Описание:** отражает готовность агента реагировать на тренд
- **Изменение при каждом контакте:**
    - `delta = base_virality_score/10 × affinity_score/5 × random_factor`
    - Обычно в диапазоне **+0.05…+0.2** [#][#]

## 2 Social Status

- **Описание:** социальное влияние и авторитет агента
- **Изменение при распространении тренда:**
    - `delta = (virality_score − 1) × 0.02`
    - Усиление авторитета за счёт удачных репостов, **+0.01…+0.08** [#]

## 3 Energy Level

- **Описание:** запас внутренней энергии
- **Изменение:**
    - `delta = −0.05 × number_of_interactions` (влияние трендов)
    - `delta = −0.25` (публикация поста)
    - Небольшая усталость от просмотра/реакции на тренд, **−0.05…−0.15** [#]

## 4 Time Budget

- **Описание:** доступное время на совершение действий
- **Изменение:**
    - `delta = −(0.5 × coverage_level_factor)`
    - Чем шире охват, тем больше затраченного времени, **−0.1…−0.5** [#]

---

## Алгоритм формирования пакета

1. **Фильтрация аудитории** по `coverage_level` и `affinity_map` [#].
2. **Расчёт вероятности реакции** каждого агента:
    
    ```python
    P = (virality_score/5) × (trend_receptivity/5) × affinity × random(0.8–1.2)
    ```
    
3. **Для каждого реактивного агента** составляется `UpdateState`:
    - `trend_receptivity` += computed_delta
    - `social_status` += computed_delta
    - `energy_level` += computed_delta
    - `time_budget` += computed_delta
4. **Запись изменений** в историю (`person_attribute_history`) и обновление текущего состояния в `persons`[#].

---

## 4. Пример таблицы изменений

| agent_id | trend_receptivity Δ | social_status Δ | energy_level Δ | time_budget Δ | reason |
| --- | --- | --- | --- | --- | --- |
| 550e8400… | +0.12 | +0.04 | −0.10 | −0.30 | TrendInfluence |
| 550e8400… | +0.08 | +0.02 | −0.10 | −0.20 | TrendInfluence |
| … | … | … | … | … | … |

## Матрица соответствия профессий к темам трендов (Affinity Map)

Таблица статичная, генерируется при создании симуляции, хранится в основной базе и является источником коэффициента для расчета склонности агента публиковать соответствующие тренды.

| Профессия | Economic | Health | Spiritual | Conspiracy | Science | Culture | Sport |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **ShopClerk** | 3 | 2 | 2 | 3 | 1 | 2 | 2 |
| **Worker** | 3 | 3 | 2 | 3 | 1 | 2 | 3 |
| **Developer** | 3 | 2 | 1 | 2 | 5 | 3 | 2 |
| **Politician** | 5 | 4 | 2 | 2 | 3 | 3 | 2 |
| **Blogger** | 4 | 4 | 3 | 4 | 3 | 5 | 4 |
| **Businessman** | 5 | 3 | 2 | 2 | 3 | 3 | 3 |
| **Doctor** | 3 | 5 | 2 | 1 | 5 | 2 | 3 |
| **Teacher** | 3 | 4 | 3 | 2 | 4 | 4 | 3 |
| **Unemployed** | 4 | 3 | 3 | 4 | 2 | 3 | 3 |
| **Artist** | 2 | 2 | 4 | 2 | 2 | 5 | 2 |
| **SpiritualMentor** | 2 | 3 | 5 | 3 | 2 | 3 | 2 |
| **Philosopher** | 3 | 3 | 5 | 3 | 4 | 4 | 1 |

### Динамические модификаторы

Базовые значения из матрицы могут корректироваться в зависимости от:

- **Текущего состояния агента** — низкий `energy_level` снижает интерес ко всем темам
- **Социального статуса** — высокий статус увеличивает вероятность публикации
- **Истории взаимодействий** — механизм насыщения снижает интерес к повторяющимся темам

### Расчет вероятности публикации

```python
probability = affinity_score * (social_status / 5.0) * (trend_receptivity / 5.0) * random_factor
```

Где `affinity_score` берется из представленной матрицы.

### Кластерные особенности

Данная матрица обеспечивает естественное формирование кластеров:

- **Интеллектуальный кластер** (Developer, Teacher, Philosopher) тяготеет к Science
- **Социальный кластер** (Politician, Blogger) активен в Economic и Culture
- **Духовный кластер** (Artist, SpiritualMentor) доминирует в Spiritual

# Система событий и приоритетов

Система использует приоритетную очередь с пятью уровнями приоритета:

LAW=1,

WEATHER=2, 

TREND=3, 

AGENT_ACTION=4, 

SYSTEM=5. 

События обрабатываются в порядке возрастания приоритета, при равных приоритетах - по временным меткам .

Ключевые системные события включают:

- `EnergyRecoveryEvent` (восстановление энергии каждые 1440 минут)
- `DailyResetEvent` (сброс временного бюджета агентов)
- `SaveDailyTrend` (сохранение дневной статистики трендов) Архивирование неактивных трендов происходит через прямой вызов метода `archive_inactive_trends()` в рамках ежедневных операций, а не через отдельное событие ArchiveCheckEvent.

### Вызов метода archive_inactive_trends()

Метод **`archive_inactive_trends()`** вызывается **каждые 24 часа симулированного времени** как часть ежедневных системных операций. Это происходит в рамках обработки системных событий, которые планируются на полночь симулированного времени.

Метод вызывается непосредственно **классом SimulationEngine**. В отличие от других событий, которые обрабатываются через очередь событий, архивирование неактивных трендов происходит через прямой вызов метода в рамках ежедневных операций.

Метод **`archive_inactive_trends()`** реализует следующую логику:

```python
def archive_inactive_trends(self) -> None:
    threshold_time = self.current_time - self.trend_archive_threshold_days * 24 * 60
    trends_to_archive = []
    
    for trend_id, trend in self.active_trends.items():
        if self.get_last_interaction_time(trend) < threshold_time:
            trends_to_archive.append(trend_id)
    
    for trend_id in trends_to_archive:
        archived_trend = self.active_trends.pop(trend_id)
        self.db_repo.archive_trend(archived_trend)
```

## Замена ArchiveCheckEvent

Важно отметить, что метод **`archive_inactive_trends()`** **заменяет** ранее планировавшееся событие **`ArchiveCheckEvent`**. Вместо создания отдельного события в очереди, архивирование теперь происходит как прямой вызов метода в рамках ежедневных системных операций SimulationEngine.

## Параметры архивирования

Система использует параметр **`trend_archive_threshold_days`** (по умолчанию 3 дня) для определения неактивных трендов. Тренды, которые не имели взаимодействий в течение указанного периода, автоматически архивируются и удаляются из активного списка **`active_trends`**

## Действия агентов

Система поддерживает пять типов действий агентов с различными требованиями к ресурсам. Агенты с **`energy_level ≤ 0`** не могут совершать действия, при **`energy_level ≤ 1.0`** приоритет отдается восстановительным действиям.

| **Действие** | **Стоимость времени** | **Стоимость энергии** | **Минимальный финансовый уровень** | **Описание** |
| --- | --- | --- | --- | --- |
| **PublishPostAction** | 2 | 0.25 | ≥0.0 | Публикация поста в социальной сети |
| **PurchaseLevel1Action** | 1 | 0.0 | ≥1.0 | Покупка товара первого уровня |
| **PurchaseLevel2Action** | 2 | 0.0 | ≥2.0 | Покупка товара второго уровня |
| **PurchaseLevel3Action** | 3 | 0.0 | ≥3.0 | Покупка товара третьего уровня |
| **SelfDevelopmentAction** | 1 | 0.0 | без ограничений | Развитие личных навыков и интересов |

В текущей версии систему используется только действие PublishPostAction.

## Ограничения по финансовым возможностям

- При **`financial_capability ≤ 0.0`**: доступны только SelfDevelopmentAction и PublishPostAction
- При **`financial_capability ≤ 2.0`**: недоступны PurchaseLevel2Action и PurchaseLevel3Action
- При **`financial_capability ≥ 3.0`**: доступны все действия

## Временные бюджеты по профессиям

Временной бюджет определяет количество действий, которые агент может выполнить в день. Значения сбрасываются ежедневно через DailyResetEvent

| Профессия | Временной бюджет |
| --- | --- |
| Unemployed | 5 |
| Student | 3 |
| Worker | 2 |
| Businessman | 4 |
| Developer | 3 |
| Doctor | 2 |
| Teacher | 3 |
| Artist | 4 |
| Politician | 4 |
| Blogger | 4 |
| SpiritualMentor | 4 |
| Philosopher | 4 |

## Расчет частоты событий агентов

Система поддерживает до 43 событий на агента в день через параметр базовой частоты 43*1000/24/60/60, что обеспечивает среднюю частоту около 0,49 событий в секунду на агента. Расчет следующего времени действия агента использует экспоненциальное распределение с модификаторами энергии и временного бюджета .

## Упрощенные алгоритмы виральности

## Формула создания тренда (INITIAL_CALCULATION)

Для расчета начальной виральности тренда используется формула:

`base_score = α × (social_status/5.0) + β × (affinity_score/5.0) + γ × (energy_level/5.0)`

где α=0.5, β=0.3, γ=0.2, с учетом случайного фактора (0.8-1.2) и затухания по времени 4.

## Формула обновления тренда (TREND_UPDATE)

Для обновления виральности после взаимодействий используется формула:

`new_score = min(5.0, base_virality_score + 0.05 × log(total_interactions + 1))`

что обеспечивает логарифмический рост виральности с ограничением максимального значения.

## Energy Recovery

Логика восстановления энергии:

- Если **`energy_level < 3.0`**: устанавливается 5.0
- Иначе: добавляется 2.0 (максимум 5.0)
- Выполняется каждые 24 часа симулированного времени

---

# Структура базы данных

Система использует PostgreSQL с шестью основными таблицами:

**agent_interests** - статичная, генерируется при запуске симуляции

**affinitive_map** - статичная, генерируется при запуске симуляции

**persons** - данные агентов с JSONB полями для exposure_history и interests

**trends** - информация о трендах с базовой вирусностью и уровнем покрытия

**events** - история всех событий симуляции

**person_attribute_history** - изменения атрибутов агентов во времени

**simulation_runs** - метаданные запусков симуляций

**daily_trend_summary** - агрегированная статистика трендов по дням 

## Индексы и оптимизация

- GIN индексы на JSONB поля exposure_history и interests
- Составные индексы на (timestamp, priority) для events
- Партиционирование по simulation_id для масштабируемости

# Транзакционная модель

## Простой Batch Commit

Все операции, включая критические PublishPostAction, используют упрощенную модель batch commit без трехфазного протокола . Массовые обновления обрабатываются пакетами размером 100 операций или принудительным commit каждую минуту симулированного времени .

Метод `process_publish_action_simple()` заменяет сложную логику 3PC на простую обработку с try-catch блоками и batch commit для повышения производительности.

## API спецификация

## REST API Endpoints

Система предоставляет исключительно REST API для всех операций . Основные endpoints включают:

**Управление симуляциями:**

- POST /api/v1/simulations - создание новой симуляции
- GET /api/v1/simulations/{simulation_id} - получение статуса симуляции
- POST /api/v1/simulations/{simulation_id}/start - запуск симуляции
- POST /api/v1/simulations/{simulation_id}/stop - остановка симуляции

**Управление агентами:**

- GET /api/v1/simulations/{simulation_id}/agents - получение списка агентов
- PUT /api/v1/simulations/{simulation_id}/agents/{agent_id} - обновление атрибутов агента

**Управление трендами:**

- GET /api/v1/simulations/{simulation_id}/trends - получение активных трендов
- POST /api/v1/simulations/{simulation_id}/trends - создание нового тренда

## Метрики производительности

- P95 latency обработки событий
- Размер приоритетной очереди событий
- Throughput обработки агентов в секунду
- Использование памяти и CPU ресурсов

## Уровни логирования

- **CRITICAL** - критические ошибки, требующие остановки симуляции
- **ERROR** - ошибки компонентов с возможностью восстановления
- **INFO** - информационные сообщения о ходе симуляции
- **WARN** - предупреждения о потенциальных проблемах

---

# Вопросы и ответы

| Вопрос | Предлагаемое рабочее решение (можно сразу закладывать в код) |
| --- | --- |
| **DDL & миграции** | ✅ Используем **Alembic**; схема лежит в `/db/migrations/0001_init.sql`. Все FK включены: `events.agent_id → persons.id`, `events.trend_id → trends.trend_id`, `persons.simulation_id → simulation_runs.run_id`, `trends.simulation_id → simulation_runs.run_id`. Индексы — PK + составной `(simulation_id, timestamp)` на `events`, партиционирование `events` и `person_attribute_history` по `simulation_id`. |
| **Формула `decide_action()`** | ✅ `score = 0.5·interest + 0.3·social_status/5 + 0.2·random(0-1)`; действие выбирается, если `score > 0.25`. Влияние `time_budget`: действие, чьё `time_cost > remaining_budget`, автоматически отбрасывается. |
| **Batch-commit** | ✅ Порог — **100 изменений** *или* истечение **1 симуляционной минуты** (какое событие раньше). Retry — 3 попытки с экспоненциальным back-off 1 s → 2 s → 4 s; после 3 ошибки пишем ERROR и движемся дальше. |
| **REST JSON-схемы** | ✅ Минимальный контракт:  • `POST /simulations` — тело `{ "num_agents": int, "duration_days": int, "seed": int? }`, ответ `{ "simulation_id": uuid }` (201) • `GET /simulations/{id}` — 200 + статус, 404 если нет. • `GET /trends?simulation_id=` — список DTO `{ trend_id, topic, total_interactions, virality }`. Ошибки: 400 (bad input), 404, 500. |
| **Формат логов** | ✅ JSON-строка в stdout (Docker-friendly) с ключами: `ts`, `level`, `sim_id`, `event_id`, `phase`, `duration_ms`, `msg`. |
| **Конфиги** | ✅ `.env` + `config.yml`. Значения: `TREND_ARCHIVE_THRESHOLD_DAYS=3`, `BATCH_SIZE=100`, `BASE_RATE=43.2`, `CACHE_TTL_MIN=360` (24 ч сим-времени). Горячая перезагрузка **не нужна** — конфиги читаются при старте симуляции. |
| **Очистка кэша `trend_last_interaction_cache`** | ✅ Размер ограничен числом *активных* трендов; при архивировании запись удаляется. Доп. TTL — 3 дня сим-времени. |
| **Мониторинг** | ✅ Prometheus-метрики: `capsim_queue_length`, `capsim_event_latency_ms` (histogram), `capsim_batch_commit_errors_total`. `/metrics` и `/healthz` эндпоинты. Алёрт: `P95 > 10 ms` 3 мин подряд → WARNING. |
| **Graceful shutdown** | ✅ При SIGTERM: • закрываем HTTP-listener;• ждём 30 сек на flush batch-commit;• если не успели — пишем CRITICAL, выходим. |
| **CI/CD** | ✅ Docker-Compose (App, Postgres, Prometheus, Grafana). Линтер `ruff`, типизация `mypy`, тесты `pytest`. |
| **Права к БД** | ✅ Два юзера: `capsim_rw` (app) + `capsim_ro` (Grafana/аналитика). |
| **`SummarizeDailyTrends`** | ✅ Запускается **сразу после** `DailyResetEvent`. Агрегирует: `total_interactions_today`, `avg_virality_today`, `top10_authors_today`, `pct_change_virality`. Записывает в `daily_trend_summary`. |

| Пункт | Принятое решение | Что добавить / изменить в репо |
| --- | --- | --- |
| **1. Партиционирование `trends`** | ❌ Не нужно.  Достаточно PK + индекс `(simulation_id, topic)` | – Удалить упоминания о партициях в DDL-заметках |
| **2. `decide_action_score_threshold`** | `0.25`, но **значение в ENV** | `DECIDE_SCORE_THRESHOLD=0.25` → `.env.example`, прочитать через `os.getenv()` |
| **3. Batch-commit retry** | `RETRY_ATTEMPTS=3`, back-off 1 → 2 → 4 с | Добавить в конфиг: `BATCH_RETRY_ATTEMPTS`, `BATCH_RETRY_BACKOFFS=1,2,4` |
| **4. Алерты** | • WARN, если `P95 > 10 ms` 3 мин подряд  • CRITICAL, если `queue_length > 5000` | Создать Prometheus-rule файл `alerts.yml` |
| **5. Кэш `trend_last_interaction_cache`** | TTL — **2 дня** сим-времени, `max_size = 10 000` | Добавить в конфиг: `CACHE_TTL_MIN=2880`, `CACHE_MAX_SIZE=10000` |
| **6. `daily_trend_summary` поля** | Оставляем базовый набор (без доп. метрик) | DDL уже ок |
| **7. REST security** | Только внутр. сеть; **без auth** и rate-limit | В README пометить «Service must run in trusted network» |
| **8. Graceful shutdown** | `SHUTDOWN_TIMEOUT_SEC` в ENV (default 30 s) | `SHUTDOWN_TIMEOUT_SEC=30` → `.env.example` и в код обработчика SIGTERM |
- **DDL-скрипт** `/db/migrations/0001_init.sql`
    - Полная схема всех таблиц (без партиций для `trends`).
    - Индексы:
        
        ```sql
        sql
        КопироватьРедактировать
        CREATE INDEX idx_events_sim_ts ON events (simulation_id, timestamp);
        CREATE INDEX idx_person_hist_sim_ts ON person_attribute_history (simulation_id, change_timestamp);
        CREATE INDEX idx_trends_sim_topic ON trends (simulation_id, topic);
        
        ```
        
- **`.env.example`** с новыми переменными
    
    ```
    dotenv
    КопироватьРедактировать
    DECIDE_SCORE_THRESHOLD=0.25
    BATCH_RETRY_ATTEMPTS=3
    BATCH_RETRY_BACKOFFS=1,2,4
    CACHE_TTL_MIN=2880
    CACHE_MAX_SIZE=10000
    SHUTDOWN_TIMEOUT_SEC=30
    
    ```
    
- **OpenAPI / JSON-schema** для объявленных REST-ручек.
    
    Минимум — `POST /simulations`, `GET /simulations/{id}`, `GET /trends`.
    
- **Протокол событий** (`BaseEvent`, `EnergyRecoveryEvent`, ...) — класс-каркас с полями и сигнатурой `process(self, engine)`.
- **Bootstrap-скрипт** `scripts/bootstrap.sh`
    1. Выполняет миграции (`alembic upgrade head`).
    2. Загружает `trend_affinity.json`.
    3. Генерирует 1000 агентов и создает запись в `simulation_runs`.
- **Prometheus config & alert rules** (`monitoring/prometheus.yml`, `monitoring/alerts.yml`).
- **Docker-compose** (`docker-compose.yml`) с сервисами:
    - `capsim-app` (Python)
    - `postgres:15`
    - `prometheus` + `grafana` (только для DEV)
- **Тест-каркас** `tests/`
    - `test_create_simulation.py` — проверка 201 и JSON схемы.
    - `test_publish_post.py` — один PublishPostAction → batch-commit.
    - `test_daily_events.py` — EnergyRecovery + DailyReset + SaveDailyTrend.
- **Лог-формат** — пример в `docs/log_format.md`
    
    ```json
    json
    {"ts":"2025-06-23T14:00:00Z","level":"INFO","sim_id":"...","event_id":"...","phase":"PROCESS","duration_ms":7,"msg":"PublishPost processed"}
    
    ```
    
- **README** раздел *Security / network* («API не защищено авторизацией, сервис должен подниматься в изолированной сети или VPN»).