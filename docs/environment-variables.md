# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=capsim321
POSTGRES_DB=capsim_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Database Configuration
DATABASE_URL=postgresql+asyncpg://capsim_rw:capsim321@localhost:5432/capsim_db
DATABASE_URL_RO=postgresql+asyncpg://capsim_ro:capsim321@localhost:5432/capsim_db

# Database Users (used during initialization)
CAPSIM_RW_PASSWORD=capsim321
CAPSIM_RO_PASSWORD=capsim321

# Simulation Configuration  
DECIDE_SCORE_THRESHOLD=0.25
TREND_ARCHIVE_THRESHOLD_DAYS=3
BASE_RATE=43.2
BATCH_SIZE=1000

# Retry Configuration
BATCH_RETRY_ATTEMPTS=3
BATCH_RETRY_BACKOFFS=1,2,4

# Cache Configuration
CACHE_TTL_MIN=2880
CACHE_MAX_SIZE=10000

# Performance Configuration
SHUTDOWN_TIMEOUT_SEC=30
MAX_QUEUE_SIZE=5000

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
GRAFANA_PASSWORD=admin

# Realtime Configuration (NEW)
SIM_SPEED_FACTOR=60
ENABLE_REALTIME=false

# Logging
LOG_LEVEL=INFO
ENABLE_JSON_LOGS=true


# docker-compose exec app python -m capsim.cli.run_simulation --agents 5 --days 1 --speed 10 --test