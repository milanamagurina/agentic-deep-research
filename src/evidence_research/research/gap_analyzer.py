"""Gap engine (sections 27-28): what is missing, and which missing piece is worth researching next.

Gap DETECTION is deterministic from the graph. The model contributes one thing: a categorical
decision-impact rating (low/medium/high) per new gap, mapped to a number by config.
estimated_value = importance x uncertainty x impact x searchability   (heuristic, not formal EVI)
"""

from __future__ import annotations

from ..config import Settings
from ..graph.evidence_graph import EvidenceGraph
from ..llm.gateway import LLMGateway, ModelRole
from ..llm.prompts import DECISION_IMPACT
from ..models import ImpactOutput, QuestionAnalysis, ResearchGap, stable_id
from ..observability.events import EventLog, EventType
from ..probability.engine import BeliefState
from ..probability.uncertainty import uncertainty


class GapEngine:
    def __init__(self, settings: Settings, events: EventLog) -> None:
        self.s = settings
        self.events = events
        self._impact: dict[str, str] = {}

    def critical_claim_ids(self, graph: EvidenceGraph) -> set[str]:
        premises = {p for i in graph.inferences.values() for p in i.premise_ids}
        return {c.id for c in graph.claims.values()
                if c.kind == "fact" and (c.requirement_ids or c.id in premises or c.importance >= 0.6)}

    def detect(self, graph: EvidenceGraph, beliefs: BeliefState, analysis: QuestionAnalysis) -> list[ResearchGap]:
        entity = analysis.key_entities[0] if analysis.key_entities else ""
        gaps: list[ResearchGap] = []

        def add(target: str, gtype: str, desc: str, importance: float, p: float, query: str | None, detail: str = "") -> None:
            gaps.append(ResearchGap(id=stable_id("G", target, gtype, detail), target_id=target, gap_type=gtype, description=desc,
                                    importance=importance, uncertainty=uncertainty(p), estimated_value=0.0,
                                    suggested_query=query))

        for cid in sorted(self.critical_claim_ids(graph)):
            c, b = graph.claims[cid], beliefs.claims.get(cid)
            if b is None or not graph.evidence_for(cid):
                continue
            if b.independent_roots == 1 and b.raw_sources >= 2:
                add(cid, "SOURCE_DEPENDENCE", f"{cid}: {b.raw_sources} sources but only 1 independent root",
                    c.importance, c.truth_probability, f"{c.natural_language} independent source")
            elif b.independent_roots <= 1:
                add(cid, "NO_INDEPENDENT_SOURCE", f"{cid}: no independent confirmation of '{c.natural_language}'",
                    c.importance, c.truth_probability, f"{c.natural_language} independent")
            if not b.has_primary:
                add(cid, "NO_PRIMARY_SOURCE", f"{cid}: no primary source for '{c.natural_language}'",
                    c.importance, c.truth_probability, f"{c.subject} {c.predicate} official")
            if b.contested:
                add(cid, "CONTRADICTORY_EVIDENCE", f"{cid}: independent sources disagree on '{c.natural_language}'",
                    c.importance, c.truth_probability, f"{c.subject} {c.predicate}")
            evs = graph.evidence_for(cid)
            if evs and all(e.temporal_relevance < 0.6 for e in evs):
                add(cid, "OUTDATED_EVIDENCE", f"{cid}: only outdated evidence", c.importance, c.truth_probability, f"{c.subject} {c.predicate} latest")

        for a, b_id in graph.contradiction_pairs():
            kinds = {d.get("kind") for d in graph.g.get_edge_data(a, b_id).values()}
            if "temporal_conflict" in kinds:
                add(a, "TEMPORAL_CONFLICT", f"{a} and {b_id} give different values for overlapping periods",
                    graph.claims[a].importance, graph.claims[a].truth_probability, None, b_id)

        for req in graph.requirements.values():
            if req.satisfaction_score < self.s.min_evidence_sufficiency and not graph.claims_for_requirement(req.id):
                hyp = graph.hypotheses[req.hypothesis_id]
                add(req.id, "MISSING_REQUIRED_DIMENSION", f"{req.id} ({hyp.id}): no evidence yet on '{req.description}'",
                    req.importance, hyp.posterior_probability, f"{entity} {req.description}".strip())

        for inf in graph.inferences.values():
            if inf.status in ("rejected", "needs_evidence"):
                hyp = graph.hypotheses.get(inf.conclusion_claim_id)
                p = hyp.posterior_probability if hyp else 0.5
                for item in (inf.missing_premises + inf.confounders)[:2]:
                    add(inf.id, "WEAK_INFERENCE", f"{inf.id} → {inf.conclusion_claim_id}: needs evidence on '{item}'",
                        0.9, p, f"{entity} {item}".strip(), item)
        return gaps

    async def update(self, llm: LLMGateway | None, graph: EvidenceGraph, beliefs: BeliefState, analysis: QuestionAnalysis) -> list[ResearchGap]:
        detected = {g.id: g for g in self.detect(graph, beliefs, analysis)}
        new = [g for gid, g in detected.items() if gid not in graph.gaps]
        if new and llm is not None:
            payload = {"question": analysis.normalized_question, "gaps": [{"id": g.id, "description": g.description} for g in new]}
            try:
                rated = await llm.structured("rate_gap_impact", ModelRole.FAST, DECISION_IMPACT, payload, ImpactOutput)
                self._impact.update({k: v for k, v in rated.impacts.items() if k in detected})
            except Exception as e:  # rating is an optimization; fall back to 'medium' and say so
                self.events.emit(EventType.ERROR, f"gap impact rating failed ({type(e).__name__}); using 'medium'")
        for g in detected.values():
            impact = self.s.heuristics.impact_scores[self._impact.get(g.id, "medium")]
            # = research_priority(importance, p, impact, searchability), with uncertainty(p) precomputed
            g.estimated_value = round(g.importance * g.uncertainty * impact * self.s.heuristics.gap_searchability[g.gap_type], 4)
            if graph.upsert_gap(g):
                self.events.emit(EventType.RESEARCH_GAP_CREATED, f"{g.id} [{g.gap_type}] {g.description} (value {g.estimated_value:.2f})",
                                 gap_id=g.id, gap_type=g.gap_type, value=g.estimated_value)
        for gid, g in graph.gaps.items():
            if gid not in detected and not g.resolved:
                g.resolved = True
                self.events.emit(EventType.RESEARCH_GAP_RESOLVED, f"{gid} resolved: {g.description}", gap_id=gid)
        return self.ranked(graph)

    @staticmethod
    def ranked(graph: EvidenceGraph) -> list[ResearchGap]:
        open_gaps = [g for g in graph.gaps.values() if not g.resolved and not g.unresolvable]
        return sorted(open_gaps, key=lambda g: -g.estimated_value)
