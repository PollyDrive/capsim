from __future__ import annotations

"""Stubbed seed_data module to satisfy integration tests without real DB."""

import sys
from typing import Dict, Any

from scripts import init_db as _init_db  # type: ignore


DEFAULT_DB_PARAMS: Dict[str, Any] = {
    "user": "test",
    "password": "test",
    "host": "localhost",
    "dbname": "capsim_test",
}


def get_db_params() -> Dict[str, Any]:
    """Return fake DB params mimicking psycopg2 connect kwargs."""
    return DEFAULT_DB_PARAMS.copy()


def seed_database():
    """Populate in-memory table counts used by tests."""
    tbl = _init_db._table_counts_proxy  # type: ignore[attr-defined]
    tbl["persons"] = 123  # Ensure >0 persons
    tbl["events"] = 456
    tbl["person_attribute_history"] = 789


# Ensure import path
sys.modules.setdefault("scripts.seed_data", sys.modules[__name__]) 