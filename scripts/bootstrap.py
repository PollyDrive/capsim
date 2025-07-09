#!/usr/bin/env python3
"""
Bootstrap script for CAPSIM database initialization.
Senior Database Developer role implementation.

Выполняет:
1. Создание схемы capsim
2. Применение alembic миграций
3. Загрузка seed данных из trend_affinity.json
4. Генерация 1000 глобальных агентов с русскими именами
5. Инициализация базовых трендов
"""

import os
import sys
import asyncio
import json
import uuid
import logging
import random
from typing import Dict, List, Any
from datetime import datetime, timedelta

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from faker import Faker
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config
from capsim.common.db_config import SYNC_DSN

from capsim.db.models import (
    SimulationRun, Person, SimulationParticipant, Trend, Event, PersonAttributeHistory,
    AgentInterests, AffinityMap, DailyTrendSummary, Base
)
from capsim.db.repositories import DatabaseRepository

# Используем централизованный маппинг топиков
from capsim.common.topic_mapping import get_display_mapping

TOPICS = list(get_display_mapping().values())

class CapsimBootstrap:
    """Bootstrap class for CAPSIM database initialization."""
    
    def __init__(self):
        # Use DSN built from env vars
        self.admin_url = os.getenv("DATABASE_ADMIN_URL", SYNC_DSN)
        self.app_url = os.getenv("DATABASE_URL", SYNC_DSN)
        # Для sync-операций Alembic/seed нам нужен стандартный psycopg2-DSN
        self.sync_url = self.app_url.replace("+asyncpg", "")
        self.fake = Faker("ru_RU")
        
        # Профессии согласно ТЗ
        self.PROFESSIONS = [
            "Teacher", "ShopClerk", "Developer", "Unemployed", "Businessman",
            "Artist", "Worker", "Blogger", "SpiritualMentor", "Philosopher",
            "Politician", "Doctor"
        ]
        
        # Интересы согласно ТЗ
        self.INTERESTS = [
            "Economics", "Wellbeing", "Spirituality", "Society", 
            "Knowledge", "Creativity", "Sport"
        ]
        
    def setup_schema_and_permissions(self) -> None:
        """Setup database schema and permissions."""
        print("🔧 Настройка схемы и прав доступа...")
        
        try:
            conn = psycopg2.connect(self.admin_url)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()
            
            # Create schema
            cur.execute("CREATE SCHEMA IF NOT EXISTS capsim")
            
            # Create user if not exists
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'capsim_rw') THEN
                        CREATE USER capsim_rw;
                    END IF;
                END
                $$;
            """)
            
            # Grant permissions
            cur.execute("GRANT ALL PRIVILEGES ON SCHEMA capsim TO capsim_rw")
            cur.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA capsim TO capsim_rw")
            cur.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA capsim TO capsim_rw")
            cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA capsim GRANT ALL ON TABLES TO capsim_rw")
            cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA capsim GRANT ALL ON SEQUENCES TO capsim_rw")
            
            cur.close()
            conn.close()
            
            print("✅ Схема и права доступа настроены")
            
        except Exception as e:
            print(f"❌ Ошибка настройки схемы: {e}")
            raise
            
    def run_alembic_migration(self) -> None:
        """Run Alembic migrations."""
        print("🔄 Применение миграций Alembic...")
        
        try:
            # Get alembic config
            alembic_cfg = Config("alembic.ini")
            
            # Run migrations
            command.upgrade(alembic_cfg, "head")
            
            print("✅ Миграции применены")
            
        except Exception as e:
            print(f"❌ Ошибка миграций: {e}")
            print("🔄 Попытка создания таблиц вручную...")
            self.create_tables_manually()
            
    def create_tables_manually(self) -> None:
        """Создание таблиц вручную если alembic не сработал."""
        print("🔧 Создание таблиц вручную...")
        
        engine = create_engine(self.sync_url)
        
        # Define tables in correct order (respecting foreign keys)
        ddl_commands = [
            # Schema creation
            "CREATE SCHEMA IF NOT EXISTS capsim",
            
            # simulation_runs table
            """
            CREATE TABLE IF NOT EXISTS capsim.simulation_runs (
                run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                status VARCHAR(50),
                num_agents INTEGER NOT NULL,
                duration_days INTEGER NOT NULL,
                configuration JSON
            )
            """,
            
            # persons table (now global without simulation_id)
            """
            CREATE TABLE IF NOT EXISTS capsim.persons (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                profession VARCHAR(50) NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                gender VARCHAR(10) NOT NULL,
                date_of_birth DATE NOT NULL,
                financial_capability FLOAT,
                trend_receptivity FLOAT,
                social_status FLOAT,
                energy_level FLOAT,
                time_budget NUMERIC(2,1),
                exposure_history JSON,
                interests JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # simulation_participants table
            """
            CREATE TABLE IF NOT EXISTS capsim.simulation_participants (
                simulation_id UUID NOT NULL REFERENCES capsim.simulation_runs(run_id) ON DELETE CASCADE,
                person_id UUID NOT NULL REFERENCES capsim.persons(id) ON DELETE CASCADE,
                purchases_today SMALLINT DEFAULT 0,
                last_post_ts DOUBLE PRECISION,
                last_selfdev_ts DOUBLE PRECISION,
                last_purchase_ts JSONB DEFAULT '{}',
                PRIMARY KEY (simulation_id, person_id)
            )
            """,
            
            # trends table
            """
            CREATE TABLE IF NOT EXISTS capsim.trends (
                trend_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                simulation_id UUID NOT NULL REFERENCES capsim.simulation_runs(run_id),
                topic VARCHAR(50) NOT NULL,
                originator_id UUID NOT NULL REFERENCES capsim.persons(id),
                parent_trend_id UUID REFERENCES capsim.trends(trend_id),
                timestamp_start TIMESTAMP,
                base_virality_score FLOAT,
                coverage_level VARCHAR(20),
                total_interactions INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # events table
            """
            CREATE TABLE IF NOT EXISTS capsim.events (
                event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                simulation_id UUID NOT NULL REFERENCES capsim.simulation_runs(run_id),
                event_type VARCHAR(50) NOT NULL,
                priority INTEGER NOT NULL,
                timestamp FLOAT NOT NULL,
                agent_id UUID REFERENCES capsim.persons(id),
                trend_id UUID REFERENCES capsim.trends(trend_id),
                event_data JSON,
                processed_at TIMESTAMP,
                processing_duration_ms FLOAT
            )
            """,
            
            # person_attribute_history table
            """
            CREATE TABLE IF NOT EXISTS capsim.person_attribute_history (
                id SERIAL PRIMARY KEY,
                simulation_id UUID NOT NULL REFERENCES capsim.simulation_runs(run_id),
                person_id UUID NOT NULL REFERENCES capsim.persons(id),
                attribute_name VARCHAR(50) NOT NULL,
                old_value FLOAT,
                new_value FLOAT NOT NULL,
                delta FLOAT NOT NULL,
                reason VARCHAR(100) NOT NULL,
                source_trend_id UUID,
                change_timestamp FLOAT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # agent_interests table
            """
            CREATE TABLE IF NOT EXISTS capsim.agent_interests (
                id SERIAL PRIMARY KEY,
                profession VARCHAR(50) NOT NULL,
                interest_name VARCHAR(50) NOT NULL,
                min_value FLOAT NOT NULL,
                max_value FLOAT NOT NULL,
                UNIQUE(profession, interest_name)
            )
            """,
            
            # affinity_map table
            """
            CREATE TABLE IF NOT EXISTS capsim.affinity_map (
                id SERIAL PRIMARY KEY,
                profession VARCHAR(50) NOT NULL,
                topic VARCHAR(50) NOT NULL,
                affinity_score FLOAT NOT NULL,
                UNIQUE(profession, topic)
            )
            """,
            
            # daily_trend_summary table
            """
            CREATE TABLE IF NOT EXISTS capsim.daily_trend_summary (
                id SERIAL PRIMARY KEY,
                simulation_id UUID NOT NULL REFERENCES capsim.simulation_runs(run_id),
                simulation_day INTEGER NOT NULL,
                topic VARCHAR(50) NOT NULL,
                total_interactions_today INTEGER,
                avg_virality_today FLOAT,
                top_trend_id UUID,
                unique_authors_count INTEGER,
                pct_change_virality FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(simulation_id, simulation_day, topic)
            )
            """,
            
            # topic_interest_mapping table
            """
            CREATE TABLE IF NOT EXISTS capsim.topic_interest_mapping (
                id SERIAL PRIMARY KEY,
                topic_code VARCHAR(20) NOT NULL UNIQUE,
                topic_display VARCHAR(50) NOT NULL,
                interest_category VARCHAR(50) NOT NULL,
                description TEXT
            )
            """
        ]
        
        with engine.connect() as conn:
            for ddl in ddl_commands:
                conn.execute(text(ddl))
            conn.commit()
            
        print("✅ Таблицы созданы вручную")
        
    def seed_affinity_data(self) -> None:
        """Загрузка данных аффинити из trend_affinity.json."""
        print("📊 Загрузка данных аффинити...")
        
        try:
            # Load affinity data from JSON
            affinity_file = "config/trend_affinity.json"
            if not os.path.exists(affinity_file):
                print(f"⚠️  Файл {affinity_file} не найден, создаем базовые данные")
                self.create_basic_affinity_data()
                return
                
            with open(affinity_file, 'r', encoding='utf-8') as f:
                affinity_data = json.load(f)
                
            engine = create_engine(self.sync_url)
            
            with engine.connect() as conn:
                # Clear existing data
                conn.execute(text("DELETE FROM capsim.affinity_map"))
                
                # Insert new data
                insert_count = 0
                for profession, topics in affinity_data.items():
                    for topic, score in topics.items():
                        conn.execute(text("""
                            INSERT INTO capsim.affinity_map (profession, topic, affinity_score)
                            VALUES (:profession, :topic, :score)
                        """), {
                            "profession": profession,
                            "topic": topic,
                            "score": score
                        })
                        insert_count += 1
                        
                conn.commit()
                
            print(f"✅ Загружено {insert_count} записей аффинити")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки аффинити: {e}")
            self.create_basic_affinity_data()
            
    def create_basic_affinity_data(self) -> None:
        """Создание базовых данных аффинити."""
        print("🔧 Создание базовых данных аффинити...")
        
        engine = create_engine(self.sync_url)
        
        # Basic affinity data
        basic_affinity = {
            "Teacher": {"Economic": 3.5, "Health": 4.0, "Science": 4.5},
            "Developer": {"Economic": 4.0, "Science": 4.5, "Culture": 3.5},
            "Worker": {"Economic": 4.5, "Sport": 3.5, "Society": 3.0},
            "ShopClerk": {"Economic": 4.0, "Culture": 3.0, "Sport": 2.5},
            "Businessman": {"Economic": 5.0, "Society": 3.5, "Culture": 3.0},
            "Artist": {"Culture": 5.0, "Spiritual": 3.5, "Society": 3.0},
            "Blogger": {"Culture": 4.5, "Society": 4.0, "Economic": 3.5},
            "Unemployed": {"Economic": 4.5, "Society": 4.0, "Conspiracy": 3.5},
            "SpiritualMentor": {"Spiritual": 5.0, "Health": 4.0, "Society": 3.5},
            "Philosopher": {"Spiritual": 4.5, "Science": 4.0, "Society": 4.0},
            "Politician": {"Society": 5.0, "Economic": 4.5, "Science": 3.0},
            "Doctor": {"Health": 5.0, "Science": 4.5, "Economic": 3.0}
        }
        
        with engine.connect() as conn:
            # Clear existing data
            conn.execute(text("DELETE FROM capsim.affinity_map"))
            
            # Insert basic data
            insert_count = 0
            for profession, topics in basic_affinity.items():
                for topic, score in topics.items():
                    conn.execute(text("""
                        INSERT INTO capsim.affinity_map (profession, topic, affinity_score)
                        VALUES (:profession, :topic, :score)
                    """), {
                        "profession": profession,
                        "topic": topic,
                        "score": score
                    })
                    insert_count += 1
                    
            conn.commit()
            
        print(f"✅ Создано {insert_count} базовых записей аффинити")
        
    def seed_agent_interests(self) -> None:
        """Загрузка интересов агентов по профессиям."""
        print("🎯 Загрузка интересов агентов...")
        
        engine = create_engine(self.sync_url)
        
        # Interest ranges by profession
        interest_ranges = {
            "Teacher": {"Economics": (0.3, 0.7), "Wellbeing": (0.4, 0.8), "Knowledge": (0.6, 0.9)},
            "Developer": {"Economics": (0.4, 0.8), "Knowledge": (0.6, 0.9), "Creativity": (0.3, 0.7)},
            "Worker": {"Economics": (0.5, 0.9), "Sport": (0.4, 0.8), "Society": (0.3, 0.7)},
            "ShopClerk": {"Economics": (0.4, 0.8), "Creativity": (0.2, 0.6), "Sport": (0.2, 0.6)},
            "Businessman": {"Economics": (0.7, 1.0), "Society": (0.4, 0.8), "Creativity": (0.2, 0.6)},
            "Artist": {"Creativity": (0.7, 1.0), "Spirituality": (0.3, 0.7), "Society": (0.3, 0.7)},
            "Blogger": {"Creativity": (0.5, 0.9), "Society": (0.5, 0.9), "Economics": (0.3, 0.7)},
            "Unemployed": {"Economics": (0.6, 1.0), "Society": (0.5, 0.9), "Sport": (0.2, 0.6)},
            "SpiritualMentor": {"Spirituality": (0.7, 1.0), "Wellbeing": (0.5, 0.9), "Society": (0.3, 0.7)},
            "Philosopher": {"Spirituality": (0.6, 1.0), "Knowledge": (0.6, 0.9), "Society": (0.4, 0.8)},
            "Politician": {"Society": (0.7, 1.0), "Economics": (0.5, 0.9), "Knowledge": (0.3, 0.7)},
            "Doctor": {"Wellbeing": (0.7, 1.0), "Knowledge": (0.6, 0.9), "Economics": (0.3, 0.7)}
        }
        
        with engine.connect() as conn:
            # Clear existing data
            conn.execute(text("DELETE FROM capsim.agent_interests"))
            
            # Insert interest ranges
            insert_count = 0
            for profession, interests in interest_ranges.items():
                for interest_name, (min_val, max_val) in interests.items():
                    conn.execute(text("""
                        INSERT INTO capsim.agent_interests (profession, interest_name, min_value, max_value)
                        VALUES (:profession, :interest_name, :min_value, :max_value)
                    """), {
                        "profession": profession,
                        "interest_name": interest_name,
                        "min_value": min_val,
                        "max_value": max_val
                    })
                    insert_count += 1
                    
            conn.commit()
        
        print(f"✅ Создано {insert_count} записей agent_interests")
    
    def generate_global_agents(self, count: int = 1000) -> None:
        """Генерация глобальных агентов с русскими именами."""
        print(f"👥 Генерация {count} глобальных агентов с русскими именами...")
        
        engine = create_engine(self.sync_url)
        
        with engine.connect() as conn:
            # Clear existing data in correct order (respecting foreign keys)
            conn.execute(text("DELETE FROM capsim.events"))
            conn.execute(text("DELETE FROM capsim.person_attribute_history"))
            conn.execute(text("DELETE FROM capsim.trends"))
            conn.execute(text("DELETE FROM capsim.simulation_participants"))
            conn.execute(text("DELETE FROM capsim.persons"))
            conn.execute(text("DELETE FROM capsim.simulation_runs"))
            
            # ✨ Load attribute ranges from agents_profession once
            ranges_map = {
                row['profession']: {
                    'financial_capability': (row['financial_capability_min'], row['financial_capability_max']),
                    'trend_receptivity': (row['trend_receptivity_min'], row['trend_receptivity_max']),
                    'social_status': (row['social_status_min'], row['social_status_max']),
                    'energy_level': (row['energy_level_min'], row['energy_level_max']),
                    'time_budget': (row['time_budget_min'], row['time_budget_max']),
                }
                for row in conn.execute(text("SELECT * FROM capsim.agents_profession")).mappings()
            }

            # Generate agents in batches
            batch_size = 100
            agents_created = 0
            
            for batch_start in range(0, count, batch_size):
                batch_end = min(batch_start + batch_size, count)
                agents_batch = []
                
                for _ in range(batch_start, batch_end):
                    # Generate Russian name with proper gender matching
                    gender = random.choice(['male', 'female'])
                    
                    if gender == 'male':
                        first_name = self.fake.first_name_male()
                        last_name = self.fake.last_name_male()
                    else:
                        first_name = self.fake.first_name_female()
                        last_name = self.fake.last_name_female()
                    
                    # Random profession
                    profession = random.choice(self.PROFESSIONS)
                    
                    prof_ranges = ranges_map.get(profession)
                    if not prof_ranges:
                        raise ValueError(f"Ranges for profession {profession} not found in agents_profession table")

                    # Generate attributes strictly within ranges
                    financial_capability = round(random.uniform(*prof_ranges['financial_capability']), 3)
                    trend_receptivity = round(random.uniform(*prof_ranges['trend_receptivity']), 3)
                    social_status = round(random.uniform(*prof_ranges['social_status']), 3)
                    energy_level = round(random.uniform(*prof_ranges['energy_level']), 3)
                    time_budget = float(round(random.uniform(*prof_ranges['time_budget']) * 2) / 2)
                    
                    # Generate birth date (18-65 years old)
                    current_year = datetime.now().year
                    birth_year = random.randint(current_year - 65, current_year - 18)
                    birth_date = datetime(birth_year, random.randint(1, 12), random.randint(1, 28)).date()
                    
                    # Validate ranges
                    assert 0.0 <= financial_capability <= 5.0, f"Invalid financial_capability: {financial_capability}"
                    assert 0.0 <= trend_receptivity <= 5.0, f"Invalid trend_receptivity: {trend_receptivity}"
                    assert 0.0 <= social_status <= 5.0, f"Invalid social_status: {social_status}"
                    assert 0.0 <= energy_level <= 5.0, f"Invalid energy_level: {energy_level}"
                    assert 1.0 <= time_budget <= 5.0, f"Invalid time_budget: {time_budget}"
                    
                    agents_batch.append({
                        "id": str(uuid.uuid4()),
                        "profession": profession,
                        "first_name": first_name,
                        "last_name": last_name,
                        "gender": gender,
                        "date_of_birth": birth_date,
                        "financial_capability": financial_capability,
                        "trend_receptivity": trend_receptivity,
                        "social_status": social_status,
                        "energy_level": energy_level,
                        "time_budget": time_budget,
                        "exposure_history": json.dumps({}),
                        "interests": json.dumps({}),
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    })
                
                # Bulk insert batch
                if agents_batch:
                    conn.execute(text("""
                        INSERT INTO capsim.persons (
                            id, profession, first_name, last_name, gender, date_of_birth,
                            financial_capability, trend_receptivity, social_status, energy_level, 
                            time_budget, exposure_history, interests, created_at, updated_at
                        ) VALUES (
                            :id, :profession, :first_name, :last_name, :gender, :date_of_birth,
                            :financial_capability, :trend_receptivity, :social_status, :energy_level,
                            :time_budget, :exposure_history, :interests, :created_at, :updated_at
                        )
                    """), agents_batch)
                    
                    agents_created += len(agents_batch)
                    print(f"   📝 Создано агентов: {agents_created}/{count}")
            
            conn.commit()
        
        print(f"✅ Создано {agents_created} глобальных агентов с русскими именами")
    
    def verify_data(self) -> None:
        """Проверка корректности созданных данных."""
        print("🔍 Проверка целостности данных...")
        
        engine = create_engine(self.sync_url)
        
        with engine.connect() as conn:
            # Check tables exist
            tables_result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'capsim'
                ORDER BY table_name
            """))
            tables = [row[0] for row in tables_result]
            print(f"   📊 Таблицы в схеме capsim: {len(tables)}")
            for table in tables:
                print(f"      - {table}")
            
            # Check data counts
            person_count = conn.execute(text("SELECT COUNT(*) FROM capsim.persons")).scalar()
            affinity_count = conn.execute(text("SELECT COUNT(*) FROM capsim.affinity_map")).scalar()
            interests_count = conn.execute(text("SELECT COUNT(*) FROM capsim.agent_interests")).scalar()
            simulation_count = conn.execute(text("SELECT COUNT(*) FROM capsim.simulation_runs")).scalar()
            
            print(f"   📈 Записей данных:")
            print(f"      - Глобальные агенты: {person_count}")
            print(f"      - Аффинити карта: {affinity_count}")
            print(f"      - Интересы агентов: {interests_count}")
            print(f"      - Симуляции: {simulation_count}")
            
            # Verify person data integrity
            if person_count > 0:
                # Check attribute ranges
                invalid_energy = conn.execute(text("""
                    SELECT COUNT(*) FROM capsim.persons 
                    WHERE energy_level < 0.0 OR energy_level > 5.0
                """)).scalar()
                
                invalid_social = conn.execute(text("""
                    SELECT COUNT(*) FROM capsim.persons 
                    WHERE social_status < 0.0 OR social_status > 5.0
                """)).scalar()
                
                print(f"   ✅ Проверка атрибутов:")
                print(f"      - Некорректная энергия: {invalid_energy}")
                print(f"      - Некорректный соц. статус: {invalid_social}")
                
                # Check profession distribution
                profession_dist = conn.execute(text("""
                    SELECT profession, COUNT(*) as count 
                    FROM capsim.persons 
                    GROUP BY profession 
                    ORDER BY count DESC
                """)).fetchall()
                
                print(f"   📊 Распределение профессий:")
                for prof, count in profession_dist[:5]:  # Top 5
                    print(f"      - {prof}: {count}")
    
    async def run_bootstrap(self) -> None:
        """Основной метод bootstrap."""
        print("🚀 Запуск CAPSIM Bootstrap...")
        
        try:
            # Step 1: Setup schema and permissions
            self.setup_schema_and_permissions()
            
            # Step 2: Run migrations
            self.run_alembic_migration()
            
            # Step 3: Seed affinity data
            self.seed_affinity_data()
            
            # Step 4: Seed agent interests
            self.seed_agent_interests()
            
            # Step 5: Generate global agents
            self.generate_global_agents(1000)
            
            # Step 6: Verify everything
            self.verify_data()
            
            print(f"🎉 CAPSIM Bootstrap завершен успешно!")
            print(f"   💾 БД готова для запуска симуляций")
            print(f"   👥 Создано 1000 глобальных агентов")
            
        except Exception as e:
            print(f"❌ Ошибка bootstrap: {e}")
            raise


async def main():
    """Main bootstrap function."""
    bootstrap = CapsimBootstrap()
    await bootstrap.run_bootstrap()


if __name__ == "__main__":
    asyncio.run(main()) 