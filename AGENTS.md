# AGENTS.md - Development Guide for CAPSIM 2.0

## Build/Test/Lint Commands
- **Test all**: `make test` or `python -m pytest tests/ -v --tb=short`
- **Test single file**: `python -m pytest tests/test_filename.py -v`
- **Test single function**: `python -m pytest tests/test_filename.py::test_function_name -v`
- **Lint**: `make lint` (runs ruff + mypy) or `python -m ruff check . --select ALL && python -m mypy --strict capsim`
- **Format**: `python -m black capsim/ tests/` and `python -m isort capsim/ tests/`

## Code Style Guidelines
- **Imports**: Standard library first, third-party, then local imports. Use `from typing import TYPE_CHECKING` for circular imports
- **Types**: Use type hints everywhere. Pydantic models for data validation, dataclasses for domain objects
- **Naming**: snake_case for variables/functions, PascalCase for classes, UPPER_CASE for constants
- **Docstrings**: Use triple quotes with brief description. Include Russian comments where domain-specific
- **Error handling**: Use structured logging with `structlog.get_logger(__name__)`, raise specific exceptions
- **Database**: Use SQLAlchemy 2.0 syntax, async/await patterns, repository pattern in `capsim/db/repositories.py`
- **Configuration**: Load from YAML files in `config/`, use environment variables for secrets
- **Testing**: Use pytest with async markers, separate unit/integration tests, mock external dependencies

## Project Structure
- `capsim/domain/` - Core business logic (Person, Trend, Events)
- `capsim/engine/` - Simulation engine and context
- `capsim/db/` - Database models and repositories  
- `capsim/api/` - FastAPI REST endpoints
- `capsim/cli/` - Command-line interface
- `capsim/common/` - Shared utilities (logging, metrics, settings)