#!/bin/bash
set -e

# This script runs during PostgreSQL container initialization
# and creates application users with passwords from environment variables

echo "Initializing CAPSIM database users..."

# Use environment variables or defaults
CAPSIM_RW_PASSWORD=${CAPSIM_RW_PASSWORD:-capsim_password}
CAPSIM_RO_PASSWORD=${CAPSIM_RO_PASSWORD:-capsim_password}
POSTGRES_DB=${POSTGRES_DB:-capsim}

# Create read-write user for the application
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create read-write user for the application
    CREATE USER capsim_rw WITH PASSWORD '$CAPSIM_RW_PASSWORD';
    GRANT CONNECT ON DATABASE $POSTGRES_DB TO capsim_rw;
    GRANT USAGE ON SCHEMA public TO capsim_rw;
    GRANT CREATE ON SCHEMA public TO capsim_rw;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO capsim_rw;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO capsim_rw;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO capsim_rw;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO capsim_rw;
    
    -- Create read-only user for analytics/monitoring
    CREATE USER capsim_ro WITH PASSWORD '$CAPSIM_RO_PASSWORD';
    GRANT CONNECT ON DATABASE $POSTGRES_DB TO capsim_ro;
    GRANT USAGE ON SCHEMA public TO capsim_ro;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO capsim_ro;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO capsim_ro;
    
    -- Extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
EOSQL

echo "CAPSIM database initialization completed successfully!"
echo "Created users: capsim_rw (read-write), capsim_ro (read-only)" 