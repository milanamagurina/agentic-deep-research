"""Stop policy (section 29). Deterministic; evaluated once per iteration in GAP_ANALYSIS.

Order: budget -> success -> convergence -> diminishing returns -> unresolvable -> continue.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Heuristics
from ..models import StopReason


@dataclass
class CriticalClaim:
    claim_id: str
    sufficiency: float
    contested: bool
    importance: float


@dataclass
class StopInputs:
    iteration: int
    max_iterations: int
    exhausted_resource: str | None
    critical_claims: list[CriticalClaim]
    posterior_history: list[dict[str, float]] = field(default_factory=list)  # one snapshot per iteration
    new_independent_roots_last_round: int = 0
    researchable_gaps: int = 0
    unresolvable_gaps: int = 0
    answer_ready: bool = False  # enough verified evidence to answer substantively (computed conservatively upstream)


@dataclass
class StopDecision:
    stop: bool
    reason: StopReason | None
    explanation: str


def max_shift(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    return max((abs(a.get(k, 0.5) - b.get(k, 0.5)) for k in keys), default=0.0)


def decide(x: StopInputs, min_sufficiency: float, h: Heuristics) -> StopDecision:
    if x.exhausted_resource:
        return StopDecision(True, StopReason.BUDGET_EXHAUSTED, f"{x.exhausted_resource} budget exhausted")
    if x.iteration >= x.max_iterations:
        return StopDecision(True, StopReason.BUDGET_EXHAUSTED, f"iteration budget reached ({x.max_iterations})")

    insufficient = [c for c in x.critical_claims if c.sufficiency < min_sufficiency]
    open_contradictions = [c for c in x.critical_claims if c.contested and c.importance >= 0.6]
    if x.critical_claims and not insufficient and not open_contradictions:
        return StopDecision(True, StopReason.SUCCESS,
                            f"all {len(x.critical_claims)} critical claims have sufficiency ≥ {min_sufficiency} and no open high-importance contradictions")

    # Answer-readiness (section 8): we can answer substantively before every claim is fully sufficient,
    # as long as no high-importance contradiction is still open. Unresolved low-value gaps do not block this.
    if x.answer_ready and not open_contradictions:
        return StopDecision(True, StopReason.SUCCESS,
                            "enough verified evidence to give a substantive answer; remaining gaps are low-value")

    n = h.convergence_stable_iterations
    if len(x.posterior_history) >= n + 1:
        shifts = [max_shift(x.posterior_history[-i - 2], x.posterior_history[-i - 1]) for i in range(n)]
        if all(s < h.convergence_epsilon for s in shifts):
            return StopDecision(True, StopReason.CONVERGENCE,
                                f"beliefs moved < {h.convergence_epsilon} for {n} iterations (max shift {max(shifts):.3f})")

    if x.iteration >= 2 and x.new_independent_roots_last_round == 0:
        return StopDecision(True, StopReason.DIMINISHING_RETURNS, "last research round produced no new independent evidence root")

    if x.researchable_gaps == 0:
        if x.unresolvable_gaps:
            return StopDecision(True, StopReason.UNRESOLVABLE,
                                f"{x.unresolvable_gaps} remaining gap(s) were researched repeatedly without new public evidence")
        return StopDecision(True, StopReason.SUCCESS, "no open research gaps remain")

    return StopDecision(False, None,
                        f"{len(insufficient)} critical claim(s) below sufficiency, {len(open_contradictions)} open contradiction(s), "
                        f"{x.researchable_gaps} researchable gap(s)")
