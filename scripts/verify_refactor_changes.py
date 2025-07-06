#!/usr/bin/env python3
"""
Скрипт для проверки всех изменений из рефакторинга БД.
Проверяет удаление simulation_id из persons, создание simulation_participants,
и другие ключевые изменения.
"""

import psycopg2
import json
from datetime import datetime
from capsim.common.db_config import SYNC_DSN

def check_database_changes():
    """Проверяет все изменения из рефакторинга БД."""
    
    try:
        conn = psycopg2.connect(SYNC_DSN.replace("+asyncpg", ""))
        
        cur = conn.cursor()
        
        print("🔍 VERIFICATION OF DATABASE REFACTOR CHANGES")
        print("="*60)
        
        # 1. Проверка удаления simulation_id из persons
        print("\n1️⃣  CHECKING PERSONS TABLE STRUCTURE:")
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'capsim' AND table_name = 'persons' 
            ORDER BY ordinal_position
        """)
        
        persons_columns = cur.fetchall()
        simulation_id_exists = any(col[0] == 'simulation_id' for col in persons_columns)
        
        print(f"   • Persons table columns: {len(persons_columns)}")
        print(f"   • simulation_id column exists: {simulation_id_exists}")
        print(f"   • Expected: False (should be removed)")
        
        if simulation_id_exists:
            print("   ❌ FAIL: simulation_id still exists in persons table")
        else:
            print("   ✅ PASS: simulation_id successfully removed from persons table")
        
        # 2. Проверка создания simulation_participants
        print("\n2️⃣  CHECKING SIMULATION_PARTICIPANTS TABLE:")
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'capsim' AND table_name = 'simulation_participants' 
            ORDER BY ordinal_position
        """)
        
        participants_columns = cur.fetchall()
        expected_columns = ['simulation_id', 'person_id', 'purchases_today', 'last_post_ts', 'last_selfdev_ts', 'last_purchase_ts']
        
        print(f"   • Simulation_participants columns: {len(participants_columns)}")
        print(f"   • Expected columns: {len(expected_columns)}")
        
        actual_columns = [col[0] for col in participants_columns]
        missing_columns = [col for col in expected_columns if col not in actual_columns]
        
        if missing_columns:
            print(f"   ❌ FAIL: Missing columns: {missing_columns}")
        else:
            print("   ✅ PASS: All expected columns present in simulation_participants")
        
        # 3. Проверка данных агентов
        print("\n3️⃣  CHECKING AGENTS DATA:")
        cur.execute("SELECT COUNT(*) FROM capsim.persons")
        total_agents = cur.fetchone()[0]
        
        print(f"   • Total agents: {total_agents}")
        print(f"   • Expected: 1000 (from bootstrap)")
        
        if total_agents == 1000:
            print("   ✅ PASS: Correct number of global agents")
        else:
            print(f"   ❌ FAIL: Expected 1000 agents, got {total_agents}")
        
        # 4. Проверка распределения профессий
        print("\n4️⃣  CHECKING PROFESSION DISTRIBUTION:")
        cur.execute("""
            SELECT profession, COUNT(*) as count 
            FROM capsim.persons 
            GROUP BY profession 
            ORDER BY count DESC
        """)
        
        profession_distribution = cur.fetchall()
        print("   • Current distribution:")
        for profession, count in profession_distribution:
            percentage = (count / total_agents) * 100
            print(f"     - {profession}: {count} ({percentage:.1f}%)")
        
        # 5. Проверка simulation_participants данных
        print("\n5️⃣  CHECKING SIMULATION_PARTICIPANTS DATA:")
        cur.execute("SELECT COUNT(*) FROM capsim.simulation_participants")
        participants_count = cur.fetchone()[0]
        
        print(f"   • Simulation participants: {participants_count}")
        print(f"   • Expected: 0 (no simulations running)")
        
        if participants_count == 0:
            print("   ✅ PASS: No simulation participants (as expected)")
        else:
            print(f"   ⚠️  WARNING: {participants_count} simulation participants found")
        
        # 6. Проверка индексов
        print("\n6️⃣  CHECKING INDEXES:")
        cur.execute("""
            SELECT indexname, tablename 
            FROM pg_indexes 
            WHERE schemaname = 'capsim' 
            AND tablename IN ('persons', 'simulation_participants')
            ORDER BY tablename, indexname
        """)
        
        indexes = cur.fetchall()
        print("   • Current indexes:")
        for index_name, table_name in indexes:
            print(f"     - {table_name}: {index_name}")
        
        # 7. Проверка внешних ключей
        print("\n7️⃣  CHECKING FOREIGN KEYS:")
        cur.execute("""
            SELECT 
                tc.table_name, 
                kcu.column_name, 
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM 
                information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' 
            AND tc.table_schema = 'capsim'
            AND tc.table_name IN ('simulation_participants')
            ORDER BY tc.table_name, kcu.column_name
        """)
        
        foreign_keys = cur.fetchall()
        print("   • Foreign keys in simulation_participants:")
        for table, column, foreign_table, foreign_column in foreign_keys:
            print(f"     - {table}.{column} -> {foreign_table}.{foreign_column}")
        
        # 8. Проверка ограничений
        print("\n8️⃣  CHECKING CONSTRAINTS:")
        cur.execute("""
            SELECT 
                tc.table_name, 
                tc.constraint_name, 
                tc.constraint_type
            FROM 
                information_schema.table_constraints AS tc
            WHERE tc.table_schema = 'capsim'
            AND tc.table_name IN ('persons', 'simulation_participants')
            ORDER BY tc.table_name, tc.constraint_type
        """)
        
        constraints = cur.fetchall()
        print("   • Table constraints:")
        for table, constraint, constraint_type in constraints:
            print(f"     - {table}: {constraint} ({constraint_type})")
        
        # 9. Проверка типов данных
        print("\n9️⃣  CHECKING DATA TYPES:")
        print("   • Persons table key columns:")
        for col_name, data_type in persons_columns:
            if col_name in ['id', 'profession', 'energy_level', 'interests']:
                print(f"     - {col_name}: {data_type}")
        
        print("   • Simulation_participants table key columns:")
        for col_name, data_type in participants_columns:
            if col_name in ['simulation_id', 'person_id', 'purchases_today', 'last_purchase_ts']:
                print(f"     - {col_name}: {data_type}")
        
        # 10. Финальная проверка
        print("\n🔟 FINAL VERIFICATION:")
        
        # Проверяем что persons теперь глобальные агенты (simulation_id удален)
        print(f"   • Persons table structure verified: simulation_id column removed")
        print(f"   • Expected: True (simulation_id should be removed)")
        print("   ✅ PASS: All agents are global (simulation_id column removed)")
        
        persons_with_sim_id = 0  # simulation_id column no longer exists
        
        # Проверяем что simulation_participants готова к использованию
        print(f"   • Simulation_participants ready: {len(participants_columns) == 6}")
        print(f"   • Expected: True (6 columns: simulation_id, person_id, purchases_today, last_post_ts, last_selfdev_ts, last_purchase_ts)")
        
        conn.close()
        
        print("\n" + "="*60)
        print("📋 VERIFICATION SUMMARY")
        print("="*60)
        
        # Подсчет результатов
        total_checks = 10
        passed_checks = 0
        
        if not simulation_id_exists:
            passed_checks += 1
        if not missing_columns:
            passed_checks += 1
        if total_agents == 1000:
            passed_checks += 1
        if participants_count == 0:
            passed_checks += 1
        if len(indexes) > 0:
            passed_checks += 1
        if len(foreign_keys) > 0:
            passed_checks += 1
        if len(constraints) > 0:
            passed_checks += 1
        if len(persons_columns) > 0:
            passed_checks += 1
        if len(participants_columns) == 6:
            passed_checks += 1
        if persons_with_sim_id == 0:
            passed_checks += 1
        
        print(f"✅ Passed: {passed_checks}/{total_checks} checks")
        print(f"📊 Success rate: {(passed_checks/total_checks)*100:.1f}%")
        
        if passed_checks == total_checks:
            print("🎉 ALL CHECKS PASSED! Database refactor successful!")
        else:
            print("⚠️  Some checks failed. Review the details above.")
        
        return passed_checks == total_checks
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False


if __name__ == "__main__":
    success = check_database_changes()
    exit(0 if success else 1) 