# External Clients Database Access

This directory contains scripts and configurations for managing database access for external systems that integrate with CAPSIM.

## Files

- `external_clients_permissions.sql` - SQL template with all permission definitions
- `setup_external_clients.sh` - Executable script to apply permissions
- `README_external_clients.md` - This documentation

## Current External Clients

### 1. Debezium (Change Data Capture)
- **User**: `debezium`
- **Purpose**: Real-time data replication to external systems
- **Permissions**: SELECT on 12 tables + REPLICATION privilege
- **Tables**:
  - `persons` - Core person entities
  - `events` - System events
  - `trends` - Trend data
  - `simulation_runs` - Simulation metadata
  - `affinity_map` - Topic affinity mappings
  - `agent_interests` - Agent interest data
  - `agents_profession` - Agent profession data
  - `daily_trend_summary` - Daily aggregated trends
  - `person_attribute_history` - Person attribute changes
  - `simulation_participants` - Simulation participation data
  - `topic_interest_mapping` - Topic-interest relationships
  - `alembic_version` - Database schema version

### 2. Airflow (Analytics & ETL)
- **User**: `airflow_reader`
- **Purpose**: Analytics workflows and reporting
- **Permissions**: SELECT on 3 key tables
- **Tables**:
  - `persons` - Person data for analytics
  - `daily_trend_summary` - Aggregated trend data
  - `trends` - Raw trend data

## Usage

### Automatic Setup (Recommended)
The permissions are automatically applied during database initialization when using Docker Compose.

### Manual Setup
```bash
# Set environment variables
export DEBEZIUM_PASSWORD="your_secure_password"
export AIRFLOW_PASSWORD="your_secure_password"

# Run the setup script
./scripts/setup_external_clients.sh
```

### Adding New External Clients

1. Edit `external_clients_permissions.sql` to add new user definitions
2. Update `setup_external_clients.sh` to include the new user creation
3. Add password environment variable to `.env.example`
4. Update this README with the new client information

## Security Best Practices

1. **Change Default Passwords**: Never use default passwords in production
2. **Use Environment Variables**: Store passwords in environment variables, not in code
3. **Principle of Least Privilege**: Grant only the minimum required permissions
4. **Regular Password Rotation**: Rotate passwords regularly
5. **Monitor Access**: Set up logging and monitoring for database access
6. **SSL/TLS**: Use encrypted connections for all external clients
7. **Network Security**: Restrict network access using firewalls/security groups

## Environment Variables

Add these to your `.env` file:

```bash
# External Clients Database Access
DEBEZIUM_PASSWORD=your_secure_debezium_password
AIRFLOW_PASSWORD=your_secure_airflow_password
```

## Troubleshooting

### Check Current Permissions
```sql
-- View permissions for a specific user
SELECT grantee, table_schema, table_name, privilege_type 
FROM information_schema.role_table_grants 
WHERE grantee = 'debezium';
```

### Verify User Exists
```sql
SELECT rolname FROM pg_roles WHERE rolname IN ('debezium', 'airflow_reader');
```

### Reset Permissions
```bash
# Drop and recreate users if needed
docker exec -i capsim-postgres-1 psql -U postgres -d capsim_db -c "DROP USER IF EXISTS debezium;"
./scripts/setup_external_clients.sh
```

## Connection Examples

### Debezium Connector Configuration
```json
{
  "database.hostname": "postgres",
  "database.port": "5432",
  "database.user": "debezium",
  "database.password": "${DEBEZIUM_PASSWORD}",
  "database.dbname": "capsim_db",
  "database.server.name": "capsim"
}
```

### Airflow Connection
```python
from airflow.providers.postgres.hooks.postgres import PostgresHook

hook = PostgresHook(
    postgres_conn_id='capsim_readonly',
    schema='capsim_db'
)
```