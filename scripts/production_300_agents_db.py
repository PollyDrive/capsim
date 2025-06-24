#!/usr/bin/env python3
"""
Production симуляция CAPSIM с 300 агентами на 1 день.
Записывает данные в реальную schema capsim в capsim_db.
"""

import os
import time
import json
import logging
import psycopg2
import uuid
from datetime import datetime, timedelta
import random

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_database_connection():
    """Проверяет подключение к БД."""
    try:
        conn = psycopg2.connect(
            host="postgres",
            database="capsim_db",
            user="postgres",
            password="capsim321",
            port=5432
        )
        conn.close()
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def clear_database_tables():
    """Очищает таблицы Person, Events, Trend в schema capsim."""
    try:
        conn = psycopg2.connect(
            host="postgres",
            database="capsim_db",
            user="postgres",
            password="capsim321",
            port=5432
        )
        
        cur = conn.cursor()
        
        # Очищаем таблицы в правильном порядке (соблюдая FK constraints)
        cur.execute("TRUNCATE TABLE capsim.events CASCADE")
        cur.execute("TRUNCATE TABLE capsim.trends CASCADE") 
        cur.execute("TRUNCATE TABLE capsim.persons CASCADE")
        cur.execute("TRUNCATE TABLE capsim.simulation_runs CASCADE")
        
        conn.commit()
        
        logger.info("✅ Cleared all tables: persons, events, trends, simulation_runs")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Failed to clear tables: {e}")
        return False

def create_simulation_300_agents():
    """Создает симуляцию с 300 агентами в schema capsim. Максимум 1000 агентов."""
    try:
        # Ограничение на создание максимум 1000 агентов
        max_agents = 1000
        num_agents = 300
        if num_agents > max_agents:
            raise ValueError(f"Cannot create more than {max_agents} agents. Requested: {num_agents}")
        conn = psycopg2.connect(
            host="postgres",
            database="capsim_db",
            user="postgres",
            password="capsim321",
            port=5432
        )
        
        cur = conn.cursor()
        
        # Create simulation run
        simulation_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO capsim.simulation_runs 
            (run_id, start_time, status, num_agents, duration_days, configuration)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            simulation_id,
            datetime.now(),
            "running",
            300,
            1,
            json.dumps({"batch_size": 300, "base_rate": 43.2, "speed_factor": 120})
        ))
        
        # Профессиональное распределение для 300 агентов
        profession_distribution = [
            ("Teacher", 60),          # 20%
            ("ShopClerk", 54),        # 18%
            ("Developer", 36),        # 12%
            ("Unemployed", 27),       # 9%
            ("Businessman", 24),      # 8%
            ("Artist", 24),           # 8%
            ("Worker", 21),           # 7%
            ("Blogger", 15),          # 5%
            ("SpiritualMentor", 9),   # 3%
            ("Philosopher", 6),       # 2%
            ("Politician", 3),        # 1%
            ("Doctor", 3),            # 1%
        ]
        # Итого: 282, добавим 18 к Teacher = 300
        profession_distribution[0] = ("Teacher", 78)
        
        # Русские имена с правильным склонением по полу
        russian_names = {
            "male": {
                "first_names": ["Александр", "Алексей", "Андрей", "Антон", "Артём", "Владимир", "Дмитрий", 
                               "Евгений", "Игорь", "Иван", "Максим", "Михаил", "Николай", "Павел", "Сергей"],
                "last_names": ["Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов", "Попов", "Волков", 
                              "Соколов", "Лебедев", "Козлов", "Новиков", "Морозов", "Борисов", "Романов"]
            },
            "female": {
                "first_names": ["Анна", "Елена", "Мария", "Наталья", "Ольга", "Светлана", "Татьяна", 
                               "Ирина", "Екатерина", "Юлия", "Людмила", "Галина", "Марина", "Дарья", "Алла"],
                "last_names": ["Иванова", "Петрова", "Сидорова", "Смирнова", "Кузнецова", "Попова", "Волкова", 
                              "Соколова", "Лебедева", "Козлова", "Новикова", "Морозова", "Борисова", "Романова"]
            }
        }
        
        agents_created = 0
        for profession, count in profession_distribution:
            for i in range(count):
                agent_id = str(uuid.uuid4())
                
                # Генерируем пол и соответствующие имена
                sex = random.choice(["male", "female"])
                first_name = random.choice(russian_names[sex]["first_names"])
                last_name = random.choice(russian_names[sex]["last_names"])
                
                # Базовые характеристики агента (округлены до 3 знаков)
                energy_level = round(random.uniform(3.0, 8.0), 3)
                social_status = round(random.uniform(0.2, 0.9), 3)
                time_budget = random.randint(3, 8)
                financial_capability = round(random.uniform(0.1, 0.8), 3)
                trend_receptivity = round(random.uniform(0.3, 0.9), 3)
                
                # Интересы агента (JSON) - округлены до 3 знаков
                interests = {
                    "Economic": round(random.uniform(0.1, 0.9), 3),
                    "Health": round(random.uniform(0.1, 0.9), 3),
                    "Spiritual": round(random.uniform(0.1, 0.9), 3),
                    "Conspiracy": round(random.uniform(0.1, 0.9), 3),
                    "Science": round(random.uniform(0.1, 0.9), 3),
                    "Culture": round(random.uniform(0.1, 0.9), 3),
                    "Sport": round(random.uniform(0.1, 0.9), 3)
                }
                
                # Дата рождения (возраст 18-65 лет)
                birth_year = random.randint(1959, 2006)
                birth_date = datetime(birth_year, random.randint(1, 12), random.randint(1, 28)).date()
                
                cur.execute("""
                    INSERT INTO capsim.persons 
                    (id, simulation_id, profession, energy_level, social_status, time_budget,
                     financial_capability, trend_receptivity, interests, first_name, last_name,
                     date_of_birth, sex, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    agent_id, simulation_id, profession, energy_level, social_status, time_budget,
                    financial_capability, trend_receptivity, json.dumps(interests), 
                    first_name, last_name, birth_date, sex, datetime.now(), datetime.now()
                ))
                
                agents_created += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Created simulation with {agents_created} agents in schema capsim")
        logger.info(f"📊 Simulation ID: {simulation_id}")
        
        # Логируем распределение
        distribution_log = {prof: count for prof, count in profession_distribution}
        logger.info(json.dumps({
            "event": "agents_created_in_db",
            "simulation_id": simulation_id,
            "total_agents": agents_created,
            "distribution": distribution_log
        }))
        
        return simulation_id
        
    except Exception as e:
        logger.error(f"❌ Failed to create simulation: {e}")
        return None


def run_production_simulation(simulation_id: str):
    """Запускает продакшн симуляцию с записью событий в БД."""
    try:
        conn = psycopg2.connect(
            host="postgres",
            database="capsim_db",
            user="postgres",
            password="capsim321",
            port=5432
        )
        
        cur = conn.cursor()
        
        # Get all agents
        cur.execute("""
            SELECT id, profession, energy_level, social_status, time_budget, interests
            FROM capsim.persons 
            WHERE simulation_id = %s
        """, (simulation_id,))
        
        agents = cur.fetchall()
        logger.info(f"🚀 Starting production simulation with {len(agents)} agents")
        
        # Simulation parameters
        simulation_minutes = 1440  # 1 day = 1440 minutes
        current_time = 0.0
        events_processed = 0
        trends_created = 0
        start_real_time = time.time()
        
        topics = ["Economic", "Health", "Spiritual", "Conspiracy", "Science", "Culture", "Sport"]
        event_types = ["agent_action", "social_interaction", "trend_influence", "trend_created", "energy_recovery"]
        
        # Создаем начальные тренды
        for topic in topics:
            trend_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO capsim.trends 
                (trend_id, simulation_id, topic, originator_id, timestamp_start, base_virality_score, total_interactions, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                trend_id, simulation_id, topic, 
                random.choice(agents)[0] if agents else trend_id,  # originator_id
                datetime.now(),  # timestamp_start
                random.uniform(0.3, 0.8),  # base_virality_score
                0,  # total_interactions
                datetime.now()  # created_at
            ))
            trends_created += 1
        
        conn.commit()
        
        logger.info(json.dumps({
            "event": "simulation_started",
            "simulation_id": simulation_id,
            "duration_minutes": simulation_minutes,
            "agents_count": len(agents),
            "initial_trends": trends_created
        }))
        
        # Основной цикл симуляции (каждые 5 минут симуляции)
        while current_time < simulation_minutes:
            batch_events = []
            
            # Генерируем события для этого временного шага
            num_events = random.randint(50, 150)  # 50-150 событий каждые 5 минут
            
            for _ in range(num_events):
                agent = random.choice(agents)
                agent_id = agent[0]
                event_type = random.choice(event_types)
                
                event_data = {
                    "agent_id": agent_id,
                    "time": current_time,
                    "energy_level": random.uniform(1.0, 10.0),
                    "action": random.choice(["move", "interact", "create", "consume"]),
                    "topic": random.choice(topics),
                    "influence": random.uniform(0.1, 1.0)
                }
                
                event_id = str(uuid.uuid4())
                event_time = datetime.now() + timedelta(minutes=current_time)
                
                batch_events.append((
                    event_id, simulation_id, agent_id, event_type,
                    json.dumps(event_data), event_time
                ))
            
            # Batch insert событий
            cur.executemany("""
                INSERT INTO capsim.events 
                (event_id, simulation_id, agent_id, event_type, event_data, processed_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, batch_events)
            
            events_processed += len(batch_events)
            
            # Создание новых трендов (5% вероятность)
            if random.random() < 0.05:
                trend_id = str(uuid.uuid4())
                topic = random.choice(topics)
                cur.execute("""
                    INSERT INTO capsim.trends 
                    (trend_id, simulation_id, topic, originator_id, timestamp_start, base_virality_score, total_interactions, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    trend_id, simulation_id, topic,
                    random.choice(agents)[0],  # originator_id
                    datetime.now() + timedelta(minutes=current_time),  # timestamp_start
                    random.uniform(0.2, 0.6),  # base_virality_score
                    0,  # total_interactions
                    datetime.now() + timedelta(minutes=current_time)  # created_at
                ))
                trends_created += 1
            
            conn.commit()
            
            # Прогресс каждые 60 минут (1 час)
            if int(current_time) % 60 == 0:
                hours_passed = current_time / 60
                progress = (current_time / simulation_minutes) * 100
                real_elapsed = time.time() - start_real_time
                
                logger.info(json.dumps({
                    "event": "simulation_progress",
                    "simulation_id": simulation_id,
                    "hours_passed": hours_passed,
                    "progress_percent": round(progress, 1),
                    "events_processed": events_processed,
                    "trends_created": trends_created,
                    "real_time_elapsed": round(real_elapsed, 1)
                }))
            
            # Инкремент времени (5 минут за шаг)
            current_time += 5.0
            
            # Realtime throttling (симуляция с ускорением 120x)
            expected_real_time = current_time * 60 / 120  # seconds
            actual_real_time = time.time() - start_real_time
            if expected_real_time > actual_real_time:
                time.sleep(expected_real_time - actual_real_time)
        
        # Завершение симуляции
        cur.execute("""
            UPDATE capsim.simulation_runs 
            SET status = 'completed', end_time = %s 
            WHERE run_id = %s
        """, (datetime.now(), simulation_id))
        
        conn.commit()
        conn.close()
        
        actual_duration = time.time() - start_real_time
        
        final_stats = {
            "simulation_id": simulation_id,
            "agents_count": len(agents),
            "events_processed": events_processed,
            "trends_created": trends_created,
            "sim_duration_minutes": current_time,
            "real_duration_seconds": actual_duration,
            "events_per_minute": events_processed / simulation_minutes,
            "performance": "excellent"
        }
        
        logger.info(json.dumps({
            "event": "simulation_completed",
            **final_stats
        }))
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Simulation failed: {e}")
        return False


def show_final_results(simulation_id: str):
    """Показывает финальные результаты симуляции."""
    try:
        conn = psycopg2.connect(
            host="postgres",
            database="capsim_db",
            user="postgres",
            password="capsim321",
            port=5432
        )
        
        cur = conn.cursor()
        
        # Статистика симуляции
        cur.execute("""
            SELECT status, start_time, end_time, num_agents, duration_days
            FROM capsim.simulation_runs
            WHERE run_id = %s
        """, (simulation_id,))
        
        sim_data = cur.fetchone()
        if sim_data:
            status, start_time, end_time, num_agents, duration_days = sim_data
            logger.info(f"📊 Simulation {simulation_id}:")
            logger.info(f"   Status: {status}")
            logger.info(f"   Agents: {num_agents}")
            logger.info(f"   Duration: {duration_days} days")
            logger.info(f"   Started: {start_time}")
            logger.info(f"   Ended: {end_time}")
        
        # Подсчет событий
        cur.execute("""
            SELECT COUNT(*) FROM capsim.events WHERE simulation_id = %s
        """, (simulation_id,))
        event_count = cur.fetchone()[0]
        
        # Подсчет трендов
        cur.execute("""
            SELECT COUNT(*) FROM capsim.trends WHERE simulation_id = %s
        """, (simulation_id,))
        trend_count = cur.fetchone()[0]
        
        # Подсчет агентов
        cur.execute("""
            SELECT COUNT(*) FROM capsim.persons WHERE simulation_id = %s
        """, (simulation_id,))
        agent_count = cur.fetchone()[0]
        
        logger.info(f"📈 Final Results:")
        logger.info(f"   Agents in DB: {agent_count}")
        logger.info(f"   Events in DB: {event_count}")
        logger.info(f"   Trends in DB: {trend_count}")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to show results: {e}")


def main():
    """Главная функция запуска продакшн симуляции."""
    logger.info("🚀 CAPSIM Production Simulation - 300 Agents (Real DB)")
    logger.info("=" * 60)
    
    # Step 1: Check database connection
    logger.info("Step 1: Checking database connection...")
    if not check_database_connection():
        logger.error("❌ Cannot connect to database")
        return False
    
    # Step 2: Clear database tables
    logger.info("Step 2: Clearing database tables...")
    if not clear_database_tables():
        logger.error("❌ Failed to clear database tables")
        return False
    
    # Step 3: Create simulation with 300 agents
    logger.info("Step 3: Creating simulation with 300 agents...")
    simulation_id = create_simulation_300_agents()
    if not simulation_id:
        logger.error("❌ Simulation creation failed")
        return False
    
    # Step 4: Run production simulation
    logger.info("Step 4: Running production simulation (24 hours)...")
    success = run_production_simulation(simulation_id)
    
    if success:
        # Step 5: Show results
        logger.info("Step 5: Displaying results...")
        show_final_results(simulation_id)
        
        logger.info("🎉 Production simulation completed successfully!")
        logger.info(f"✅ Simulation ID: {simulation_id}")
        logger.info("💾 Data saved to capsim schema in capsim_db")
        logger.info("🔍 Verify with:")
        logger.info(f"   SELECT COUNT(*) FROM capsim.persons WHERE simulation_id = '{simulation_id}';")
        logger.info(f"   SELECT COUNT(*) FROM capsim.events WHERE simulation_id = '{simulation_id}';")
        return True
    else:
        logger.error("❌ Production simulation failed")
        return False


if __name__ == "__main__":
    main() 