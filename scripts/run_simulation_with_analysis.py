#!/usr/bin/env python3
"""
Запуск симуляции CAPSIM с анализом статистики PublishPost actions.

Выполняет все требования:
1. Проверяет существующих агентов в таблице Persons
2. Добавляет seed actions с распределением по симуляционному времени
3. Обрабатывает actions агентов с обновлением состояния
4. Батчами создает новые actions с учетом лимитов
5. Подсчитывает процент агентов делающих PublishPost
"""

import os
import sys
import json
import asyncio
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set
import psycopg2

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def analyze_simulation_results(simulation_id: str, db_repo) -> Dict[str, float]:
    """
    Анализирует результаты симуляции для подсчета процента агентов с PublishPost.
    
    Args:
        simulation_id: ID симуляции
        db_repo: Database repository instance
        
    Returns:
        Словарь со статистикой
    """
    logger.info(f"📊 Анализ результатов симуляции {simulation_id}")
    
    # SQL запрос для получения статистики PublishPost событий
    publishpost_stats_query = """
    SELECT 
        COUNT(DISTINCT e.agent_id) as agents_with_publishpost,
        COUNT(*) as total_publishpost_events,
        (SELECT COUNT(*) FROM capsim.persons WHERE simulation_id = %s) as total_agents
    FROM capsim.events e
    WHERE e.simulation_id = %s 
    AND e.event_type = 'PublishPostAction'
    AND e.agent_id IS NOT NULL
    """
    
    # SQL для подробной статистики по агентам
    agent_detail_query = """
    SELECT 
        p.id,
        p.profession,
        p.first_name,
        p.last_name,
        COUNT(e.event_id) as publishpost_count
    FROM capsim.persons p
    LEFT JOIN capsim.events e ON p.id = e.agent_id 
        AND e.event_type = 'PublishPostAction'
        AND e.simulation_id = %s
    WHERE p.simulation_id = %s
    GROUP BY p.id, p.profession, p.first_name, p.last_name
    ORDER BY publishpost_count DESC
    """
    
    # SQL для статистики по профессиям
    profession_stats_query = """
    SELECT 
        p.profession,
        COUNT(DISTINCT p.id) as total_agents_profession,
        COUNT(DISTINCT CASE WHEN e.event_type = 'PublishPostAction' THEN e.agent_id END) as active_agents_profession,
        COUNT(CASE WHEN e.event_type = 'PublishPostAction' THEN e.event_id END) as total_posts_profession
    FROM capsim.persons p
    LEFT JOIN capsim.events e ON p.id = e.agent_id AND e.simulation_id = %s
    WHERE p.simulation_id = %s
    GROUP BY p.profession
    ORDER BY active_agents_profession DESC
    """
    
    try:
        # Основная статистика
        result = await db_repo.execute_query(publishpost_stats_query, (simulation_id, simulation_id))
        main_stats = result[0] if result else {"agents_with_publishpost": 0, "total_publishpost_events": 0, "total_agents": 0}
        
        # Детальная статистика агентов
        agent_details = await db_repo.execute_query(agent_detail_query, (simulation_id, simulation_id))
        
        # Статистика по профессиям
        profession_stats = await db_repo.execute_query(profession_stats_query, (simulation_id, simulation_id))
        
        # Вычисляем проценты
        total_agents = main_stats["total_agents"]
        agents_with_posts = main_stats["agents_with_publishpost"]
        total_posts = main_stats["total_publishpost_events"]
        
        percentage_active = (agents_with_posts / total_agents * 100) if total_agents > 0 else 0
        
        # Создаем отчет
        analysis_results = {
            "simulation_id": simulation_id,
            "total_agents": total_agents,
            "agents_with_publishpost": agents_with_posts,
            "agents_without_posts": total_agents - agents_with_posts,
            "percentage_agents_with_posts": round(percentage_active, 2),
            "total_publishpost_events": total_posts,
            "avg_posts_per_active_agent": round(total_posts / agents_with_posts, 2) if agents_with_posts > 0 else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Выводим результаты
        print("\n" + "="*60)
        print("📈 АНАЛИЗ РЕЗУЛЬТАТОВ СИМУЛЯЦИИ")
        print("="*60)
        print(f"🆔 ID симуляции: {simulation_id}")
        print(f"👥 Всего агентов: {total_agents}")
        print(f"📝 Агентов с публикациями: {agents_with_posts}")
        print(f"🚫 Агентов без публикаций: {total_agents - agents_with_posts}")
        print(f"📊 Процент активных агентов: {percentage_active:.2f}%")
        print(f"📰 Всего публикаций: {total_posts}")
        print(f"📈 Среднее постов на активного агента: {analysis_results['avg_posts_per_active_agent']}")
        
        # Топ-5 самых активных агентов
        print(f"\n🏆 ТОП-5 САМЫХ АКТИВНЫХ АГЕНТОВ:")
        for i, agent in enumerate(agent_details[:5], 1):
            print(f"  {i}. {agent['first_name']} {agent['last_name']} ({agent['profession']}) - {agent['publishpost_count']} постов")
        
        # Статистика по профессиям
        print(f"\n👔 СТАТИСТИКА ПО ПРОФЕССИЯМ:")
        for prof in profession_stats:
            prof_percentage = (prof['active_agents_profession'] / prof['total_agents_profession'] * 100) if prof['total_agents_profession'] > 0 else 0
            print(f"  {prof['profession']}: {prof['active_agents_profession']}/{prof['total_agents_profession']} ({prof_percentage:.1f}%) - {prof['total_posts_profession']} постов")
        
        print("="*60)
        
        return analysis_results
        
    except Exception as e:
        logger.error(f"❌ Ошибка анализа: {e}")
        return {"error": str(e)}


async def run_simulation_with_analysis(
    num_agents: int = 300,
    duration_days: float = 1.0,
    enable_realtime: bool = False,
    sim_speed_factor: float = 60.0
):
    """
    Запускает симуляцию с полным анализом результатов.
    
    Args:
        num_agents: Количество агентов
        duration_days: Продолжительность в днях
        enable_realtime: Включить realtime режим
        sim_speed_factor: Фактор скорости (60.0 = 1 сим-минута = 1 реальная секунда)
    """
    print("🚀 CAPSIM Simulation with Analysis")
    print(f"👥 Агентов: {num_agents}")
    print(f"⏱️  Продолжительность: {duration_days} дней")
    print(f"🕐 Realtime режим: {'Да' if enable_realtime else 'Нет'}")
    print(f"⚡ Скорость: {sim_speed_factor}x")
    
    # Настройка окружения
    os.environ["SIM_SPEED_FACTOR"] = str(sim_speed_factor)
    os.environ["ENABLE_REALTIME"] = "true" if enable_realtime else "false"
    
    try:
        # Импортируем модули
        from capsim.engine.simulation_engine import SimulationEngine
        from capsim.db.repositories import DatabaseRepository
        
        # Создаем подключение к БД
        database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://capsim_rw:capsim321@localhost:5432/capsim_db")
        db_repo = DatabaseRepository(database_url)
        
        print("\n🔗 Подключение к базе данных...")
        
        # Создаем движок симуляции
        engine = SimulationEngine(db_repo)
        
        # Инициализация с проверкой существующих агентов
        print(f"\n🔄 Инициализация симуляции с {num_agents} агентами...")
        await engine.initialize(num_agents=num_agents)
        
        print(f"✅ Агентов в симуляции: {len(engine.agents)}")
        print(f"✅ ID симуляции: {engine.simulation_id}")
        
        # Проверяем количество системных событий
        initial_queue_size = len(engine.event_queue)
        print(f"✅ События в очереди: {initial_queue_size}")
        
        simulation_start = time.time()
        
        # Запуск симуляции
        print(f"\n▶️  Запуск симуляции...")
        await engine.run_simulation(duration_days=duration_days)
        
        simulation_duration = time.time() - simulation_start
        
        # Получаем статистику движка
        engine_stats = engine.get_simulation_stats()
        
        print(f"\n✅ Симуляция завершена за {simulation_duration:.2f} секунд")
        print(f"📊 Время симуляции: {engine_stats['current_time']:.1f} минут")
        print(f"📈 Активных трендов: {engine_stats['active_trends']}")
        
        # Проводим анализ результатов
        analysis_results = await analyze_simulation_results(str(engine.simulation_id), db_repo)
        
        # Сохраняем результаты в файл
        results_file = f"simulation_results_{engine.simulation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "simulation_params": {
                    "num_agents": num_agents,
                    "duration_days": duration_days,
                    "enable_realtime": enable_realtime,
                    "sim_speed_factor": sim_speed_factor
                },
                "engine_stats": engine_stats,
                "analysis_results": analysis_results,
                "execution_time_seconds": simulation_duration
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Результаты сохранены в: {results_file}")
        
        # Cleanup
        await engine.shutdown()
        await db_repo.close()
        
        return analysis_results
        
    except Exception as e:
        logger.error(f"❌ Ошибка симуляции: {e}")
        import traceback
        traceback.print_exc()
        raise


def main():
    """Точка входа для CLI."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CAPSIM Simulation with Analysis")
    parser.add_argument("--agents", type=int, default=300, help="Количество агентов (default: 300)")
    parser.add_argument("--days", type=float, default=1.0, help="Продолжительность в днях (default: 1.0)")
    parser.add_argument("--realtime", action="store_true", help="Включить realtime режим")
    parser.add_argument("--speed", type=float, default=60.0, help="Фактор скорости симуляции (default: 60.0)")
    parser.add_argument("--test", action="store_true", help="Тестовый режим (50 агентов, 2 часа)")
    
    args = parser.parse_args()
    
    # Тестовый режим
    if args.test:
        print("🧪 Тестовый режим")
        args.agents = 50
        args.days = 2.0 / 24.0  # 2 часа
        args.speed = 60.0
    
    try:
        asyncio.run(run_simulation_with_analysis(
            num_agents=args.agents,
            duration_days=args.days,
            enable_realtime=args.realtime,
            sim_speed_factor=args.speed
        ))
        print("\n🎉 Симуляция завершена успешно!")
        
    except KeyboardInterrupt:
        print("\n⚠️  Симуляция прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 