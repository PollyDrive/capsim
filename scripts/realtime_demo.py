#!/usr/bin/env python3
"""
Демонстрационный скрипт для тестирования realtime режима CAPSIM.
"""

import asyncio
import time
import os
import sys
from typing import Optional
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from capsim.common.clock import RealTimeClock, SimClock
from capsim.common.settings import settings
from capsim.engine.simulation_engine import SimulationEngine


class MockDatabaseRepository:
    """Mock repository для демонстрации без реальной БД."""
    
    def __init__(self):
        self.events = []
        self.persons = []
        self.trends = []
        
    async def create_simulation_run(self, **kwargs):
        """Mock создания симуляции."""
        from uuid import uuid4
        from dataclasses import dataclass
        
        @dataclass
        class MockRun:
            run_id: str
        
        return MockRun(run_id=str(uuid4()))
        
    async def load_affinity_map(self):
        """Mock affinity map."""
        return {
            "Teacher": {"Science": 0.8, "Culture": 0.6, "Economic": 0.3},
            "Developer": {"Science": 0.9, "Economic": 0.5, "Culture": 0.4},
            "Artist": {"Culture": 0.9, "Spiritual": 0.6, "Science": 0.2},
            "Blogger": {"Culture": 0.7, "Economic": 0.6, "Sport": 0.5}
        }
        
    async def get_active_trends(self, simulation_id):
        """Mock активных трендов."""
        return []
        
    async def bulk_create_persons(self, persons):
        """Mock создания агентов."""
        self.persons.extend(persons)
        print(f"✓ Создано {len(persons)} агентов")
        
    async def batch_commit_states(self, updates):
        """Mock batch commit."""
        print(f"✓ Batch commit: {len(updates)} обновлений")
        
    async def create_event(self, event):
        """Mock создания события."""
        self.events.append(event)
        
    async def update_simulation_status(self, simulation_id, status, timestamp):
        """Mock обновления статуса."""
        print(f"✓ Симуляция {simulation_id} - статус: {status}")


async def run_realtime_demo(speed_factor: float = 10.0, duration_minutes: int = 5):
    """
    Запуск демонстрации realtime режима.
    
    Args:
        speed_factor: Коэффициент ускорения (10 = 10x быстрее реального времени)
        duration_minutes: Длительность симуляции в минутах
    """
    print(f"🚀 CAPSIM Realtime Demo")
    print(f"Speed Factor: {speed_factor}x")
    print(f"Duration: {duration_minutes} simulation minutes")
    print(f"Expected real time: {duration_minutes * 60 / speed_factor:.1f} seconds")
    print("-" * 50)
    
    # Создаем mock repository
    mock_repo = MockDatabaseRepository()
    
    # Создаем realtime clock
    clock = RealTimeClock(speed_factor=speed_factor)
    
    # Создаем симуляционный движок
    engine = SimulationEngine(mock_repo, clock)
    
    # Временно переопределяем настройки
    original_realtime = os.environ.get('ENABLE_REALTIME')
    original_speed = os.environ.get('SIM_SPEED_FACTOR')
    
    os.environ['ENABLE_REALTIME'] = 'true'
    os.environ['SIM_SPEED_FACTOR'] = str(speed_factor)
    
    try:
        print("⏱️  Начинаем инициализацию...")
        start_time = time.time()
        
        # Инициализируем с небольшим количеством агентов
        await engine.initialize(num_agents=20)
        
        init_time = time.time() - start_time
        print(f"✓ Инициализация завершена за {init_time:.2f}s")
        
        print(f"⚡ Запускаем realtime симуляцию...")
        print(f"   Следите за временными метками...")
        
        simulation_start = time.time()
        
        # Запускаем симуляцию
        await engine.run_simulation(duration_days=duration_minutes/1440.0)
        
        total_time = time.time() - simulation_start
        expected_time = duration_minutes * 60 / speed_factor
        accuracy = abs(total_time - expected_time) / expected_time * 100
        
        print("-" * 50)
        print(f"✅ Симуляция завершена!")
        print(f"Expected time: {expected_time:.2f}s")
        print(f"Actual time:   {total_time:.2f}s")
        print(f"Accuracy:      {100-accuracy:.1f}%")
        print(f"Events created: {len(mock_repo.events)}")
        
        if accuracy < 10:
            print("🎯 Отличная точность timing!")
        elif accuracy < 20:
            print("👍 Хорошая точность timing")
        else:
            print("⚠️  Timing может быть улучшен")
            
    finally:
        # Восстанавливаем оригинальные настройки
        if original_realtime:
            os.environ['ENABLE_REALTIME'] = original_realtime
        else:
            os.environ.pop('ENABLE_REALTIME', None)
            
        if original_speed:
            os.environ['SIM_SPEED_FACTOR'] = original_speed  
        else:
            os.environ.pop('SIM_SPEED_FACTOR', None)


async def compare_modes():
    """Сравнение fast и realtime режимов."""
    print("🔬 Сравнение режимов симуляции")
    print("=" * 50)
    
    mock_repo = MockDatabaseRepository()
    
    # Тест fast режима
    print("1️⃣  Fast Mode (SimClock)")
    sim_clock = SimClock()
    engine_fast = SimulationEngine(mock_repo, sim_clock)
    
    start_time = time.time()
    await engine_fast.initialize(num_agents=50)
    await engine_fast.run_simulation(duration_days=10/1440.0)  # 10 минут
    fast_time = time.time() - start_time
    
    print(f"   10 sim-minutes completed in {fast_time:.3f}s")
    
    # Тест realtime режима
    print("2️⃣  Realtime Mode (10x speed)")
    real_clock = RealTimeClock(speed_factor=10.0)
    engine_real = SimulationEngine(mock_repo, real_clock)
    
    os.environ['ENABLE_REALTIME'] = 'true'
    
    start_time = time.time()
    await engine_real.initialize(num_agents=50)
    await engine_real.run_simulation(duration_days=1/1440.0)  # 1 минута
    real_time = time.time() - start_time
    
    print(f"   1 sim-minute completed in {real_time:.3f}s (expected ~6s)")
    
    # Сравнение
    print("\n📊 Результаты:")
    print(f"   Fast mode throughput: {10/fast_time:.1f} sim-min/sec")
    print(f"   Realtime accuracy: {abs(real_time - 6.0)/6.0*100:.1f}% deviation")
    
    os.environ.pop('ENABLE_REALTIME', None)


async def main():
    """Главная функция демо."""
    import argparse
    
    parser = argparse.ArgumentParser(description='CAPSIM Realtime Demo')
    parser.add_argument('--speed', type=float, default=10.0, 
                       help='Speed factor (default: 10x)')
    parser.add_argument('--duration', type=int, default=2,
                       help='Simulation duration in minutes (default: 2)')
    parser.add_argument('--compare', action='store_true',
                       help='Compare fast vs realtime modes')
    
    args = parser.parse_args()
    
    if args.compare:
        await compare_modes()
    else:
        await run_realtime_demo(args.speed, args.duration)


if __name__ == "__main__":
    asyncio.run(main()) 