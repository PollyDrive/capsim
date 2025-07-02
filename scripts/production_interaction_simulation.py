#!/usr/bin/env python3
"""
Production Interactive Simulation - Core Engine Dev
Реальная ускоренная симуляция с взаимодействиями на production БД
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from capsim.engine.simulation_engine import SimulationEngine
from capsim.db.repositories import DatabaseRepository
from capsim.common.settings import settings


class InteractionMonitor:
    """Мониторинг взаимодействий в реальном времени."""
    
    def __init__(self):
        self.start_time = time.time()
        self.checkpoints = []
    
    def add_checkpoint(self, sim_time: float, stats: Dict[str, Any]):
        """Добавляет контрольную точку с метриками."""
        real_time = time.time() - self.start_time
        checkpoint = {
            'sim_time': sim_time,
            'real_time': real_time,
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            **stats
        }
        self.checkpoints.append(checkpoint)
        
        # Выводим прогресс
        print(f"⏰ {checkpoint['timestamp']} | "
              f"Sim: {sim_time:.1f}m | "
              f"Trends: {stats.get('trends', 0)} | "
              f"Events: {stats.get('events', 0)} | "
              f"Actions: {stats.get('actions', 0)}")
    
    def show_summary(self):
        """Показывает итоговую статистику."""
        if not self.checkpoints:
            return
            
        last = self.checkpoints[-1]
        total_time = last['real_time']
        
        print(f"\n📊 ИТОГОВАЯ СТАТИСТИКА ВЗАИМОДЕЙСТВИЙ:")
        print(f"   ⏱️ Время симуляции: {last['sim_time']:.1f} минут")
        print(f"   🕐 Реальное время: {total_time:.1f} секунд")
        print(f"   🚄 Ускорение: {(last['sim_time'] * 60) / total_time:.1f}x")
        print(f"   📈 Трендов: {last.get('trends', 0)}")
        print(f"   🎬 Событий: {last.get('events', 0)}")
        print(f"   🎯 Действий: {last.get('actions', 0)}")


async def run_production_interaction_simulation():
    """Запуск production симуляции с мониторингом взаимодействий."""
    
    print('🏭 PRODUCTION INTERACTIVE SIMULATION')
    print('='*60)
    print('Core Engine Dev: Демонстрация взаимодействий на реальной БД')
    print()
    print('🎯 Параметры симуляции:')
    print('   👥 Агентов: 100')
    print('   🚄 Ускорение: 5x') 
    print('   📊 Мониторинг: каждые 15 симуляционных минут')
    print('   💾 База данных: Production (реальная)')
    print()
    
    # Initialize production components
    try:
        database_url = settings.DATABASE_URL
        db_repo = DatabaseRepository(database_url)
        print(f'✅ База данных подключена: {database_url[:50]}...')
    except Exception as e:
        print(f'❌ Ошибка подключения к БД: {e}')
        return
    
    # Initialize engine
    engine = SimulationEngine(db_repo)
    monitor = InteractionMonitor()
    
    try:
        # Initialize with 100 agents
        print(f'\n🏗️ Инициализация симуляции...')
        await engine.initialize(num_agents=100)
        
        simulation_id = engine.simulation_id
        print(f'✅ Симуляция создана: {simulation_id}')
        print(f'📊 Агентов инициализировано: {len(engine.agents)}')
        print(f'🎯 Активных трендов: {len(engine.active_trends)}')
        
        # Start simulation
        print(f'\n🚀 ЗАПУСК СИМУЛЯЦИИ')
        print('-' * 40)
        
        # Run simulation for 2 hours (120 minutes)
        simulation_task = asyncio.create_task(
            engine.run_simulation(duration_days=120/1440)
        )
        
        # Monitoring loop
        monitoring_interval = 15.0  # каждые 15 симуляционных минут
        next_checkpoint = monitoring_interval
        
        while not simulation_task.done() and engine.current_time < 120.0:
            await asyncio.sleep(10)  # проверяем каждые 10 реальных секунд
            
            # Checkpoint мониторинга
            if engine.current_time >= next_checkpoint:
                stats = await collect_interaction_stats(engine, db_repo)
                monitor.add_checkpoint(engine.current_time, stats)
                next_checkpoint += monitoring_interval
                
                # Проверяем достаточно ли взаимодействий
                if stats.get('trends', 0) >= 10 and stats.get('actions', 0) >= 50:
                    print(f"\n✅ Достигнут критерий взаимодействий!")
                    print(f"   📈 Трендов: {stats['trends']}")
                    print(f"   🎯 Действий: {stats['actions']}")
                    break
        
        # Graceful shutdown
        if not simulation_task.done():
            print(f"\n⏹️ Останавливаем симуляцию...")
            await engine.stop_simulation("manual_stop")
        
        await simulation_task
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Прерывание пользователем")
        await engine.stop_simulation("interrupted")
    except Exception as e:
        print(f"\n❌ Ошибка симуляции: {e}")
        await engine.stop_simulation("error")
    finally:
        # Final stats
        try:
            final_stats = await collect_interaction_stats(engine, db_repo)
            monitor.add_checkpoint(engine.current_time, final_stats)
            monitor.show_summary()
            
            # Detailed analysis
            await analyze_interaction_patterns(engine, db_repo, simulation_id)
            
        except Exception as e:
            print(f"⚠️ Ошибка финальной статистики: {e}")
        
        # Cleanup
        await engine.shutdown()
        await db_repo.close()


async def collect_interaction_stats(engine: SimulationEngine, db_repo: DatabaseRepository) -> Dict[str, Any]:
    """Собирает статистику взаимодействий из БД."""
    
    try:
        # Get stats from database
        simulation_stats = await db_repo.get_simulation_stats(engine.simulation_id)
        
        # Count active agents
        active_agents = sum(1 for agent in engine.agents if agent.energy_level > 1.0)
        
        stats = {
            'trends': simulation_stats.get('trends_count', 0),
            'events': simulation_stats.get('events_count', 0),
            'actions': simulation_stats.get('actions_count', 0),
            'active_agents': active_agents,
            'events_in_queue': len(engine.event_queue),
            'active_trends': len(engine.active_trends)
        }
        
        return stats
        
    except Exception as e:
        print(f"⚠️ Ошибка сбора статистики: {e}")
        return {
            'trends': len(engine.active_trends),
            'events': len(engine.event_queue), 
            'actions': 0,
            'active_agents': sum(1 for agent in engine.agents if agent.energy_level > 1.0),
            'events_in_queue': len(engine.event_queue),
            'active_trends': len(engine.active_trends)
        }


async def analyze_interaction_patterns(engine: SimulationEngine, db_repo: DatabaseRepository, 
                                     simulation_id: uuid.UUID):
    """Анализирует паттерны взаимодействий."""
    
    print(f"\n🔍 АНАЛИЗ ПАТТЕРНОВ ВЗАИМОДЕЙСТВИЙ")
    print('='*50)
    
    try:
        # Get recent trends from database
        query = """
        SELECT topic, COUNT(*) as trend_count, 
               AVG(base_virality_score) as avg_virality,
               SUM(total_interactions) as total_interactions
        FROM capsim.trends 
        WHERE simulation_id = %s 
        GROUP BY topic 
        ORDER BY trend_count DESC
        """
        
        trend_results = await db_repo.execute_query(query, [str(simulation_id)])
        
        if trend_results:
            print(f"📈 ТРЕНДЫ ПО ТЕМАМ:")
            for row in trend_results[:5]:  # Топ 5 тем
                print(f"   {row['topic']}: {row['trend_count']} трендов, "
                      f"виральность {row['avg_virality']:.1f}, "
                      f"взаимодействий {row['total_interactions']}")
        
        # Analyze agent activity
        active_agents = [a for a in engine.agents if a.energy_level > 1.0]
        if active_agents:
            avg_energy = sum(a.energy_level for a in active_agents) / len(active_agents)
            avg_social = sum(a.social_status for a in active_agents) / len(active_agents)
            
            print(f"\n👥 АКТИВНОСТЬ АГЕНТОВ:")
            print(f"   Активных: {len(active_agents)}/{len(engine.agents)} "
                  f"({len(active_agents)/len(engine.agents)*100:.1f}%)")
            print(f"   Средняя энергия: {avg_energy:.1f}/5.0")
            print(f"   Средний соц. статус: {avg_social:.1f}/5.0")
        
        # Event queue analysis
        if engine.event_queue:
            event_types = {}
            for event_wrapper in engine.event_queue:
                event_type = type(event_wrapper.event).__name__
                event_types[event_type] = event_types.get(event_type, 0) + 1
            
            print(f"\n🎬 ОЧЕРЕДЬ СОБЫТИЙ:")
            print(f"   Всего в очереди: {len(engine.event_queue)}")
            for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   {event_type}: {count}")
        
        # Success indicators
        trends_count = len(engine.active_trends)
        events_count = len(engine.event_queue)
        
        print(f"\n🎯 ИНДИКАТОРЫ УСПЕХА:")
        
        if trends_count > 0:
            print(f"   ✅ Активные тренды: {trends_count}")
        else:
            print(f"   ❌ Нет активных трендов")
            
        if events_count > 0:
            print(f"   ✅ События в очереди: {events_count}")
        else:
            print(f"   ❌ Очередь событий пуста")
            
        if len(active_agents) > len(engine.agents) * 0.3:
            print(f"   ✅ Хорошая активность: {len(active_agents)}")
        else:
            print(f"   ⚠️ Низкая активность: {len(active_agents)}")
    
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")


if __name__ == "__main__":
    print("🚀 Starting Production Interactive Simulation...")
    print("Core Engine Dev: Демонстрация взаимодействий")
    print()
    
    try:
        asyncio.run(run_production_interaction_simulation())
    except KeyboardInterrupt:
        print("\n⚠️ Симуляция прервана пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
    
    print("\n🏁 Симуляция завершена") 