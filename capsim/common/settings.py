"""
Settings и configuration для CAPSIM симуляции.
"""

import os
from typing import Optional


class Settings:
    """Centralized configuration management."""
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://capsim_rw:password@localhost:5432/capsim")
    DATABASE_URL_RO: str = os.getenv("DATABASE_URL_RO", "postgresql://capsim_ro:password@localhost:5432/capsim")
    
    # Simulation core settings
    DECIDE_SCORE_THRESHOLD: float = float(os.getenv("DECIDE_SCORE_THRESHOLD", "0.25"))
    BASE_RATE: float = float(os.getenv("BASE_RATE", "43.2"))
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "100"))
    
    # Realtime mode configuration  
    SIM_SPEED_FACTOR: float = float(os.getenv("SIM_SPEED_FACTOR", "60"))
    ENABLE_REALTIME: bool = os.getenv("ENABLE_REALTIME", "false").lower() == "true"
    
    # Performance settings
    BATCH_RETRY_ATTEMPTS: int = int(os.getenv("BATCH_RETRY_ATTEMPTS", "3"))
    BATCH_RETRY_BACKOFFS: str = os.getenv("BATCH_RETRY_BACKOFFS", "1,2,4")
    SHUTDOWN_TIMEOUT_SEC: int = int(os.getenv("SHUTDOWN_TIMEOUT_SEC", "30"))
    MAX_QUEUE_SIZE: int = int(os.getenv("MAX_QUEUE_SIZE", "5000"))
    
    # Cache settings
    CACHE_TTL_MIN: int = int(os.getenv("CACHE_TTL_MIN", "2880"))
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE", "10000"))
    
    # Trend settings
    TREND_ARCHIVE_THRESHOLD_DAYS: int = int(os.getenv("TREND_ARCHIVE_THRESHOLD_DAYS", "3"))
    
    # Monitoring settings
    ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "9090"))
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_JSON_LOGS: bool = os.getenv("ENABLE_JSON_LOGS", "true").lower() == "true"
    
    @classmethod
    def get_batch_retry_backoffs(cls) -> list[float]:
        """Parse BATCH_RETRY_BACKOFFS as list of floats."""
        backoffs_str = cls.BATCH_RETRY_BACKOFFS
        return [float(x.strip()) for x in backoffs_str.split(",")]
    
    @classmethod
    def validate_sim_speed_factor(cls) -> None:
        """Validate SIM_SPEED_FACTOR is in reasonable range."""
        if not (0.1 <= cls.SIM_SPEED_FACTOR <= 1000.0):
            raise ValueError(
                f"SIM_SPEED_FACTOR must be between 0.1 and 1000, got {cls.SIM_SPEED_FACTOR}"
            )
    
    @classmethod 
    def get_batch_timeout_seconds(cls) -> float:
        """Calculate batch timeout in real seconds based on speed factor."""
        return 60.0 / cls.SIM_SPEED_FACTOR


# Global settings instance
settings = Settings()

# Validate critical settings on import
settings.validate_sim_speed_factor() 