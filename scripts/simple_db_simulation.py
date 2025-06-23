#!/usr/bin/env python3
"""
Simple database simulation for CAPSIM.

Direct database simulation with 100 agents for 1 day.
Uses basic SQL operations without complex ORM dependencies.
"""

import os
import sys
import json
import logging
import psycopg2
import uuid
import random
import time
from pathlib import Path
from datetime import datetime, timedelta, date
from typing import Dict, List, Any
from faker import Faker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализируем Faker для русских имен
fake = Faker('ru_RU')


def check_database_connection():
    """Проверяет подключение к базе данных."""
    try:
        conn = psycopg2.connect(
            host="postgres",
            database="capsim_db",
            user="postgres",
            password="capsim321",
            port=5432
        )
        
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()[0]
        logger.info(f"✅ Database connected: {version}")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def initialize_database():
    """Инициализирует базу данных с минимальными данными."""
    try:
        conn = psycopg2.connect(
            host="postgres",
            database="capsim_db",
            user="postgres",
            password="capsim321",
            port=5432
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Create schema if not exists
        cur.execute("CREATE SCHEMA IF NOT EXISTS capsim")
        
        # Drop existing tables to recreate with correct schema
        cur.execute("DROP TABLE IF EXISTS capsim.events CASCADE")
        cur.execute("DROP TABLE IF EXISTS capsim.trends CASCADE")
        cur.execute("DROP TABLE IF EXISTS capsim.persons CASCADE")
        cur.execute("DROP TABLE IF EXISTS capsim.simulation_runs CASCADE")
        
        # Create basic tables if they don't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS capsim.simulation_runs (
                run_id UUID PRIMARY KEY,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                status VARCHAR(50),
                num_agents INTEGER,
                duration_days INTEGER,
                configuration JSONB
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS capsim.persons (
                id UUID PRIMARY KEY,
                simulation_id UUID,
                profession VARCHAR(50),
                energy_level FLOAT,
                social_status FLOAT,
                time_budget INTEGER,
                financial_capability FLOAT DEFAULT 0.0,
                trend_receptivity FLOAT DEFAULT 0.0,
                interests JSONB,
                first_name VARCHAR(100),
                last_name VARCHAR(100),
                date_of_birth DATE,
                sex VARCHAR(10),
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS capsim.trends (
                trend_id UUID PRIMARY KEY,
                simulation_id UUID,
                topic VARCHAR(50),
                originator_id UUID,
                timestamp_start TIMESTAMP,
                base_virality_score FLOAT,
                total_interactions INTEGER DEFAULT 0,
                created_at TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS capsim.events (
                event_id UUID PRIMARY KEY,
                simulation_id UUID,
                event_type VARCHAR(50),
                priority INTEGER DEFAULT 1,
                timestamp FLOAT,
                agent_id UUID,
                trend_id UUID,
                event_data JSONB,
                processed_at TIMESTAMP
            )
        """)
        
        # Create agent_interests table for normalized interest data
        cur.execute("""
            CREATE TABLE IF NOT EXISTS capsim.agent_interests (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                agent_id UUID REFERENCES capsim.persons(id),
                simulation_id UUID,
                profession VARCHAR(50),
                interest_category VARCHAR(50),
                interest_value FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create users if they don't exist
        try:
            cur.execute("CREATE USER capsim_rw WITH PASSWORD 'capsim321'")
            cur.execute("CREATE USER capsim_ro WITH PASSWORD 'capsim321'")
        except psycopg2.errors.DuplicateObject:
            pass
        
        # Grant permissions
        cur.execute("GRANT ALL PRIVILEGES ON SCHEMA capsim TO capsim_rw")
        cur.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA capsim TO capsim_rw")
        cur.execute("GRANT USAGE ON SCHEMA capsim TO capsim_ro")
        cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA capsim TO capsim_ro")
        
        logger.info("✅ Database initialized")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False


def create_simulation_with_agents():
    """Создает симуляцию с 100 агентами."""
    try:
        conn = psycopg2.connect(
            host="postgres",
            database="capsim_db",
            user="capsim_rw",
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
            100,
            1,
            json.dumps({"batch_size": 100, "base_rate": 43.2})
        ))
        
        # Generate 100 agents
        # Правильный список из 12 профессий согласно ТЗ (пропорционально масштабирован для 100 агентов)
        profession_distribution = [
            ("ShopClerk", 18),    # 18% = 18 агентов
            ("Teacher", 20),      # 20% = 20 агентов  
            ("Developer", 12),    # 12% = 12 агентов
            ("Unemployed", 9),    # 9% = 9 агентов
            ("Businessman", 8),   # 8% = 8 агентов
            ("Artist", 8),        # 8% = 8 агентов
            ("Worker", 7),        # 7% = 7 агентов
            ("Blogger", 5),       # 5% = 5 агентов
            ("SpiritualMentor", 3), # 3% = 3 агентов
            ("Philosopher", 2),   # 2% = 2 агентов
            ("Politician", 1),    # 1% = 1 агент
            ("Doctor", 1),        # 1% = 1 агент
        ]
        # Итого: 94 агента, добавим 6 к самым популярным профессиям
        # ShopClerk +2, Teacher +2, Developer +2 = 100 агентов
        profession_distribution[0] = ("ShopClerk", 20)
        profession_distribution[1] = ("Teacher", 22) 
        profession_distribution[2] = ("Developer", 14)
        
        agents_created = 0
        for profession, count in profession_distribution:
            for i in range(count):
                agent_id = str(uuid.uuid4())
                
                # Generate attributes based on profession (from ТЗ table)
                profession_attributes = {
                    "ShopClerk": {
                        "financial_capability": (2, 4), "trend_receptivity": (1, 3), 
                        "social_status": (1, 3), "energy_level": (2, 5), "time_budget": (3, 5),
                        "interests": {
                            "Economics": (4.59, 5.0), "Wellbeing": (0.74, 1.34), "Spirituality": (0.64, 1.24),
                            "Knowledge": (1.15, 1.75), "Creativity": (1.93, 2.53), "Society": (2.70, 3.30)
                        }
                    },
                    "Worker": {
                        "financial_capability": (2, 4), "trend_receptivity": (1, 3),
                        "social_status": (1, 2), "energy_level": (2, 5), "time_budget": (3, 5),
                        "interests": {
                            "Economics": (3.97, 4.57), "Wellbeing": (1.05, 1.65), "Spirituality": (1.86, 2.46),
                            "Knowledge": (1.83, 2.43), "Creativity": (0.87, 1.47), "Society": (0.69, 1.29)
                        }
                    },
                    "Developer": {
                        "financial_capability": (3, 5), "trend_receptivity": (3, 5),
                        "social_status": (2, 4), "energy_level": (2, 5), "time_budget": (2, 4),
                        "interests": {
                            "Economics": (1.82, 2.42), "Wellbeing": (1.15, 1.75), "Spirituality": (0.72, 1.32),
                            "Knowledge": (4.05, 4.65), "Creativity": (2.31, 2.91), "Society": (1.59, 2.19)
                        }
                    },
                    "Politician": {
                        "financial_capability": (3, 5), "trend_receptivity": (3, 5),
                        "social_status": (4, 5), "energy_level": (2, 4), "time_budget": (2, 4),
                        "interests": {
                            "Economics": (0.51, 1.11), "Wellbeing": (1.63, 2.23), "Spirituality": (0.32, 0.92),
                            "Knowledge": (2.07, 2.67), "Creativity": (1.73, 2.33), "Society": (3.57, 4.17)
                        }
                    },
                    "Blogger": {
                        "financial_capability": (2, 4), "trend_receptivity": (4, 5),
                        "social_status": (3, 5), "energy_level": (2, 5), "time_budget": (3, 5),
                        "interests": {
                            "Economics": (1.32, 1.92), "Wellbeing": (1.01, 1.61), "Spirituality": (1.20, 1.80),
                            "Knowledge": (1.23, 1.83), "Creativity": (3.27, 3.87), "Society": (2.43, 3.03)
                        }
                    },
                    "Businessman": {
                        "financial_capability": (4, 5), "trend_receptivity": (2, 4),
                        "social_status": (4, 5), "energy_level": (2, 5), "time_budget": (2, 4),
                        "interests": {
                            "Economics": (4.01, 4.61), "Wellbeing": (0.76, 1.36), "Spirituality": (0.91, 1.51),
                            "Knowledge": (1.35, 1.95), "Creativity": (2.04, 2.64), "Society": (2.42, 3.02)
                        }
                    },
                    "SpiritualMentor": {
                        "financial_capability": (1, 3), "trend_receptivity": (2, 5),
                        "social_status": (2, 4), "energy_level": (3, 5), "time_budget": (2, 4),
                        "interests": {
                            "Economics": (0.62, 1.22), "Wellbeing": (2.04, 2.64), "Spirituality": (3.86, 4.46),
                            "Knowledge": (2.11, 2.71), "Creativity": (2.12, 2.72), "Society": (1.95, 2.55)
                        }
                    },
                    "Philosopher": {
                        "financial_capability": (1, 3), "trend_receptivity": (1, 3),
                        "social_status": (1, 3), "energy_level": (2, 4), "time_budget": (2, 4),
                        "interests": {
                            "Economics": (1.06, 1.66), "Wellbeing": (2.22, 2.82), "Spirituality": (3.71, 4.31),
                            "Knowledge": (3.01, 3.61), "Creativity": (2.21, 2.81), "Society": (1.80, 2.40)
                        }
                    },
                    "Unemployed": {
                        "financial_capability": (1, 2), "trend_receptivity": (3, 5),
                        "social_status": (1, 2), "energy_level": (3, 5), "time_budget": (3, 5),
                        "interests": {
                            "Economics": (0.72, 1.32), "Wellbeing": (1.38, 1.98), "Spirituality": (3.69, 4.29),
                            "Knowledge": (2.15, 2.75), "Creativity": (2.33, 2.93), "Society": (2.42, 3.02)
                        }
                    },
                    "Teacher": {
                        "financial_capability": (1, 3), "trend_receptivity": (1, 3),
                        "social_status": (2, 4), "energy_level": (1, 3), "time_budget": (2, 4),
                        "interests": {
                            "Economics": (1.32, 1.92), "Wellbeing": (2.16, 2.76), "Spirituality": (1.40, 2.00),
                            "Knowledge": (3.61, 4.21), "Creativity": (1.91, 2.51), "Society": (2.24, 2.84)
                        }
                    },
                    "Artist": {
                        "financial_capability": (1, 3), "trend_receptivity": (2, 4),
                        "social_status": (2, 4), "energy_level": (4, 5), "time_budget": (3, 5),
                        "interests": {
                            "Economics": (0.86, 1.46), "Wellbeing": (0.91, 1.51), "Spirituality": (2.01, 2.61),
                            "Knowledge": (1.82, 2.42), "Creativity": (3.72, 4.32), "Society": (1.94, 2.54)
                        }
                    },
                    "Doctor": {
                        "financial_capability": (2, 4), "trend_receptivity": (1, 3),
                        "social_status": (3, 5), "energy_level": (2, 4), "time_budget": (1, 2),
                        "interests": {
                            "Economics": (1.02, 1.62), "Wellbeing": (3.97, 4.57), "Spirituality": (1.37, 1.97),
                            "Knowledge": (2.01, 2.61), "Creativity": (1.58, 2.18), "Society": (2.45, 3.05)
                        }
                    }
                }
                
                # Get attributes for this profession
                prof_attrs = profession_attributes.get(profession, profession_attributes["Worker"])
                
                # Generate interests based on profession ranges
                interests = {}
                for interest_name, (min_val, max_val) in prof_attrs["interests"].items():
                    interests[interest_name] = round(random.uniform(min_val, max_val), 2)
                
                # Generate other attributes based on profession ranges
                financial_capability = round(random.uniform(*prof_attrs["financial_capability"]), 2)
                trend_receptivity = round(random.uniform(*prof_attrs["trend_receptivity"]), 2)
                social_status = round(random.uniform(*prof_attrs["social_status"]), 2)
                energy_level = round(random.uniform(*prof_attrs["energy_level"]), 2)
                time_budget = random.randint(*prof_attrs["time_budget"])
                
                # Generate personal data with proper age restrictions
                personal_data = generate_personal_data(profession)
                
                cur.execute("""
                    INSERT INTO capsim.persons 
                    (id, simulation_id, profession, financial_capability, trend_receptivity,
                     social_status, energy_level, time_budget, interests, 
                     first_name, last_name, date_of_birth, sex, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    agent_id,
                    simulation_id,
                    profession,
                    financial_capability,
                    trend_receptivity,
                    social_status,
                    energy_level,
                    time_budget,
                    json.dumps(interests),
                    personal_data['first_name'],
                    personal_data['last_name'],
                    personal_data['date_of_birth'],
                    personal_data['sex'],
                    datetime.now(),
                    datetime.now()
                ))
                
                agents_created += 1
        
        # Populate agent_interests table from persons data
        cur.execute("""
            INSERT INTO capsim.agent_interests (agent_id, simulation_id, profession, interest_category, interest_value)
            SELECT 
                p.id,
                p.simulation_id,
                p.profession,
                interest_key,
                (interest_value::text)::float
            FROM capsim.persons p,
                 LATERAL jsonb_each(p.interests) AS interest(interest_key, interest_value)
            WHERE p.simulation_id = %s
        """, (simulation_id,))
        
        conn.commit()
        logger.info(f"✅ Created simulation {simulation_id} with {agents_created} agents")
        logger.info(f"✅ Populated agent_interests table with normalized data")
        
        cur.close()
        conn.close()
        return simulation_id
    except Exception as e:
        logger.error(f"❌ Simulation creation failed: {e}")
        return None


def run_basic_simulation(simulation_id: str):
    """Запускает базовую симуляцию на 1 день."""
    try:
        conn = psycopg2.connect(
            host="postgres",
            database="capsim_db",
            user="capsim_rw",
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
        logger.info(f"🚀 Starting simulation with {len(agents)} agents")
        
        # Simulation parameters
        simulation_minutes = 1440  # 1 day = 1440 minutes
        current_time = 0.0
        events_processed = 0
        trends_created = 0
        
        topics = ["Economic", "Health", "Spiritual", "Conspiracy", "Science", "Culture", "Sport"]
        
        # Run simulation loop
        start_real_time = time.time()
        
        while current_time < simulation_minutes:
            # Each agent has a chance to act every hour (60 minutes)
            if current_time % 60 == 0:  # Every hour
                for agent_data in agents:
                    agent_id, profession, energy, social_status, time_budget, interests_json = agent_data
                    # Handle both dict and string JSON data
                    if isinstance(interests_json, dict):
                        interests = interests_json
                    else:
                        interests = json.loads(interests_json)
                    
                    # Simple decision making: agent acts if energy > 2.0 and random chance
                    if energy > 2.0 and random.random() < 0.3:  # 30% chance per hour
                        # Affinity matrix from ТЗ
                        affinity_map = {
                            "ShopClerk": {"Economic": 3, "Health": 2, "Spiritual": 2, "Conspiracy": 3, "Science": 1, "Culture": 2, "Sport": 2},
                            "Worker": {"Economic": 3, "Health": 3, "Spiritual": 2, "Conspiracy": 3, "Science": 1, "Culture": 2, "Sport": 3},
                            "Developer": {"Economic": 3, "Health": 2, "Spiritual": 1, "Conspiracy": 2, "Science": 5, "Culture": 3, "Sport": 2},
                            "Politician": {"Economic": 5, "Health": 4, "Spiritual": 2, "Conspiracy": 2, "Science": 3, "Culture": 3, "Sport": 2},
                            "Blogger": {"Economic": 4, "Health": 4, "Spiritual": 3, "Conspiracy": 4, "Science": 3, "Culture": 5, "Sport": 4},
                            "Businessman": {"Economic": 5, "Health": 3, "Spiritual": 2, "Conspiracy": 2, "Science": 3, "Culture": 3, "Sport": 3},
                            "Doctor": {"Economic": 3, "Health": 5, "Spiritual": 2, "Conspiracy": 1, "Science": 5, "Culture": 2, "Sport": 3},
                            "Teacher": {"Economic": 3, "Health": 4, "Spiritual": 3, "Conspiracy": 2, "Science": 4, "Culture": 4, "Sport": 3},
                            "Unemployed": {"Economic": 4, "Health": 3, "Spiritual": 3, "Conspiracy": 4, "Science": 2, "Culture": 3, "Sport": 3},
                            "Artist": {"Economic": 2, "Health": 2, "Spiritual": 4, "Conspiracy": 2, "Science": 2, "Culture": 5, "Sport": 2},
                            "SpiritualMentor": {"Economic": 2, "Health": 3, "Spiritual": 5, "Conspiracy": 3, "Science": 2, "Culture": 3, "Sport": 2},
                            "Philosopher": {"Economic": 3, "Health": 3, "Spiritual": 5, "Conspiracy": 3, "Science": 4, "Culture": 4, "Sport": 1}
                        }
                        
                        # Choose topic based on affinity and interests
                        topic_scores = []
                        profession_affinities = affinity_map.get(profession, {})
                        
                        for topic in topics:
                            # Map new topics to old interest categories
                            interest_mapping = {
                                "Economic": "Economics",
                                "Health": "Wellbeing", 
                                "Spiritual": "Spirituality",
                                "Conspiracy": "Society",
                                "Science": "Knowledge",
                                "Culture": "Creativity",
                                "Sport": "Society"
                            }
                            
                            interest_category = interest_mapping.get(topic, "Economics")
                            interest_score = interests.get(interest_category, 1.0)
                            affinity_score = profession_affinities.get(topic, 2.5)
                            
                            # Scoring formula from ТЗ
                            score = affinity_score * (social_status / 5.0) * (interest_score / 5.0) * random.uniform(0.8, 1.2)
                            topic_scores.append((topic, score))
                        
                        # Choose topic with highest score
                        chosen_topic = max(topic_scores, key=lambda x: x[1])[0]
                        
                        # Create trend
                        trend_id = str(uuid.uuid4())
                        base_virality = round(random.uniform(1.0, 3.0), 2)
                        
                        cur.execute("""
                            INSERT INTO capsim.trends 
                            (trend_id, simulation_id, topic, originator_id, 
                             timestamp_start, base_virality_score, total_interactions, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            trend_id,
                            simulation_id,
                            chosen_topic,
                            agent_id,
                            datetime.now(),
                            base_virality,
                            1,  # Initial interaction
                            datetime.now()
                        ))
                        
                        # Create event
                        event_id = str(uuid.uuid4())
                        cur.execute("""
                            INSERT INTO capsim.events 
                            (event_id, simulation_id, event_type, priority, timestamp, 
                             agent_id, trend_id, event_data, processed_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            event_id,
                            simulation_id,
                            "PublishPostAction",
                            1,  # Default priority
                            current_time,
                            agent_id,
                            trend_id,
                            json.dumps({"topic": chosen_topic, "virality": base_virality}),
                            datetime.now()
                        ))
                        
                        trends_created += 1
                        events_processed += 1
                        
                        # Update agent energy (decrease slightly)
                        new_energy = max(1.0, energy - 0.1)
                        cur.execute("""
                            UPDATE capsim.persons 
                            SET energy_level = %s, updated_at = %s
                            WHERE id = %s
                        """, (new_energy, datetime.now(), agent_id))
            
            # Advance time by 1 minute
            current_time += 1.0
            
            # Commit every 100 events for performance
            if events_processed % 100 == 0:
                conn.commit()
                logger.info(f"⏰ Time: {current_time:.0f}min, Events: {events_processed}, Trends: {trends_created}")
        
        # Final commit
        conn.commit()
        
        # Update simulation status
        cur.execute("""
            UPDATE capsim.simulation_runs 
            SET status = %s, end_time = %s
            WHERE run_id = %s
        """, ("completed", datetime.now(), simulation_id))
        
        conn.commit()
        
        end_real_time = time.time()
        execution_time = end_real_time - start_real_time
        
        logger.info("🎉 Simulation completed successfully!")
        logger.info(f"📊 Final Statistics:")
        logger.info(f"   Simulation ID: {simulation_id}")
        logger.info(f"   Simulation time: {current_time:.0f} minutes")
        logger.info(f"   Total agents: {len(agents)}")
        logger.info(f"   Events processed: {events_processed}")
        logger.info(f"   Trends created: {trends_created}")
        logger.info(f"   Execution time: {execution_time:.2f} seconds")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_results(simulation_id: str):
    """Показывает результаты симуляции."""
    try:
        conn = psycopg2.connect(
            host="postgres",
            database="capsim_db",
            user="capsim_ro",
            password="capsim321",
            port=5432
        )
        
        cur = conn.cursor()
        
        # Simulation summary
        cur.execute("""
            SELECT status, num_agents, duration_days, start_time, end_time
            FROM capsim.simulation_runs 
            WHERE run_id = %s
        """, (simulation_id,))
        
        result = cur.fetchone()
        if result:
            status, num_agents, duration_days, start_time, end_time = result
            logger.info(f"📈 Final Results:")
            logger.info(f"   Status: {status}")
            logger.info(f"   Agents: {num_agents}")
            logger.info(f"   Duration: {duration_days} days")
            logger.info(f"   Started: {start_time}")
            logger.info(f"   Ended: {end_time}")
        
        # Count trends by topic
        cur.execute("""
            SELECT topic, COUNT(*) as count, AVG(base_virality_score) as avg_virality
            FROM capsim.trends 
            WHERE simulation_id = %s 
            GROUP BY topic
            ORDER BY count DESC
        """, (simulation_id,))
        
        topic_stats = cur.fetchall()
        if topic_stats:
            logger.info(f"   Trends by topic:")
            for topic, count, avg_virality in topic_stats:
                logger.info(f"     - {topic}: {count} trends, avg virality={avg_virality:.2f}")
        
        # Count events by type
        cur.execute("""
            SELECT event_type, COUNT(*) as count
            FROM capsim.events 
            WHERE simulation_id = %s 
            GROUP BY event_type
        """, (simulation_id,))
        
        event_stats = cur.fetchall()
        if event_stats:
            logger.info(f"   Events by type:")
            for event_type, count in event_stats:
                logger.info(f"     - {event_type}: {count}")
        
        # Top trends by virality
        cur.execute("""
            SELECT topic, base_virality_score, total_interactions
            FROM capsim.trends 
            WHERE simulation_id = %s 
            ORDER BY base_virality_score DESC 
            LIMIT 5
        """, (simulation_id,))
        
        top_trends = cur.fetchall()
        if top_trends:
            logger.info(f"   Top 5 trends by virality:")
            for topic, virality, interactions in top_trends:
                logger.info(f"     - {topic}: virality={virality:.2f}, interactions={interactions}")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Results display failed: {e}")
        return False


def generate_personal_data(profession: str) -> Dict[str, Any]:
    """
    Генерирует персональные данные с учетом профессиональных ограничений.
    
    Возрастные ограничения:
    - Политик: от 35 лет
    - Учитель и Доктор: от 30 лет  
    - Остальные: от 18 лет
    Максимальный возраст: 80 лет
    """
    # Определяем возрастные ограничения
    min_age = 18
    if profession == "Politician":
        min_age = 35
    elif profession in ["Teacher", "Doctor"]:
        min_age = 30
    
    max_age = 80
    age = random.randint(min_age, max_age)
    
    # Вычисляем дату рождения
    birth_year = datetime.now().year - age
    birth_month = random.randint(1, 12)
    
    # Определяем максимальный день в месяце
    if birth_month in [1, 3, 5, 7, 8, 10, 12]:
        max_day = 31
    elif birth_month in [4, 6, 9, 11]:
        max_day = 30
    else:  # февраль
        # Проверяем високосный год
        if (birth_year % 4 == 0 and birth_year % 100 != 0) or (birth_year % 400 == 0):
            max_day = 29
        else:
            max_day = 28
    
    birth_day = random.randint(1, max_day)
    date_of_birth = date(birth_year, birth_month, birth_day)
    
    # Случайно выбираем пол
    sex = random.choice(['male', 'female'])
    
    # Генерируем имя и фамилию в соответствии с полом
    if sex == 'male':
        first_name = fake.first_name_male()
        last_name = fake.last_name_male()
    else:
        first_name = fake.first_name_female()
        last_name = fake.last_name_female()
    
    return {
        'first_name': first_name,
        'last_name': last_name,
        'date_of_birth': date_of_birth,
        'sex': sex,
        'age': age
    }


def main():
    """Главная функция запуска."""
    logger.info("🏗️ CAPSIM Simple Database Simulation")
    logger.info("=" * 50)
    
    # Step 1: Check database connection
    logger.info("Step 1: Checking database connection...")
    if not check_database_connection():
        logger.error("❌ Cannot connect to database")
        return False
    
    # Step 2: Initialize database
    logger.info("Step 2: Initializing database...")
    if not initialize_database():
        logger.error("❌ Database initialization failed")
        return False
    
    # Step 3: Create simulation with agents
    logger.info("Step 3: Creating simulation with 100 agents...")
    simulation_id = create_simulation_with_agents()
    if not simulation_id:
        logger.error("❌ Simulation creation failed")
        return False
    
    # Step 4: Run simulation
    logger.info("Step 4: Running 1-day simulation...")
    success = run_basic_simulation(simulation_id)
    
    if success:
        # Step 5: Show results
        logger.info("Step 5: Displaying results...")
        show_results(simulation_id)
        
        logger.info("🎉 All steps completed successfully!")
        logger.info(f"✅ Simulation ID: {simulation_id}")
        logger.info("💾 Data saved to PostgreSQL database")
        logger.info("🔍 Check results with:")
        logger.info("   docker exec -it capsim-postgres-1 psql -U postgres -d capsim_db")
        logger.info("   \\c capsim_db")
        logger.info(f"   SELECT * FROM capsim.simulation_runs WHERE run_id = '{simulation_id}';")
        return True
    else:
        logger.error("❌ Simulation failed")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("⚠️ Simulation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 