#!/usr/bin/env python3
"""
Скрипт для синхронизации конфигурации профессий из simulation.yaml в таблицу agents_profession.
"""

import os
import yaml
from sqlalchemy import create_engine, text
from pathlib import Path


def get_database_url():
    """Gets the database URL from environment variables or uses a default value."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL environment variable not set.")
        default_url = "postgresql://capsim_rw:capsim321@localhost:5432/capsim_db"
        print(f"Using default URL: {default_url}")
        db_url = default_url
    
    if os.getenv("DOCKER_ENV") != "true":
        db_url = db_url.replace("@postgres:", "@localhost:")
        
    db_url = db_url.replace("postgresql+asyncpg", "postgresql")
    return db_url


def load_simulation_config():
    """Loads simulation configuration from config/simulation.yaml."""
    config_path = Path(__file__).parent.parent / "config" / "simulation.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def sync_profession_config():
    """Синхронизирует конфигурацию профессий из simulation.yaml в таблицу agents_profession."""
    print("🔄 Синхронизация конфигурации профессий из simulation.yaml...")
    
    # Загружаем конфигурацию из YAML
    config = load_simulation_config()
    professions_config = config.get('professions', {})
    
    if not professions_config:
        print("❌ Конфигурация профессий не найдена в simulation.yaml")
        return
    
    print(f"📊 Найдено {len(professions_config)} профессий в конфигурации")
    
    # Подключаемся к БД
    db_url = get_database_url()
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # Очищаем таблицу
        conn.execute(text("TRUNCATE TABLE capsim.agents_profession RESTART IDENTITY CASCADE"))
        print("🗑️  Очищена таблица agents_profession")
        
        # Подготавливаем данные для вставки
        insert_data = []
        for profession, prof_config in professions_config.items():
            attributes = prof_config.get('attributes', {})
            
            # Извлекаем диапазоны атрибутов
            financial_capability = attributes.get('financial_capability', [1, 5])
            trend_receptivity = attributes.get('trend_receptivity', [1, 5])
            social_status = attributes.get('social_status', [1, 5])
            energy_level = attributes.get('energy_level', [1, 5])
            time_budget = attributes.get('time_budget', [1, 5])
            
            insert_data.append({
                "profession": profession,
                "financial_capability_min": financial_capability[0],
                "financial_capability_max": financial_capability[1],
                "trend_receptivity_min": trend_receptivity[0],
                "trend_receptivity_max": trend_receptivity[1],
                "social_status_min": social_status[0],
                "social_status_max": social_status[1],
                "energy_level_min": energy_level[0],
                "energy_level_max": energy_level[1],
                "time_budget_min": time_budget[0],
                "time_budget_max": time_budget[1],
            })
            
            print(f"  ✅ {profession}: trend_receptivity={trend_receptivity}")
        
        # Вставляем данные
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
            
        print(f"✅ Синхронизировано {len(insert_data)} профессий в agents_profession")
        
        # Проверяем результат
        result = conn.execute(text("SELECT profession, trend_receptivity_min, trend_receptivity_max FROM capsim.agents_profession ORDER BY profession"))
        print("\n📋 Результат синхронизации:")
        for row in result:
            print(f"  {row.profession}: trend_receptivity=[{row.trend_receptivity_min}, {row.trend_receptivity_max}]")


if __name__ == "__main__":
    sync_profession_config()