#!/bin/bash
set -e

# Setup External Clients Database Permissions
# This script applies permissions for external systems (Debezium, Airflow, etc.)

echo "Setting up external client database permissions..."

# Database connection parameters
POSTGRES_DB=${POSTGRES_DB:-capsim_db}
POSTGRES_USER=${POSTGRES_USER:-postgres}

# External client passwords (should be set via environment variables)
DEBEZIUM_PASSWORD=${DEBEZIUM_PASSWORD:-"debezium_secure_password_2024"}
AIRFLOW_PASSWORD=${AIRFLOW_PASSWORD:-"airflow_secure_password_2024"}

# Check if we're running inside Docker container
if [ -n "$DOCKER_ENV" ]; then
    # Running inside Docker container
    PSQL_CMD="psql -v ON_ERROR_STOP=1 --username $POSTGRES_USER --dbname $POSTGRES_DB"
else
    # Running from host, connect to Docker container
    CONTAINER_NAME=${CONTAINER_NAME:-"capsim-postgres-1"}
    PSQL_CMD="docker exec -i $CONTAINER_NAME psql -v ON_ERROR_STOP=1 --username $POSTGRES_USER --dbname $POSTGRES_DB"
fi

echo "Applying external client permissions..."

$PSQL_CMD <<-EOSQL
    -- =============================================================================
    -- DEBEZIUM USER - Change Data Capture (CDC) for replication
    -- =============================================================================
    
    -- Create debezium user for CDC replication
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'debezium') THEN
            CREATE USER debezium WITH PASSWORD '$DEBEZIUM_PASSWORD';
        END IF;
    END
    \$\$;
    
    -- Grant schema access
    GRANT USAGE ON SCHEMA public TO debezium;
    
    -- Grant replication privileges (required for CDC)
    ALTER USER debezium REPLICATION;
    
    -- Grant SELECT on specific tables for CDC replication
    GRANT SELECT ON TABLE persons TO debezium;
    GRANT SELECT ON TABLE events TO debezium;
    GRANT SELECT ON TABLE trends TO debezium;
    GRANT SELECT ON TABLE simulation_runs TO debezium;
    GRANT SELECT ON TABLE affinity_map TO debezium;
    GRANT SELECT ON TABLE agent_interests TO debezium;
    GRANT SELECT ON TABLE agents_profession TO debezium;
    GRANT SELECT ON TABLE daily_trend_summary TO debezium;
    GRANT SELECT ON TABLE person_attribute_history TO debezium;
    GRANT SELECT ON TABLE simulation_participants TO debezium;
    GRANT SELECT ON TABLE topic_interest_mapping TO debezium;
    GRANT SELECT ON TABLE alembic_version TO debezium;
    
    -- =============================================================================
    -- AIRFLOW USER - Analytics and ETL workflows
    -- =============================================================================
    
    -- Create airflow reader user for analytics workflows
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'airflow_reader') THEN
            CREATE USER airflow_reader WITH PASSWORD '$AIRFLOW_PASSWORD';
        END IF;
    END
    \$\$;
    
    -- Grant schema access
    GRANT USAGE ON SCHEMA public TO airflow_reader;
    
    -- Grant SELECT on specific tables for analytics
    GRANT SELECT ON TABLE persons TO airflow_reader;
    GRANT SELECT ON TABLE daily_trend_summary TO airflow_reader;
    GRANT SELECT ON TABLE trends TO airflow_reader;
    
    -- Grant future table permissions
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO debezium;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO airflow_reader;
    
EOSQL

echo "External client permissions applied successfully!"
echo "Created users:"
echo "  - debezium (replication access to 12 tables)"
echo "  - airflow_reader (read access to 3 tables)"
echo ""
echo "Security reminder: Change default passwords in production!"