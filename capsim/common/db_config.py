import os

"""Database configuration utilities.
    Provides unified way to build DSN for sync and async postgres connections using
    environment variables only. Defaults are safe for local dev when `.env.local` is loaded.
"""

# Prefer full URL env vars first
# Common names: POSTGRES_URL or DATABASE_URL
_full_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")

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
    # Fallback to individual variables
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "capsim_db")

    SYNC_DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    ASYNC_DSN = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

__all__ = [
    "SYNC_DSN",
    "ASYNC_DSN",
]

# Backward compatibility exports for code referencing individual vars
globals().update({
    "DB_USER": locals().get("DB_USER", ""),
    "DB_PASSWORD": locals().get("DB_PASSWORD", ""),
    "DB_HOST": locals().get("DB_HOST", ""),
    "DB_PORT": locals().get("DB_PORT", ""),
    "DB_NAME": locals().get("DB_NAME", ""),
}) 