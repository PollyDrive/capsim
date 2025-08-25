-- External Clients Database Permissions
-- This file manages database access for external systems integrating with CAPSIM

-- =============================================================================
-- DEBEZIUM USER - Change Data Capture (CDC) for replication
-- =============================================================================

-- Create debezium user for CDC replication
CREATE USER debezium WITH PASSWORD 'dbz';

-- Grant schema access
GRANT USAGE ON SCHEMA capsim TO debezium;

-- Grant replication privileges (required for CDC)
ALTER USER debezium REPLICATION;

-- Grant SELECT on specific tables for CDC replication
-- These are the core tables that need to be replicated to external systems
GRANT SELECT ON TABLE capsim.persons TO debezium;
GRANT SELECT ON TABLE capsim.events TO debezium;
-- GRANT SELECT ON TABLE capsim.trends TO debezium;
-- GRANT SELECT ON TABLE capsim.simulation_runs TO debezium;

-- Additional tables that were previously replicated
-- GRANT SELECT ON TABLE capsim.affinity_map TO debezium;
-- GRANT SELECT ON TABLE capsim.agent_interests TO debezium;
-- GRANT SELECT ON TABLE capsim.agents_profession TO debezium;
-- GRANT SELECT ON TABLE capsim.daily_trend_summary TO debezium;
GRANT SELECT ON TABLE capsim.person_attribute_history TO debezium;
GRANT SELECT ON TABLE capsim.simulation_participants TO debezium;
-- GRANT SELECT ON TABLE capsim.topic_interest_mapping TO debezium;
-- GRANT SELECT ON TABLE capsim.alembic_version TO debezium;

-- =============================================================================
-- AIRFLOW USER - Analytics and ETL workflows
-- =============================================================================

-- Create airflow reader user for analytics workflows
CREATE USER IF NOT EXISTS airflow_reader WITH PASSWORD 'airflow_2025';

-- Grant schema access
GRANT USAGE ON SCHEMA capsim TO airflow_reader;
ALTER USER airflow_reader WITH REPLICATION;

-- Grant SELECT on specific tables for analytics
-- These tables contain aggregated data needed for reporting and analytics
GRANT SELECT ON TABLE capsim.simulation_runs TO airflow_reader;
GRANT SELECT ON TABLE capsim.daily_trend_summary TO airflow_reader;
GRANT SELECT ON TABLE capsim.trends TO airflow_reader;

-- =============================================================================
-- FUTURE EXTERNAL CLIENTS TEMPLATE
-- =============================================================================

-- Template for adding new external clients:
/*
-- Create new external client user
CREATE USER IF NOT EXISTS client_name WITH PASSWORD 'secure_password';

-- Grant schema access
GRANT USAGE ON SCHEMA capsim TO client_name;

-- Grant specific table permissions based on needs:
-- For read-only analytics:
GRANT SELECT ON TABLE capsim.table_name TO client_name;

-- For specific operations:
GRANT INSERT, UPDATE ON TABLE capsim.table_name TO client_name;

-- For sequence access (if needed for inserts):
GRANT USAGE ON SEQUENCE capsim.sequence_name TO client_name;
*/

-- =============================================================================
-- SECURITY NOTES
-- =============================================================================

-- 1. Change default passwords before using in production
-- 2. Use environment variables for passwords in deployment scripts
-- 3. Regularly rotate passwords
-- 4. Monitor access logs for unusual activity
-- 5. Grant minimal required permissions (principle of least privilege)
-- 6. Consider using connection pooling for external clients
-- 7. Set up SSL/TLS for all external connections

-- =============================================================================
-- MAINTENANCE COMMANDS
-- =============================================================================

-- View current permissions for a user:
-- SELECT grantee, table_schema, table_name, privilege_type 
-- FROM information_schema.role_table_grants 
-- WHERE grantee = 'username';

-- Revoke permissions if needed:
-- REVOKE SELECT ON TABLE capsim.table_name FROM username;

-- Drop user if needed:
-- DROP USER IF EXISTS username;