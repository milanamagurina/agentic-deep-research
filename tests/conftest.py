import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evidence_research.config import Settings  # noqa: E402
from evidence_research.models import Claim, Evidence, Source, stable_id  # noqa: E402
from evidence_research.retrieval.url_normalizer import canonicalize  # noqa: E402

TODAY = date(2026, 10, 18)


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings.from_env({"DATA_DIR": str(tmp_path / "data")})


def make_source(url: str, text: str = "", published: date | None = None, title: str = "", publisher: str = "") -> Source:
    return Source(id=stable_id("S", url), url=url, canonical_url=canonicalize(url), title=title, publisher=publisher,
                  published_at=published, raw_text=text, extracted=True)


def make_claim(text: str = "Acme FY2025 revenue increased 70% YoY", category: str = "self_reported_metric", importance: float = 0.5) -> Claim:
    return Claim(id=stable_id("C", text), subject="Acme", predicate="FY2025 revenue growth", object="70%",
                 natural_language=text, category=category, importance=importance)


def make_evidence(source: Source, claim: Claim, stance: str = "supports", strength: float = 0.95, directness: float = 1.0) -> Evidence:
    return Evidence(id=stable_id("E", source.id, claim.id, stance), source_id=source.id, claim_id=claim.id,
                    exact_excerpt="excerpt", stance=stance,
                    entailment_probability=strength if stance == "supports" else 0.05,
                    contradiction_probability=strength if stance == "contradicts" else 0.05,
                    directness=directness, temporal_relevance=1.0, extraction_confidence=0.9)
