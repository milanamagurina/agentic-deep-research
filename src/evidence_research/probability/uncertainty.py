"""Evidence sufficiency, uncertainty, research priority and status labels (sections 26-29).

Three separate dimensions per claim/hypothesis:
  truth posterior      P(claim | evidence)   - bayesian.py
  evidence sufficiency how much independent, primary, direct evidence exists (here); for hypotheses
                       0.5 x requirement coverage + 0.5 x sufficiency of the weakest accepted premise
  inference validity   verifier scores of accepted inferences (hypotheses only)
"""

from __future__ import annotations

from ..models import ClaimStatus, EvidenceStatus, StopReason


def claim_sufficiency(independent_roots: int, has_primary: bool, max_directness: float) -> float:
    """1 root -> 0.5, 2 -> 0.75, 3 -> 0.875 (times primary and directness factors)."""
    if independent_roots <= 0:
        return 0.0
    roots = 1 - 0.5 ** independent_roots
    return round(roots * (0.7 + 0.3 * has_primary) * (0.5 + 0.5 * max_directness), 4)


def uncertainty(p: float) -> float:
    """Highest at p = 0.5, zero at 0 or 1."""
    return round(1 - abs(2 * p - 1), 4)


def research_priority(importance: float, p: float, impact: float, searchability: float) -> float:
    """Heuristic expected information value. Not formal information theory."""
    return round(importance * uncertainty(p) * impact * searchability, 4)


def classify_claim(p: float, sufficiency: float, contested: bool, min_conf: float, min_suff: float) -> ClaimStatus:
    if contested:
        return ClaimStatus.CONTESTED
    if p <= 0.2 and sufficiency >= 0.5:
        return ClaimStatus.REFUTED
    if p >= min_conf and sufficiency >= min_suff:
        return ClaimStatus.SUPPORTED
    if p >= 0.6:
        return ClaimStatus.LIKELY
    return ClaimStatus.INSUFFICIENT


def classify_hypothesis(p: float, sufficiency: float, min_conf: float, min_suff: float) -> str:
    if p <= 0.15 and sufficiency >= 0.4:
        return "rejected"
    if sufficiency < 0.3:
        return "insufficient"
    if p >= min_conf and sufficiency >= min_suff:
        return "supported"
    if p < 0.4:
        return "weakened"
    return "active"


def overall_status(lead_p: float, lead_suff: float, contested: bool, stop: StopReason | None, min_conf: float, min_suff: float) -> EvidenceStatus:
    if lead_suff < 0.35:
        return EvidenceStatus.UNRESOLVABLE_WITH_PUBLIC_DATA if stop is StopReason.UNRESOLVABLE else EvidenceStatus.INSUFFICIENT_EVIDENCE
    if contested and lead_p < min_conf:
        return EvidenceStatus.CONTESTED
    if lead_p >= min_conf and lead_suff >= min_suff:
        return EvidenceStatus.SUPPORTED
    if lead_p >= 0.6:
        return EvidenceStatus.LIKELY
    if lead_p <= 0.2:
        return EvidenceStatus.REFUTED
    return EvidenceStatus.CONTESTED if contested else EvidenceStatus.INSUFFICIENT_EVIDENCE
