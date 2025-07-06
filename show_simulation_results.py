#!/usr/bin/env python3
"""
Скрипт для демонстрации результатов симуляции CAPSIM
"""

import asyncio
import os
from capsim.db.repositories import DatabaseRepository
from capsim.common.db_config import ASYNC_DSN
from datetime import datetime

async def show_simulation_results():
    """Показывает результаты симуляции в наглядном виде."""
    
    # Подключение к БД через DSN из env
    db_repo = DatabaseRepository(ASYNC_DSN)
    
    print("🎯 РЕЗУЛЬТАТЫ СИМУЛЯЦИИ CAPSIM")
    print("=" * 50)
    
    # 1. Общая статистика
    print("\n📊 ОБЩАЯ СТАТИСТИКА:")
    print("-" * 30)
    
    # Количество агентов
    persons_count = await db_repo.get_persons_count()
    print(f"👥 Всего агентов: {persons_count}")
    
    # Количество событий
    events_result = await db_repo.execute_query("SELECT COUNT(*) as count FROM capsim.events")
    total_events = events_result[0]['count']
    print(f"📈 Всего событий: {total_events}")
    
    # Количество трендов
    trends_result = await db_repo.execute_query("SELECT COUNT(*) as count FROM capsim.trends")
    total_trends = trends_result[0]['count']
    print(f"🔥 Всего трендов: {total_trends}")
    
    # 2. Распределение по профессиям
    print("\n👨‍💼 РАСПРЕДЕЛЕНИЕ ПО ПРОФЕССИЯМ:")
    print("-" * 40)
    
    profession_stats = await db_repo.execute_query("""
        SELECT profession, COUNT(*) as count 
        FROM capsim.persons 
        GROUP BY profession 
        ORDER BY count DESC
    """)
    
    for row in profession_stats:
        percentage = (row['count'] / persons_count) * 100
        print(f"  {row['profession']:<15} | {row['count']:>3} ({percentage:>5.1f}%)")
    
    # 3. Активность по типам событий
    print("\n⚡ АКТИВНОСТЬ ПО ТИПАМ СОБЫТИЙ:")
    print("-" * 40)
    
    event_stats = await db_repo.execute_query("""
        SELECT event_type, COUNT(*) as count 
        FROM capsim.events 
        GROUP BY event_type 
        ORDER BY count DESC
    """)
    
    for row in event_stats:
        percentage = (row['count'] / total_events) * 100
        print(f"  {row['event_type']:<20} | {row['count']:>4} ({percentage:>5.1f}%)")
    
    # 4. Тренды по темам
    print("\n🔥 ТРЕНДЫ ПО ТЕМАМ:")
    print("-" * 30)
    
    trend_stats = await db_repo.execute_query("""
        SELECT topic, COUNT(*) as count, 
               AVG(base_virality_score) as avg_virality,
               SUM(total_interactions) as total_interactions
        FROM capsim.trends 
        GROUP BY topic 
        ORDER BY count DESC
    """)
    
    for row in trend_stats:
        print(f"  {row['topic']:<12} | {row['count']:>2} трендов | "
              f"виральность: {row['avg_virality']:.3f} | "
              f"взаимодействий: {row['total_interactions']}")
    
    # 5. Временная активность
    print("\n⏰ ВРЕМЕННАЯ АКТИВНОСТЬ:")
    print("-" * 30)
    
    time_stats = await db_repo.execute_query("""
        SELECT 
            DATE(processed_at) as date,
            COUNT(*) as events_count,
            COUNT(DISTINCT agent_id) as active_agents
        FROM capsim.events 
        WHERE processed_at IS NOT NULL
        GROUP BY DATE(processed_at)
        ORDER BY date DESC
        LIMIT 5
    """)
    
    for row in time_stats:
        print(f"  {row['date']} | {row['events_count']:>4} событий | {row['active_agents']:>3} активных агентов")
    
    # 6. Realtime режим
    print("\n🔄 REALTIME РЕЖИМ:")
    print("-" * 25)
    
    realtime_events = await db_repo.execute_query("""
        SELECT timestamp, processed_at, event_type
        FROM capsim.events 
        WHERE timestamp > 1000000000  -- Unix timestamp
        ORDER BY processed_at DESC
        LIMIT 3
    """)
    
    if realtime_events:
        print("  Последние события в realtime режиме:")
        for row in realtime_events:
            sim_time = row['timestamp'] / 60  # Конвертируем в минуты
            print(f"    {row['event_type']} | sim_time: {sim_time:.1f} мин | "
                  f"real_time: {row['processed_at']}")
    else:
        print("  Realtime события не найдены")
    
    # 7. Цепочки трендов (parent_trend_id)
    print("\n🔗 ЦЕПОЧКИ ТРЕНДОВ:")
    print("-" * 25)
    
    trend_chains = await db_repo.execute_query("""
        SELECT 
            t1.topic as parent_topic,
            t2.topic as child_topic,
            COUNT(*) as chain_count
        FROM capsim.trends t1
        JOIN capsim.trends t2 ON t1.trend_id = t2.parent_trend_id
        GROUP BY t1.topic, t2.topic
        ORDER BY chain_count DESC
    """)
    
    if trend_chains:
        print("  Найденные цепочки трендов:")
        for row in trend_chains:
            print(f"    {row['parent_topic']} → {row['child_topic']} ({row['chain_count']} раз)")
    else:
        print("  Цепочки трендов не найдены")
    
    print("\n" + "=" * 50)
    print("✅ Демонстрация завершена!")
    
    await db_repo.close()

if __name__ == "__main__":
    asyncio.run(show_simulation_results()) 