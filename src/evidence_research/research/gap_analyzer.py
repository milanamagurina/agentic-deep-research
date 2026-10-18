"""Gap engine (sections 27-28): what is missing, and which missing piece is worth researching next.

Gap DETECTION is deterministic from the graph. The model contributes one thing: a categorical
decision-impact rating (low/medium/high) per new gap, mapped to a number by config.
estimated_value = importance x uncertainty x impact x searchability   (heuristic, not formal EVI)
uncertainty     = max(1 - |2P - 1|, 1 - evidence_sufficiency) for claim targets
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

    def critical_claim_ids(self, graph: EvidenceGraph, limit: int = 15) -> set[str]:
        """Fact claims that carry the argument: tied to a requirement, a premise, or a necessary dependency."""
        premises = {p for i in graph.inferences.values() for p in i.premise_ids}
        necessary = {a.premise_id for a in graph.necessity.values() if a.necessary}
        crit = [c for c in graph.claims.values()
                if c.kind == "fact" and (c.requirement_ids or c.id in premises or c.id in necessary)]
        crit.sort(key=lambda c: (c.id not in necessary, -c.importance, c.id))
        return {c.id for c in crit[:limit]}

    def detect(self, graph: EvidenceGraph, beliefs: BeliefState, analysis: QuestionAnalysis) -> list[ResearchGap]:
        entity = analysis.key_entities[0] if analysis.key_entities else ""
        gaps: list[ResearchGap] = []

        def add(target: str, gtype: str, desc: str, importance: float, p: float, query: str | None, detail: str = "") -> None:
            # Epistemic uncertainty: a confident posterior resting on thin evidence is still uncertain.
            u = uncertainty(p)
            if target in graph.claims:
                u = max(u, 1 - graph.claims[target].evidence_sufficiency)
            gaps.append(ResearchGap(id=stable_id("G", target, gtype, detail), target_id=target, gap_type=gtype, description=desc,
                                    importance=importance, uncertainty=round(u, 4), estimated_value=0.0,
                                    suggested_query=query))

        critical = sorted(self.critical_claim_ids(graph))
        for cid in critical:
            c, b = graph.claims[cid], beliefs.claims.get(cid)
            if not graph.evidence_for(cid):
                if graph.evidence_for(cid, verified_only=False):
                    add(cid, "UNVERIFIED_EXTRACTION", f"{cid}: '{c.natural_language}' was extracted but its excerpt could not be located in the source",
                        c.importance, c.truth_probability, c.natural_language)
                continue
            if b is None:
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
                    item = item.strip().rstrip(".")[:90]
                    add(inf.id, "WEAK_INFERENCE", f"{inf.id} → {inf.conclusion_claim_id}: needs evidence on '{item}'",
                        0.9, p, f"{entity} {item[:60]}".strip(), item.lower())

        # Scientific evidence (sections 11, 24, 30).
        for st in graph.studies.values():
            sa = graph.study_assessments.get(st.id)
            rels = graph.study_relations_to(st.id)
            if any(r.relation == "FAILS_TO_REPLICATE" for r in rels):
                add(st.id, "FAILED_REPLICATION", f"{st.id} '{st.title[:60]}' has a failed replication: which result holds, and why?",
                    1.0, 0.5, f"{st.title[:70]} replication")
            if sa and (sa.study_design is None or sa.sample_size is None):
                add(st.id, "MISSING_METHOD_INFORMATION", f"{st.id}: design or sample size not reported", 0.6, 0.5, f"{st.title[:70]} methods")
            if sa and sa.sample_size is not None and sa.sample_size < 50:
                add(st.id, "INSUFFICIENT_SAMPLE", f"{st.id}: n={sa.sample_size} is too small to carry the claim alone", 0.7, 0.5, None)
        for cid in critical:
            sci = {st.id for e in graph.evidence_for(cid) if e.stance == "supports" and (st := graph.study_for_source(e.source_id))}
            if len(sci) == 1:
                st = graph.studies[next(iter(sci))]
                if not graph.study_relations_to(st.id):
                    c = graph.claims[cid]
                    add(cid, "NO_REPLICATION", f"{cid}: supported by a single study ({st.id}) with no known replication",
                        c.importance, c.truth_probability, f"{st.title[:70]} replication")
        return gaps

    async def update(self, llm: LLMGateway | None, graph: EvidenceGraph, beliefs: BeliefState, analysis: QuestionAnalysis,
                     limit: int = 25) -> list[ResearchGap]:
        h = self.s.heuristics
        found = self.detect(graph, beliefs, analysis)
        # Keep the most valuable gaps (provisional value with 'medium' impact); the rest is noise for planning.
        found.sort(key=lambda g: -(g.importance * g.uncertainty * h.gap_searchability[g.gap_type]))
        # Normalize (section 7): merge equivalent gaps (same target and type) into the highest-value one,
        # so repeated rounds and near-duplicate detail do not flood the planner with the same gap.
        merged: dict[tuple[str, str], ResearchGap] = {}
        for g in found:
            merged.setdefault((g.target_id, g.gap_type), g)
        found = list(merged.values())
        detected = {g.id: g for g in found[:limit]}
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
            # answer_relevance: gaps on claims/requirements that carry the answer rank above incidental ones.
            relevance = 1.0 if (g.target_id in graph.claims or g.target_id in graph.requirements) else 0.8
            # = research_priority(importance, p, impact, searchability) x answer_relevance, uncertainty(p) precomputed
            g.estimated_value = round(g.importance * g.uncertainty * impact * self.s.heuristics.gap_searchability[g.gap_type] * relevance, 4)
            if graph.upsert_gap(g):
                self.events.emit(EventType.RESEARCH_GAP_CREATED, f"{g.id} [{g.gap_type}] {g.description} (value {g.estimated_value:.2f})",
                                 gap_id=g.id, gap_type=g.gap_type, value=g.estimated_value)
        still_open = {g.id for g in found}
        for gid, g in graph.gaps.items():
            if gid not in still_open and not g.resolved:
                g.resolved = True
                self.events.emit(EventType.RESEARCH_GAP_RESOLVED, f"{gid} resolved: {g.description}", gap_id=gid)
        return self.ranked(graph)

    @staticmethod
    def ranked(graph: EvidenceGraph) -> list[ResearchGap]:
        open_gaps = [g for g in graph.gaps.values() if not g.resolved and not g.unresolvable]
        return sorted(open_gaps, key=lambda g: -g.estimated_value)
