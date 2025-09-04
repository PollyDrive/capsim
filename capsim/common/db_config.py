import os
from .environment import get_database_config, is_production

"""Database configuration utilities.
    Provides unified way to build DSN for sync and async postgres connections using
    environment variables only. Now supports environment-aware configuration.
"""

# Get environment-aware configuration
db_config = get_database_config()

# Prefer full URL env vars first
# Common names: POSTGRES_URL or DATABASE_URL
_full_url = db_config.get("DATABASE_URL") or os.getenv("POSTGRES_URL")

# If provided, use it directly (both sync and async forms)
if _full_url:
    # Ensure driver prefix for async form
    if _full_url.startswith("postgresql+asyncpg"):  # already async
        SYNC_DSN = _full_url.replace("+asyncpg", "")
        ASYNC_DSN = _full_url
    else:
        SYNC_DSN = _full_url
        # convert to asyncpg for async driver
        ASYNC_DSN = _full_url.replace("postgresql://", "postgresql+asyncpg://")
else:
    # Fallback to individual variables from environment-aware config
    DB_USER = db_config.get("POSTGRES_USER", "postgres")
    DB_PASSWORD = db_config.get("POSTGRES_PASSWORD", "")
    DB_HOST = db_config.get("POSTGRES_HOST", "localhost")
    DB_PORT = db_config.get("POSTGRES_PORT", "5432")
    DB_NAME = db_config.get("POSTGRES_DB", "capsim_db")
    
    # Add SSL for production
    ssl_suffix = "?sslmode=require" if is_production() else ""

    SYNC_DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}{ssl_suffix}"
    ASYNC_DSN = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}{ssl_suffix}"

__all__ = [
    "SYNC_DSN",
    "ASYNC_DSN",
]

# Backward compatibility exports for code referencing individual vars
globals().update({
    "DB_USER": locals().get("DB_USER", db_config.get("POSTGRES_USER", "")),
    "DB_PASSWORD": locals().get("DB_PASSWORD", db_config.get("POSTGRES_PASSWORD", "")),
    "DB_HOST": locals().get("DB_HOST", db_config.get("POSTGRES_HOST", "")),
    "DB_PORT": locals().get("DB_PORT", db_config.get("POSTGRES_PORT", "")),
    "DB_NAME": locals().get("DB_NAME", db_config.get("POSTGRES_DB", "")),
}) 