"""
Settings и configuration для CAPSIM симуляции.
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path
import logging

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

logger = logging.getLogger(__name__)


class ActionConfig:
    """Configuration for v1.8 action system."""
    
    def __init__(self):
        self.cooldowns = {}
        self.limits = {}
        self.effects = {}
        self.shop_weights = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from config/actions.yaml."""
        config_path = Path(__file__).parent.parent.parent / "config" / "actions.yaml"
        
        if not HAS_YAML:
            logger.warning("YAML module not available, using default action config")
            self._load_defaults()
            return
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                
            self.cooldowns = config_data.get('COOLDOWNS', {})
            self.limits = config_data.get('LIMITS', {})
            self.effects = config_data.get('EFFECTS', {})
            self.shop_weights = config_data.get('SHOP_WEIGHTS', {})
            self.night_recovery = config_data.get('NIGHT_RECOVERY', {"energy_bonus":1.2, "financial_bonus":1.0})
            
            logger.info(f"✅ ActionConfig loaded from {config_path}")
            
        except FileNotFoundError:
            logger.warning(f"⚠️ Config file not found: {config_path}, using defaults")
            self._load_defaults()
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}, using defaults")
            self._load_defaults()
    
    def _load_defaults(self):
        """Load default configuration if file not found."""
        self.cooldowns = {
            "POST_MIN": 60,
            "SELF_DEV_MIN": 30
        }
        self.limits = {
            "MAX_PURCHASES_DAY": 5
        }
        self.effects = {
            "POST": {
                "time_budget": -0.20,
                "energy_level": -0.50,
                "social_status": 0.10
            },
            "SELF_DEV": {
                "time_budget": -1.00,
                "energy_level": 0.80
            },
            "PURCHASE": {
                "L1": {
                    "financial_capability": -0.05,
                    "energy_level": 0.20
                },
                "L2": {
                    "financial_capability": -0.50,
                    "energy_level": -0.10,
                    "social_status": 0.20
                },
                "L3": {
                    "financial_capability": -2.00,
                    "energy_level": -0.15,
                    "social_status": 1.00
                }
            }
        }
        self.shop_weights = {
            "Businessman": 1.20,
            "Worker": 0.80,
            "Developer": 1.00,
            "Teacher": 0.90,
            "Doctor": 1.00,
            "Blogger": 1.05,
            "Politician": 1.15,
            "ShopClerk": 0.85,
            "Artist": 0.75,
            "SpiritualMentor": 0.80,
            "Philosopher": 0.75,
            "Unemployed": 0.60
        }
        self.night_recovery = {"energy_bonus":1.2, "financial_bonus":1.0}


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
    DECIDE_SCORE_THRESHOLD: float = float(os.getenv("DECIDE_SCORE_THRESHOLD", "0.15"))
    BASE_RATE: float = float(os.getenv("BASE_RATE", "0.1"))
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "1000")) # Увеличено с 100 до 1000
    
    # Realtime mode configuration  
    SIM_SPEED_FACTOR: float = float(os.getenv("SIM_SPEED_FACTOR", "60.0"))
    ENABLE_REALTIME: bool = os.getenv("ENABLE_REALTIME", "false").lower() == "true"
    
    # Performance settings
    BATCH_RETRY_ATTEMPTS: int = int(os.getenv("BATCH_RETRY_ATTEMPTS", "3"))
    BATCH_RETRY_BACKOFFS: str = os.getenv("BATCH_RETRY_BACKOFFS", "1,2,4")
    SHUTDOWN_TIMEOUT_SEC: int = int(os.getenv("SHUTDOWN_TIMEOUT_SEC", "30"))
    MAX_QUEUE_SIZE: int = int(os.getenv("MAX_QUEUE_SIZE", "5000"))
    BATCH_COMMIT_TIMEOUT_SEC: int = int(os.getenv("BATCH_COMMIT_TIMEOUT_SEC", "5"))
    
    # Cache settings
    CACHE_TTL_MIN: int = int(os.getenv("CACHE_TTL_MIN"))
    CACHE_MAX_SIZE: int = int(os.getenv("CACHE_MAX_SIZE"))
    
    # Trend settings
    TREND_ARCHIVE_THRESHOLD_DAYS: int = int(os.getenv("TREND_ARCHIVE_THRESHOLD_DAYS"))
    
    # Monitoring settings
    ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT"))
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL")
    ENABLE_JSON_LOGS: bool = os.getenv("ENABLE_JSON_LOGS").lower() == "true"
    
    # Docker integration
    DOCKER_ENV: bool = os.getenv("DOCKER_ENV", "false").lower() == "true"
    
    # v1.8 Action cooldowns (can override YAML config)
    POST_COOLDOWN_MIN: int = int(os.getenv("POST_COOLDOWN_MIN", "60"))
    SELF_DEV_COOLDOWN_MIN: int = int(os.getenv("SELF_DEV_COOLDOWN_MIN", "30"))
    
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

# Global action configuration instance
action_config = ActionConfig()

# Validate critical settings on import
settings.validate_sim_speed_factor() 