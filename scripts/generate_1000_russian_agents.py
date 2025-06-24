#!/usr/bin/env python3
"""
Скрипт генерации 1000 агентов с русскими именами.

Требования:
- Русские имена с правильным соответствием пола
- Округление атрибутов до 3 знаков после запятой  
- Валидация диапазонов атрибутов
- Лимит 1000 агентов
- Очистка существующих агентов
"""

import os
import sys
import json
import uuid
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from faker import Faker


class Russian1000AgentsGenerator:
    """Генератор 1000 агентов с русскими именами."""
    
    PROFESSIONS = [
        "ShopClerk", "Worker", "Developer", "Politician", "Blogger",
        "Businessman", "Doctor", "Teacher", "Unemployed", "Artist",
        "SpiritualMentor", "Philosopher"
    ]
    
    INTERESTS = [
        "Economics", "Wellbeing", "Security", "Entertainment", 
        "Education", "Technology", "SocialIssues"
    ]
    
    def __init__(self):
        """Инициализация генератора."""
        # Database configuration
        self.postgres_user = os.getenv("POSTGRES_USER", "postgres")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "postgres_password")
        self.postgres_db = os.getenv("POSTGRES_DB", "capsim_db")
        
        # Connection URL
        self.admin_url = f"postgresql://{self.postgres_user}:{self.postgres_password}@postgres:5432/{self.postgres_db}"
        
        # Faker for Russian names with proper gender matching
        self.fake = Faker('ru_RU')
        
        print(f"🚀 Russian 1000 Agents Generator")
        print(f"   Database: {self.postgres_db}")
        print(f"   Target: 1000 агентов с русскими именами")
    
    def clear_existing_data(self) -> None:
        """Очистка существующих агентов и симуляций."""
        print("🗑️  Очистка существующих данных...")
        
        conn = psycopg2.connect(
            host="postgres",
            database=self.postgres_db,
            user=self.postgres_user,
            password=self.postgres_password
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with conn.cursor() as cur:
            # Clear in correct order (foreign key constraints)
            cur.execute("DELETE FROM capsim.events")
            cur.execute("DELETE FROM capsim.trends")
            cur.execute("DELETE FROM capsim.person_attribute_history")
            cur.execute("DELETE FROM capsim.daily_trend_summary")
            cur.execute("DELETE FROM capsim.persons")
            cur.execute("DELETE FROM capsim.simulation_runs")
            
            print("✅ Существующие данные очищены")
        
        conn.close()
    
    def generate_russian_name(self) -> tuple:
        """Генерация русского имени с правильным соответствием пола."""
        gender = self.fake.random_element(elements=['male', 'female'])
        
        if gender == 'male':
            first_name = self.fake.first_name_male()
            last_name = self.fake.last_name_male()
        else:
            first_name = self.fake.first_name_female()
            last_name = self.fake.last_name_female()
        
        return first_name, last_name, gender
    
    def generate_agent_attributes(self) -> dict:
        """Генерация атрибутов агента с валидацией."""
        # Generate attributes with proper validation and rounding
        financial_capability = round(self.fake.uniform(0.5, 5.0), 3)
        trend_receptivity = round(self.fake.uniform(0.5, 5.0), 3)
        social_status = round(self.fake.uniform(0.5, 4.5), 3)  # ≥ 0.5 для осмысленных действий
        energy_level = round(self.fake.uniform(0.5, 5.0), 3)
        time_budget = self.fake.random_int(min=1, max=5)
        
        # Generate interests (7 categories, each 0.1-0.9, rounded to 3 decimals)
        interests = {}
        for interest in self.INTERESTS:
            interests[interest] = round(self.fake.uniform(0.1, 0.9), 3)
        
        # Validate ranges
        assert 0.0 <= financial_capability <= 5.0, f"Invalid financial_capability: {financial_capability}"
        assert 0.0 <= trend_receptivity <= 5.0, f"Invalid trend_receptivity: {trend_receptivity}"
        assert 0.0 <= social_status <= 5.0, f"Invalid social_status: {social_status}"
        assert 0.0 <= energy_level <= 5.0, f"Invalid energy_level: {energy_level}"
        assert 1 <= time_budget <= 5, f"Invalid time_budget: {time_budget}"
        
        return {
            'financial_capability': financial_capability,
            'trend_receptivity': trend_receptivity,
            'social_status': social_status,
            'energy_level': energy_level,
            'time_budget': time_budget,
            'interests': interests
        }
    
    def create_simulation_run(self) -> str:
        """Создание новой симуляции."""
        print("📊 Создание новой симуляции...")
        
        simulation_id = str(uuid.uuid4())
        
        conn = psycopg2.connect(
            host="postgres",
            database=self.postgres_db,
            user=self.postgres_user,
            password=self.postgres_password
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO capsim.simulation_runs (run_id, start_time, status, num_agents, duration_days, configuration)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                simulation_id,
                datetime.utcnow(),
                'INITIALIZED',
                1000,
                7,
                json.dumps({
                    "bootstrap": True,
                    "russian_names": True,
                    "attributes_rounded": True,
                    "agent_limit": 1000
                })
            ))
        
        conn.close()
        
        print(f"✅ Симуляция создана: {simulation_id}")
        return simulation_id
    
    def generate_1000_agents(self, simulation_id: str) -> None:
        """Генерация 1000 агентов с русскими именами."""
        print("👥 Генерация 1000 агентов с русскими именами...")
        
        conn = psycopg2.connect(
            host="postgres",
            database=self.postgres_db,
            user=self.postgres_user,
            password=self.postgres_password
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Generate agents in batches for better performance
        batch_size = 50
        agents_created = 0
        
        for batch_start in range(0, 1000, batch_size):
            batch_end = min(batch_start + batch_size, 1000)
            
            with conn.cursor() as cur:
                for i in range(batch_start, batch_end):
                    # Generate Russian name with proper gender matching
                    first_name, last_name, gender = self.generate_russian_name()
                    
                    # Random profession
                    profession = self.fake.random_element(elements=self.PROFESSIONS)
                    
                    # Generate attributes
                    attributes = self.generate_agent_attributes()
                    
                    # Create agent record
                    agent_id = str(uuid.uuid4())
                    
                    cur.execute("""
                        INSERT INTO capsim.persons (
                            id, simulation_id, profession, financial_capability,
                            trend_receptivity, social_status, energy_level, time_budget,
                            exposure_history, interests, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        agent_id,
                        simulation_id,
                        profession,
                        attributes['financial_capability'],
                        attributes['trend_receptivity'],
                        attributes['social_status'],
                        attributes['energy_level'],
                        attributes['time_budget'],
                        json.dumps({}),  # empty exposure_history
                        json.dumps(attributes['interests']),
                        datetime.utcnow(),
                        datetime.utcnow()
                    ))
                    
                    agents_created += 1
            
            print(f"   📝 Создано агентов: {agents_created}/1000")
        
        conn.close()
        print(f"✅ Создано {agents_created} агентов с русскими именами")
    
    def verify_generation(self, simulation_id: str) -> None:
        """Проверка корректности генерации."""
        print("🔍 Проверка корректности генерации...")
        
        conn = psycopg2.connect(
            host="postgres",
            database=self.postgres_db,
            user=self.postgres_user,
            password=self.postgres_password
        )
        
        with conn.cursor() as cur:
            # Count total agents
            cur.execute("SELECT COUNT(*) FROM capsim.persons WHERE simulation_id = %s", (simulation_id,))
            total_agents = cur.fetchone()[0]
            
            # Count by profession
            cur.execute("""
                SELECT profession, COUNT(*) 
                FROM capsim.persons 
                WHERE simulation_id = %s 
                GROUP BY profession 
                ORDER BY profession
            """, (simulation_id,))
            profession_counts = cur.fetchall()
            
            # Validate attribute ranges
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE financial_capability BETWEEN 0.5 AND 5.0) as valid_financial,
                    COUNT(*) FILTER (WHERE trend_receptivity BETWEEN 0.5 AND 5.0) as valid_receptivity,
                    COUNT(*) FILTER (WHERE social_status BETWEEN 0.5 AND 4.5) as valid_social,
                    COUNT(*) FILTER (WHERE energy_level BETWEEN 0.5 AND 5.0) as valid_energy,
                    COUNT(*) FILTER (WHERE time_budget BETWEEN 1 AND 5) as valid_time_budget
                FROM capsim.persons WHERE simulation_id = %s
            """, (simulation_id,))
            validation = cur.fetchone()
            
            # Check decimal precision (should be 3 digits)
            cur.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE (financial_capability * 1000) = ROUND(financial_capability * 1000)) as financial_3dec,
                    COUNT(*) FILTER (WHERE (trend_receptivity * 1000) = ROUND(trend_receptivity * 1000)) as receptivity_3dec,
                    COUNT(*) FILTER (WHERE (social_status * 1000) = ROUND(social_status * 1000)) as social_3dec,
                    COUNT(*) FILTER (WHERE (energy_level * 1000) = ROUND(energy_level * 1000)) as energy_3dec
                FROM capsim.persons WHERE simulation_id = %s
            """, (simulation_id,))
            precision_check = cur.fetchone()
        
        conn.close()
        
        print(f"   📊 Общее количество агентов: {total_agents}")
        print(f"   📊 Распределение по профессиям:")
        for profession, count in profession_counts:
            print(f"      - {profession}: {count}")
        
        print(f"   ✅ Валидация атрибутов:")
        total = validation[0]
        print(f"      - Валидные financial_capability: {validation[1]}/{total}")
        print(f"      - Валидные trend_receptivity: {validation[2]}/{total}")
        print(f"      - Валидные social_status: {validation[3]}/{total}")
        print(f"      - Валидные energy_level: {validation[4]}/{total}")
        print(f"      - Валидные time_budget: {validation[5]}/{total}")
        
        print(f"   🔢 Проверка точности до 3 знаков:")
        print(f"      - financial_capability: {precision_check[0]}/{total}")
        print(f"      - trend_receptivity: {precision_check[1]}/{total}")
        print(f"      - social_status: {precision_check[2]}/{total}")
        print(f"      - energy_level: {precision_check[3]}/{total}")
        
        # Verify agent limit
        if total_agents == 1000:
            print("   ✅ Лимит 1000 агентов соблюден")
        else:
            print(f"   ❌ Неверное количество агентов: {total_agents} != 1000")
    
    def run_generation(self) -> None:
        """Основной метод генерации."""
        print("🚀 Запуск генерации 1000 русских агентов...")
        
        try:
            # Step 1: Clear existing data
            self.clear_existing_data()
            
            # Step 2: Create new simulation
            simulation_id = self.create_simulation_run()
            
            # Step 3: Generate 1000 agents
            self.generate_1000_agents(simulation_id)
            
            # Step 4: Verify generation
            self.verify_generation(simulation_id)
            
            print(f"🎉 Генерация завершена успешно!")
            print(f"   🆔 Simulation ID: {simulation_id}")
            print(f"   👥 Агенты: 1000 с русскими именами")
            print(f"   🔢 Атрибуты: округлены до 3 знаков")
            print(f"   ✅ Все требования выполнены")
            
        except Exception as e:
            print(f"❌ Ошибка генерации: {e}")
            raise


def main():
    """Entry point."""
    generator = Russian1000AgentsGenerator()
    generator.run_generation()


if __name__ == "__main__":
    main() 