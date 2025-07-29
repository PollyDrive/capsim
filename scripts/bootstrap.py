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
                sentiment VARCHAR(10) DEFAULT 'Positive',
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
        
    def seed_agents_profession_table(self) -> None:
        """Заполняет таблицу agents_profession диапазонами атрибутов согласно ТЗ v1.5."""
        print("📊 Заполнение `agents_profession`...")
        
        engine = create_engine(self.sync_url)
        
        profession_ranges = {
            'ShopClerk': {'financial_capability': (2, 4), 'trend_receptivity': (1.5, 3.0), 'social_status': (1, 3), 'energy_level': (2, 5), 'time_budget': (3, 5)},
            'Worker': {'financial_capability': (2, 4), 'trend_receptivity': (1.5, 3.0), 'social_status': (1, 2), 'energy_level': (2, 5), 'time_budget': (3, 5)},
            'Developer': {'financial_capability': (3, 5), 'trend_receptivity': (2.5, 4.0), 'social_status': (2, 4), 'energy_level': (2, 5), 'time_budget': (2, 4)},
            'Politician': {'financial_capability': (3, 5), 'trend_receptivity': (2.5, 4.0), 'social_status': (4, 5), 'energy_level': (2, 5), 'time_budget': (2, 4)},
            'Blogger': {'financial_capability': (2, 4), 'trend_receptivity': (3.0, 4.0), 'social_status': (3, 5), 'energy_level': (2, 5), 'time_budget': (3, 5)},
            'Businessman': {'financial_capability': (4, 5), 'trend_receptivity': (2, 3.5), 'social_status': (4, 5), 'energy_level': (2, 5), 'time_budget': (2, 4)},
            'SpiritualMentor': {'financial_capability': (1, 3), 'trend_receptivity': (1.5, 3.5), 'social_status': (2, 4), 'energy_level': (3, 5), 'time_budget': (2, 4)},
            'Philosopher': {'financial_capability': (1, 3), 'trend_receptivity': (1.5, 3.0), 'social_status': (1, 3), 'energy_level': (2, 5), 'time_budget': (2, 4)},
            'Unemployed': {'financial_capability': (1, 2), 'trend_receptivity': (2.5, 4.0), 'social_status': (1, 2), 'energy_level': (3, 5), 'time_budget': (3, 5)},
            'Teacher': {'financial_capability': (1, 3), 'trend_receptivity': (1.5, 3.0), 'social_status': (2, 4), 'energy_level': (2, 5), 'time_budget': (2, 4)},
            'Artist': {'financial_capability': (1, 3), 'trend_receptivity': (1.5, 3.5), 'social_status': (2, 4), 'energy_level': (4, 5), 'time_budget': (3, 5)},
            'Doctor': {'financial_capability': (2, 4), 'trend_receptivity': (1.5, 3.0), 'social_status': (3, 5), 'energy_level': (2, 5), 'time_budget': (1, 2)}
        }

        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE capsim.agents_profession RESTART IDENTITY CASCADE"))
            
            insert_data = []
            for profession, ranges in profession_ranges.items():
                insert_data.append({
                    "profession": profession,
                    "financial_capability_min": ranges['financial_capability'][0], "financial_capability_max": ranges['financial_capability'][1],
                    "trend_receptivity_min": ranges['trend_receptivity'][0], "trend_receptivity_max": ranges['trend_receptivity'][1],
                    "social_status_min": ranges['social_status'][0], "social_status_max": ranges['social_status'][1],
                    "energy_level_min": ranges['energy_level'][0], "energy_level_max": ranges['energy_level'][1],
                    "time_budget_min": ranges['time_budget'][0], "time_budget_max": ranges['time_budget'][1],
                })
            
            if insert_data:
                conn.execute(text("""
                    INSERT INTO capsim.agents_profession (
                        profession, financial_capability_min, financial_capability_max, 
                        trend_receptivity_min, trend_receptivity_max, social_status_min, social_status_max, 
                        energy_level_min, energy_level_max, time_budget_min, time_budget_max
                    ) VALUES (
                        :profession, :financial_capability_min, :financial_capability_max, 
                        :trend_receptivity_min, :trend_receptivity_max, :social_status_min, :social_status_max, 
                        :energy_level_min, :energy_level_max, :time_budget_min, :time_budget_max
                    )
                """), insert_data)
            conn.commit()
            
        print(f"✅ Заполнено {len(profession_ranges)} профессий в `agents_profession`")

    def seed_affinity_map_table(self) -> None:
        """Заполняет `affinity_map` согласно ТЗ v1.5."""
        print("📊 Заполнение `affinity_map`...")
        engine = create_engine(self.sync_url)
        affinity_data = {
            'ShopClerk': {'Economic': 3, 'Health': 2, 'Spiritual': 2, 'Conspiracy': 3, 'Science': 1, 'Culture': 2, 'Sport': 2},
            'Worker': {'Economic': 3, 'Health': 3, 'Spiritual': 2, 'Conspiracy': 3, 'Science': 1, 'Culture': 2, 'Sport': 3},
            'Developer': {'Economic': 3, 'Health': 2, 'Spiritual': 1, 'Conspiracy': 2, 'Science': 5, 'Culture': 3, 'Sport': 2},
            'Politician': {'Economic': 5, 'Health': 4, 'Spiritual': 2, 'Conspiracy': 2, 'Science': 3, 'Culture': 3, 'Sport': 2},
            'Blogger': {'Economic': 4, 'Health': 4, 'Spiritual': 3, 'Conspiracy': 4, 'Science': 3, 'Culture': 5, 'Sport': 4},
            'Businessman': {'Economic': 5, 'Health': 3, 'Spiritual': 2, 'Conspiracy': 2, 'Science': 3, 'Culture': 3, 'Sport': 3},
            'Doctor': {'Economic': 3, 'Health': 5, 'Spiritual': 2, 'Conspiracy': 1, 'Science': 5, 'Culture': 2, 'Sport': 3},
            'Teacher': {'Economic': 3, 'Health': 4, 'Spiritual': 3, 'Conspiracy': 2, 'Science': 4, 'Culture': 4, 'Sport': 3},
            'Unemployed': {'Economic': 4, 'Health': 3, 'Spiritual': 3, 'Conspiracy': 4, 'Science': 2, 'Culture': 3, 'Sport': 3},
            'Artist': {'Economic': 2, 'Health': 2, 'Spiritual': 4, 'Conspiracy': 2, 'Science': 2, 'Culture': 5, 'Sport': 2},
            'SpiritualMentor': {'Economic': 2, 'Health': 3, 'Spiritual': 5, 'Conspiracy': 3, 'Science': 2, 'Culture': 3, 'Sport': 2},
            'Philosopher': {'Economic': 3, 'Health': 3, 'Spiritual': 5, 'Conspiracy': 3, 'Science': 4, 'Culture': 4, 'Sport': 1}
        }
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE capsim.affinity_map RESTART IDENTITY CASCADE"))
            insert_data = []
            for profession, topics in affinity_data.items():
                for topic, score in topics.items():
                    insert_data.append({"profession": profession, "topic": topic, "affinity_score": score})
            
            if insert_data:
                conn.execute(text("""
                    INSERT INTO capsim.affinity_map (profession, topic, affinity_score)
                    VALUES (:profession, :topic, :affinity_score)
                """), insert_data)
            conn.commit()
        print(f"✅ Загружено {len(insert_data)} записей аффинити")

    def seed_agent_interests_table(self) -> None:
        """Заполняет `agent_interests` согласно ТЗ v1.5."""
        print("🎯 Заполнение `agent_interests`...")
        engine = create_engine(self.sync_url)
        interest_ranges = {
            'ShopClerk': {'Economics': (4.59, 5.0), 'Wellbeing': (0.74, 1.34), 'Spirituality': (0.64, 1.24), 'Knowledge': (1.15, 1.75), 'Creativity': (1.93, 2.53), 'Society': (2.70, 3.30)},
            'Worker': {'Economics': (3.97, 4.57), 'Wellbeing': (1.05, 1.65), 'Spirituality': (1.86, 2.46), 'Knowledge': (1.83, 2.43), 'Creativity': (0.87, 1.47), 'Society': (0.69, 1.29)},
            'Developer': {'Economics': (1.82, 2.42), 'Wellbeing': (1.15, 1.75), 'Spirituality': (0.72, 1.32), 'Knowledge': (4.05, 4.65), 'Creativity': (2.31, 2.91), 'Society': (1.59, 2.19)},
            'Politician': {'Economics': (0.51, 1.11), 'Wellbeing': (1.63, 2.23), 'Spirituality': (0.32, 0.92), 'Knowledge': (2.07, 2.67), 'Creativity': (1.73, 2.33), 'Society': (3.57, 4.17)},
            'Blogger': {'Economics': (1.32, 1.92), 'Wellbeing': (1.01, 1.61), 'Spirituality': (1.20, 1.80), 'Knowledge': (1.23, 1.83), 'Creativity': (3.27, 3.87), 'Society': (2.43, 3.03)},
            'Businessman': {'Economics': (4.01, 4.61), 'Wellbeing': (0.76, 1.36), 'Spirituality': (0.91, 1.51), 'Knowledge': (1.35, 1.95), 'Creativity': (2.04, 2.64), 'Society': (2.42, 3.02)},
            'Doctor': {'Economics': (1.02, 1.62), 'Wellbeing': (3.97, 4.57), 'Spirituality': (1.37, 1.97), 'Knowledge': (2.01, 2.61), 'Creativity': (1.58, 2.18), 'Society': (2.45, 3.05)},
            'Teacher': {'Economics': (1.32, 1.92), 'Wellbeing': (2.16, 2.76), 'Spirituality': (1.40, 2.00), 'Knowledge': (3.61, 4.21), 'Creativity': (1.91, 2.51), 'Society': (2.24, 2.84)},
            'Unemployed': {'Economics': (0.72, 1.32), 'Wellbeing': (1.38, 1.98), 'Spirituality': (3.69, 4.29), 'Knowledge': (2.15, 2.75), 'Creativity': (2.33, 2.93), 'Society': (2.42, 3.02)},
            'Artist': {'Economics': (0.86, 1.46), 'Wellbeing': (0.91, 1.51), 'Spirituality': (2.01, 2.61), 'Knowledge': (1.82, 2.42), 'Creativity': (3.72, 4.32), 'Society': (1.94, 2.54)},
            'SpiritualMentor': {'Economics': (0.62, 1.22), 'Wellbeing': (2.04, 2.64), 'Spirituality': (3.86, 4.46), 'Knowledge': (2.11, 2.71), 'Creativity': (2.12, 2.72), 'Society': (1.95, 2.55)},
            'Philosopher': {'Economics': (1.06, 1.66), 'Wellbeing': (2.22, 2.82), 'Spirituality': (3.71, 4.31), 'Knowledge': (3.01, 3.61), 'Creativity': (2.21, 2.81), 'Society': (1.80, 2.40)}
        }
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE capsim.agent_interests RESTART IDENTITY CASCADE"))
            insert_data = []
            for profession, interests in interest_ranges.items():
                for interest_name, (min_val, max_val) in interests.items():
                    insert_data.append({"profession": profession, "interest_name": interest_name, "min_value": min_val, "max_value": max_val})
            
            if insert_data:
                conn.execute(text("""
                    INSERT INTO capsim.agent_interests (profession, interest_name, min_value, max_value)
                    VALUES (:profession, :interest_name, :min_value, :max_value)
                """), insert_data)
            conn.commit()
        print(f"✅ Создано {len(insert_data)} записей `agent_interests`")
        
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
            
            # Step 3: Seed config tables from TZ
            self.seed_agents_profession_table()
            self.seed_affinity_map_table()
            self.seed_agent_interests_table()
            
            # Step 4: Verify everything
            self.verify_data()
            
            print(f"🎉 CAPSIM Bootstrap завершен успешно!")
            print(f"   💾 БД готова для запуска симуляций")
            
        except Exception as e:
            print(f"❌ Ошибка bootstrap: {e}")
            raise


async def main():
    """Main bootstrap function."""
    bootstrap = CapsimBootstrap()
    await bootstrap.run_bootstrap()


if __name__ == "__main__":
    asyncio.run(main()) 