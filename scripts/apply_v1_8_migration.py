#!/usr/bin/env python3
"""
Apply CAPSIM v1.8 Database Migration
Applies the v1.8 schema changes to add new person fields for action tracking.

Senior-DB script for production deployment.
"""

import asyncio
import sys
import os
from pathlib import Path
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def apply_v1_8_migration():
    """Apply v1.8 migration to add new person fields."""
    
    print("🔧 CAPSIM v1.8 Database Migration")
    print("="*50)
    
    try:
        # 1. Check database connection
        print("📡 Checking database connection...")
        
        # Get database URL from environment
        db_url = os.getenv('POSTGRES_URL', 'postgresql://capsim_rw:pwd@localhost:5432/capsim')
        
        # Test connection
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Connected to PostgreSQL: {version[:50]}...")
        
        # 2. Check current migration status
        print("\n📋 Checking current migration status...")
        
        alembic_cfg = Config('alembic.ini')
        alembic_cfg.set_main_option('sqlalchemy.url', db_url)
        
        print("Current revision:")
        command.current(alembic_cfg, verbose=True)
        
        # 3. Show pending migrations
        print("\n📈 Showing migration history...")
        command.history(alembic_cfg, verbose=True)
        
        # 4. Apply migration
        print("\n🚀 Applying v1.8 migration...")
        print("Target revision: 0005 (add_new_person_fields_v1_8)")
        
        # Apply migration to target revision
        command.upgrade(alembic_cfg, '0005')
        
        print("✅ Migration applied successfully!")
        
        # 5. Verify new fields exist
        print("\n🔍 Verifying new fields...")
        
        with engine.connect() as conn:
            # Check if new columns exist
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'capsim' 
                AND table_name = 'persons'
                AND column_name IN ('purchases_today', 'last_post_ts', 'last_selfdev_ts', 'last_purchase_ts')
                ORDER BY column_name;
            """))
            
            columns = result.fetchall()
            
            if len(columns) == 4:
                print("✅ All v1.8 fields verified:")
                for col in columns:
                    print(f"   • {col.column_name}: {col.data_type} (nullable: {col.is_nullable})")
            else:
                print(f"❌ Expected 4 fields, found {len(columns)}")
                return False
        
        # 6. Verify constraints and indexes
        print("\n🔒 Verifying constraints and indexes...")
        
        with engine.connect() as conn:
            # Check constraints
            result = conn.execute(text("""
                SELECT constraint_name, check_clause
                FROM information_schema.check_constraints
                WHERE constraint_schema = 'capsim'
                AND table_name = 'persons'
                AND constraint_name IN ('check_purchases_today_positive', 'check_energy_level_positive');
            """))
            
            constraints = result.fetchall()
            print(f"✅ Constraints verified: {len(constraints)} found")
            
            # Check indexes
            result = conn.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'capsim'
                AND tablename = 'persons'
                AND indexname = 'idx_persons_last_purchase_ts';
            """))
            
            indexes = result.fetchall()
            print(f"✅ GIN index verified: {len(indexes)} found")
        
        print("\n🎉 v1.8 MIGRATION COMPLETED SUCCESSFULLY!")
        print("\nNew fields available:")
        print("• purchases_today (SMALLINT) - Daily purchase counter")
        print("• last_post_ts (DOUBLE) - Last post timestamp")
        print("• last_selfdev_ts (DOUBLE) - Last self-dev timestamp")  
        print("• last_purchase_ts (JSONB) - Purchase history by level")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        logger.error(f"Migration error: {e}")
        return False


def check_migration_status():
    """Check if v1.8 migration is already applied."""
    
    print("🔍 Checking if v1.8 migration is already applied...")
    
    try:
        db_url = os.getenv('POSTGRES_URL', 'postgresql://capsim_rw:pwd@localhost:5432/capsim')
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'capsim' 
                AND table_name = 'persons'
                AND column_name = 'purchases_today';
            """))
            
            if result.fetchone():
                print("✅ v1.8 migration already applied!")
                return True
            else:
                print("❌ v1.8 migration not applied yet")
                return False
                
    except Exception as e:
        print(f"❌ Cannot check migration status: {e}")
        return False


def main():
    """Main migration execution."""
    
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        success = check_migration_status()
    else:
        success = apply_v1_8_migration()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 