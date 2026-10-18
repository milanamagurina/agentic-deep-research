import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FAKE_NEBIUS_KEY = "nebius-test-key-DO-NOT-LEAK"
FAKE_TAVILY_KEY = "tvly-test-key-DO-NOT-LEAK"


@pytest.fixture
def env(monkeypatch, tmp_path):
    """Fake credentials and an isolated runs dir; real .env files are ignored."""
    for var in ("NEBIUS_MODEL", "NEBIUS_WORKER_MODEL", "NEBIUS_CHECKER_MODEL", "NEBIUS_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NEBIUS_API_KEY", FAKE_NEBIUS_KEY)
    monkeypatch.setenv("TAVILY_API_KEY", FAKE_TAVILY_KEY)
    monkeypatch.setenv("RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setattr("app._load_dotenv", lambda: None)
    return tmp_path
