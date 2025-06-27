#!/usr/bin/env python3
"""
Senior Database Developer Bootstrap Script для CAPSIM.

Выполняет полную инициализацию БД:
1. Создание схемы capsim с правами доступа
2. Создание всех таблиц
3. Загрузка seed данных из trend_affinity.json
4. Генерация 1000 агентов с русскими именами
5. Валидация данных
"""

import os
import sys
import asyncio
import json
import uuid
from typing import Dict, List, Any
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from faker import Faker
from sqlalchemy import create_engine, text

# Используем централизованный маппинг топиков
from capsim.common.topic_mapping import get_display_mapping


class CapsimSeniorBootstrap:
    """Senior Database Developer bootstrap implementation."""
    
    PROFESSIONS = [
        "ShopClerk", "Worker", "Developer", "Politician", "Blogger",
        "Businessman", "Doctor", "Teacher", "Unemployed", "Artist",
        "SpiritualMentor", "Philosopher"
    ]
    
    INTERESTS = [
        "Economics", "Wellbeing", "Security", "Entertainment", 
        "Education", "Technology", "SocialIssues"
    ]
    
    # Используем централизованный маппинг топиков
    TOPICS = list(get_display_mapping().values())
    
    def __init__(self):
        """Инициализация с настройками БД."""
        # Database configuration
        self.postgres_user = os.getenv("POSTGRES_USER", "postgres")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "postgres_password")
        self.postgres_db = os.getenv("POSTGRES_DB", "capsim_db")
        self.capsim_rw_password = os.getenv("CAPSIM_RW_PASSWORD", "capsim321")
        
        # Connection URLs
        self.admin_url = f"postgresql://{self.postgres_user}:{self.postgres_password}@postgres:5432/{self.postgres_db}"
        self.app_url = f"postgresql://capsim_rw:{self.capsim_rw_password}@postgres:5432/{self.postgres_db}"
        
        # Faker for Russian names
        self.fake = Faker('ru_RU')
        
        print(f"🚀 CAPSIM Senior Bootstrap: Инициализация БД...")
        print(f"   Database: {self.postgres_db}")
        print(f"   Schema: capsim")
        print(f"   Target: 1000 русских агентов")
    
    def setup_schema_and_permissions(self) -> None:
        """Создание схемы и настройка прав доступа."""
        print("📊 Создание схемы capsim и настройка прав...")
        
        # Connect as admin user
        conn = psycopg2.connect(
            host="postgres",
            database=self.postgres_db,
            user=self.postgres_user,
            password=self.postgres_password
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with conn.cursor() as cur:
            # Create schema
            cur.execute("CREATE SCHEMA IF NOT EXISTS capsim")
            
            # Grant permissions to capsim_rw
            cur.execute("""
                GRANT USAGE, CREATE ON SCHEMA capsim TO capsim_rw;
                GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA capsim TO capsim_rw;
                GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA capsim TO capsim_rw;
                ALTER DEFAULT PRIVILEGES IN SCHEMA capsim GRANT ALL ON TABLES TO capsim_rw;
                ALTER DEFAULT PRIVILEGES IN SCHEMA capsim GRANT ALL ON SEQUENCES TO capsim_rw;
            """)
            
            print("✅ Схема и права настроены")
        
        conn.close()
    
    def create_tables(self) -> None:
        """Создание всех таблиц в правильном порядке."""
        print("🔧 Создание таблиц capsim...")
        
        engine = create_engine(self.admin_url)
        
        # Define tables in correct order (respecting foreign keys)
        ddl_commands = [
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
            
            # persons table  
            """
            CREATE TABLE IF NOT EXISTS capsim.persons (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                simulation_id UUID NOT NULL REFERENCES capsim.simulation_runs(run_id),
                profession VARCHAR(50) NOT NULL,
                financial_capability FLOAT,
                trend_receptivity FLOAT,
                social_status FLOAT,
                energy_level FLOAT,
                time_budget INTEGER,
                exposure_history JSON,
                interests JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        ]
        
        # Create indexes
        index_commands = [
            "CREATE INDEX IF NOT EXISTS idx_persons_simulation_id ON capsim.persons(simulation_id)",
            "CREATE INDEX IF NOT EXISTS idx_trends_simulation_id ON capsim.trends(simulation_id)",
            "CREATE INDEX IF NOT EXISTS idx_trends_topic ON capsim.trends(topic)",
            "CREATE INDEX IF NOT EXISTS idx_events_simulation_id ON capsim.events(simulation_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON capsim.events(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_events_priority ON capsim.events(priority)",
        ]
        
        with engine.connect() as conn:
            tables_created = 0
            for ddl in ddl_commands:
                try:
                    conn.execute(text(ddl))
                    conn.commit()
                    tables_created += 1
                except Exception as e:
                    print(f"⚠️  Warning creating table: {e}")
                    continue
            
            # Create indexes
            indexes_created = 0
            for idx in index_commands:
                try:
                    conn.execute(text(idx))
                    conn.commit()
                    indexes_created += 1
                except Exception as e:
                    print(f"⚠️  Warning creating index: {e}")
                    continue
        
        print(f"✅ Создано {tables_created} таблиц и {indexes_created} индексов")
    
    def seed_affinity_data(self) -> None:
        """Загрузка данных аффинити из JSON."""
        print("📥 Загрузка данных affinity_map...")
        
        # Load trend_affinity.json
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'trend_affinity.json')
        
        if not os.path.exists(config_path):
            print(f"❌ Файл {config_path} не найден")
            return
        
        with open(config_path, 'r', encoding='utf-8') as f:
            affinity_data = json.load(f)
        
        # Insert data
        engine = create_engine(self.app_url)
        
        with engine.connect() as conn:
            # Clear existing data
            conn.execute(text("DELETE FROM capsim.affinity_map"))
            
            # Insert new data
            insert_count = 0
            for topic, professions in affinity_data.items():
                for profession, score in professions.items():
                    conn.execute(text("""
                        INSERT INTO capsim.affinity_map (profession, topic, affinity_score)
                        VALUES (:profession, :topic, :score)
                        ON CONFLICT (profession, topic) DO UPDATE SET
                            affinity_score = EXCLUDED.affinity_score
                    """), {"profession": profession, "topic": topic, "score": float(score)})
                    insert_count += 1
            
            conn.commit()
        
        print(f"✅ Загружено {insert_count} записей affinity_map")
    
    def seed_agent_interests(self) -> None:
        """Загрузка справочника интересов агентов."""
        print("📊 Создание справочника интересов агентов...")
        
        engine = create_engine(self.app_url)
        
        with engine.connect() as conn:
            # Clear existing data
            conn.execute(text("DELETE FROM capsim.agent_interests"))
            
            # Generate interests for each profession
            insert_count = 0
            for profession in self.PROFESSIONS:
                for interest in self.INTERESTS:
                    # Different ranges for different profession-interest combinations
                    if profession == "Developer" and interest == "Technology":
                        min_val, max_val = 0.7, 0.9
                    elif profession == "Doctor" and interest == "Wellbeing":
                        min_val, max_val = 0.6, 0.9
                    elif profession == "Businessman" and interest == "Economics":
                        min_val, max_val = 0.6, 0.9
                    elif profession == "Teacher" and interest == "Education":
                        min_val, max_val = 0.7, 0.9
                    else:
                        min_val, max_val = 0.1, 0.7
                    
                    conn.execute(text("""
                        INSERT INTO capsim.agent_interests (profession, interest_name, min_value, max_value)
                        VALUES (:profession, :interest, :min_val, :max_val)
                        ON CONFLICT (profession, interest_name) DO UPDATE SET
                            min_value = EXCLUDED.min_value,
                            max_value = EXCLUDED.max_value
                    """), {
                        "profession": profession,
                        "interest": interest, 
                        "min_val": round(min_val, 3),
                        "max_val": round(max_val, 3)
                    })
                    insert_count += 1
            
            conn.commit()
        
        print(f"✅ Создано {insert_count} записей agent_interests")
    
    def generate_russian_agents(self, count: int = 1000) -> str:
        """Генерация агентов с русскими именами и правильным соответствием пола."""
        print(f"👥 Генерация {count} агентов с русскими именами...")
        
        engine = create_engine(self.app_url)
        
        # Create a test simulation run first
        simulation_id = str(uuid.uuid4())
        
        with engine.connect() as conn:
            # Clear existing data  
            conn.execute(text("DELETE FROM capsim.persons"))
            conn.execute(text("DELETE FROM capsim.simulation_runs"))
            
            # Create simulation run
            conn.execute(text("""
                INSERT INTO capsim.simulation_runs (run_id, start_time, status, num_agents, duration_days, configuration)
                VALUES (:run_id, :start_time, :status, :num_agents, :duration_days, :config)
            """), {
                "run_id": simulation_id,
                "start_time": datetime.utcnow(),
                "status": "INITIALIZED", 
                "num_agents": count,
                "duration_days": 7,
                "config": json.dumps({"bootstrap": True, "russian_names": True})
            })
            
            # Generate agents in batches
            batch_size = 100
            agents_created = 0
            
            for batch_start in range(0, count, batch_size):
                batch_end = min(batch_start + batch_size, count)
                agents_batch = []
                
                for i in range(batch_start, batch_end):
                    # Generate Russian name with proper gender matching
                    gender = self.fake.random_element(elements=['male', 'female'])
                    
                    if gender == 'male':
                        first_name = self.fake.first_name_male()
                        last_name = self.fake.last_name_male()
                    else:
                        first_name = self.fake.first_name_female()
                        last_name = self.fake.last_name_female()
                    
                    # Random profession
                    profession = self.fake.random_element(elements=self.PROFESSIONS)
                    
                    # Generate attributes with proper validation
                    financial_capability = round(self.fake.uniform(0.5, 5.0), 3)
                    trend_receptivity = round(self.fake.uniform(0.5, 5.0), 3)
                    social_status = round(self.fake.uniform(0.5, 4.5), 3)  # ≥ 0.5 для осмысленных действий
                    energy_level = round(self.fake.uniform(0.5, 5.0), 3)
                    time_budget = self.fake.random_int(min=1, max=5)
                    
                    # Generate interests (7 categories, each 0.1-0.9)
                    interests = {}
                    for interest in self.INTERESTS:
                        interests[interest] = round(self.fake.uniform(0.1, 0.9), 3)
                    
                    # Validate ranges
                    assert 0.0 <= financial_capability <= 5.0, f"Invalid financial_capability: {financial_capability}"
                    assert 0.0 <= trend_receptivity <= 5.0, f"Invalid trend_receptivity: {trend_receptivity}"
                    assert 0.0 <= social_status <= 5.0, f"Invalid social_status: {social_status}"
                    assert 0.0 <= energy_level <= 5.0, f"Invalid energy_level: {energy_level}"
                    assert 1 <= time_budget <= 5, f"Invalid time_budget: {time_budget}"
                    
                    agents_batch.append({
                        "id": str(uuid.uuid4()),
                        "simulation_id": simulation_id,
                        "profession": profession,
                        "financial_capability": financial_capability,
                        "trend_receptivity": trend_receptivity,
                        "social_status": social_status,
                        "energy_level": energy_level,
                        "time_budget": time_budget,
                        "exposure_history": json.dumps({}),
                        "interests": json.dumps(interests),
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    })
                
                # Bulk insert batch
                if agents_batch:
                    conn.execute(text("""
                        INSERT INTO capsim.persons (
                            id, simulation_id, profession, financial_capability, 
                            trend_receptivity, social_status, energy_level, time_budget,
                            exposure_history, interests, created_at, updated_at
                        ) VALUES (
                            :id, :simulation_id, :profession, :financial_capability,
                            :trend_receptivity, :social_status, :energy_level, :time_budget,
                            :exposure_history, :interests, :created_at, :updated_at
                        )
                    """), agents_batch)
                    
                    agents_created += len(agents_batch)
                    print(f"   📝 Создано агентов: {agents_created}/{count}")
            
            conn.commit()
        
        print(f"✅ Создано {agents_created} агентов с русскими именами")
        return simulation_id
    
    def verify_data(self) -> None:
        """Проверка корректности созданных данных."""
        print("🔍 Проверка целостности данных...")
        
        engine = create_engine(self.app_url)
        
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
            print(f"      - Агенты: {person_count}")
            print(f"      - Аффинити карта: {affinity_count}")
            print(f"      - Интересы агентов: {interests_count}")
            print(f"      - Симуляции: {simulation_count}")
            
            # Validate agent attributes
            if person_count > 0:
                validation_result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE financial_capability BETWEEN 0.5 AND 5.0) as valid_financial,
                        COUNT(*) FILTER (WHERE trend_receptivity BETWEEN 0.5 AND 5.0) as valid_receptivity,
                        COUNT(*) FILTER (WHERE social_status BETWEEN 0.5 AND 4.5) as valid_social,
                        COUNT(*) FILTER (WHERE energy_level BETWEEN 0.5 AND 5.0) as valid_energy
                    FROM capsim.persons
                """)).fetchone()
                
                total = validation_result[0]
                valid_counts = validation_result[1:5]
                
                print(f"   ✅ Валидация атрибутов агентов:")
                print(f"      - Всего агентов: {total}")
                print(f"      - Валидные financial_capability: {valid_counts[0]}/{total}")
                print(f"      - Валидные trend_receptivity: {valid_counts[1]}/{total}")
                print(f"      - Валидные social_status: {valid_counts[2]}/{total}")
                print(f"      - Валидные energy_level: {valid_counts[3]}/{total}")
        
        print("✅ Проверка завершена")
    
    def run_bootstrap(self) -> None:
        """Основной метод bootstrap."""
        print("🚀 Запуск CAPSIM Senior Bootstrap...")
        
        try:
            # Step 1: Setup schema and permissions
            self.setup_schema_and_permissions()
            
            # Step 2: Create tables
            self.create_tables()
            
            # Step 3: Seed affinity data
            self.seed_affinity_data()
            
            # Step 4: Seed agent interests
            self.seed_agent_interests()
            
            # Step 5: Generate Russian agents
            simulation_id = self.generate_russian_agents(1000)
            
            # Step 6: Verify everything
            self.verify_data()
            
            print(f"🎉 CAPSIM Senior Bootstrap завершен успешно!")
            print(f"   💾 БД готова для запуска симуляций")
            print(f"   🆔 Test Simulation ID: {simulation_id}")
            
        except Exception as e:
            print(f"❌ Ошибка bootstrap: {e}")
            raise


def main():
    """Entry point."""
    bootstrap = CapsimSeniorBootstrap()
    bootstrap.run_bootstrap()


if __name__ == "__main__":
    main() 