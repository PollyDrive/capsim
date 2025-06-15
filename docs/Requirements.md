## Техническое задание: MVP Генератора Данных

## 1. Цель и объем MVP: Расширенный генератор данных

**Цель MVP**: Создание продвинутой системы для генерации связанных, многомерных транзакционных данных. Система эмулирует поведение 1000 виртуальных агентов, которые управляют своими ресурсами (время, энергия, финансы), совершают разнообразные действия и взаимодействуют в рамках простой экономической модели. Основная задача — получить на выходе датасеты, пригодные для отработки сложных дата-инженерных практик, анализа временных рядов, сегментации и выявления поведенческих паттернов.

**Ограничения MVP**:

- Пользователи: 1000 виртуальных агентов.
- Профессии сведены к 4 кластерам.
- Внешние события управляются через `god mode`.
- Технологии: только батч-обработка (без потоков на стороне генератора).

---

## 2. Ролевая модель и атрибуты

### 2.1. Кластеры профессий

| Cluster | Примеры профессий |
| --- | --- |
| **Worker** | ShopClerk, Artisan, Developer |
| **Social** | Politician, Blogger, Marketer, Businessman |
| **Spiritual** | SpiritualMentor, Philosopher |
| **Other** | Student, Unemployed, Athlete, Fraudster |

## 2.2. Атрибуты персонажа (Person)

| **Поле** | **Тип** | **Описание** | **Изменение** |
| --- | --- | --- | --- |
| **`id`** | UUID | Уникальный идентификатор |  |
| **`first_name`** | **STRING** | **Имя агента** | **Новое поле** |
| **`last_name`** | **STRING** | **Фамилия агента** | **Новое поле** |
| **`middle_name`** | **STRING | None** | **Отчество (опционально, для некоторых локалей)** | **Новое поле (рекомендация)** |
| **`age`** | INT | Возраст агента |  |
| **`gender`** | ENUM | Пол агента (**`Male`**, **`Female`**) |  |
| **`cluster`** | ENUM | Worker, Social, Spiritual, Other |  |
| **`profession`** | ENUM | Конкретная профессия |  |
| **`financial_capability`** | FLOAT | Покупательская способность |  |
| **`trend_receptivity`** | FLOAT | Склонность подхватывать тренды |  |
| **`social_status`** | FLOAT | Влиятельность |  |
| **`energy_level`** | FLOAT | Суточная энергия |  |
| **`time_budget`** | INT | Временные слоты на день |  |

## 2.3. Распределение персонажей по профессиям

Ниже приведена таблица с 13 профессиями, количеством агентов и долей от общего населения (1 000):

| Profession | Cluster | Count | Share (%) |
| --- | --- | --- | --- |
| ShopClerk | Worker | 180 | 18.0 |
| Artisan | Worker | 70 | 7.0 |
| Developer | Worker | 120 | 12.0 |
| Politician | Social | 10 | 1.0 |
| Blogger | Social | 50 | 5.0 |
| Marketer | Social | 60 | 6.0 |
| Businessman | Social | 80 | 8.0 |
| SpiritualMentor | Spiritual | 30 | 3.0 |
| Philosopher | Spiritual | 20 | 2.0 |
| Student | Other | 200 | 20.0 |
| Unemployed | Other | 90 | 9.0 |
| Athlete | Other | 80 | 8.0 |
| Fraudster | Other | 10 | 1.0 |

## 2.4. Диапазоны распределения атрибутов по профессиям

*(Таблица 2.4 из исходного ТЗ остается актуальной, но значения теперь будут начальными точками для FLOAT атрибутов. Рекомендуется установить начальный `financial_capability` ближе к середине диапазона, чтобы дать пространство для роста и падения).*

Для каждой профессии задаём минимальные и максимальные значения ключевых атрибутов персонажа.

| Profession | financial_capability | trend_receptivity | social_status | energy_level | time_budget |
| --- | --- | --- | --- | --- | --- |
| ShopClerk | 1–3 | 2–4 | 1–2 | 2–5 | 1–3 |
| Artisan | 2–4 | 3–5 | 1–2 | 2–5 | 2–4 |
| Developer | 3–5 | 2–4 | 2–4 | 2–5 | 2–4 |
| Politician | 4–5 | 2–4 | 4–5 | 2–4 | 1–3 |
| Blogger | 2–4 | 4–5 | 3–5 | 2–5 | 3–4 |
| Marketer | 3–4 | 3–5 | 3–4 | 2–5 | 2–4 |
| Businessman | 4–5 | 2–4 | 3–5 | 2–5 | 1–3 |
| SpiritualMentor | 1–3 | 2–5 | 2–5 | 3–5 | 2–4 |
| Philosopher | 1–3 | 1–3 | 1–4 | 2–4 | 2–4 |
| Student | 1–2 | 2–4 | 1–2 | 3–5 | 1–4 |
| Unemployed | 1–2 | 1–3 | 1–2 | 1–3 | 3–5 |
| Athlete | 2–4 | 1–3 | 1–4 | 4–5 | 2–4 |
| Fraudster | 2–5 | 1–3 | 1–4 | 2–4 | 3–5 |

## 2.5. Генерация демографических атрибутов

Для создания реалистичного населения при инициализации симуляции используются следующие правила:

- **`first_name`, `last_name`, `middle_name`, `gender`**: Генерируются с помощью библиотеки **Faker** для конкретной локали (например, **`ru_RU`**). Пол присваивается вместе с именем для соответствия.
    - **`agent.first_name = faker.first_name()`**
    - **`agent.last_name = faker.last_name()`**
    - **`agent.middle_name = faker.middle_name()`** (если применимо для локали)
- **`age`**: Генерируется с использованием **усеченного нормального распределения**.
    - Параметры: min=18, max=75, mean=~38, std=~12.

---

## 3. Базовые действия, их стоимость и механика

Агенты могут выполнять **несколько действий в день**, пока у них хватает `time_budget` и `energy_level`.

## 3.1. Категории действий и их "стоимость"

| Категория | ActionEvent | `time_cost` | `energy_cost` | Описание |
| --- | --- | --- | --- | --- |
| **Consumption** | `PurchaseGoods_Cheap` | 1 | 0.5 | Покупка еды, базовых вещей |
|  | `PurchaseGoods_Medium` | 2 | 0.5 | Покупка техники, билетов |
|  | `PurchaseGoods_Expensive` | 3 | 1.0 | Покупка недвижимости, транспорта |
| **Expression** | `PublishPost` | 2 | 1.5 | Публикация контента |
| **SelfDevelopment** | `PerformSelfDevelopment` | 2 | **-2.0 (gain)** | Восстановление энергии (отдых, медитация) |

## 3.2. Механика влияния действий

- **`PurchaseGoods_Cheap`**:
    - **Условие доступности:** Всегда.
    - **Эффект:** `financial_capability -= 0.2`; `energy_level += 0.3`.
- **`PurchaseGoods_Medium`**:
    - **Условие доступности:** `financial_capability >= 3.0`.
    - **Эффект:** `financial_capability -= 1.5`; `social_status += 0.1`.
- **`PurchaseGoods_Expensive`**:
    - **Условие доступности:** `financial_capability >= 7.0` И `cluster` НЕ `Unemployed`.
    - **Эффект:** `financial_capability -= 4.0`; `social_status += 0.5`.
- **`PublishPost`**:
    - **Стоимость публикации (предварительная):** `social_status -= 0.1`.
    - **Эффект на аудиторию:** (см. Раздел 5 "Публикации и охват"). `trend_receptivity` и `social_status` целевых агентов увеличиваются на `virality_score * 0.05` (уменьшенный коэффициент для более плавной динамики).
- **`PerformSelfDevelopment`**:
    - **Эффект:** `energy_level += 2.0` (но не выше максимума 5.0).

---

## 4. Ежедневный доход и логика принятия решений

Демографические данные могут влиять на экономику и поведение агента.

## 4.1. Механизм дохода

Карта **`income_map`** может учитывать не только профессию, но и возраст.

- **Базовый доход:** Определяется профессией.
- **Возрастной коэффициент:** Применяется поверх базового дохода.
    - Пример логики: **`final_income = base_income * (1 + (agent.age - 35) * 0.01)`**. Это имитирует рост дохода с опытом до определенного момента.

В начале каждого дня (перед фазой действий) агенты получают доход.

- Создается карта `income_map = {profession: daily_income_value}`.
    - Пример: `{"Developer": 0.4, "Businessman": 0.5, "ShopClerk": 0.2, "Student": 0.1, "Unemployed": 0.05}`.
- Логика: `agent.financial_capability += income_map[agent.profession]`. `financial_capability` ограничивается сверху значением 10.0.

## 4.2. Логика выбора и выполнения действий

Агент пытается выполнить действия в порядке **приоритета**, пока у него есть `time_budget` и `energy_level`.

**Псевдокод цикла принятия решений агентом на день:**

`*# Начало дня для агента*
current_time_budget = agent.time_budget *# Копируем начальный бюджет на день*
current_energy_level = agent.energy_level

*# 1. Приоритет: Саморазвитие, если энергия низкая*
if current_energy_level < 1.5 and current_time_budget >= PerformSelfDevelopment.time_cost:
    agent.perform(PerformSelfDevelopment)
    current_time_budget -= PerformSelfDevelopment.time_cost
    current_energy_level += PerformSelfDevelopment.energy_gain *# Энергия восстанавливается от действия# 2. Приоритет: Публикация для социальных агентов*
if agent.cluster == 'Social' and agent.social_status > 3.0 and \
   current_time_budget >= PublishPost.time_cost and \
   current_energy_level >= PublishPost.energy_cost and \
   random.choice([True, False]): *# Не каждый день*
    agent.perform(PublishPost)
    current_time_budget -= PublishPost.time_cost
    current_energy_level -= PublishPost.energy_cost

*# 3. Приоритет: Дорогие покупки (если очень хочется и можется)*
if agent.financial_capability >= 7.0 and agent.cluster != 'Unemployed' and \
   current_time_budget >= PurchaseGoods_Expensive.time_cost and \
   current_energy_level >= PurchaseGoods_Expensive.energy_cost and \
   random.random() < 0.1: *# Редкое событие*
    agent.perform(PurchaseGoods_Expensive)
    current_time_budget -= PurchaseGoods_Expensive.time_cost
    current_energy_level -= PurchaseGoods_Expensive.energy_cost

*# 4. Приоритет: Средние покупки*
if agent.financial_capability >= 3.0 and \
   current_time_budget >= PurchaseGoods_Medium.time_cost and \
   current_energy_level >= PurchaseGoods_Medium.energy_cost and \
   random.random() < 0.3: *# Не каждый день*
    agent.perform(PurchaseGoods_Medium)
    current_time_budget -= PurchaseGoods_Medium.time_cost
    current_energy_level -= PurchaseGoods_Medium.energy_cost

*# 5. Базовое действие: Дешевые покупки (если есть ресурсы)*
if current_time_budget >= PurchaseGoods_Cheap.time_cost and \
   current_energy_level >= PurchaseGoods_Cheap.energy_cost:
    agent.perform(PurchaseGoods_Cheap)
    *# Обновление current_time_budget и current_energy_level не обязательно, если это последнее действие в приоритете*`

**Псевдокод с демографическими факторами:**

`*# ... (начало цикла)*`

`*# Агент с низкой энергией или в "кризисе среднего возраста" склонен к саморазвитию*
if agent.energy_level < 1.5 or (38 <= agent.age <= 45 and random.random() < 0.1):
    agent.perform(PerformSelfDevelopment)
    *# ...# Молодые агенты более склонны к публикациям для набора статуса*
if (agent.cluster == 'Social' or agent.age < 25) and agent.social_status < 4.0:
    if *#... есть ресурсы и желание*
        agent.perform(PublishPost)
        *# ...# Покупка дорогих вещей чаще происходит в зрелом возрасте*
if agent.financial_capability >= 7.0 and 35 <= agent.age <= 55:
    if *#... есть ресурсы и желание*
        agent.perform(PurchaseGoods_Expensive)
        *# ...# ... (остальная логика)*`

*Эта логика — пример. Ее можно настраивать, добавлять вероятности, менять порядок приоритетов. Главное — она создает осмысленную последовательность транзакций.*

---

## 5. Публикации и охват

- **Параметры:** `coverage_level` (Low, Middle, High) и `virality_score` (FLOAT 1.0–5.0).
- **Логика применения:**
    1. **Стоимость публикации:** Перед расчетом бонусов, сам акт публикации требует затрат социального капитала. **Стоимость публикации:** `social_status` автора **снижается на 0.1**.
    2. Собирается список `target_ids` по `coverage_level`.
    3. Для каждого `target_id` генерятся дочерние события, которые повышают атрибуты:
        - `trend_receptivity += virality_score * 0.05`
        - `social_status += virality_score * 0.05`
    4. Значения округляются (например, до 2 знаков после запятой) и ограничиваются диапазоном 1.0–5.0.

---

## 6. Внешние факторы и «God Mode»

*(Логика остается такой же, как в v2.0, с относительным влиянием финансовых факторов и абсолютным для других. Тип данных `strength` для факторов также может быть FLOAT для более тонкой настройки.)*

- Сущность `ExternalFactor` остается без изменений.
- **Сценарии воздействия:**
    - `Law`:
        - **`TaxIncrease`**: Снижает `financial_capability` всех агентов на `(strength * 5)%`.
        - **`Subsidy`**: Увеличивает `financial_capability` всех агентов на `(strength * 5)%`.
        - `AdvertisingBan`, `Curfew`: Влияние на `social_status` и `time_budget` остается абсолютным (например, `strength * 0.5`).
    - `Trend`:
        - `StockBoom`: Влияет на агентов с `financial_capability > 2.0`, увеличивая их `financial_capability` на `strength * 0.5`.
        - Другие тренды (`ViralDance`, `HealthFad` и т.д.) повышают `trend_receptivity`, `social_status` или `energy_level` на `strength * 0.1` или `strength * 0.2`.

---

## 7. Суточная батч-логика

1. **Начало дня (State Update):**
    - **Доход:** Агенты получают доход согласно их профессии.
    - **Восстановление бюджетов:** `time_budget` восстанавливается до своего максимального значения для каждого агента. `energy_level` может частично восстанавливаться (например, `+= 1.0`, но не выше максимума), если не было `PerformSelfDevelopment`.
2. **Загрузка глобальных факторов:** Загрузка активных записей из `ExternalFactor`.
3. **Цикл действий агентов:**
    - Для каждого агента выполняется логика выбора и выполнения действий (см. Раздел 4.2), пока у него есть ресурсы (`time_budget`, `energy_level`) и желание действовать.
    - Все совершенные действия записываются в таблицу `Event`.
4. **Обработка последствий событий:**
    - Система обрабатывает все события из таблицы `Event`.
    - События `PublishPost` генерируют дочерние события-просмотры, которые влияют на `trend_receptivity` и `social_status` целевой аудитории.
5. **Применение глобальных факторов:**
    - Применяются эффекты от активных `ExternalFactor` ко всем затронутым агентам.
6. **Финализация атрибутов:** Окончательный пересчет и ограничение всех атрибутов агентов (например, `financial_capability` не может быть < 0).
7. **Архивация:** Таблицы `Event` и `FactorEvent` архивируются.