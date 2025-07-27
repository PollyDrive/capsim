# Техническое задание CAPSIM v1.9: Система позитивных/негативных трендов и PostEffect

## Обзор версии v1.9

Версия v1.9 вводит кардинальные изменения в механику влияния трендов на агентов, добавляет систему оценки эффективности постов (PostEffect) и реализует суточные циклы активности с ночным восстановлением. Основная цель — создать более реалистичную и сбалансированную модель социального взаимодействия.

## Ключевые нововведения

## 1. Система позитивных/негативных трендов

- Добавление свойства `sentiment` к трендам ("Positive"/"Negative")
- Случайное присвоение тональности при создании тренда (50/50)
- Дифференцированное воздействие на читателей в зависимости от тональности и соответствия интересам

## 2. PostEffect система

- Замена мгновенного воздействия на автора агрегированным эффектом
- Расчет влияния на автора на основе охвата аудитории и суммарного энергетического воздействия
- Логарифмическое масштабирование для учета виральности

## 3. Суточные циклы и ночное восстановление

- 16-часовой цикл активности (08:00-00:00)
- 8-часовая "ночь" с блокировкой действий
- Восстановление энергии и финансов в начале нового дня

## 4. Ребалансировка экономики действий

- Снижение энергетических затрат на публикации
- Пересмотр системы покупок L1/L2/L3
- Оптимизация пассивного восстановления энергии

## Детальные технические требования

## 1. Модификация класса Trend

`pythonclass Trend:
    *# Существующие поля...*
    sentiment: str  *# "Positive" или "Negative"*`

**Изменения в базе данных:**

- Добавить поле `sentiment VARCHAR(10)` в таблицу `trends`
- Обновить индексы для поддержки фильтрации по тональности

## 2. Обновление PersonInfluence.processpost()

**Новая логика:**

- Убрать мгновенные эффекты для автора поста
- Добавить случайное присвоение `sentiment` при создании тренда
- Реализовать дифференцированное воздействие на читателей

**Матрица воздействий на читателей:**

| Тип тренда | Соответствие интересам | Восприимчивость | Энергия | Примечание |
| --- | --- | --- | --- | --- |
| Positive | Да (affinity > 3) | +0.01 | +0.02 | Позитивный контент по интересам |
| Positive | Нет (affinity ≤ 3) | 0 | +0.015 | Нейтральный позитив |
| Negative | Да (affinity > 3) | +0.01 | -0.015 | Негатив по интересам |
| Negative | Нет (affinity ≤ 3) | +0.01 | -0.01 | Общий негатив |

## 3. Реализация PostEffect системы

**Новый метод:**

`def calculate_author_post_effect(self, author: Person, trend: Trend, audience_effects: List[StateUpdate]) -> StateUpdate:
    total_reach = len(audience_effects)
    total_energy_change = sum(effect.attributechanges.get("energylevel", {}).get("delta", 0) 
                             for effect in audience_effects)
    
    reach_multiplier = math.log(total_reach + 1) / math.log(10)
    sentiment_multiplier = 1.0 if trend.sentiment == "Positive" else -1.0
    
    post_effect_delta = (total_energy_change * reach_multiplier * sentiment_multiplier) / 50
    post_effect_delta = max(-1.0, min(1.0, post_effect_delta))
    
    return StateUpdate(
        personid=author.id,
        attributechanges={"socialstatus": {"delta": post_effect_delta}},
        reason="PostEffect",
        sourcetrendid=trend.trendid
    )`

## 4. Суточные циклы

**Новые события:**

- `NightCycleEvent` — блокировка активности в 00:00
- `MorningRecoveryEvent` — восстановление в 08:00

**Модификация can_perform_action():**

`pythondef can_perform_action(self, action_type: str, current_time: int) -> bool:
    *# Проверка времени суток*
    day_time = current_time % 1440  *# минуты в дне*
    if 0 <= day_time < 480:  *# 00:00 - 08:00*
        return False
    
    *# Существующие проверки...*`

## 5. Ребалансировка экономики

**Новые значения в config/actions.yaml:**

`textPOST_ACTION:
  energy_cost: -0.20
  time_cost: -0.15
  social_bonus: 0.05
  cooldown_minutes: 40

SELF_DEV_ACTION:
  time_cost: -0.80
  energy_bonus: 0.45
  social_bonus: 0.10
  cooldown_minutes: 30

PURCHASE_L1:
  energy_bonus: 0.30
  time_cost: -0.10
  cost_range: [0.1, 1.0]

PURCHASE_L2:
  energy_bonus: 0.45
  time_cost: -0.10
  social_bonus: 0.05
  cost_range: [1.1, 2.4]

PURCHASE_L3:
  energy_bonus: 0.70
  time_cost: -0.10
  social_bonus: 0.20
  cost_range: [2.5, 3.5]`

**Ночное восстановление:**

`textNIGHT_RECOVERY:
  energy_bonus: 1.2
  financial_bonus: 1.0`

## Изменения в архитектуре

## 1. Новые классы событий

- `NightCycleEvent` — управление ночным циклом
- `MorningRecoveryEvent` — утреннее восстановление

## 2. Модификация существующих классов

- `TrendInfluenceEvent` — интеграция PostEffect расчетов
- `Person` — добавление флага `is_night_mode`
- `SimulationEngine` — планирование суточных событий

## 3. Обновление базы данных

`sqlALTER TABLE trends ADD COLUMN sentiment VARCHAR(10) DEFAULT 'Positive';
CREATE INDEX idx_trends_sentiment ON trends(sentiment);`