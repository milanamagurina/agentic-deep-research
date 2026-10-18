"""Candidate ranking and selection before (expensive) extraction. Deterministic."""

from __future__ import annotations

from ..evidence.source_classifier import classify_domain
from .tavily_client import SearchHit
from .url_normalizer import canonicalize, registrable_domain

_TYPE_BONUS = {"regulator": 0.35, "academic": 0.3, "official_statistics": 0.35, "company": 0.2,
               "major_news": 0.15, "trade_press": 0.05, "press_wire": -0.05, "review_site": 0.1,
               "blog": -0.1, "social": -0.2, "other": 0.0}


def rank_hits(hits: list[SearchHit], seen_canonical: set[str], key_entities: list[str]) -> list[tuple[float, SearchHit, str]]:
    """Return (score, hit, reason) best-first, dropping already-known URLs and duplicates."""
    out: list[tuple[float, SearchHit, str]] = []
    batch: set[str] = set()
    domain_count: dict[str, int] = {}
    for hit in hits:
        canon = canonicalize(hit.url)
        if canon in seen_canonical or canon in batch:
            continue
        batch.add(canon)
        stype = classify_domain(hit.url, key_entities)
        domain = registrable_domain(hit.url)
        # Diversity: later hits from an already-selected publisher rank lower.
        diversity_penalty = 0.15 * domain_count.get(domain, 0)
        domain_count[domain] = domain_count.get(domain, 0) + 1
        score = (hit.score or 0.5) + _TYPE_BONUS.get(stype, 0.0) - diversity_penalty
        out.append((round(score, 3), hit, f"{stype}, tavily={hit.score}, diversity_penalty={diversity_penalty:.2f}"))
    return sorted(out, key=lambda t: -t[0])
