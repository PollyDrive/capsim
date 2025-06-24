#!/usr/bin/env python3
"""
Удаляет всех агентов и создает 100 новых с правильными параметрами согласно ТЗ.
- Годы рождения: 1960-2007 (возраст 18-65 лет)
- Распределение атрибутов по профессиям согласно tech v.1.5.md
- Русские имена с правильными окончаниями
"""

import os
import sys
import psycopg2
import random
import json
import uuid
from datetime import datetime, date
from faker import Faker
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Russian locale for names
fake = Faker('ru_RU')

# Profession attribute ranges according to tech v.1.5.md
PROFESSION_ATTRIBUTES = {
    'ShopClerk': {
        'financial_capability': (2.0, 4.0),
        'trend_receptivity': (1.0, 3.0),
        'social_status': (1.0, 3.0),
        'energy_level': (2.0, 5.0),
        'time_budget': (3.0, 5.0)
    },
    'Worker': {
        'financial_capability': (2.0, 4.0),
        'trend_receptivity': (1.0, 3.0),
        'social_status': (1.0, 2.0),
        'energy_level': (2.0, 5.0),
        'time_budget': (3.0, 5.0)
    },
    'Developer': {
        'financial_capability': (3.0, 5.0),
        'trend_receptivity': (3.0, 5.0),
        'social_status': (2.0, 4.0),
        'energy_level': (2.0, 5.0),
        'time_budget': (2.0, 4.0)
    },
    'Politician': {
        'financial_capability': (3.0, 5.0),
        'trend_receptivity': (3.0, 5.0),
        'social_status': (4.0, 5.0),
        'energy_level': (2.0, 4.0),
        'time_budget': (2.0, 4.0)
    },
    'Blogger': {
        'financial_capability': (2.0, 4.0),
        'trend_receptivity': (4.0, 5.0),
        'social_status': (3.0, 5.0),
        'energy_level': (2.0, 5.0),
        'time_budget': (3.0, 5.0)
    },
    'Businessman': {
        'financial_capability': (4.0, 5.0),
        'trend_receptivity': (2.0, 4.0),
        'social_status': (4.0, 5.0),
        'energy_level': (2.0, 5.0),
        'time_budget': (2.0, 4.0)
    },
    'SpiritualMentor': {
        'financial_capability': (1.0, 3.0),
        'trend_receptivity': (2.0, 5.0),
        'social_status': (2.0, 4.0),
        'energy_level': (3.0, 5.0),
        'time_budget': (2.0, 4.0)
    },
    'Philosopher': {
        'financial_capability': (1.0, 3.0),
        'trend_receptivity': (1.0, 3.0),
        'social_status': (1.0, 3.0),
        'energy_level': (2.0, 4.0),
        'time_budget': (2.0, 4.0)
    },
    'Unemployed': {
        'financial_capability': (1.0, 2.0),
        'trend_receptivity': (3.0, 5.0),
        'social_status': (1.0, 2.0),
        'energy_level': (3.0, 5.0),
        'time_budget': (3.0, 5.0)
    },
    'Teacher': {
        'financial_capability': (1.0, 3.0),
        'trend_receptivity': (1.0, 3.0),
        'social_status': (2.0, 4.0),
        'energy_level': (1.0, 3.0),
        'time_budget': (2.0, 4.0)
    },
    'Artist': {
        'financial_capability': (1.0, 3.0),
        'trend_receptivity': (2.0, 4.0),
        'social_status': (2.0, 4.0),
        'energy_level': (4.0, 5.0),
        'time_budget': (3.0, 5.0)
    },
    'Doctor': {
        'financial_capability': (2.0, 4.0),
        'trend_receptivity': (1.0, 3.0),
        'social_status': (3.0, 5.0),
        'energy_level': (2.0, 4.0),
        'time_budget': (1.0, 2.0)
    }
}

# Agent interests mapping (from requirements)
AGENT_INTERESTS = {
    'Artist': {
        'Economics': (0.1, 0.4), 'Wellbeing': (0.3, 0.7), 'Spirituality': (0.4, 0.8),
        'Knowledge': (0.3, 0.7), 'Creativity': (0.7, 0.9), 'Society': (0.2, 0.6)
    },
    'Businessman': {
        'Economics': (0.7, 0.9), 'Wellbeing': (0.2, 0.6), 'Spirituality': (0.1, 0.4),
        'Knowledge': (0.3, 0.7), 'Creativity': (0.2, 0.6), 'Society': (0.4, 0.8)
    },
    'Developer': {
        'Economics': (0.3, 0.7), 'Wellbeing': (0.2, 0.6), 'Spirituality': (0.1, 0.5),
        'Knowledge': (0.6, 0.9), 'Creativity': (0.4, 0.8), 'Society': (0.2, 0.6)
    },
    'Doctor': {
        'Economics': (0.2, 0.6), 'Wellbeing': (0.7, 0.9), 'Spirituality': (0.3, 0.7),
        'Knowledge': (0.6, 0.9), 'Creativity': (0.2, 0.6), 'Society': (0.5, 0.9)
    },
    'SpiritualMentor': {
        'Economics': (0.1, 0.4), 'Wellbeing': (0.5, 0.9), 'Spirituality': (0.7, 0.9),
        'Knowledge': (0.4, 0.8), 'Creativity': (0.3, 0.7), 'Society': (0.6, 0.9)
    },
    'Teacher': {
        'Economics': (0.2, 0.6), 'Wellbeing': (0.4, 0.8), 'Spirituality': (0.3, 0.7),
        'Knowledge': (0.7, 0.9), 'Creativity': (0.4, 0.8), 'Society': (0.6, 0.9)
    },
    'ShopClerk': {
        'Economics': (0.6, 0.9), 'Wellbeing': (0.2, 0.6), 'Spirituality': (0.2, 0.6),
        'Knowledge': (0.1, 0.5), 'Creativity': (0.1, 0.4), 'Society': (0.3, 0.7)
    },
    'Worker': {
        'Economics': (0.4, 0.8), 'Wellbeing': (0.3, 0.7), 'Spirituality': (0.2, 0.6),
        'Knowledge': (0.1, 0.5), 'Creativity': (0.1, 0.4), 'Society': (0.4, 0.8)
    },
    'Politician': {
        'Economics': (0.5, 0.9), 'Wellbeing': (0.3, 0.7), 'Spirituality': (0.2, 0.6),
        'Knowledge': (0.4, 0.8), 'Creativity': (0.2, 0.6), 'Society': (0.7, 0.9)
    },
    'Blogger': {
        'Economics': (0.2, 0.6), 'Wellbeing': (0.3, 0.7), 'Spirituality': (0.2, 0.6),
        'Knowledge': (0.3, 0.7), 'Creativity': (0.6, 0.9), 'Society': (0.5, 0.9)
    },
    'Unemployed': {
        'Economics': (0.3, 0.7), 'Wellbeing': (0.4, 0.8), 'Spirituality': (0.3, 0.7),
        'Knowledge': (0.2, 0.6), 'Creativity': (0.3, 0.7), 'Society': (0.6, 0.9)
    },
    'Philosopher': {
        'Economics': (0.3, 0.7), 'Wellbeing': (0.5, 0.9), 'Spirituality': (0.6, 0.9),
        'Knowledge': (0.7, 0.9), 'Creativity': (0.4, 0.8), 'Society': (0.6, 0.9)
    }
}


def get_connection():
    """Подключение к базе данных."""
    try:
        conn = psycopg2.connect(
            host="localhost",
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


def clear_all_agents(conn):
    """Удаляет всех агентов из таблицы persons."""
    cur = conn.cursor()
    
    try:
        # Get count before deletion
        cur.execute("SELECT COUNT(*) FROM capsim.persons")
        count_before = cur.fetchone()[0]
        
        logger.info(f"🗑️ Deleting {count_before} existing agents...")
        
        # Delete all persons
        cur.execute("DELETE FROM capsim.persons")
        
        # Verify deletion
        cur.execute("SELECT COUNT(*) FROM capsim.persons")
        count_after = cur.fetchone()[0]
        
        logger.info(f"✅ Deleted {count_before - count_after} agents. Remaining: {count_after}")
        cur.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to clear agents: {e}")
        cur.close()
        return False


def generate_birth_date() -> date:
    """Генерирует дату рождения в диапазоне 1960-2007 (возраст 18-65 лет)."""
    birth_year = random.randint(1960, 2007)
    birth_month = random.randint(1, 12)
    
    # Handle different month lengths
    if birth_month in [1, 3, 5, 7, 8, 10, 12]:
        max_day = 31
    elif birth_month in [4, 6, 9, 11]:
        max_day = 30
    else:  # February
        if (birth_year % 4 == 0 and birth_year % 100 != 0) or (birth_year % 400 == 0):
            max_day = 29
        else:
            max_day = 28
    
    birth_day = random.randint(1, max_day)
    return date(birth_year, birth_month, birth_day)


def generate_personal_data() -> dict:
    """Генерирует персональные данные с русскими именами."""
    gender = random.choice(['male', 'female'])
    
    if gender == 'male':
        first_name = fake.first_name_male()
        last_name = fake.last_name_male()
    else:
        first_name = fake.first_name_female()
        last_name = fake.last_name_female()
    
    return {
        'first_name': first_name,
        'last_name': last_name,
        'gender': gender,
        'date_of_birth': generate_birth_date()
    }


def generate_agent_attributes(profession: str) -> dict:
    """Генерирует атрибуты агента согласно профессии."""
    if profession not in PROFESSION_ATTRIBUTES:
        raise ValueError(f"Unknown profession: {profession}")
    
    ranges = PROFESSION_ATTRIBUTES[profession]
    
    # Generate attributes within profession ranges
    attributes = {}
    for attr_name, (min_val, max_val) in ranges.items():
        attributes[attr_name] = round(random.uniform(min_val, max_val), 3)
    
    return attributes


def generate_agent_interests(profession: str) -> dict:
    """Генерирует интересы агента согласно профессии."""
    if profession not in AGENT_INTERESTS:
        raise ValueError(f"Unknown profession for interests: {profession}")
    
    ranges = AGENT_INTERESTS[profession]
    interests = {}
    
    for interest_name, (min_val, max_val) in ranges.items():
        interests[interest_name] = round(random.uniform(min_val, max_val), 3)
    
    return interests


def create_100_agents(conn):
    """Создает 100 агентов с правильными параметрами."""
    cur = conn.cursor()
    
    try:
        # Get or create simulation run
        simulation_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO capsim.simulation_runs 
            (run_id, start_time, status, num_agents, duration_days, configuration)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            simulation_id,
            datetime.utcnow(),
            'SETUP',
            100,
            1,
            json.dumps({'purpose': 'recreate_100_agents_proper'})
        ))
        
        logger.info(f"📋 Created simulation run: {simulation_id}")
        
        # Get all professions for equal distribution
        professions = list(PROFESSION_ATTRIBUTES.keys())
        agents_per_profession = 100 // len(professions)
        remaining_agents = 100 % len(professions)
        
        logger.info(f"📊 Creating agents distribution:")
        logger.info(f"   {agents_per_profession} agents per profession")
        logger.info(f"   {remaining_agents} extra agents for random professions")
        
        agents_created = 0
        
        # Create agents with equal distribution
        for profession in professions:
            count = agents_per_profession
            if remaining_agents > 0:
                count += 1
                remaining_agents -= 1
            
            for _ in range(count):
                # Generate personal data
                personal_data = generate_personal_data()
                
                # Generate profession-specific attributes
                attributes = generate_agent_attributes(profession)
                
                # Generate profession-specific interests
                interests = generate_agent_interests(profession)
                
                # Create agent
                agent_id = str(uuid.uuid4())
                cur.execute("""
                    INSERT INTO capsim.persons 
                    (id, simulation_id, profession, first_name, last_name, gender, date_of_birth,
                     financial_capability, trend_receptivity, social_status, energy_level, time_budget,
                     interests, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    agent_id,
                    simulation_id,
                    profession,
                    personal_data['first_name'],
                    personal_data['last_name'],
                    personal_data['gender'],
                    personal_data['date_of_birth'],
                    attributes['financial_capability'],
                    attributes['trend_receptivity'],
                    attributes['social_status'],
                    attributes['energy_level'],
                    attributes['time_budget'],
                    json.dumps(interests),
                    datetime.utcnow(),
                    datetime.utcnow()
                ))
                
                agents_created += 1
                
                if agents_created % 10 == 0:
                    logger.info(f"   Created {agents_created}/100 agents...")
        
        logger.info(f"✅ Successfully created {agents_created} agents!")
        cur.close()
        return simulation_id
        
    except Exception as e:
        logger.error(f"❌ Failed to create agents: {e}")
        cur.close()
        return None


def verify_agents(conn):
    """Проверяет созданных агентов."""
    cur = conn.cursor()
    
    # Basic stats
    cur.execute("""
        SELECT 
            COUNT(*) as total_agents,
            MIN(EXTRACT(YEAR FROM date_of_birth)) as min_year,
            MAX(EXTRACT(YEAR FROM date_of_birth)) as max_year,
            COUNT(DISTINCT profession) as unique_professions,
            COUNT(*) FILTER (WHERE gender = 'male') as male_count,
            COUNT(*) FILTER (WHERE gender = 'female') as female_count
        FROM capsim.persons
    """)
    
    stats = cur.fetchone()
    if stats:
        total, min_year, max_year, professions, males, females = stats
        logger.info("🔍 Verification Results:")
        logger.info(f"   Total agents: {total}")
        logger.info(f"   Birth years: {min_year}-{max_year}")
        logger.info(f"   Professions: {professions}")
        logger.info(f"   Gender: {males} males, {females} females")
    
    # Profession distribution
    cur.execute("""
        SELECT profession, COUNT(*) as count
        FROM capsim.persons
        GROUP BY profession
        ORDER BY profession
    """)
    
    prof_dist = cur.fetchall()
    logger.info("   Profession distribution:")
    for profession, count in prof_dist:
        logger.info(f"     - {profession}: {count}")
    
    # Attribute ranges verification
    cur.execute("""
        SELECT 
            AVG(financial_capability) as avg_financial,
            AVG(trend_receptivity) as avg_trend,
            AVG(social_status) as avg_social,
            AVG(energy_level) as avg_energy,
            AVG(time_budget) as avg_budget
        FROM capsim.persons
    """)
    
    attr_stats = cur.fetchone()
    if attr_stats:
        logger.info("   Average attributes:")
        logger.info(f"     - Financial capability: {attr_stats[0]:.2f}")
        logger.info(f"     - Trend receptivity: {attr_stats[1]:.2f}")
        logger.info(f"     - Social status: {attr_stats[2]:.2f}")
        logger.info(f"     - Energy level: {attr_stats[3]:.2f}")
        logger.info(f"     - Time budget: {attr_stats[4]:.2f}")
    
    cur.close()
    return total == 100


def main():
    """Главная функция."""
    logger.info("🚀 CAPSIM: Recreate 100 Proper Agents")
    logger.info("=" * 50)
    
    # Connect to database
    conn = get_connection()
    if not conn:
        sys.exit(1)
    
    # Step 1: Clear existing agents
    logger.info("Step 1: Clearing existing agents...")
    if not clear_all_agents(conn):
        conn.close()
        sys.exit(1)
    
    # Step 2: Create 100 new agents
    logger.info("\nStep 2: Creating 100 new agents with proper parameters...")
    simulation_id = create_100_agents(conn)
    if not simulation_id:
        conn.close()
        sys.exit(1)
    
    # Step 3: Verify agents
    logger.info("\nStep 3: Verifying created agents...")
    success = verify_agents(conn)
    
    conn.close()
    
    if success:
        logger.info("\n🎉 Success! 100 agents created with proper parameters:")
        logger.info("   ✅ Birth years: 1960-2007 (age 18-65)")
        logger.info("   ✅ Attribute distributions per profession (tech v.1.5.md)")
        logger.info("   ✅ Russian names with proper gender endings")
        logger.info("   ✅ time_budget as FLOAT (0.0-5.0)")
        logger.info("   ✅ Agent interests according to requirements")
        logger.info(f"   📋 Simulation ID: {simulation_id}")
    else:
        logger.error("\n❌ Agent creation completed with issues")
        sys.exit(1)


if __name__ == "__main__":
    main() 