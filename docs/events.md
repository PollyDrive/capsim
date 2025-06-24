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