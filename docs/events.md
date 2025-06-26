# Event Catalogue - CAPSIM 2.0

## Event Types Overview

Система CAPSIM использует приоритетную очередь событий с 5 уровнями приоритета. События обрабатываются в порядке возрастания приоритета, при равных приоритетах - по временным меткам.

## Event Priority Levels

| Priority | EventType | Category | Description |
|----------|-----------|----------|-------------|
| 1 | LAW | External | Законодательные изменения (высший приоритет) |
| 2 | WEATHER | External | Погодные факторы и климатические условия |
| 3 | TREND | Social | Распространение трендов через социальные сети |
| 4 | AGENT_ACTION | Agent | Действия агентов (PublishPostAction, PurchaseAction, etc.) |
| 5 | SYSTEM | System | Системные события (энергия, архивирование, сброс) |

## Алгоритм назначения Timestamp

### 1. Базовый принцип
Все события используют **simulation time** в минутах от начала симуляции:
- `timestamp = 0.0` - начало симуляции
- `timestamp = 60.0` - 1 час симуляции  
- `timestamp = 1440.0` - 1 день (24 часа) симуляции

### 2. Системные события (фиксированные интервалы)
```python
# Восстановление энергии каждые 6 часов
EnergyRecoveryEvent(timestamp=current_time + 360.0)

# Ежедневный сброс временных бюджетов  
DailyResetEvent(timestamp=current_time + 1440.0)

# Сохранение дневной статистики
SaveDailyTrendEvent(timestamp=current_time + 1440.0)
```

### 3. Действия агентов (с задержками)
```python
# Seed события: равномерно в первые 60 минут с jitter
base_time = (i * 60.0 / selected_agents_count)
jitter = random.uniform(-5.0, 5.0)  
timestamp = current_time + max(1.0, base_time + jitter)

# Ответные действия: случайная задержка 1-30 минут
delay = random.uniform(1.0, 30.0)
timestamp = current_time + delay

# Влияние трендов: задержка 10-60 минут  
response_delay = random.uniform(10.0, 60.0)
timestamp = current_time + response_delay
```

### 4. События трендов (цепочечные)
```python
# TrendInfluenceEvent всегда через 5 минут после PublishPost
influence_timestamp = publish_timestamp + 5.0

# Каскадные ответы с экспоненциальным распределением
next_response = current_time + random.expovariate(1.0/15.0)  # λ=15 минут
```

### 5. Ограничения времени
- **Минимальная задержка**: 1.0 минута (для предотвращения одновременных событий)
- **Максимальная очередь**: 5000 событий (graceful degradation)
- **Временной бюджет**: агенты ограничены 43 действиями в день

## Detailed Event Specifications

### LAW Events (Priority 1)
**Category**: External  
**Description**: Критические события от внешних факторов, влияющие на всю симуляцию  
**Processing**: Немедленная обработка с приостановкой других событий  
**Examples**: Новые регуляции, изменения законодательства

### WEATHER Events (Priority 2)  
**Category**: External  
**Description**: Погодные условия, влияющие на настроение и активность агентов  
**Processing**: Массовые изменения атрибутов агентов  
**Examples**: Сезонные изменения, экстремальные погодные условия

### TREND Events (Priority 3)
**Category**: Social  
**Description**: Распространение информационных трендов через социальные связи  
**Processing**: Фильтрация аудитории, расчет влияния, обновление атрибутов  
**Components**:
- `TrendProcessor` - создание и модификация трендов
- `PersonInfluence` - расчет воздействия на агентов
- **Coverage Levels**: Low/Middle/High по социальной значимости темы

### AGENT_ACTION Events (Priority 4)
**Category**: Agent  
**Description**: Действия индивидуальных агентов в симуляции  

| Action | Time Cost | Energy Cost | Min Financial Level | Status |
|--------|-----------|-------------|-------------------|---------|
| **PublishPostAction** | 2 | 1.5 | ≥0.0 | ✅ Active |
| **PurchaseLevel1Action** | 1 | 0.0 | ≥1.0 | 🚧 Future |
| **PurchaseLevel2Action** | 2 | 0.0 | ≥2.0 | 🚧 Future |  
| **PurchaseLevel3Action** | 3 | 0.0 | ≥3.0 | 🚧 Future |
| **SelfDevelopmentAction** | 1 | 0.0 | No limit | 🚧 Future |

**Processing**: Проверка ограничений → выполнение действия → обновление состояния агента

### SYSTEM Events (Priority 5)
**Category**: System  
**Description**: Автоматические системные операции по расписанию  

| Event | Frequency | Description | Implementation |
|-------|-----------|-------------|----------------|
| **EnergyRecoveryEvent** | 24h | Восстановление энергии агентов | Direct method call |
| **DailyResetEvent** | 24h | Сброс временных бюджетов | Direct method call |
| **SaveDailyTrend** | 24h | Сохранение дневной статистики | Direct method call |
| **ArchiveInactiveTrends** | 24h | Архивирование неактивных трендов (3+ дня) | Direct method call |

## Event Processing Flow

1. **Generation**: События создаются агентами или системными компонентами
2. **Queueing**: Добавление в приоритетную очередь с timestamp
3. **Priority Sorting**: Сортировка по priority → timestamp  
4. **Processing**: SimulationEngine.process_event() обрабатывает по типу
5. **State Update**: Изменения агрегируются для batch-commit
6. **Persistence**: Batch-commit каждые 100 операций или 1 минуту

## Event Rate Limiting

- **Max queue size**: 1000 событий
- **Agent event rate**: до 43 событий на агента в день  
- **Base frequency**: экспоненциальное распределение с λ = 43*1000/24/60/60 ≈ 0.49 events/sec/agent
- **Modifiers**: energy_level и time_budget влияют на частоту генерации

## Performance Targets

- **P95 latency**: < 10ms для обработки одного события
- **Throughput**: поддержка 1000 агентов × 43 события/день = 43000 событий/день
- **Queue overflow**: graceful degradation при превышении 5000 событий
- **Batch commit**: автоматический commit каждую минуту симулированного времени 