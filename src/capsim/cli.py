import typer
import yaml
from pathlib import Path
from typing import Optional
from .models.base import SimulationConfig
from .core.engine import SimulationEngine
from .actions.education import EducationAction
from .actions.work import WorkAction

app = typer.Typer()

def load_config(config_path: Path) -> SimulationConfig:
    """Load simulation configuration from YAML file"""
    with open(config_path) as f:
        config_data = yaml.safe_load(f)
    return SimulationConfig(**config_data)

@app.command()
def run_simulation(
    config_path: Path = typer.Option(
        ...,
        help="Path to simulation configuration file"
    ),
    output_path: Optional[Path] = typer.Option(
        None,
        help="Path to save simulation results"
    )
):
    """Run the simulation with the given configuration"""
    # Load configuration
    config = load_config(config_path)
    
    # Initialize simulation engine
    engine = SimulationEngine(config)
    
    # Add some default actions
    engine.add_action(EducationAction(
        level="Bachelor",
        cost=50000.0,
        income_boost=2000.0,
        duration_days=365
    ))
    
    engine.add_action(WorkAction(
        job_title="Junior Developer",
        base_salary=3000.0,
        experience_required=0
    ))
    
    # Run simulation
    engine.run()
    
    if output_path:
        # TODO: Implement results saving
        typer.echo(f"Results saved to {output_path}")

@app.command()
def validate_config(
    config_path: Path = typer.Option(
        ...,
        help="Path to simulation configuration file"
    )
):
    """Validate the simulation configuration file"""
    try:
        config = load_config(config_path)
        typer.echo("Configuration is valid!")
    except Exception as e:
        typer.echo(f"Configuration is invalid: {str(e)}", err=True)
        raise typer.Exit(1)

if __name__ == "__main__":
    app() 