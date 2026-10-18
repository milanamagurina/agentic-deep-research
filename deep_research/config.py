"""Runtime settings, read once from the environment.

Credentials are held as ``SecretStr`` so they never show up in ``repr()``,
logs or tracebacks. Nothing in this package prints them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import SecretStr

DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1"
DEFAULT_MODEL = "MiniMaxAI/MiniMax-M3"
DEFAULT_QUESTION = (
    "Which grid-scale energy storage technologies besides lithium-ion reached "
    "commercial deployment by 2026, and what evidence is there on their cost "
    "per kWh?"
)


class ConfigError(RuntimeError):
    """Raised when required settings are missing. Message never holds secrets."""


@dataclass(frozen=True)
class Settings:
    nebius_api_key: SecretStr = field(repr=False)
    tavily_api_key: SecretStr = field(repr=False)
    nebius_base_url: str = DEFAULT_BASE_URL
    lead_model: str = DEFAULT_MODEL
    worker_model: str = DEFAULT_MODEL
    checker_model: str = DEFAULT_MODEL
    max_parallel_researchers: int = 4
    recursion_limit: int = 250
    runs_dir: Path = Path("runs")

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        env = dict(os.environ if env is None else env)
        missing = [k for k in ("NEBIUS_API_KEY", "TAVILY_API_KEY") if not env.get(k)]
        if missing:
            raise ConfigError(
                "Missing required environment variable(s): "
                + ", ".join(missing)
                + ". Export them or put them in a .env file (see .env.example)."
            )
        lead = env.get("NEBIUS_MODEL") or DEFAULT_MODEL
        return cls(
            nebius_api_key=SecretStr(env["NEBIUS_API_KEY"]),
            tavily_api_key=SecretStr(env["TAVILY_API_KEY"]),
            nebius_base_url=env.get("NEBIUS_BASE_URL") or DEFAULT_BASE_URL,
            lead_model=lead,
            # Roles fall back to the lead model, so one variable is enough.
            worker_model=env.get("NEBIUS_WORKER_MODEL") or lead,
            checker_model=env.get("NEBIUS_CHECKER_MODEL") or lead,
            max_parallel_researchers=int(env.get("MAX_PARALLEL_RESEARCHERS") or 4),
            recursion_limit=int(env.get("RECURSION_LIMIT") or 250),
            runs_dir=Path(env.get("RUNS_DIR") or "runs"),
        )
