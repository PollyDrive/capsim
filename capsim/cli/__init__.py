"""
CLI модуль для CAPSIM.
"""

from .run_simulation import main as run_simulation_main
from .stop_simulation import main as stop_simulation_main

__all__ = ["run_simulation_main", "stop_simulation_main"]
