import pytest
from pathlib import Path
from capsim.main import load_config
from capsim.models.base import SimulationConfig

def test_config_loads_successfully():
    """
    This test verifies that the main config file can be loaded and parsed
    by the Pydantic model without errors.
    """
    config_path = Path("config/simulation.yaml")
    assert config_path.exists(), "The main configuration file is missing."

    try:
        config = load_config(config_path)
    except Exception as e:
        pytest.fail(f"Configuration loading failed with a critical error: {e}")

    assert isinstance(config, SimulationConfig)
    assert hasattr(config, 'simulation_parameters'), "Config object is missing 'simulation_parameters'"
    assert hasattr(config, 'actions'), "Config object is missing 'actions'"
    assert hasattr(config, 'professions'), "Config object is missing 'professions'"
    assert len(config.actions) > 0, "No actions were loaded from the config" 