"""Evidence strength -> heuristic likelihood ratio.

strength s in [0, 1] for ONE evidence item and ONE claim:
    s = p_stance * (0.4 + 0.6 * directness) * (0.5 + 0.5 * temporal_relevance)
        * reliability(source, claim) * (0.5 + 0.5 * extraction_confidence)

p_stance is the entailment (or contradiction) probability, itself a fixed mapping of the judge's
categorical label. The bucket of s selects a configured likelihood ratio. Claim importance does
not appear anywhere in this module, on purpose.
"""

from __future__ import annotations

import math

from ..config import Heuristics
from ..models import Evidence


def evidence_strength(e: Evidence, reliability: float) -> float:
    if e.stance == "supports":
        p = e.entailment_probability
    elif e.stance == "contradicts":
        p = e.contradiction_probability
    else:
        return 0.0
    s = p * (0.4 + 0.6 * e.directness) * (0.5 + 0.5 * e.temporal_relevance) * reliability * (0.5 + 0.5 * e.extraction_confidence)
    return round(max(0.0, min(1.0, s)), 4)


def bucket(strength: float, h: Heuristics) -> str:
    for threshold, name in h.strength_buckets:
        if strength >= threshold:
            return name
    return "neutral"


def likelihood_ratio(e: Evidence, strength: float, h: Heuristics) -> tuple[float, str]:
    name = bucket(strength, h)
    if name == "neutral" or e.stance in ("neutral", "qualifies"):
        return 1.0, "neutral"
    label = f"{name}_{'support' if e.stance == 'supports' else 'contradiction'}"
    return h.likelihood_ratios[label], label


def log_odds(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def from_log_odds(x: float) -> float:
    return 1 / (1 + math.exp(-x))
