#!/usr/bin/env python3
"""
🌍 CAPSIM Environment Switcher

Utility for switching between development and production environments.
Updates environment variables and validates configuration.
"""

import os
import sys
import shutil
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load .env file from the project root
project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=project_root / ".env")

from capsim.common.environment import EnvironmentManager


class EnvironmentSwitcher:
    """Utility for switching between environments."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.env_manager = EnvironmentManager()
        
    def current_status(self):
        """Show current environment status."""
        print("🌍 CAPSIM Environment Status")
        print("=" * 40)
        print(f"Current environment: {self.env_manager.get_current_environment()}")
        print(f"Project root: {self.project_root}")
        print(f"Active .env file: {self.env_manager.get_env_file_path()}")
        
        # Check if files exist
        env_files = {
            "development": self.project_root / ".env",
            "production": self.project_root / ".env.production"
        }
        
        print("\n📁 Environment Files:")
        for env, path in env_files.items():
            status = "✅ EXISTS" if path.exists() else "❌ MISSING"
            print(f"  {env}: {status} - {path}")
            
        # Database config
        print("\n🗄️ Database Configuration:")
        db_config = self.env_manager.get_database_config()
        print(f"  Host: {db_config.get('POSTGRES_HOST', 'unknown')}")
        print(f"  Port: {db_config.get('POSTGRES_PORT', 'unknown')}")
        print(f"  Database: {db_config.get('POSTGRES_DB', 'unknown')}")
        print(f"  User: {db_config.get('POSTGRES_USER', 'unknown')}")
        
    def switch_to(self, target_env: str):
        """Switch to target environment."""
        if target_env not in self.env_manager.SUPPORTED_ENVIRONMENTS:
            print(f"❌ Unsupported environment: {target_env}")
            print(f"Supported: {', '.join(self.env_manager.SUPPORTED_ENVIRONMENTS)}")
            return False
            
        target_file = self.project_root / f".env.{target_env}" if target_env != "development" else self.project_root / ".env"
        
        if not target_file.exists():
            print(f"❌ Environment file not found: {target_file}")
            if target_env == "production":
                print("💡 Hint: Create .env.production file with production settings")
            return False
            
        # Update ENVIRONMENT variable in .env
        self._update_environment_variable("development", target_env)
        
        # If switching to production, optionally copy production settings
        if target_env == "production":
            choice = input("📋 Copy production settings to .env? (y/N): ").lower().strip()
            if choice == 'y':
                self._copy_production_settings()
        
        print(f"✅ Switched to {target_env} environment")
        print("🔄 Please restart your application for changes to take effect")
        return True
        
    def _update_environment_variable(self, current_env: str, target_env: str):
        """Update ENVIRONMENT variable in .env file."""
        env_file = self.project_root / ".env"
        
        if not env_file.exists():
            print(f"❌ Main .env file not found: {env_file}")
            return
            
        # Read current content
        lines = env_file.read_text().splitlines()
        
        # Update ENVIRONMENT line
        updated_lines = []
        environment_found = False
        
        for line in lines:
            if line.startswith("ENVIRONMENT="):
                updated_lines.append(f"ENVIRONMENT={target_env}")
                environment_found = True
                print(f"📝 Updated ENVIRONMENT={target_env}")
            else:
                updated_lines.append(line)
                
        # Add ENVIRONMENT if not found
        if not environment_found:
            # Insert after header comments
            insert_pos = 0
            for i, line in enumerate(updated_lines):
                if not line.startswith("#") and line.strip():
                    insert_pos = i
                    break
            updated_lines.insert(insert_pos, f"ENVIRONMENT={target_env}")
            print(f"➕ Added ENVIRONMENT={target_env}")
            
        # Write back
        env_file.write_text('\n'.join(updated_lines) + '\n')
        
    def _copy_production_settings(self):
        """Copy essential production settings to main .env file."""
        prod_file = self.project_root / ".env.production"
        main_file = self.project_root / ".env"
        
        if not prod_file.exists():
            print("❌ .env.production file not found")
            return
            
        # Read production settings
        prod_lines = prod_file.read_text().splitlines()
        main_lines = main_file.read_text().splitlines()
        
        # Extract production DATABASE_URL and POSTGRES_* settings
        prod_vars = {}
        for line in prod_lines:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                if key.strip().startswith(('DATABASE_URL', 'POSTGRES_')):
                    prod_vars[key.strip()] = value.strip()
        
        # Update main .env with production vars
        updated_lines = []
        updated_vars = set()
        
        for line in main_lines:
            if '=' in line and not line.strip().startswith('#'):
                key, _ = line.split('=', 1)
                key = key.strip()
                if key in prod_vars:
                    updated_lines.append(f"{key}={prod_vars[key]}")
                    updated_vars.add(key)
                    print(f"📝 Updated {key} with production value")
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        # Add missing production vars
        for key, value in prod_vars.items():
            if key not in updated_vars:
                updated_lines.append(f"{key}={value}")
                print(f"➕ Added {key} with production value")
        
        # Write back
        main_file.write_text('\n'.join(updated_lines) + '\n')
        print("✅ Production settings copied to .env")
        
    def validate_environment(self, env_name: str = None):
        """Validate environment configuration."""
        if env_name:
            # Temporarily switch for validation
            original_env = os.environ.get("ENVIRONMENT")
            os.environ["ENVIRONMENT"] = env_name
            self.env_manager = EnvironmentManager()
        
        print(f"🔍 Validating {env_name or 'current'} environment...")
        
        try:
            # Test database config
            db_config = self.env_manager.get_database_config()
            
            required_vars = ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER"]
            missing_vars = [var for var in required_vars if not db_config.get(var)]
            
            if missing_vars:
                print(f"❌ Missing required variables: {', '.join(missing_vars)}")
                return False
            
            # Test database URL construction
            try:
                fallback_url = self.env_manager.get_fallback_database_url()
                print(f"✅ Database URL: {fallback_url[:50]}...")
            except Exception as e:
                print(f"❌ Database URL construction failed: {e}")
                return False
                
            print("✅ Environment validation passed")
            return True
            
        except Exception as e:
            print(f"❌ Environment validation failed: {e}")
            return False
        finally:
            # Restore original environment
            if env_name and original_env:
                os.environ["ENVIRONMENT"] = original_env
            elif env_name:
                os.environ.pop("ENVIRONMENT", None)


def main():
    """Main CLI interface."""
    switcher = EnvironmentSwitcher()
    
    if len(sys.argv) == 1:
        # Show current status
        switcher.current_status()
        return
    
    command = sys.argv[1].lower()
    
    if command == "status":
        switcher.current_status()
        
    elif command == "switch":
        if len(sys.argv) < 3:
            print("❌ Usage: python switch_environment.py switch <development|production>")
            return
        target = sys.argv[2].lower()
        switcher.switch_to(target)
        
    elif command == "validate":
        env_name = sys.argv[2].lower() if len(sys.argv) > 2 else None
        switcher.validate_environment(env_name)
        
    elif command == "help":
        print("""🌍 CAPSIM Environment Switcher

Usage:
  python switch_environment.py                    # Show current status
  python switch_environment.py status             # Show current status
  python switch_environment.py switch <env>       # Switch to environment
  python switch_environment.py validate [<env>]   # Validate environment
  python switch_environment.py help               # Show this help

Examples:
  python switch_environment.py switch production  # Switch to production
  python switch_environment.py switch development # Switch to development
  python switch_environment.py validate production # Validate production config
""")
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'help' for usage information")


if __name__ == "__main__":
    main()