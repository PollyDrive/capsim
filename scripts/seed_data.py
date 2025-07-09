#!/usr/bin/env python3
"""
Заполняет базу данных начальными данными для симуляции.
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from capsim.db.repositories import DatabaseRepository
from capsim.db.models import AgentsProfession, TopicInterestMapping
from capsim.common.db_config import ASYNC_DSN
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

async def seed_agent_profession_ranges():
    """Заполняет таблицу agents_profession диапазонами атрибутов согласно базовой таблице."""
    
    # Диапазоны атрибутов по профессиям из базовой таблицы
    profession_ranges = {
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
            "energy_level": (2.0, 5.0),
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
            "energy_level": (2.0, 5.0),
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
            "energy_level": (2.0, 5.0),
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
            "energy_level": (2.0, 5.0),
            "time_budget": (1.0, 2.0)
        }
    }
    
    database_url = ASYNC_DSN
    engine = create_async_engine(database_url, echo=False)
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # Очищаем существующие данные
        await session.execute(text("DELETE FROM capsim.agents_profession"))
        
        # Заполняем новыми данными
        for profession, ranges in profession_ranges.items():
            agent_prof = AgentsProfession(
                profession=profession,
                financial_capability_min=ranges["financial_capability"][0],
                financial_capability_max=ranges["financial_capability"][1],
                trend_receptivity_min=ranges["trend_receptivity"][0],
                trend_receptivity_max=ranges["trend_receptivity"][1],
                social_status_min=ranges["social_status"][0],
                social_status_max=ranges["social_status"][1],
                energy_level_min=ranges["energy_level"][0],
                energy_level_max=ranges["energy_level"][1],
                time_budget_min=ranges["time_budget"][0],
                time_budget_max=ranges["time_budget"][1]
            )
            session.add(agent_prof)
        
        await session.commit()
        print(f"✅ Заполнено {len(profession_ranges)} профессий в agents_profession")
    
    await engine.dispose()

async def seed_topic_interest_mapping():
    """Заполняет таблицу topic_interest_mapping маппингом тем к интересам."""
    
    # Маппинг тем трендов к категориям интересов
    topic_mappings = {
        "ECONOMIC": "Economics",
        "HEALTH": "Wellbeing", 
        "SPIRITUAL": "Spirituality",
        "CONSPIRACY": "Society",
        "SCIENCE": "Knowledge",
        "CULTURE": "Creativity",
        "SPORT": "Wellbeing"
    }
    
    database_url = ASYNC_DSN
    engine = create_async_engine(database_url, echo=False)
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # Очищаем существующие данные
        await session.execute(text("DELETE FROM capsim.topic_interest_mapping"))
        
        # Заполняем новыми данными
        for topic, interest_category in topic_mappings.items():
            mapping = TopicInterestMapping(
                topic_code=topic,
                topic_display=topic.capitalize(),
                interest_category=interest_category
            )
            session.add(mapping)
        
        await session.commit()
        print(f"✅ Заполнено {len(topic_mappings)} маппингов в topic_interest_mapping")
    
    await engine.dispose()

async def clear_persons_table():
    """Очищает таблицу persons для создания новых агентов."""
    
    database_url = ASYNC_DSN
    engine = create_async_engine(database_url, echo=False)
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # Очищаем таблицу persons
        await session.execute(text("TRUNCATE TABLE capsim.persons CASCADE"))
        await session.commit()
        print("✅ Очищена таблица persons")
    
    await engine.dispose()

async def main():
    """Основная функция для заполнения базы данных."""
    print("🔄 Заполнение базы данных начальными данными...")
    
    try:
        await seed_agent_profession_ranges()
        await seed_topic_interest_mapping()
        await clear_persons_table()
        print("✅ База данных успешно заполнена!")
        
    except Exception as e:
        print(f"❌ Ошибка при заполнении базы данных: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 