"""
Settings и configuration для CAPSIM симуляции.
"""

import os
from typing import Optional


class Settings:
    """Centralized configuration management."""
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    DATABASE_URL_RO: str = os.getenv("DATABASE_URL_RO")
    
    def __post_init__(self):
        """Validate required environment variables."""
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is required")
        if not self.DATABASE_URL_RO:
            raise ValueError("DATABASE_URL_RO environment variable is required")
    
    # Simulation core settings  
    DECIDE_SCORE_THRESHOLD: float = float(os.getenv("DECIDE_SCORE_THRESHOLD"))
    BASE_RATE: float = float(os.getenv("BASE_RATE"))
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE"))
    
    # Realtime mode configuration  
    SIM_SPEED_FACTOR: float = float(os.getenv("SIM_SPEED_FACTOR"))
    ENABLE_REALTIME: bool = os.getenv("ENABLE_REALTIME").lower() == "true"
    
    # Performance settings
    BATCH_RETRY_ATTEMPTS: int = int(os.getenv("BATCH_RETRY_ATTEMPTS"))
    BATCH_RETRY_BACKOFFS: str = os.getenv("BATCH_RETRY_BACKOFFS")
    SHUTDOWN_TIMEOUT_SEC: int = int(os.getenv("SHUTDOWN_TIMEOUT_SEC"))
    MAX_QUEUE_SIZE: int = int(os.getenv("MAX_QUEUE_SIZE"))
    
    # Cache settings
    CACHE_TTL_MIN: int = int(os.getenv("CACHE_TTL_MIN"))
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE"))
    
    # Trend settings
    TREND_ARCHIVE_THRESHOLD_DAYS: int = int(os.getenv("TREND_ARCHIVE_THRESHOLD_DAYS"))
    
    # Monitoring settings
    ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT"))
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL")
    ENABLE_JSON_LOGS: bool = os.getenv("ENABLE_JSON_LOGS").lower() == "true"
    
    # Docker integration
    DOCKER_ENV: bool = os.getenv("DOCKER_ENV", "false").lower() == "true"
    
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