"""Answer confidence (sections 5-6).

The public output exposes ONE number: how strongly the currently verified evidence supports the
answer we are giving. It is a heuristic, NOT a calibrated truth probability.

It is computed ONLY from the claims the final answer actually uses — never averaged over every
claim or gap in the graph — as an importance-weighted mean of their posteriors, then penalized for:
  * unresolved contradiction among the used claims,
  * source dependence among them (few independent roots),
  * weak inference the answer leans on,
  * lack of independent evidence overall.
"""

from __future__ import annotations

from dataclasses import dataclass

from .engine import BeliefState
from ..graph.evidence_graph import EvidenceGraph


@dataclass
class ConfidenceBreakdown:
    confidence: float
    base: float                 # importance-weighted mean posterior of used claims
    mean_sufficiency: float
    independence: float         # 0..1, from independent roots behind used claims
    contested: bool
    inference_validity: float | None
    used_claims: int
    penalties: list[str]


def answer_confidence(graph: EvidenceGraph, beliefs: BeliefState, used_claim_ids: list[str],
                      inference_validity: float | None = None) -> ConfidenceBreakdown:
    claims = [graph.claims[c] for c in dict.fromkeys(used_claim_ids) if c in graph.claims]
    if not claims:
        return ConfidenceBreakdown(0.0, 0.0, 0.0, 0.0, False, inference_validity, 0, ["no claims used in the answer"])

    weights = [max(0.1, c.importance) for c in claims]
    wsum = sum(weights)
    base = sum(w * c.truth_probability for w, c in zip(weights, claims)) / wsum
    mean_suff = sum(w * c.evidence_sufficiency for w, c in zip(weights, claims)) / wsum

    beliefs_for = [beliefs.claims.get(c.id) for c in claims]
    contested = any(b.contested for b in beliefs_for if b)
    roots = [min(b.independent_roots, 2) for b in beliefs_for if b]
    independence = (sum(roots) / len(roots) / 2) if roots else 0.0  # 1.0 when every used claim has >=2 roots

    penalties: list[str] = []
    conf = base
    conf *= 0.6 + 0.4 * mean_suff
    if mean_suff < 0.7:
        penalties.append(f"thin evidence sufficiency ({mean_suff:.0%})")
    if contested:
        conf *= 0.85
        penalties.append("unresolved contradiction among the claims used")
    conf *= 0.7 + 0.3 * independence
    if independence < 1.0:
        penalties.append(f"limited independent corroboration (independence {independence:.0%})")
    if inference_validity is not None:
        conf *= 0.7 + 0.3 * inference_validity
        if inference_validity < 0.6:
            penalties.append(f"the answer leans on a weak inference (validity {inference_validity:.0%})")

    return ConfidenceBreakdown(round(min(0.95, max(0.05, conf)), 2), round(base, 3), round(mean_suff, 3),
                               round(independence, 3), contested, inference_validity, len(claims), penalties)
