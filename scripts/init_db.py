import psycopg2
from capsim.utils.db_connector import get_db_connection

def create_tables():
    """
    Creates the persons and events tables in the PostgreSQL database.
    This will drop existing tables first.
    """
    commands = (
        "DROP TABLE IF EXISTS events CASCADE;",
        "DROP TABLE IF EXISTS persons CASCADE;",
        """
        CREATE TABLE IF NOT EXISTS persons (
            id UUID PRIMARY KEY,
            first_name VARCHAR(255) NOT NULL,
            last_name VARCHAR(255) NOT NULL,
            middle_name VARCHAR(255),
            age INT NOT NULL,
            gender VARCHAR(50) NOT NULL,
            cluster VARCHAR(50) NOT NULL,
            profession VARCHAR(50) NOT NULL,
            financial_capability FLOAT NOT NULL,
            trend_receptivity FLOAT NOT NULL,
            social_status FLOAT NOT NULL,
            energy_level FLOAT NOT NULL,
            time_budget FLOAT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS events (
            event_id SERIAL PRIMARY KEY,
            actor_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            event_type VARCHAR(50) NOT NULL,
            details JSONB
        );
        """
    )
    
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("Failed to get database connection.")
            return

        cur = conn.cursor()
        for command in commands:
            cur.execute(command)
        
        cur.close()
        conn.commit()
        print("Tables created successfully.")
    
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()

if __name__ == '__main__':
    create_tables() 