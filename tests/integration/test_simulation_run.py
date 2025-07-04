import pytest
import psycopg2
from typer.testing import CliRunner
from pathlib import Path
import os
import shutil

from src.capsim.main import app
from scripts import init_db, seed_data

runner = CliRunner()

@pytest.fixture(scope="module")
def setup_test_database():
    """
    A fixture to set up a clean test database for the entire test module.
    It points to a test config, initializes schema, and seeds data.
    """
    original_config_path = Path("config/database.ini")
    test_config_path = Path("config/database.ini.test")
    
    if not test_config_path.exists():
        pytest.skip("Test database config 'config/database.ini.test' not found.")

    # Temporarily replace main config with test config
    if original_config_path.exists():
        os.rename(original_config_path, "config/database.ini.bak")
    shutil.copy(test_config_path, original_config_path)
    
    print("\n--- Setting up test database ---")
    try:
        # Check connection to create DB if not exists
        conn_params = seed_data.get_db_params()
        db_name = conn_params.pop('dbname')
        conn = psycopg2.connect(**conn_params)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {db_name}")
            print(f"Database '{db_name}' created.")
        cur.close()
        conn.close()
    except Exception as e:
        pytest.fail(f"Could not connect to PostgreSQL to set up test database. Is it running? Error: {e}")

    init_db.create_tables()
    seed_data.seed_database()
    print("--- Test database setup complete ---")

    yield

    print("\n--- Tearing down test database ---")
    # Restore original config
    os.remove(original_config_path)
    if Path("config/database.ini.bak").exists():
        os.rename("config/database.ini.bak", original_config_path)


def get_table_count(table_name: str) -> int:
    conn = init_db.get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table_name};")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count

def test_simulation_full_run(setup_test_database):
    """
    Tests a full 1-day simulation run, verifying database state changes.
    """
    # 1. Get initial state
    initial_person_count = get_table_count("persons")
    assert initial_person_count > 0, "Seeding failed, no persons in db"

    # 2. Run the simulation via the CLI
    result = runner.invoke(app, ["--days", "1"])
    
    assert result.exit_code == 0, f"CLI command failed: {result.stdout}"
    assert "Simulation completed successfully." in result.stdout

    # 3. Assert final database state
    # Check that simulation log was created and marked completed
    conn = init_db.get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, simulated_days, person_count FROM simulation_logs ORDER BY start_time DESC LIMIT 1")
    log_status, log_days, log_person_count = cur.fetchone()
    cur.close()
    conn.close()

    assert log_status == "completed"
    assert log_days == 1
    assert log_person_count == initial_person_count

    # Check that events and history were logged
    assert get_table_count("events") > 0, "No events were logged"
    assert get_table_count("person_attribute_history") > 0, "No attribute changes were logged" 