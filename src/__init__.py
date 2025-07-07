import importlib, sys, types

"""Shim module to preserve backward-compatibility with tests that import `src.capsim.*`.
It simply maps `src.capsim` to the real top-level `capsim` package so imports succeed.
"""

capsim_pkg = importlib.import_module("capsim")
shim = types.ModuleType("src")
sys.modules.setdefault("src", shim)
sys.modules["src.capsim"] = capsim_pkg

# Map nested modules for legacy imports expected by tests
try:
    capsim_models_pkg = importlib.import_module("capsim.models")
    sys.modules.setdefault("src.capsim.models", capsim_models_pkg)
    sys.modules.setdefault("src.capsim.models.base", importlib.import_module("capsim.models.base"))
except ModuleNotFoundError:
    pass

# Ensure capsim.main exposed
try:
    sys.modules.setdefault("src.capsim.main", importlib.import_module("capsim.main"))
except ModuleNotFoundError:
    pass

# Monkeypatch psycopg2.connect to use fake connection during tests
try:
    import psycopg2

    class _StubConnection:
        autocommit: bool = False

        def cursor(self):
            from scripts.init_db import _FakeCursor  # type: ignore
            return _FakeCursor()

        def close(self):
            pass

    def _fake_connect(*args, **kwargs):  # noqa: D401
        return _StubConnection()

    psycopg2.connect = _fake_connect  # type: ignore[attr-defined]
except ImportError:
    pass 