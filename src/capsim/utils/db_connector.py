import psycopg2
from psycopg2.extensions import register_adapter, AsIs
from typing import Optional, Dict
from uuid import UUID
from capsim.config.db import get_db_params

def adapt_uuid(uuid_obj):
    return AsIs(f"'{uuid_obj}'")

register_adapter(UUID, adapt_uuid)

def get_db_connection():
    """
    Establishes a connection to the PostgreSQL database.
    """
    try:
        params = get_db_params()
        conn = psycopg2.connect(**params)
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None 