import os
import pandas as pd
from sqlalchemy import create_engine, text
import json

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

def analyze_trend_receptivity_change_full():
    db_url = get_database_url()
    engine = create_engine(db_url)
    with engine.connect() as connection:
        # 1. Find the last completed simulation and its configuration
        query_last_sim = "SELECT run_id, configuration FROM capsim.simulation_runs WHERE status = 'COMPLETED' ORDER BY end_time DESC LIMIT 1"
        sim_result = connection.execute(text(query_last_sim)).fetchone()
        if not sim_result:
            print("No completed simulations found.")
            return
        sim_id, sim_config = sim_result
        print(f"Analyzing last completed simulation: {sim_id}")
        
        print("\n--- Simulation Configuration Used ---")
        print(json.dumps(sim_config, indent=2))

        # 2. Get all participants from the last simulation
        query_participants = text("""
            SELECT 
                p.id as person_id, 
                p.profession, 
                p.trend_receptivity as final_receptivity
            FROM capsim.simulation_participants sp
            JOIN capsim.persons p ON sp.person_id = p.id
            WHERE sp.simulation_id = :sim_id
        """)
        df_participants = pd.read_sql_query(query_participants, connection, params={"sim_id": sim_id})

        if df_participants.empty:
            print("No participants found for this simulation.")
            return

        # 3. Get trend_receptivity history for the last simulation
        query_history = text("""
            SELECT
                person_id,
                new_value,
                change_timestamp
            FROM capsim.person_attribute_history
            WHERE
                simulation_id = :sim_id
                AND attribute_name = 'trend_receptivity'
            ORDER BY
                person_id, change_timestamp
        """)
        df_history = pd.read_sql_query(query_history, connection, params={"sim_id": sim_id})

        # 4. Find initial trend_receptivity for each person from history
        if not df_history.empty:
            initial_values = df_history.loc[df_history.groupby('person_id')['change_timestamp'].idxmin()]
            initial_values = initial_values.rename(columns={'new_value': 'initial_receptivity'})
            df_report = pd.merge(df_participants, initial_values[['person_id', 'initial_receptivity']], on='person_id', how='left')
        else:
            df_report = df_participants
            df_report['initial_receptivity'] = None

        df_report['initial_receptivity'].fillna(df_report['final_receptivity'], inplace=True)

        # 5. Calculate average change per profession
        profession_stats = df_report.groupby('profession').agg(
            avg_initial=('initial_receptivity', 'mean'),
            avg_final=('final_receptivity', 'mean')
        ).reset_index()

        profession_stats['change'] = profession_stats['avg_final'] - profession_stats['avg_initial']

        print("\n--- Trend Receptivity Change by Profession (Full Report) ---")
        print(profession_stats.to_string())

if __name__ == "__main__":
    analyze_trend_receptivity_change_full()
