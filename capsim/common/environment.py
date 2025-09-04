"""
Environment management system for CAPSIM.
Provides environment-aware configuration loading and switching between dev/production.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class EnvironmentManager:
    """Manages environment configuration and switching."""
    
    SUPPORTED_ENVIRONMENTS = ["development", "production"]
    DEFAULT_ENVIRONMENT = "development"
    
    def __init__(self):
        self.current_env = self.get_current_environment()
        self.project_root = self._find_project_root()
        
    def get_current_environment(self) -> str:
        """Get current environment from ENVIRONMENT variable."""
        env = os.getenv("ENVIRONMENT", self.DEFAULT_ENVIRONMENT).lower()
        if env not in self.SUPPORTED_ENVIRONMENTS:
            logger.warning(f"Unknown environment '{env}', falling back to '{self.DEFAULT_ENVIRONMENT}'")
            return self.DEFAULT_ENVIRONMENT
        return env
        
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.current_env == "production"
        
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.current_env == "development"
        
    def _find_project_root(self) -> Path:
        """Find project root directory (contains .env files)."""
        current = Path(__file__).parent
        while current != current.parent:
            if (current / ".env").exists():
                return current
            current = current.parent
        return Path.cwd()
        
    def get_env_file_path(self) -> Path:
        """Get path to appropriate .env file based on environment."""
        if self.is_production():
            env_file = self.project_root / ".env.production"
            if not env_file.exists():
                logger.error(f"Production environment file not found: {env_file}")
                # Fallback to .env for compatibility
                return self.project_root / ".env"
            return env_file
        else:
            return self.project_root / ".env"
            
    def get_database_config(self) -> Dict[str, str]:
        """Get database configuration based on current environment."""
        config = {}
        
        # Primary: Use DATABASE_URL if available
        if database_url := os.getenv("DATABASE_URL"):
            config["DATABASE_URL"] = database_url
            
        if database_url_ro := os.getenv("DATABASE_URL_RO"):
            config["DATABASE_URL_RO"] = database_url_ro
            
        # Fallback: Build from individual components
        config.update({
            "POSTGRES_HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "POSTGRES_PORT": os.getenv("POSTGRES_PORT", "5432"),
            "POSTGRES_DB": os.getenv("POSTGRES_DB", "capsim_db"),
            "POSTGRES_USER": os.getenv("POSTGRES_USER", "postgres"),
            "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        })
        
        return config
        
    def get_fallback_database_url(self) -> str:
        """Get fallback database URL for scripts."""
        if self.is_production():
            # Production fallback
            fallback = os.getenv("DATABASE_URL_PRODUCTION_FALLBACK")
            if fallback:
                return fallback
                
            # Build from components
            host = os.getenv("POSTGRES_HOST", "localhost")
            port = os.getenv("POSTGRES_PORT", "5432")
            db = os.getenv("POSTGRES_DB", "capsim_db")
            user = os.getenv("CAPSIM_RW_PASSWORD", "capsim321")  # Use RW user for scripts
            password = os.getenv("CAPSIM_RW_PASSWORD", "capsim321")
            
            ssl_suffix = "?sslmode=require" if self.is_production() else ""
            return f"postgresql://{user}:{password}@{host}:{port}/{db}{ssl_suffix}"
        else:
            # Development fallback
            return "postgresql://capsim_rw:capsim321@localhost:5432/capsim_db"
            
    def log_environment_info(self):
        """Log current environment configuration for debugging."""
        logger.info(f"🌍 Environment: {self.current_env}")
        logger.info(f"📁 Project root: {self.project_root}")
        logger.info(f"⚙️ Env file: {self.get_env_file_path()}")
        
        db_config = self.get_database_config()
        logger.info(f"🗄️ Database host: {db_config.get('POSTGRES_HOST', 'unknown')}")
        logger.info(f"🗄️ Database: {db_config.get('POSTGRES_DB', 'unknown')}")


# Singleton instance
env_manager = EnvironmentManager()

# Convenience functions
def get_current_environment() -> str:
    """Get current environment name."""
    return env_manager.get_current_environment()

def is_production() -> bool:
    """Check if running in production."""
    return env_manager.is_production()

def is_development() -> bool:
    """Check if running in development."""
    return env_manager.is_development()

def get_database_config() -> Dict[str, str]:
    """Get database configuration for current environment."""
    return env_manager.get_database_config()

def get_fallback_database_url() -> str:
    """Get fallback database URL for current environment."""
    return env_manager.get_fallback_database_url()

def log_environment_info():
    """Log environment information."""
    env_manager.log_environment_info()


# Auto-log environment on import for debugging
if __name__ != "__main__":
    log_environment_info()