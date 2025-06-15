import configparser
from pathlib import Path
from typing import Dict, Optional

def get_db_params(filename: Path = Path('config/database.ini'), section: str = 'postgresql') -> Dict[str, str]:
    """
    Parses the database configuration file and returns a dictionary of parameters.
    """
    if not filename.exists():
        raise FileNotFoundError(f"Database config file not found: {filename}")

    parser = configparser.ConfigParser()
    parser.read(filename)

    db_params = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db_params[param[0]] = param[1]
    else:
        raise Exception(f'Section {section} not found in the {filename} file')

    return db_params 