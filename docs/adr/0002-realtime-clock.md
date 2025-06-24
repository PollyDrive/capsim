# ADR-0002: Realtime Clock Architecture

## Status
Proposed

## Context

В настоящее время CAPSIM использует дискретно-событийную симуляцию с максимальной скоростью обработки — 120 симуляционных минут обрабатываются за 2 реальных секунды. Такой режим эффективен для массового тестирования и анализа, но не подходит для:

- Realtime мониторинга динамики событий
- Демонстрации постепенного развития социальных трендов
- Интерактивного наблюдения за агентами
- Отладки timing-зависимых алгоритмов

Требуется добавить возможность запуска симуляции в «реальном времени», когда виртуальные события наступают синхронно (или с заданным ускорением) с настенными часами.

## Decision

### Clock Abstraction Protocol

Введем абстракцию Clock с двумя реализациями:

```python
class Clock(Protocol):
    def now(self) -> float:
        """Возвращает текущее время симуляции в минутах"""
        
    async def sleep_until(self, timestamp: float) -> None:
        """Ожидает наступления указанного времени симуляции"""
```

- **SimClock** (legacy) — без задержек, максимальная скорость
- **RealTimeClock** — с `await asyncio.sleep(delay)` для синхронизации

### Speed Factor Configuration

Добавляется ENV переменная `SIM_SPEED_FACTOR`:
- `SIM_SPEED_FACTOR=1` — реальное время (1 сим-минута = 1 реальная минута)
- `SIM_SPEED_FACTOR=60` — ускорение в 60 раз (1 сим-минута = 1 реальная секунда)
- `SIM_SPEED_FACTOR=0.5` — замедление в 2 раза (1 сим-минута = 2 реальные минуты)

### Engine Async Conversion

SimulationEngine.run_simulation() переводится в async:
- Добавление `await self.clock.sleep_until(event.timestamp_real)` перед обработкой событий
- Конвертация `sim_ts` в `timestamp_real = start_real + sim_minutes*60/SIM_SPEED_FACTOR`
- Сохранение обратной совместимости через Clock interface

### Batch Commit Adjustment

Логика batch-commit адаптируется для realtime:
- Flush по времени: каждые `60/SIM_SPEED_FACTOR` реальных секунд
- Flush по размеру: каждые 100 операций (без изменений)
- Предотвращение накопления backlog при медленной скорости

### Metrics Impact

Метрики адаптируются для realtime режима:
- `EVENT_LATENCY` измеряется в wall-clock времени
- Добавляется `SIMULATION_DRIFT` — отклонение от планового времени
- `QUEUE_SIZE` мониторится для предотвращения переполнения

## Consequences

### Положительные:
- Возможность realtime наблюдения за развитием трендов
- Гибкость настройки скорости симуляции
- Сохранение производительности в fast-режиме
- Упрощение отладки timing-критичных компонентов
- Демонстрационные возможности для stakeholders

### Отрицательные:
- Усложнение архитектуры добавлением async/await
- Потенциальный drift при высокой нагрузке
- Дополнительная сложность тестирования async кода
- Риск deadlock при неправильной обработке исключений

### Риски и митигация:

**Риск**: Накопление задержек (drift) при SIM_SPEED_FACTOR=1
**Митигация**: Мониторинг drift через Prometheus, автоматический catch-up механизм

**Риск**: Производительность async кода при fast-режиме
**Митигация**: SimClock с no-op sleep_until(), профилирование async overhead

**Риск**: Проблемы совместимости с существующими тестами
**Митигация**: Тесты используют SimClock по умолчанию, отдельные RT-тесты

### KPI Impact:
- Latency в realtime режиме: P95 < 100ms (vs 10ms в fast-режиме)
- Memory overhead: +5-10% для async корутин
- CPU overhead: +2-3% для clock операций

## Implementation Plan

1. **Phase 1**: Clock interface + SimClock + RealTimeClock
2. **Phase 2**: Engine async conversion + timestamp_real mapping
3. **Phase 3**: ENV configuration + batch-commit adjustment
4. **Phase 4**: Metrics adaptation + drift monitoring
5. **Phase 5**: Testing + documentation

## Roll-out Strategy

- **Staging**: тестирование с SIM_SPEED_FACTOR=10 на малых симуляциях
- **Production**: feature flag для переключения режимов
- **Monitoring**: dashboard для drift и performance метрик
- **Fallback**: автоматический откат к SimClock при критических ошибках 