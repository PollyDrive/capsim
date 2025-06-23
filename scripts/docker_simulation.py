#!/usr/bin/env python3
"""
Docker-based simulation runner for CAPSIM.

Runs simulation with 100 agents for 1 day inside Docker container.
All dependencies are already available in the container.
"""

import os
import sys
import json
import asyncio
import logging
import psycopg2
import uuid
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

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
        conn = psycopg2.connect(
            host="postgres",  # Docker service name
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


def run_alembic_migrations():
    """Выполняет миграции Alembic программно."""
    try:
        from alembic.config import Config
        from alembic import command
        
        # Configure Alembic
        alembic_cfg = Config(str(project_root / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(project_root / "alembic"))
        
        # Set database URL for migrations
        database_url = "postgresql://postgres:capsim321@postgres:5432/capsim_db"
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
            host="postgres",
            database="capsim_db",
            user="postgres",
            password="capsim321",
            port=5432
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Create capsim_rw user
        try:
            cur.execute("CREATE USER capsim_rw WITH PASSWORD 'capsim321'")
            logger.info("✅ Created capsim_rw user")
        except psycopg2.errors.DuplicateObject:
            logger.info("⚡ capsim_rw user already exists")
        
        # Create capsim_ro user  
        try:
            cur.execute("CREATE USER capsim_ro WITH PASSWORD 'capsim321'")
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


def load_static_data():
    """Загружает статические данные: affinity map и agent interests."""
    try:
        # Load affinity map
        affinity_file = project_root / "config" / "trend_affinity.json"
        with open(affinity_file, 'r') as f:
            affinity_data = json.load(f)
        
        # Agent interests data
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
        
        # Connect to database
        conn = psycopg2.connect(
            host="postgres",
            database="capsim_db",
            user="capsim_rw",
            password="capsim321",
            port=5432
        )
        
        cur = conn.cursor()
        
        # Load affinity map
        cur.execute("SELECT COUNT(*) FROM capsim.affinity_map")
        count = cur.fetchone()[0]
        
        if count == 0:
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
        
        # Load agent interests
        cur.execute("SELECT COUNT(*) FROM capsim.agent_interests")
        count = cur.fetchone()[0]
        
        if count == 0:
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
        logger.error(f"❌ Static data loading failed: {e}")
        return False


def create_simulation_record():
    """Создает запись симуляции и генерирует 100 агентов."""
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
        
        # Get interest ranges for agents
        cur.execute("SELECT profession, interest_name, min_value, max_value FROM capsim.agent_interests")
        interest_ranges = {}
        for row in cur.fetchall():
            profession, interest_name, min_val, max_val = row
            if profession not in interest_ranges:
                interest_ranges[profession] = {}
            interest_ranges[profession][interest_name] = (min_val, max_val)
        
        # Generate 100 agents
        professions = ["Banker", "Developer", "Teacher", "Worker", "ShopClerk"]
        agents_per_profession = 20  # 100 / 5 = 20 each
        
        agents_created = 0
        for profession in professions:
            for i in range(agents_per_profession):
                agent_id = str(uuid.uuid4())
                
                # Generate interests based on ranges
                interests = {}
                if profession in interest_ranges:
                    for interest_name, (min_val, max_val) in interest_ranges[profession].items():
                        interests[interest_name] = round(random.uniform(min_val, max_val), 2)
                
                # Generate other attributes
                energy_level = round(random.uniform(1.0, 5.0), 2)
                social_status = round(random.uniform(0.5, 4.5), 2)
                time_budget = random.randint(1, 5)
                
                cur.execute("""
                    INSERT INTO capsim.persons 
                    (id, simulation_id, profession, energy_level, social_status, 
                     time_budget, interests, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    agent_id,
                    simulation_id,
                    profession,
                    energy_level,
                    social_status,
                    time_budget,
                    json.dumps(interests),
                    datetime.now(),
                    datetime.now()
                ))
                
                agents_created += 1
        
        conn.commit()
        logger.info(f"✅ Created simulation {simulation_id} with {agents_created} agents")
        
        cur.close()
        conn.close()
        return simulation_id
    except Exception as e:
        logger.error(f"❌ Simulation creation failed: {e}")
        return None


async def run_simple_simulation(simulation_id: str):
    """Запускает упрощенную симуляцию."""
    try:
        # Import simulation components
        from capsim.engine.simulation_engine import SimulationEngine
        from capsim.db.repositories import DatabaseRepository
        
        # Configure database URL
        database_url = "postgresql://capsim_rw:capsim321@postgres:5432/capsim_db"
        
        # Create repository and engine
        db_repo = DatabaseRepository(database_url)
        engine = SimulationEngine(db_repo)
        
        logger.info("🚀 Starting simulation with existing agents for 1 day")
        
        # Load existing simulation
        await engine.load_simulation(simulation_id)
        logger.info(f"✅ Loaded simulation: {simulation_id}")
        
        # Run simulation for 1 day (1440 minutes)
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
        
        # Update simulation status
        await db_repo.update_simulation_status(simulation_id, "completed")
        await db_repo.close()
        
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
            logger.info(f"📈 Simulation Results:")
            logger.info(f"   Status: {status}")
            logger.info(f"   Agents: {num_agents}")
            logger.info(f"   Duration: {duration_days} days")
            logger.info(f"   Started: {start_time}")
            logger.info(f"   Ended: {end_time}")
        
        # Count trends created
        cur.execute("SELECT COUNT(*) FROM capsim.trends WHERE simulation_id = %s", (simulation_id,))
        trend_count = cur.fetchone()[0]
        logger.info(f"   Trends created: {trend_count}")
        
        # Count events processed
        cur.execute("SELECT COUNT(*) FROM capsim.events WHERE simulation_id = %s", (simulation_id,))
        event_count = cur.fetchone()[0]
        logger.info(f"   Events processed: {event_count}")
        
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
            logger.info(f"   Top trends:")
            for topic, virality, interactions in top_trends:
                logger.info(f"     - {topic}: virality={virality:.2f}, interactions={interactions}")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"❌ Results display failed: {e}")
        return False


def main():
    """Главная функция запуска."""
    logger.info("🏗️ CAPSIM Docker Simulation Runner")
    logger.info("=" * 50)
    
    # Step 1: Check database connection
    logger.info("Step 1: Checking database connection...")
    if not check_database_connection():
        logger.error("❌ Cannot connect to database")
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
    logger.info("Step 4: Loading static data...")
    if not load_static_data():
        logger.error("❌ Static data loading failed")
        return False
    
    # Step 5: Create simulation with agents
    logger.info("Step 5: Creating simulation with 100 agents...")
    simulation_id = create_simulation_record()
    if not simulation_id:
        logger.error("❌ Simulation creation failed")
        return False
    
    # Step 6: Run simulation
    logger.info("Step 6: Running simulation...")
    success = asyncio.run(run_simple_simulation(simulation_id))
    
    if success:
        # Step 7: Show results
        logger.info("Step 7: Displaying results...")
        show_results(simulation_id)
        
        logger.info("🎉 All steps completed successfully!")
        logger.info(f"Simulation ID: {simulation_id}")
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