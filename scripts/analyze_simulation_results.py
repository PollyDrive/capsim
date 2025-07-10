#!/usr/bin/env python3
"""
Скрипт для анализа результатов симуляции.

Подключается к базе данных, извлекает данные о трендах и взаимодействиях
из последней симуляции, а затем выводит топ-5 самых виральных трендов.
"""
import os
import pandas as pd
from sqlalchemy import create_engine, text

def get_database_url():
    """Получает URL базы данных из переменных окружения или использует дефолтное значение."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Переменная окружения DATABASE_URL не установлена.")
        # Для локального запуска скрипта напрямую, а не через `capsim run`
        default_url = "postgresql://capsim_rw:capsim321@localhost:5432/capsim_db"
        print(f"Используется URL по умолчанию: {default_url}")
        db_url = default_url
    
    # pandas + postgresql требуют драйвер psycopg2, а не asyncpg
    return db_url.replace("postgresql+asyncpg", "postgresql")

def analyze_results(db_url: str):
    """
    Анализирует результаты симуляции.
    
    - Подключается к БД.
    - Находит ID последней завершенной симуляции.
    - Загружает все тренды из этой симуляции.
    - Выводит топ-5 трендов по количеству взаимодействий.
    """
    print(f"Подключение к базе данных...")
    try:
        engine = create_engine(db_url)
        with engine.connect() as connection:
            print("Соединение установлено.")
            
            # 1. Найти последнюю завершенную симуляцию
            query_last_sim = "SELECT simulation_id FROM simulations WHERE status = 'COMPLETED' ORDER BY end_time DESC LIMIT 1"
            sim_id_result = connection.execute(text(query_last_sim)).fetchone()
            
            if not sim_id_result:
                print("Не найдено завершенных симуляций для анализа.")
                return
                
            sim_id = sim_id_result[0]
            print(f"Анализ последней завершенной симуляции: {sim_id}")

            # 2. Загрузить все тренды для этой симуляции
            query_trends = text("""
                SELECT 
                    t.trend_id,
                    t.topic,
                    t.base_virality_score,
                    t.total_interactions,
                    t.author_id
                FROM trends t
                WHERE t.simulation_id = :sim_id
            """)
            
            df = pd.read_sql_query(query_trends, connection, params={"sim_id": sim_id})

            if df.empty:
                print("В этой симуляции не найдено трендов.")
                return

            # 3. Вывести топ-5 самых виральных
            top_5_viral = df.sort_values(by="total_interactions", ascending=False).head(5)

            print("\n--- Топ-5 самых виральных трендов ---")
            print(top_5_viral.to_string())

    except Exception as e:
        print(f"Произошла ошибка при анализе: {e}")

if __name__ == "__main__":
    db_url = get_database_url()
    analyze_results(db_url) 