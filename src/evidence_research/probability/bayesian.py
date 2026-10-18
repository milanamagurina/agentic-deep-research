"""Approximate Bayesian updating with correlated-evidence handling (sections 24-25).

posterior_odds = prior_odds * product(likelihood ratios), in log space. Evidence is first grouped
by independent provenance root. Within one root, the strongest supporting and the strongest
contradicting item count in full; every further item from that root contributes only
``dependent_evidence_discount`` of its log-LR. Across roots, contributions add normally.

These are heuristic evidence beliefs, not calibrated probabilities.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..config import Heuristics
from ..models import Evidence, Inference
from .evidence_score import from_log_odds, likelihood_ratio, log_odds


@dataclass
class Contribution:
    evidence_id: str
    root_id: str
    stance: str
    strength: float
    lr: float
    label: str
    weight: float  # 1.0 for the primary item of its root/direction, discount otherwise
    log_lr: float


@dataclass
class UpdateResult:
    prior: float
    posterior: float
    contributions: list[Contribution] = field(default_factory=list)

    @property
    def independent_roots(self) -> int:
        return len({c.root_id for c in self.contributions if c.lr != 1.0})

    def roots_by_stance(self, stance: str) -> int:
        return len({c.root_id for c in self.contributions if c.stance == stance and c.lr != 1.0})


def update_claim(prior: float, items: list[tuple[Evidence, float, str]], h: Heuristics) -> UpdateResult:
    """items: (evidence, strength, provenance_root_id)."""
    groups: dict[tuple[str, str], list[tuple[Evidence, float, float, str]]] = {}
    for e, strength, root in items:
        lr, label = likelihood_ratio(e, strength, h)
        groups.setdefault((root, e.stance), []).append((e, strength, lr, label))

    total = log_odds(prior)
    contribs: list[Contribution] = []
    for (root, stance), members in sorted(groups.items()):
        members.sort(key=lambda m: -abs(math.log(m[2])))
        for rank, (e, strength, lr, label) in enumerate(members):
            weight = 1.0 if rank == 0 else h.dependent_evidence_discount
            contribution = weight * math.log(lr)
            total += contribution
            contribs.append(Contribution(e.id, root, stance, strength, lr, label, weight, round(contribution, 4)))
    return UpdateResult(prior=prior, posterior=round(from_log_odds(total), 4), contributions=contribs)


STRENGTH_NUM = {"weak": 0.4, "moderate": 0.7, "strong": 1.0}


def inference_strength(inf: Inference, premise_posteriors: list[float]) -> float:
    """Effective strength of an ACCEPTED inference: weakest premise bounds the conclusion."""
    if not premise_posteriors:
        return 0.0
    return round(inf.verifier_score * inf.proposed_strength * min(premise_posteriors), 4)


def update_hypothesis(prior: float, accepted: list[tuple[Inference, float]], h: Heuristics) -> tuple[float, list[dict]]:
    """accepted: (inference, effective_strength). Inferences sharing premises are discounted like dependent evidence."""
    total = log_odds(prior)
    used_premises: set[str] = set()
    trail = []
    for inf, strength in sorted(accepted, key=lambda t: -t[1]):
        name = "neutral"
        for threshold, bucket_name in h.strength_buckets:
            if strength >= threshold:
                name = bucket_name
                break
        lr = 1.0 if name == "neutral" else h.likelihood_ratios[f"{name}_{'support' if inf.direction == 'supports' else 'contradiction'}"]
        weight = h.dependent_evidence_discount if used_premises & set(inf.premise_ids) else 1.0
        used_premises |= set(inf.premise_ids)
        total += weight * math.log(lr)
        trail.append({"inference_id": inf.id, "strength": strength, "lr": lr, "weight": weight})
    return round(from_log_odds(total), 4), trail
