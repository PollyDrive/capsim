#!/usr/bin/env python3
"""
Анализ существующих данных симуляции в базе данных PostgreSQL.
Подсчитывает процент агентов, которые делают PublishPost и другую статистику.
"""

import os
import sys
import json
import psycopg2
from datetime import datetime
from typing import Dict, List

def analyze_simulation_data():
    """
    Анализирует данные симуляции в PostgreSQL и выводит подробную статистику.
    """
    print("🔍 АНАЛИЗ ДАННЫХ СИМУЛЯЦИИ CAPSIM")
    print("="*50)
    
    try:
        # Подключаемся к базе данных через Docker
        conn = psycopg2.connect(
            host="localhost",
            database="capsim_db",
            user="capsim_rw",
            password="capsim321",
            port=5432
        )
        cur = conn.cursor()
        
        print("✅ Подключение к базе данных успешно")
        
        # 1. Общая статистика агентов
        print("\n📊 ОБЩАЯ СТАТИСТИКА АГЕНТОВ")
        print("-" * 30)
        
        cur.execute("SELECT COUNT(*) FROM capsim.persons")
        total_agents = cur.fetchone()[0]
        print(f"Всего агентов в базе: {total_agents}")
        
        # Статистика по профессиям
        cur.execute("""
            SELECT profession, COUNT(*) as count
            FROM capsim.persons 
            GROUP BY profession 
            ORDER BY count DESC
        """)
        professions = cur.fetchall()
        
        print("\nРаспределение по профессиям:")
        for prof, count in professions:
            percentage = (count / total_agents * 100) if total_agents > 0 else 0
            print(f"  {prof}: {count} ({percentage:.1f}%)")
        
        # 2. Статистика симуляций
        print("\n🎮 СТАТИСТИКА СИМУЛЯЦИЙ")
        print("-" * 25)
        
        cur.execute("""
            SELECT run_id, start_time, status, num_agents, duration_days
            FROM capsim.simulation_runs 
            ORDER BY start_time DESC
            LIMIT 5
        """)
        simulations = cur.fetchall()
        
        print("Последние симуляции:")
        for sim_id, start_time, status, num_agents, duration in simulations:
            print(f"  {sim_id}: {status}, {num_agents} агентов, {duration} дней")
            print(f"    Начало: {start_time}")
        
        # 3. Анализ PublishPost событий
        print("\n📝 АНАЛИЗ PUBLISHPOST СОБЫТИЙ")
        print("-" * 32)
        
        # Общая статистика PublishPost
        cur.execute("""
            SELECT 
                COUNT(DISTINCT e.agent_id) as agents_with_posts,
                COUNT(*) as total_posts,
                COUNT(DISTINCT e.simulation_id) as simulations_with_posts
            FROM capsim.events e
            WHERE e.event_type = 'PublishPostAction'
            AND e.agent_id IS NOT NULL
        """)
        post_stats = cur.fetchone()
        
        if post_stats and post_stats[0] > 0:
            agents_with_posts, total_posts, sims_with_posts = post_stats
            percentage_active = (agents_with_posts / total_agents * 100) if total_agents > 0 else 0
            
            print(f"Агентов с публикациями: {agents_with_posts} из {total_agents}")
            print(f"🎯 ПРОЦЕНТ АКТИВНЫХ АГЕНТОВ: {percentage_active:.2f}%")
            print(f"Всего публикаций: {total_posts}")
            print(f"Среднее постов на активного агента: {total_posts / agents_with_posts:.2f}")
            print(f"Симуляций с публикациями: {sims_with_posts}")
            
            # Топ-5 самых активных агентов
            print("\n🏆 ТОП-5 САМЫХ АКТИВНЫХ АГЕНТОВ:")
            cur.execute("""
                SELECT 
                    p.first_name, p.last_name, p.profession,
                    COUNT(e.event_id) as post_count
                FROM capsim.persons p
                JOIN capsim.events e ON p.id = e.agent_id
                WHERE e.event_type = 'PublishPostAction'
                GROUP BY p.id, p.first_name, p.last_name, p.profession
                ORDER BY post_count DESC
                LIMIT 5
            """)
            top_agents = cur.fetchall()
            
            for i, (first_name, last_name, profession, count) in enumerate(top_agents, 1):
                print(f"  {i}. {first_name} {last_name} ({profession}) - {count} постов")
            
            # Статистика по профессиям
            print("\n👔 АКТИВНОСТЬ ПО ПРОФЕССИЯМ:")
            cur.execute("""
                SELECT 
                    p.profession,
                    COUNT(DISTINCT p.id) as total_agents_prof,
                    COUNT(DISTINCT CASE WHEN e.event_type = 'PublishPostAction' THEN e.agent_id END) as active_agents_prof,
                    COUNT(CASE WHEN e.event_type = 'PublishPostAction' THEN e.event_id END) as total_posts_prof
                FROM capsim.persons p
                LEFT JOIN capsim.events e ON p.id = e.agent_id
                GROUP BY p.profession
                ORDER BY active_agents_prof DESC
            """)
            prof_stats = cur.fetchall()
            
            for profession, total_prof, active_prof, posts_prof in prof_stats:
                prof_percentage = (active_prof / total_prof * 100) if total_prof > 0 else 0
                avg_posts = (posts_prof / active_prof) if active_prof > 0 else 0
                print(f"  {profession}: {active_prof}/{total_prof} ({prof_percentage:.1f}%) - {posts_prof} постов (ср. {avg_posts:.1f})")
            
            # Анализ тем постов
            print("\n🎯 ПОПУЛЯРНЫЕ ТЕМЫ ПОСТОВ:")
            cur.execute("""
                SELECT 
                    event_data->>'topic' as topic,
                    COUNT(*) as count
                FROM capsim.events 
                WHERE event_type = 'PublishPostAction'
                AND event_data->>'topic' IS NOT NULL
                GROUP BY event_data->>'topic'
                ORDER BY count DESC
                LIMIT 10
            """)
            topics = cur.fetchall()
            
            total_topic_posts = sum(count for _, count in topics)
            for topic, count in topics:
                percentage = (count / total_topic_posts * 100) if total_topic_posts > 0 else 0
                print(f"  {topic}: {count} постов ({percentage:.1f}%)")
        
        else:
            print("❌ Нет данных о PublishPost событиях в базе")
        
        # 4. Статистика трендов
        print("\n📈 СТАТИСТИКА ТРЕНДОВ")
        print("-" * 20)
        
        cur.execute("SELECT COUNT(*) FROM capsim.trends")
        total_trends = cur.fetchone()[0]
        print(f"Всего трендов создано: {total_trends}")
        
        if total_trends > 0:
            # Топ темы трендов
            cur.execute("""
                SELECT topic, COUNT(*) as count, AVG(base_virality_score) as avg_virality
                FROM capsim.trends 
                GROUP BY topic 
                ORDER BY count DESC
                LIMIT 5
            """)
            trend_topics = cur.fetchall()
            
            print("\nТоп темы трендов:")
            for topic, count, avg_virality in trend_topics:
                print(f"  {topic}: {count} трендов (средняя виральность: {avg_virality:.2f})")
        
        # 5. Временная статистика
        print("\n⏰ ВРЕМЕННАЯ СТАТИСТИКА")
        print("-" * 21)
        
        cur.execute("""
            SELECT 
                DATE(processed_at) as date,
                COUNT(*) as events_count
            FROM capsim.events 
            WHERE event_type = 'PublishPostAction'
            GROUP BY DATE(processed_at)
            ORDER BY date DESC
            LIMIT 7
        """)
        daily_stats = cur.fetchall()
        
        if daily_stats:
            print("Публикации по дням:")
            for date, count in daily_stats:
                print(f"  {date}: {count} публикаций")
        
        print("\n" + "="*50)
        print("✅ АНАЛИЗ ЗАВЕРШЕН")
        
        # Сохраняем результаты в файл
        results = {
            "timestamp": datetime.now().isoformat(),
            "total_agents": total_agents,
            "agents_with_posts": agents_with_posts if 'agents_with_posts' in locals() else 0,
            "percentage_active": percentage_active if 'percentage_active' in locals() else 0,
            "total_posts": total_posts if 'total_posts' in locals() else 0,
            "total_trends": total_trends,
            "professions": [{"profession": p, "count": c} for p, c in professions],
            "top_agents": [{"name": f"{fn} {ln}", "profession": p, "posts": c} for fn, ln, p, c in (top_agents if 'top_agents' in locals() else [])]
        }
        
        results_file = f"simulation_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"📁 Результаты сохранены в: {results_file}")
        
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()


def main():
    """Точка входа для скрипта."""
    try:
        analyze_simulation_data()
    except KeyboardInterrupt:
        print("\n⚠️  Анализ прерван пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 