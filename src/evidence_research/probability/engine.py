"""Recompute every claim and hypothesis belief from the graph. Pure function of graph + config.

Run after each research round. Changes are appended as satellite observations and emitted as
CLAIM_POSTERIOR_UPDATED / HYPOTHESIS_UPDATED events with the reasons (roots, raw sources).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..config import Settings
from ..evidence.source_classifier import is_primary, reliability_for
from ..graph.evidence_graph import EvidenceGraph
from ..observability.events import EventLog, EventType
from .bayesian import UpdateResult, inference_strength, update_claim, update_hypothesis
from .evidence_score import evidence_strength
from .uncertainty import claim_sufficiency, classify_claim, classify_hypothesis


@dataclass
class ClaimBelief:
    claim_id: str
    update: UpdateResult
    raw_sources: int
    independent_roots: int
    has_primary: bool
    contested: bool


@dataclass
class BeliefState:
    claims: dict[str, ClaimBelief] = field(default_factory=dict)
    hypothesis_trails: dict[str, list[dict]] = field(default_factory=dict)

    def max_shift(self, previous: dict[str, float], current: dict[str, float]) -> float:
        keys = set(previous) | set(current)
        return max((abs(current.get(k, 0.5) - previous.get(k, 0.5)) for k in keys), default=0.0)


def recompute(graph: EvidenceGraph, settings: Settings, events: EventLog, today: date) -> BeliefState:
    h = settings.heuristics
    state = BeliefState()

    for claim in graph.claims.values():
        items = []
        for e in graph.evidence_for(claim.id):
            assessment = graph.assessments.get(e.source_id)
            if assessment is None:
                continue
            strength = evidence_strength(e, reliability_for(assessment, claim))
            items.append((e, strength, graph.root_of.get(e.source_id, e.source_id)))
        result = update_claim(h.claim_prior, items, h)
        informative = [c for c in result.contributions if c.lr != 1.0]
        roots = {c.root_id for c in informative}
        primary = any(is_primary(graph.assessments[graph.evidence[c.evidence_id].source_id]) for c in informative)
        directness = max((graph.evidence[c.evidence_id].directness for c in informative), default=0.0)
        support_roots = {c.root_id for c in informative if c.stance == "supports" and c.lr >= 2}
        contra_roots = {c.root_id for c in informative if c.stance == "contradicts" and c.lr <= 0.5}
        contested = bool(support_roots and contra_roots and (support_roots | contra_roots) - (support_roots & contra_roots))
        sufficiency = claim_sufficiency(len(roots), primary, directness)
        raw = len({graph.evidence[c.evidence_id].source_id for c in result.contributions})

        old_p, old_s = claim.truth_probability, claim.evidence_sufficiency
        claim.truth_probability, claim.evidence_sufficiency = result.posterior, sufficiency
        claim.status = classify_claim(result.posterior, sufficiency, contested, settings.min_claim_confidence, settings.min_evidence_sufficiency)
        state.claims[claim.id] = ClaimBelief(claim.id, result, raw, len(roots), primary, contested)
        if abs(old_p - result.posterior) >= 0.005 or abs(old_s - sufficiency) >= 0.005:
            reason = f"{raw} raw source(s), {len(roots)} independent root(s){', primary source' if primary else ''}"
            graph.observe(claim.id, "posterior", {"p": result.posterior, "sufficiency": sufficiency, "status": claim.status.value}, reason)
            events.emit(EventType.CLAIM_POSTERIOR_UPDATED,
                        f"{claim.id} posterior {old_p:.2f} → {result.posterior:.2f}, sufficiency {old_s:.2f} → {sufficiency:.2f} ({reason})",
                        claim_id=claim.id, old=old_p, new=result.posterior, sufficiency=sufficiency,
                        raw_sources=raw, independent_roots=len(roots))

    # Requirements: satisfied by sufficiently evidenced claims, whatever their direction.
    for req in graph.requirements.values():
        linked = graph.claims_for_requirement(req.id)
        req.satisfaction_score = round(max((c.evidence_sufficiency for c in linked), default=0.0), 4)
        req.satisfied = req.satisfaction_score >= settings.min_evidence_sufficiency

    non_null = [x for x in graph.hypotheses.values() if not x.is_null_hypothesis]
    for hyp in non_null:
        reqs = graph.requirements_for(hyp.id)
        weight = sum(r.importance for r in reqs)
        coverage = sum(r.importance * r.satisfaction_score for r in reqs) / weight if weight else 0.0
        accepted = []
        for inf in graph.inferences_for(hyp.id):
            if inf.status != "accepted":
                continue
            posts = [graph.claims[p].truth_probability for p in inf.premise_ids if p in graph.claims]
            accepted.append((inf, inference_strength(inf, posts)))
        # Sufficiency = half requirement coverage, half the weakest premise the conclusion rests on.
        premise_suff = [graph.claims[p].evidence_sufficiency for inf, _ in accepted for p in inf.premise_ids if p in graph.claims]
        hyp.evidence_sufficiency = round(0.5 * coverage + 0.5 * (min(premise_suff) if premise_suff else 0.0), 4)
        posterior, trail = update_hypothesis(hyp.prior_probability, accepted, h)
        hyp.inference_validity = round(sum(i.verifier_score for i, _ in accepted) / len(accepted), 4) if accepted else None
        _set_hypothesis(graph, events, hyp, posterior, settings, trail)
        state.hypothesis_trails[hyp.id] = trail

    # Null hypothesis ("public information is insufficient"): a deterministic function of how
    # well the best-evidenced competing hypothesis is covered. Labelled as such in the report.
    best_suff = max((x.evidence_sufficiency for x in non_null), default=0.0)
    for hyp in graph.hypotheses.values():
        if hyp.is_null_hypothesis:
            hyp.evidence_sufficiency = 1.0
            hyp.inference_validity = None
            _set_hypothesis(graph, events, hyp, round(min(0.95, max(0.05, 1 - best_suff)), 4), settings, [])
    return state


def _set_hypothesis(graph, events, hyp, posterior: float, settings: Settings, trail: list[dict]) -> None:
    old = hyp.posterior_probability
    hyp.posterior_probability = posterior
    hyp.status = classify_hypothesis(posterior, hyp.evidence_sufficiency, settings.min_claim_confidence, settings.min_evidence_sufficiency)
    if abs(old - posterior) >= 0.005:
        graph.observe(hyp.id, "posterior", {"p": posterior, "sufficiency": hyp.evidence_sufficiency, "status": hyp.status}, f"{len(trail)} accepted inference(s)")
        events.emit(EventType.HYPOTHESIS_UPDATED, f"{hyp.id} posterior {old:.2f} → {posterior:.2f} (sufficiency {hyp.evidence_sufficiency:.2f}, {hyp.status})",
                    hypothesis_id=hyp.id, old=old, new=posterior)
