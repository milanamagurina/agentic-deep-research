"""Research Policy Engine: dynamic agent selection by heuristic utility (section 29).

No fixed planner -> researcher -> critic -> writer pipeline. After every round each capability
bids ``utility_of_acting_now`` from the state of the active graph; the highest bids run next. The
utilities are transparent heuristics over gap values (no learned controller). Every bid, with its
reasons, is written to the trace.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..graph.evidence_graph import EvidenceGraph
from ..models import AgentBid, ResearchGap

# Which gap types each researcher is built to close, and how much it is favoured for them.
AGENT_GAPS: dict[str, tuple[set[str], float]] = {
    "PrimarySourceResearcher": ({"NO_PRIMARY_SOURCE", "UNVERIFIED_EXTRACTION"}, 1.10),
    "IndependenceResearcher": ({"SOURCE_DEPENDENCE", "NO_INDEPENDENT_SOURCE"}, 1.10),
    "ContradictionResearcher": ({"CONTRADICTORY_EVIDENCE", "TEMPORAL_CONFLICT"}, 1.15),
    "GapResearcher": ({"MISSING_REQUIRED_DIMENSION", "WEAK_INFERENCE", "OUTDATED_EVIDENCE"}, 1.0),
    "ReplicationResearcher": ({"NO_REPLICATION", "FAILED_REPLICATION", "MISSING_METHOD_INFORMATION", "INSUFFICIENT_SAMPLE"}, 1.10),
}
MIN_UTILITY = 0.12


@dataclass
class PolicyState:
    iteration: int = 0
    adversarial_done_for: str | None = None
    last_yield: dict[str, int] = field(default_factory=dict)  # agent -> new independent roots its last task produced


def bid(graph: EvidenceGraph, gaps: list[ResearchGap], state: PolicyState, critical_ids: set[str]) -> list[AgentBid]:
    bids: list[AgentBid] = []
    has_evidence = any(e.verification_status == "verified" for e in graph.evidence.values())

    if not has_evidence:
        bids.append(AgentBid(agent_type="GeneralResearcher", utility=0.95, reasons=["no evidence collected yet: broad discovery first"]))
    else:
        uncovered = [r for r in graph.requirements.values() if not graph.claims_for_requirement(r.id)]
        share = len(uncovered) / max(1, len(graph.requirements))
        bids.append(AgentBid(agent_type="GeneralResearcher", utility=round(0.15 + 0.3 * share, 3),
                             reasons=[f"{len(uncovered)}/{len(graph.requirements)} evidence requirements have no claim yet"],
                             target_ids=[r.id for r in uncovered[:4]]))

    for agent, (types, weight) in AGENT_GAPS.items():
        mine = [g for g in gaps if g.gap_type in types]
        if not mine:
            bids.append(AgentBid(agent_type=agent, utility=0.0, reasons=["no gaps of this kind"]))
            continue
        top = mine[:3]
        utility = min(1.0, weight * top[0].estimated_value + 0.05 * (len(mine) - 1))
        bids.append(AgentBid(agent_type=agent, utility=round(utility, 3), reasons=[f"[{g.gap_type}] {g.description}" for g in top],
                             target_ids=[g.id for g in top]))

    hyps = [h for h in graph.hypotheses.values() if not h.is_null_hypothesis]
    leader = max(hyps, key=lambda h: h.posterior_probability) if hyps else None
    if leader and has_evidence:
        if leader.id != state.adversarial_done_for:
            u = 0.5 + 0.45 * leader.posterior_probability
            why = f"leading hypothesis {leader.id} (posterior {leader.posterior_probability:.2f}) has not been challenged yet"
        else:
            u, why = 0.1, f"{leader.id} was already challenged; re-challenge only if it keeps leading"
        bids.append(AgentBid(agent_type="AdversarialResearcher", utility=round(u, 3), reasons=[why], target_ids=[leader.id]))

    for b in bids:  # a researcher whose last task found nothing new is discounted
        if state.last_yield.get(b.agent_type) == 0:
            b.utility = round(b.utility * 0.5, 3)
            b.reasons.append("last task of this agent found no new independent evidence (×0.5)")

    crit = [graph.claims[c] for c in critical_ids if c in graph.claims]
    readiness = sum(c.evidence_sufficiency for c in crit) / len(crit) if crit else 0.0
    best = max((b.utility for b in bids), default=0.0)
    bids.append(AgentBid(agent_type="Synthesis", utility=round(readiness * (1 - best), 3),
                         reasons=[f"mean sufficiency of critical claims {readiness:.2f}; best research bid {best:.2f}"]))
    return sorted(bids, key=lambda b: -b.utility)


def select(bids: list[AgentBid], k: int = 2) -> list[AgentBid]:
    researchers = [b for b in bids if b.agent_type != "Synthesis" and b.utility >= MIN_UTILITY]
    return researchers[:k]
