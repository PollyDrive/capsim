#!/usr/bin/env python3
"""
Валидация и очистка данных согласно требованиям @senior-db.mdc

Проверяет:
1. Соответствие атрибутов агентов диапазонам из ТЗ  
2. Корректность русских имен и склонений
3. Правильность создания событий с agent_id/trend_id
4. Целостность parent_trend_id в trends
"""

import asyncio
import asyncpg
import json
import logging
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional

# Настройка логгирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Диапазоны атрибутов по профессиям из ТЗ (таблица 2.4)
PROFESSION_RANGES = {
    "ShopClerk": {
        "financial_capability": (2.0, 4.0),
        "trend_receptivity": (1.0, 3.0), 
        "social_status": (1.0, 3.0),
        "energy_level": (2.0, 5.0),
        "time_budget": (3.0, 5.0)
    },
    "Worker": {
        "financial_capability": (2.0, 4.0),
        "trend_receptivity": (1.0, 3.0),
        "social_status": (1.0, 2.0),
        "energy_level": (2.0, 5.0),
        "time_budget": (3.0, 5.0)
    },
    "Developer": {
        "financial_capability": (3.0, 5.0),
        "trend_receptivity": (3.0, 5.0),
        "social_status": (2.0, 4.0),
        "energy_level": (2.0, 5.0),
        "time_budget": (2.0, 4.0)
    },
    "Politician": {
        "financial_capability": (3.0, 5.0),
        "trend_receptivity": (3.0, 5.0),
        "social_status": (4.0, 5.0),
        "energy_level": (2.0, 4.0),
        "time_budget": (2.0, 4.0)
    },
    "Blogger": {
        "financial_capability": (2.0, 4.0),
        "trend_receptivity": (4.0, 5.0),
        "social_status": (3.0, 5.0),
        "energy_level": (2.0, 5.0),
        "time_budget": (3.0, 5.0)
    },
    "Businessman": {
        "financial_capability": (4.0, 5.0),
        "trend_receptivity": (2.0, 4.0),
        "social_status": (4.0, 5.0),
        "energy_level": (2.0, 5.0),
        "time_budget": (2.0, 4.0)
    },
    "SpiritualMentor": {
        "financial_capability": (1.0, 3.0),
        "trend_receptivity": (2.0, 5.0),
        "social_status": (2.0, 4.0),
        "energy_level": (3.0, 5.0),
        "time_budget": (2.0, 4.0)
    },
    "Philosopher": {
        "financial_capability": (1.0, 3.0),
        "trend_receptivity": (1.0, 3.0),
        "social_status": (1.0, 3.0),
        "energy_level": (2.0, 4.0),
        "time_budget": (2.0, 4.0)
    },
    "Unemployed": {
        "financial_capability": (1.0, 2.0),
        "trend_receptivity": (3.0, 5.0),
        "social_status": (1.0, 2.0),
        "energy_level": (3.0, 5.0),
        "time_budget": (3.0, 5.0)
    },
    "Teacher": {
        "financial_capability": (1.0, 3.0),
        "trend_receptivity": (1.0, 3.0),
        "social_status": (2.0, 4.0),
        "energy_level": (1.0, 3.0),
        "time_budget": (2.0, 4.0)
    },
    "Artist": {
        "financial_capability": (1.0, 3.0),
        "trend_receptivity": (2.0, 4.0),
        "social_status": (2.0, 4.0),
        "energy_level": (4.0, 5.0),
        "time_budget": (3.0, 5.0)
    },
    "Doctor": {
        "financial_capability": (2.0, 4.0),
        "trend_receptivity": (1.0, 3.0),
        "social_status": (3.0, 5.0),
        "energy_level": (2.0, 4.0),
        "time_budget": (1.0, 2.0)
    }
}

VALID_PROFESSIONS = list(PROFESSION_RANGES.keys())
VALID_TOPICS = ["Economic", "Health", "Spiritual", "Conspiracy", "Science", "Culture", "Sport"]

# Русские имена для валидации
RUSSIAN_MALE_NAMES = ["Александр", "Дмитрий", "Максим", "Сергей", "Андрей", "Алексей", "Артем", "Илья", "Кирилл", "Михаил"]
RUSSIAN_FEMALE_NAMES = ["Анна", "Мария", "Елена", "Ольга", "Светлана", "Наталья", "Ирина", "Юлия", "Виктория", "Екатерина"]

async def connect_db() -> asyncpg.Connection:
    """Подключение к базе данных."""
    try:
        conn = await asyncpg.connect("postgresql://capsim_rw:capsim321@localhost:5432/capsim_db")
        logger.info("✅ Успешное подключение к БД")
        return conn
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
        raise

async def validate_agents(conn: asyncpg.Connection) -> Tuple[List[str], List[str]]:
    """
    Валидация агентов согласно ТЗ.
    
    Returns:
        Tuple[valid_agents, invalid_agents]
    """
    logger.info("🔍 Проверка соответствия агентов требованиям ТЗ...")
    
    # Получаем всех агентов
    agents = await conn.fetch("""
        SELECT id, profession, first_name, last_name, gender, date_of_birth,
               financial_capability, trend_receptivity, social_status, 
               energy_level, time_budget, interests
        FROM capsim.persons
    """)
    
    valid_agents = []
    invalid_agents = []
    
    for agent in agents:
        violations = []
        
        # 1. Проверка профессии
        if agent['profession'] not in VALID_PROFESSIONS:
            violations.append(f"Invalid profession: {agent['profession']}")
            
        # 2. Проверка диапазонов атрибутов
        if agent['profession'] in PROFESSION_RANGES:
            ranges = PROFESSION_RANGES[agent['profession']]
            
            for attr, (min_val, max_val) in ranges.items():
                value = agent[attr]
                if not (min_val <= value <= max_val):
                    violations.append(f"{attr}={value} not in range [{min_val}, {max_val}]")
        
        # 3. Проверка русских имен
        if agent['gender'] == 'male':
            if agent['first_name'] not in RUSSIAN_MALE_NAMES:
                violations.append(f"Non-Russian male name: {agent['first_name']}")
        elif agent['gender'] == 'female':
            if agent['first_name'] not in RUSSIAN_FEMALE_NAMES:
                violations.append(f"Non-Russian female name: {agent['first_name']}")
                
        # 4. Проверка возраста (18-65 лет)
        if agent['date_of_birth']:
            today = date.today()
            age = today.year - agent['date_of_birth'].year
            if not (18 <= age <= 65):
                violations.append(f"Invalid age: {age} (must be 18-65)")
        
        # 5. Проверка базовых диапазонов (0.0-5.0)
        for attr in ['financial_capability', 'trend_receptivity', 'social_status', 'energy_level']:
            value = agent[attr]
            if not (0.0 <= value <= 5.0):
                violations.append(f"{attr}={value} not in range [0.0, 5.0]")
                
        if violations:
            invalid_agents.append({
                "id": str(agent['id']),
                "name": f"{agent['first_name']} {agent['last_name']}",
                "profession": agent['profession'],
                "violations": violations
            })
        else:
            valid_agents.append(str(agent['id']))
    
    logger.info(f"✅ Валидных агентов: {len(valid_agents)}")
    logger.info(f"❌ Невалидных агентов: {len(invalid_agents)}")
    
    return valid_agents, invalid_agents

async def validate_events(conn: asyncpg.Connection) -> Dict:
    """Валидация событий и их связей."""
    logger.info("🔍 Проверка событий...")
    
    # События без agent_id ИЛИ trend_id (должны быть системными)
    system_events = await conn.fetch("""
        SELECT event_type, COUNT(*) as count
        FROM capsim.events 
        WHERE agent_id IS NULL AND trend_id IS NULL
        GROUP BY event_type
        ORDER BY count DESC
    """)
    
    # События с agent_id (должны быть действиями агентов)
    agent_events = await conn.fetch("""
        SELECT event_type, COUNT(*) as count
        FROM capsim.events 
        WHERE agent_id IS NOT NULL
        GROUP BY event_type
        ORDER BY count DESC
    """)
    
    # События с trend_id (должны быть связаны с трендами)
    trend_events = await conn.fetch("""
        SELECT event_type, COUNT(*) as count
        FROM capsim.events 
        WHERE trend_id IS NOT NULL
        GROUP BY event_type
        ORDER BY count DESC
    """)
    
    return {
        "system_events": [(row['event_type'], row['count']) for row in system_events],
        "agent_events": [(row['event_type'], row['count']) for row in agent_events],
        "trend_events": [(row['event_type'], row['count']) for row in trend_events]
    }

async def validate_trends(conn: asyncpg.Connection) -> Dict:
    """Валидация трендов и parent_trend_id."""
    logger.info("🔍 Проверка трендов...")
    
    # Статистика по parent_trend_id
    trends_stat = await conn.fetchrow("""
        SELECT COUNT(*) as total,
               COUNT(parent_trend_id) as with_parent,
               COUNT(*) - COUNT(parent_trend_id) as without_parent
        FROM capsim.trends
    """)
    
    # Проверка корректности parent_trend_id (self-references)
    self_refs = await conn.fetch("""
        SELECT trend_id, parent_trend_id
        FROM capsim.trends
        WHERE trend_id = parent_trend_id
    """)
    
    # Проверка несуществующих parent_trend_id
    orphan_parents = await conn.fetch("""
        SELECT t1.trend_id, t1.parent_trend_id
        FROM capsim.trends t1
        LEFT JOIN capsim.trends t2 ON t1.parent_trend_id = t2.trend_id
        WHERE t1.parent_trend_id IS NOT NULL AND t2.trend_id IS NULL
    """)
    
    return {
        "total_trends": trends_stat['total'],
        "with_parent": trends_stat['with_parent'],
        "without_parent": trends_stat['without_parent'],
        "self_references": len(self_refs),
        "orphan_parents": len(orphan_parents)
    }

async def clean_invalid_agents(conn: asyncpg.Connection, invalid_agents: List[Dict]) -> int:
    """
    Удаляет невалидных агентов и все связанные с ними данные.
    
    Args:
        conn: Подключение к БД
        invalid_agents: Список невалидных агентов
        
    Returns:
        Количество удаленных агентов
    """
    if not invalid_agents:
        logger.info("🎉 Нет невалидных агентов для удаления")
        return 0
    
    agent_ids = [agent['id'] for agent in invalid_agents]
    logger.warning(f"🗑️ Удаление {len(agent_ids)} невалидных агентов...")
    
    try:
        async with conn.transaction():
            # 1. Получаем ID трендов созданных этими агентами
            trend_ids_result = await conn.fetch("""
                SELECT trend_id FROM capsim.trends 
                WHERE originator_id = ANY($1::uuid[])
            """, agent_ids)
            trend_ids = [row['trend_id'] for row in trend_ids_result]
            logger.info(f"🔍 Найдено трендов для удаления: {len(trend_ids)}")
            
            # 2. Удаляем события связанные с агентами
            events_by_agent_deleted = await conn.execute("""
                DELETE FROM capsim.events 
                WHERE agent_id = ANY($1::uuid[])
            """, agent_ids)
            logger.info(f"🗑️ Удалено событий агентов: {events_by_agent_deleted}")
            
            # 3. Удаляем события связанные с трендами этих агентов
            if trend_ids:
                events_by_trend_deleted = await conn.execute("""
                    DELETE FROM capsim.events 
                    WHERE trend_id = ANY($1::uuid[])
                """, trend_ids)
                logger.info(f"🗑️ Удалено событий трендов: {events_by_trend_deleted}")
            
            # 4. Удаляем тренды созданные этими агентами 
            trends_deleted = await conn.execute("""
                DELETE FROM capsim.trends 
                WHERE originator_id = ANY($1::uuid[])
            """, agent_ids)
            logger.info(f"🗑️ Удалено трендов: {trends_deleted}")
            
            # 5. Удаляем историю атрибутов
            history_deleted = await conn.execute("""
                DELETE FROM capsim.person_attribute_history 
                WHERE person_id = ANY($1::uuid[])
            """, agent_ids)
            logger.info(f"🗑️ Удалено записей истории: {history_deleted}")
            
            # 6. Наконец удаляем самих агентов
            agents_deleted = await conn.execute("""
                DELETE FROM capsim.persons 
                WHERE id = ANY($1::uuid[])
            """, agent_ids)
            
            logger.info(f"✅ Удалено агентов: {agents_deleted}")
            return len(agent_ids)
            
    except Exception as e:
        logger.error(f"❌ Ошибка при удалении агентов: {e}")
        raise

async def main():
    """Основная функция валидации и очистки."""
    print("🧪 CAPSIM Data Validation & Cleanup Tool")
    print("=" * 60)
    
    conn = await connect_db()
    
    try:
        # 1. Валидация агентов
        valid_agents, invalid_agents = await validate_agents(conn)
        
        # 2. Валидация событий
        events_stat = await validate_events(conn)
        
        # 3. Валидация трендов
        trends_stat = await validate_trends(conn)
        
        # Отчет
        print("\n📊 ОТЧЕТ О ВАЛИДАЦИИ:")
        print("-" * 40)
        print(f"👥 Агенты:")
        print(f"   ✅ Валидные: {len(valid_agents)}")
        print(f"   ❌ Невалидные: {len(invalid_agents)}")
        
        if invalid_agents:
            print(f"\n🔍 Детали невалидных агентов:")
            for agent in invalid_agents[:5]:  # Показываем первые 5
                print(f"   • {agent['name']} ({agent['profession']})")
                for violation in agent['violations']:
                    print(f"     - {violation}")
                    
        print(f"\n📅 События:")
        print(f"   🔧 Системные: {len(events_stat['system_events'])} типов")
        print(f"   👤 Агентов: {len(events_stat['agent_events'])} типов") 
        print(f"   📈 Трендов: {len(events_stat['trend_events'])} типов")
        
        print(f"\n📈 Тренды:")
        print(f"   📊 Всего: {trends_stat['total_trends']}")
        print(f"   🔗 С parent_trend_id: {trends_stat['with_parent']}")
        print(f"   ⭐ Без parent (корневые): {trends_stat['without_parent']}")
        
        if trends_stat['self_references'] > 0:
            print(f"   ⚠️ Self-references: {trends_stat['self_references']}")
        if trends_stat['orphan_parents'] > 0:
            print(f"   ⚠️ Orphan parents: {trends_stat['orphan_parents']}")
            
        # 4. Очистка данных (по запросу)
        if invalid_agents:
            print(f"\n❓ Удалить {len(invalid_agents)} невалидных агентов? (y/N): ", end="")
            response = input().strip().lower()
            
            if response == 'y':
                deleted = await clean_invalid_agents(conn, invalid_agents)
                print(f"✅ Очистка завершена. Удалено {deleted} агентов.")
            else:
                print("ℹ️ Очистка отменена.")
        
        print(f"\n✅ Валидация завершена в {datetime.now().strftime('%H:%M:%S')}")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main()) 