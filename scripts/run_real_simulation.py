#!/usr/bin/env python3
"""
Real database simulation runner for CAPSIM.

Runs simulation with 100 agents for 1 day on actual PostgreSQL database.
Includes full database initialization, migration, and data seeding.
"""

import os
import sys
import json
import asyncio
import logging
import psycopg2
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_database_connection():
    """Проверяет подключение к базе данных."""
    try:
        # Use docker container hostname
        conn = psycopg2.connect(
            host="localhost",  # Docker exposes on localhost:5432
            database=os.getenv("POSTGRES_DB", "capsim_db"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "capsim321"),
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


def run_alembic_migrations():
    """Выполняет миграции Alembic программно."""
    try:
        from alembic.config import Config
        from alembic import command
        
        # Configure Alembic
        alembic_cfg = Config(str(project_root / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))
        
        # Set database URL for migrations
        database_url = f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'capsim321')}@localhost:5432/{os.getenv('POSTGRES_DB', 'capsim_db')}"
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        
        # Run upgrade
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Database migrations completed")
        return True
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


def create_database_users():
    """Создает пользователей базы данных capsim_rw и capsim_ro."""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database=os.getenv("POSTGRES_DB", "capsim_db"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "capsim321"),
            port=5432
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Create capsim_rw user
        rw_password = os.getenv("CAPSIM_RW_PASSWORD", "capsim321")
        try:
            cur.execute(f"CREATE USER capsim_rw WITH PASSWORD '{rw_password}'")
            logger.info("✅ Created capsim_rw user")
        except psycopg2.errors.DuplicateObject:
            logger.info("⚡ capsim_rw user already exists")
        
        # Create capsim_ro user  
        ro_password = os.getenv("CAPSIM_RO_PASSWORD", "capsim321")
        try:
            cur.execute(f"CREATE USER capsim_ro WITH PASSWORD '{ro_password}'")
            logger.info("✅ Created capsim_ro user")
        except psycopg2.errors.DuplicateObject:
            logger.info("⚡ capsim_ro user already exists")
        
        # Grant permissions
        cur.execute("GRANT ALL PRIVILEGES ON SCHEMA capsim TO capsim_rw")
        cur.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA capsim TO capsim_rw")
        cur.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA capsim TO capsim_rw")
        
        cur.execute("GRANT USAGE ON SCHEMA capsim TO capsim_ro")
        cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA capsim TO capsim_ro")
        
        logger.info("✅ Database users configured")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ User creation failed: {e}")
        return False


def load_affinity_map():
    """Загружает affinity map из config файла."""
    try:
        # Load from config
        affinity_file = project_root / "config" / "trend_affinity.json"
        with open(affinity_file, 'r') as f:
            affinity_data = json.load(f)
        
        # Connect as capsim_rw
        conn = psycopg2.connect(
            host="localhost",
            database=os.getenv("POSTGRES_DB", "capsim_db"),
            user="capsim_rw",
            password=os.getenv("CAPSIM_RW_PASSWORD", "capsim321"),
            port=5432
        )
        
        cur = conn.cursor()
        
        # Check if data already exists
        cur.execute("SELECT COUNT(*) FROM capsim.affinity_map")
        count = cur.fetchone()[0]
        
        if count == 0:
            # Insert affinity mappings
            for topic, professions in affinity_data.items():
                for profession, score in professions.items():
                    cur.execute("""
                        INSERT INTO capsim.affinity_map (profession, topic, affinity_score)
                        VALUES (%s, %s, %s)
                    """, (profession, topic, score))
            
            conn.commit()
            logger.info(f"✅ Loaded {sum(len(p) for p in affinity_data.values())} affinity mappings")
        else:
            logger.info("⚡ Affinity map already loaded")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Affinity map loading failed: {e}")
        return False


def load_agent_interests():
    """Загружает диапазоны интересов агентов."""
    try:
        # Agent interests from specification
        interests_data = [
            # Banker
            {"profession": "Banker", "interest_name": "Economics", "min_value": 3.0, "max_value": 5.0},
            {"profession": "Banker", "interest_name": "Wellbeing", "min_value": 1.5, "max_value": 3.0},
            {"profession": "Banker", "interest_name": "Religion", "min_value": 0.5, "max_value": 2.0},
            {"profession": "Banker", "interest_name": "Politics", "min_value": 2.0, "max_value": 4.0},
            {"profession": "Banker", "interest_name": "Education", "min_value": 1.5, "max_value": 3.5},
            {"profession": "Banker", "interest_name": "Entertainment", "min_value": 2.0, "max_value": 4.0},
            
            # Developer
            {"profession": "Developer", "interest_name": "Economics", "min_value": 2.0, "max_value": 4.0},
            {"profession": "Developer", "interest_name": "Wellbeing", "min_value": 1.5, "max_value": 3.5},
            {"profession": "Developer", "interest_name": "Religion", "min_value": 0.5, "max_value": 2.5},
            {"profession": "Developer", "interest_name": "Politics", "min_value": 1.0, "max_value": 3.0},
            {"profession": "Developer", "interest_name": "Education", "min_value": 3.5, "max_value": 5.0},
            {"profession": "Developer", "interest_name": "Entertainment", "min_value": 2.5, "max_value": 4.5},
            
            # Teacher
            {"profession": "Teacher", "interest_name": "Economics", "min_value": 1.5, "max_value": 3.5},
            {"profession": "Teacher", "interest_name": "Wellbeing", "min_value": 2.5, "max_value": 4.5},
            {"profession": "Teacher", "interest_name": "Religion", "min_value": 1.0, "max_value": 3.0},
            {"profession": "Teacher", "interest_name": "Politics", "min_value": 2.0, "max_value": 4.5},
            {"profession": "Teacher", "interest_name": "Education", "min_value": 4.0, "max_value": 5.0},
            {"profession": "Teacher", "interest_name": "Entertainment", "min_value": 3.0, "max_value": 5.0},
            
            # Worker
            {"profession": "Worker", "interest_name": "Economics", "min_value": 2.0, "max_value": 4.0},
            {"profession": "Worker", "interest_name": "Wellbeing", "min_value": 2.0, "max_value": 4.0},
            {"profession": "Worker", "interest_name": "Religion", "min_value": 1.5, "max_value": 3.5},
            {"profession": "Worker", "interest_name": "Politics", "min_value": 1.5, "max_value": 3.5},
            {"profession": "Worker", "interest_name": "Education", "min_value": 1.0, "max_value": 3.0},
            {"profession": "Worker", "interest_name": "Entertainment", "min_value": 2.5, "max_value": 4.5},
            
            # ShopClerk
            {"profession": "ShopClerk", "interest_name": "Economics", "min_value": 2.5, "max_value": 4.5},
            {"profession": "ShopClerk", "interest_name": "Wellbeing", "min_value": 1.5, "max_value": 3.5},
            {"profession": "ShopClerk", "interest_name": "Religion", "min_value": 0.5, "max_value": 2.5},
            {"profession": "ShopClerk", "interest_name": "Politics", "min_value": 1.0, "max_value": 3.0},
            {"profession": "ShopClerk", "interest_name": "Education", "min_value": 1.5, "max_value": 3.5},
            {"profession": "ShopClerk", "interest_name": "Entertainment", "min_value": 2.5, "max_value": 4.5},
        ]
        
        # Connect as capsim_rw
        conn = psycopg2.connect(
            host="localhost",
            database=os.getenv("POSTGRES_DB", "capsim_db"),
            user="capsim_rw",
            password=os.getenv("CAPSIM_RW_PASSWORD", "capsim321"),
            port=5432
        )
        
        cur = conn.cursor()
        
        # Check if data already exists
        cur.execute("SELECT COUNT(*) FROM capsim.agent_interests")
        count = cur.fetchone()[0]
        
        if count == 0:
            # Insert interest ranges
            for interest in interests_data:
                cur.execute("""
                    INSERT INTO capsim.agent_interests (profession, interest_name, min_value, max_value)
                    VALUES (%s, %s, %s, %s)
                """, (interest["profession"], interest["interest_name"], 
                      interest["min_value"], interest["max_value"]))
            
            conn.commit()
            logger.info(f"✅ Loaded {len(interests_data)} interest ranges")
        else:
            logger.info("⚡ Agent interests already loaded")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Agent interests loading failed: {e}")
        return False


async def run_simulation_with_real_db():
    """Запускает симуляцию с реальной базой данных."""
    try:
        # Import simulation components
        from capsim.db.repositories import DatabaseRepository
        from capsim.engine.simulation_engine import SimulationEngine
        
        # Configure database URL for capsim_rw user
        database_url = f"postgresql://capsim_rw:{os.getenv('CAPSIM_RW_PASSWORD', 'capsim321')}@localhost:5432/{os.getenv('POSTGRES_DB', 'capsim_db')}"
        
        # Create repository and engine
        db_repo = DatabaseRepository(database_url)
        engine = SimulationEngine(db_repo)
        
        logger.info("🚀 Starting simulation with 100 agents for 1 day")
        
        # Initialize simulation
        await engine.initialize(num_agents=100)
        logger.info(f"✅ Simulation initialized: {engine.simulation_id}")
        
        # Run simulation for 1 day
        start_time = datetime.now()
        await engine.run_simulation(duration_days=1)
        end_time = datetime.now()
        
        # Get final statistics
        stats = engine.get_simulation_stats()
        execution_time = (end_time - start_time).total_seconds()
        
        logger.info("🎉 Simulation completed successfully!")
        logger.info(f"📊 Final Statistics:")
        logger.info(f"   Simulation ID: {stats['simulation_id']}")
        logger.info(f"   Simulation time: {stats['current_time']:.1f} minutes")
        logger.info(f"   Total agents: {stats['total_agents']}")
        logger.info(f"   Active agents: {stats['active_agents']}")
        logger.info(f"   Active trends: {stats['active_trends']}")
        logger.info(f"   Queue size: {stats['queue_size']}")
        logger.info(f"   Execution time: {execution_time:.2f} seconds")
        
        # Close database connections
        await db_repo.close()
        
        return True
    except Exception as e:
        logger.error(f"❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Главная функция запуска."""
    logger.info("🏗️ CAPSIM Real Database Simulation Runner")
    logger.info("=" * 50)
    
    # Step 1: Check database connection
    logger.info("Step 1: Checking database connection...")
    if not check_database_connection():
        logger.error("❌ Cannot connect to database. Is Docker running?")
        return False
    
    # Step 2: Run migrations
    logger.info("Step 2: Running database migrations...")
    if not run_alembic_migrations():
        logger.error("❌ Database migration failed")
        return False
    
    # Step 3: Create database users
    logger.info("Step 3: Creating database users...")
    if not create_database_users():
        logger.error("❌ User creation failed")
        return False
    
    # Step 4: Load static data
    logger.info("Step 4: Loading affinity map...")
    if not load_affinity_map():
        logger.error("❌ Affinity map loading failed")
        return False
    
    logger.info("Step 5: Loading agent interests...")
    if not load_agent_interests():
        logger.error("❌ Agent interests loading failed")
        return False
    
    # Step 6: Run simulation
    logger.info("Step 6: Running simulation...")
    success = asyncio.run(run_simulation_with_real_db())
    
    if success:
        logger.info("🎉 All steps completed successfully!")
        logger.info("Check the database for simulation results:")
        logger.info("   docker exec -it capsim-postgres-1 psql -U postgres -d capsim_db")
        logger.info("   \\c capsim_db")
        logger.info("   SELECT * FROM capsim.simulation_runs;")
        logger.info("   SELECT COUNT(*) FROM capsim.persons;")
        logger.info("   SELECT COUNT(*) FROM capsim.trends;")
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