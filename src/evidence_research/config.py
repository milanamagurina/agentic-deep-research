"""Configuration: credentials, budgets, thresholds and every scoring heuristic in one place.

All numeric heuristics (likelihood ratios, source priors, sufficiency weights) live here so
they are visible, documented and tunable. None of them are empirically calibrated.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class ConfigError(RuntimeError):
    """Missing or invalid configuration. The message never contains secret values."""


class Depth(str, Enum):
    FAST = "fast"
    STANDARD = "standard"
    DEEP = "deep"


class Budget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_iterations: int = 5
    max_search_queries: int = 20
    max_extracted_sources: int = 30
    max_model_calls: int = 50


DEPTH_BUDGETS: dict[Depth, Budget] = {
    Depth.FAST: Budget(max_iterations=3, max_search_queries=10, max_extracted_sources=10, max_model_calls=40),
    Depth.STANDARD: Budget(max_iterations=5, max_search_queries=18, max_extracted_sources=20, max_model_calls=70),
    Depth.DEEP: Budget(max_iterations=7, max_search_queries=30, max_extracted_sources=36, max_model_calls=110),
}


class Heuristics(BaseModel):
    """Transparent implementation heuristics. Change them here, nowhere else."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Heuristic evidence likelihood ratios, by strength bucket (section 24).
    likelihood_ratios: dict[str, float] = Field(default_factory=lambda: {
        "very_strong_support": 8.0,
        "strong_support": 4.0,
        "moderate_support": 2.0,
        "weak_support": 1.25,
        "neutral": 1.0,
        "weak_contradiction": 0.8,
        "moderate_contradiction": 0.5,
        "strong_contradiction": 0.25,
        "very_strong_contradiction": 0.125,
    })
    # Evidence strength s in [0, 1] -> bucket. Checked from the top down.
    strength_buckets: list[tuple[float, str]] = Field(default_factory=lambda: [
        (0.70, "very_strong"), (0.50, "strong"), (0.30, "moderate"), (0.12, "weak"),
    ])
    # Categorical judge output -> entailment / contradiction probability. The model never gives numbers.
    stance_strength_probability: dict[str, float] = Field(default_factory=lambda: {
        "explicit": 0.95, "strong": 0.80, "partial": 0.60, "weak": 0.40,
    })
    # Contribution of further evidence from the same provenance cluster (section 25).
    dependent_evidence_discount: float = 0.15
    # Directness cap for evidence that only REPORTS someone else's statement (section 22).
    reported_speech_directness: float = 0.35
    claim_prior: float = 0.5
    hypothesis_prior_floor: float = 0.05
    # Lineage: a pair is "dependent" above this dependency probability.
    lineage_threshold: float = 0.5
    # Categorical verifier verdict -> inference validity score.
    inference_scores: dict[str, float] = Field(default_factory=lambda: {
        "valid": 0.9, "plausible": 0.65, "weak": 0.35, "invalid": 0.05,
    })
    inference_accept_threshold: float = 0.6
    # Decision impact category -> number (heuristic expected information value, section 27).
    impact_scores: dict[str, float] = Field(default_factory=lambda: {"low": 0.3, "medium": 0.6, "high": 1.0})
    # How likely more public search is to close a gap of this type.
    gap_searchability: dict[str, float] = Field(default_factory=lambda: {
        "NO_PRIMARY_SOURCE": 0.7,
        "NO_INDEPENDENT_SOURCE": 0.8,
        "CONTRADICTORY_EVIDENCE": 0.7,
        "TEMPORAL_CONFLICT": 0.6,
        "INSUFFICIENT_SAMPLE": 0.5,
        "MISSING_REQUIRED_DIMENSION": 0.9,
        "WEAK_INFERENCE": 0.8,
        "SOURCE_DEPENDENCE": 0.8,
        "OUTDATED_EVIDENCE": 0.7,
        "NO_REPLICATION": 0.8,
        "FAILED_REPLICATION": 0.6,
        "MISSING_METHOD_INFORMATION": 0.5,
        "UNVERIFIED_EXTRACTION": 0.6,
    })
    # Convergence stop rule (section 29).
    convergence_epsilon: float = 0.03
    convergence_stable_iterations: int = 2
    # A gap researched this many times with no new independent evidence is unresolvable.
    gap_attempts_before_unresolvable: int = 2


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nebius_api_key: SecretStr | None = Field(default=None, repr=False)
    tavily_api_key: SecretStr | None = Field(default=None, repr=False)
    nebius_base_url: str = "https://api.tokenfactory.nebius.com/v1"
    nebius_model: str = "MiniMaxAI/MiniMax-M3"
    nebius_reasoning_model: str | None = None

    budget: Budget = Field(default_factory=Budget)
    min_claim_confidence: float = 0.75
    min_evidence_sufficiency: float = 0.70
    heuristics: Heuristics = Field(default_factory=Heuristics)

    llm_timeout_s: float = 180.0
    llm_max_tokens: int = 8192  # reasoning models spend output tokens on hidden reasoning before the JSON
    llm_max_retries: int = 3
    llm_concurrency: int = 4
    tavily_concurrency: int = 4
    search_max_results: int = 8
    extract_per_round: int = 6
    data_dir: Path = Path("data")

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Settings":
        e = dict(os.environ if env is None else env)

        def num(name: str, default: float, kind: type = int):
            raw = e.get(name)
            if raw in (None, ""):
                return default
            try:
                return kind(raw)
            except ValueError as exc:
                raise ConfigError(f"{name} must be a {kind.__name__}, got {raw!r}") from exc

        budget = Budget(
            max_iterations=num("MAX_RESEARCH_ITERATIONS", 5),
            max_search_queries=num("MAX_SEARCH_QUERIES", 20),
            max_extracted_sources=num("MAX_EXTRACTED_SOURCES", 30),
            max_model_calls=num("MAX_MODEL_CALLS", 50),
        )
        return cls(
            nebius_api_key=SecretStr(e["NEBIUS_API_KEY"]) if e.get("NEBIUS_API_KEY") else None,
            tavily_api_key=SecretStr(e["TAVILY_API_KEY"]) if e.get("TAVILY_API_KEY") else None,
            nebius_base_url=e.get("NEBIUS_BASE_URL") or "https://api.tokenfactory.nebius.com/v1",
            nebius_model=e.get("NEBIUS_MODEL") or "MiniMaxAI/MiniMax-M3",
            nebius_reasoning_model=e.get("NEBIUS_REASONING_MODEL") or None,
            budget=budget,
            min_claim_confidence=num("MIN_CLAIM_CONFIDENCE", 0.75, float),
            min_evidence_sufficiency=num("MIN_EVIDENCE_SUFFICIENCY", 0.70, float),
            heuristics=Heuristics(dependent_evidence_discount=num("DEPENDENT_EVIDENCE_DISCOUNT", 0.15, float)),
            data_dir=Path(e.get("DATA_DIR") or "data"),
            llm_max_tokens=num("LLM_MAX_TOKENS", 8192),
        )

    def require_live(self) -> None:
        """Fail fast, naming (never printing) what is missing, before any live run."""
        missing = [n for n, v in (("NEBIUS_API_KEY", self.nebius_api_key), ("TAVILY_API_KEY", self.tavily_api_key)) if v is None]
        if missing:
            raise ConfigError(
                f"Missing {', '.join(missing)}. Copy .env.example to .env and fill it in, "
                "or run the offline synthetic demo with --demo."
            )
        if not self.nebius_base_url.startswith("https://"):
            raise ConfigError("NEBIUS_BASE_URL must be an https:// URL.")

    def with_depth(self, depth: Depth) -> "Settings":
        """Depth presets never raise a budget above what the environment allows."""
        preset = DEPTH_BUDGETS[depth]
        capped = Budget(**{k: min(getattr(preset, k), getattr(self.budget, k)) for k in Budget.model_fields})
        return self.model_copy(update={"budget": capped})


def load_dotenv_if_present() -> None:
    """Load .env unless EVIDENCE_NO_DOTENV=1 (tests, CI). Real environment variables always win."""
    if os.environ.get("EVIDENCE_NO_DOTENV") == "1":
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(override=False)
