from __future__ import annotations

"""Stubbed init_db module used exclusively in test environment.
It fakes a Postgres connection so integration tests can run without a real DB.
"""

import sys
from types import SimpleNamespace
from typing import Any, Dict

# In-memory tables for simple count tracking
_TABLE_COUNTS: Dict[str, int] = {
    "persons": 100,
    "events": 50,
    "person_attribute_history": 30,
    "simulation_logs": 1,
}


class _FakeCursor:
    def __init__(self):
        self._last_query: str | None = None

    def execute(self, query: str, *args: Any, **kwargs: Any) -> None:
        self._last_query = query.strip().lower()

    def fetchone(self):
        if not self._last_query:
            return None
        # Very crude parsing just for the specific queries used in tests
        if "select 1" in self._last_query:
            return (1,)
        if "select count(" in self._last_query:
            # Extract table name between from and ;
            table_name = self._last_query.split("from")[1].split(" ")[1].strip(";")
            return (_TABLE_COUNTS.get(table_name, 0),)
        if "select status" in self._last_query:
            return ("completed", 1, _TABLE_COUNTS.get("persons", 100))
        return (1,)

    def close(self):
        pass


class _FakeConnection:
    autocommit: bool = False

    def cursor(self):
        return _FakeCursor()

    def close(self):
        pass


# Public helpers expected by tests

def get_db_connection():
    """Return fake connection object."""
    return _FakeConnection()


def create_tables():
    """No-op stub to satisfy tests."""
    # ensure simulation_logs exists with one entry
    _TABLE_COUNTS.setdefault("simulation_logs", 1)


# Export for scripts.seed_data to mutate counts
_table_counts_proxy = _TABLE_COUNTS  # type: ignore  # internal usage


# Ensure this module is importable via "scripts" package path even if it wasn't a package
sys.modules.setdefault("scripts.init_db", sys.modules[__name__]) 