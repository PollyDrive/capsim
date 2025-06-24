#!/usr/bin/env python3
"""
Script to apply Migration 0004: Fix birth years and time_budget type
Исправляет года рождения агентов (18-65 лет) и тип time_budget (float)
"""

import os
import sys
import psycopg2
from datetime import datetime, date
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def get_connection():
    """Подключение к базе данных."""
    try:
        conn = psycopg2.connect(
            host="postgres",
            database="capsim_db", 
            user="postgres",
            password="capsim321",
            port=5432
        )
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return None


def check_current_schema(conn):
    """Проверяет текущее состояние схемы."""
    cur = conn.cursor()
    
    # Check date_of_birth type
    cur.execute("""
        SELECT data_type 
        FROM information_schema.columns 
        WHERE table_schema='capsim' AND table_name='persons' AND column_name='date_of_birth'
    """)
    date_type = cur.fetchone()
    
    # Check time_budget type  
    cur.execute("""
        SELECT data_type
        FROM information_schema.columns
        WHERE table_schema='capsim' AND table_name='persons' AND column_name='time_budget'
    """)
    budget_type = cur.fetchone()
    
    # Check birth year ranges
    cur.execute("""
        SELECT 
            MIN(EXTRACT(YEAR FROM date_of_birth)) as min_year,
            MAX(EXTRACT(YEAR FROM date_of_birth)) as max_year,
            COUNT(*) as total_agents
        FROM capsim.persons 
        WHERE date_of_birth IS NOT NULL
    """)
    birth_stats = cur.fetchone()
    
    logger.info("📊 Current Schema Status:")
    logger.info(f"   date_of_birth type: {date_type[0] if date_type else 'NULL'}")
    logger.info(f"   time_budget type: {budget_type[0] if budget_type else 'NULL'}")
    if birth_stats and birth_stats[2] > 0:
        logger.info(f"   Birth years: {birth_stats[0]}-{birth_stats[1]} ({birth_stats[2]} agents)")
    
    cur.close()
    return date_type, budget_type, birth_stats


def apply_migration_0004(conn):
    """Применяет миграцию 0004."""
    cur = conn.cursor()
    
    try:
        logger.info("🔧 Applying Migration 0004...")
        
        # 1. Change date_of_birth to Date type
        logger.info("   Step 1: Changing date_of_birth to Date type...")
        cur.execute("""
            ALTER TABLE capsim.persons 
            ALTER COLUMN date_of_birth TYPE DATE
        """)
        
        # 2. Fix birth years to 18-65 range (1960-2007)
        logger.info("   Step 2: Fixing birth years to 18-65 range...")
        cur.execute("""
            UPDATE capsim.persons
            SET date_of_birth = CASE
                WHEN EXTRACT(YEAR FROM date_of_birth) > 2007 THEN 
                    DATE(2007 - (EXTRACT(YEAR FROM date_of_birth) - 2007), EXTRACT(MONTH FROM date_of_birth), EXTRACT(DAY FROM date_of_birth))
                WHEN EXTRACT(YEAR FROM date_of_birth) < 1960 THEN
                    DATE(1960 + (1960 - EXTRACT(YEAR FROM date_of_birth)), EXTRACT(MONTH FROM date_of_birth), EXTRACT(DAY FROM date_of_birth))
                ELSE date_of_birth
            END
            WHERE date_of_birth IS NOT NULL
        """)
        
        # 3. Fill missing birth dates  
        logger.info("   Step 3: Filling missing birth dates...")
        cur.execute("""
            UPDATE capsim.persons 
            SET date_of_birth = DATE('1960-01-01') + INTERVAL '1 day' * (RANDOM() * (DATE('2007-12-31') - DATE('1960-01-01')))
            WHERE date_of_birth IS NULL
        """)
        
        # 4. Change time_budget to FLOAT
        logger.info("   Step 4: Changing time_budget to FLOAT...")
        cur.execute("""
            ALTER TABLE capsim.persons
            ALTER COLUMN time_budget TYPE FLOAT USING time_budget::FLOAT
        """)
        
        # 5. Normalize time_budget values
        logger.info("   Step 5: Normalizing time_budget values...")
        cur.execute("""
            UPDATE capsim.persons
            SET time_budget = CASE
                WHEN time_budget IS NULL THEN 2.5
                WHEN time_budget < 1 THEN 1.0
                WHEN time_budget > 5 THEN 5.0
                ELSE time_budget
            END
        """)
        
        logger.info("✅ Migration 0004 applied successfully!")
        cur.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        cur.close()
        return False


def verify_migration(conn):
    """Проверяет результаты миграции."""
    cur = conn.cursor()
    
    # Check final schema
    cur.execute("""
        SELECT 
            COUNT(*) as total_agents,
            MIN(EXTRACT(YEAR FROM date_of_birth)) as min_year,
            MAX(EXTRACT(YEAR FROM date_of_birth)) as max_year,
            COUNT(*) FILTER (WHERE EXTRACT(YEAR FROM date_of_birth) BETWEEN 1960 AND 2007) as valid_years,
            AVG(time_budget) as avg_time_budget,
            MIN(time_budget) as min_time_budget,
            MAX(time_budget) as max_time_budget
        FROM capsim.persons
    """)
    
    stats = cur.fetchone()
    if stats:
        total, min_year, max_year, valid_years, avg_budget, min_budget, max_budget = stats
        logger.info("🔍 Verification Results:")
        logger.info(f"   Total agents: {total}")
        logger.info(f"   Birth years: {min_year}-{max_year}")
        logger.info(f"   Valid birth years (1960-2007): {valid_years}/{total}")
        logger.info(f"   time_budget range: {min_budget:.2f}-{max_budget:.2f} (avg: {avg_budget:.2f})")
        
        # Check if all requirements are met
        all_valid_years = valid_years == total
        valid_budget_range = min_budget >= 0.0 and max_budget <= 5.0
        
        if all_valid_years and valid_budget_range:
            logger.info("✅ All requirements satisfied!")
            return True
        else:
            logger.warning("⚠️ Some requirements not met")
            return False
    
    cur.close()
    return False


def main():
    """Главная функция."""
    logger.info("🚀 CAPSIM Migration 0004: Fix Birth Years & Time Budget")
    logger.info("=" * 60)
    
    # Connect to database
    conn = get_connection()
    if not conn:
        sys.exit(1)
    
    # Check current state
    logger.info("Step 1: Checking current schema...")
    check_current_schema(conn)
    
    # Apply migration
    logger.info("\nStep 2: Applying migration...")
    success = apply_migration_0004(conn)
    if not success:
        conn.close()
        sys.exit(1)
    
    # Verify results
    logger.info("\nStep 3: Verifying migration...")
    verified = verify_migration(conn)
    
    conn.close()
    
    if verified:
        logger.info("\n🎉 Migration 0004 completed successfully!")
        logger.info("   ✅ Birth years fixed to 18-65 range (1960-2007)")
        logger.info("   ✅ time_budget changed to FLOAT (0.0-5.0)")
        logger.info("   ✅ All agents have valid data")
    else:
        logger.error("\n❌ Migration completed with issues")
        sys.exit(1)


if __name__ == "__main__":
    main() 