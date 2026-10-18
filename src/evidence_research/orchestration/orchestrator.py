"""The research loop. Code owns state and control flow; models are called for narrow semantic tasks.

INITIALIZED → QUESTION_ANALYSIS → HYPOTHESIS_GENERATION →
  ┌→ DISCOVERY → EVIDENCE_COLLECTION → CLAIM_VERIFICATION → [ADVERSARIAL_RESEARCH] → GAP_ANALYSIS ─┐
  └──────────────────────────────── stop policy says continue ─────────────────────────────────────┘
→ SYNTHESIS → FINAL_REVIEW → COMPLETED

Model context is built from structured state for each call, never from the raw transcript.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from ..config import Settings
from ..evidence.extractor import EvidencePipeline
from ..evidence.lineage import detect_lineage
from ..graph.evidence_graph import EvidenceGraph
from ..graph.repository import Repository
from ..llm.gateway import LLMGateway
from ..models import QuestionAnalysis, ResearchPhase as P, ResearchSession, Source, stable_id, utcnow
from ..observability.events import EventLog, EventType
from ..probability.engine import BeliefState, recompute
from ..research.analysis import analyze_question, generate_hypotheses
from ..research.gap_analyzer import GapEngine
from ..research.query_planner import adversarial_queries, discovery_queries, gap_queries
from ..retrieval.service import RetrievalService
from ..retrieval.tavily_client import SearchClient
from ..synthesis.report import Report, build_report
from ..synthesis.serializer import to_json, to_markdown
from ..verification.contradiction import detect_claim_conflicts
from ..verification.inference_verifier import propose_and_verify
from .budget import BudgetExceeded, BudgetTracker
from .state_machine import transition
from .stop_policy import CriticalClaim, StopInputs, decide

log = logging.getLogger("evidence_research")
GAPS_PER_ROUND = 3


@dataclass
class RunResult:
    session: ResearchSession
    report: Report
    graph: EvidenceGraph
    events: EventLog
    analysis: QuestionAnalysis
    beliefs: BeliefState


class Orchestrator:
    def __init__(self, settings: Settings, llm: LLMGateway, search: SearchClient, budget: BudgetTracker,
                 events: EventLog | None = None, repository: Repository | None = None, today: date | None = None) -> None:
        self.s, self.llm, self.budget = settings, llm, budget
        self.events = events or EventLog()
        self.repo = repository
        self.today = today or date.today()
        self.graph = EvidenceGraph()
        self.retrieval = RetrievalService(search, self.graph, budget, self.events, settings)
        self.pipeline = EvidencePipeline(llm, self.graph, self.events, settings, self.today)
        self.gaps = GapEngine(settings, self.events)
        self._seen_queries: set[str] = set()
        self._checked_pairs: set[tuple[str, str]] = set()
        self.beliefs = BeliefState()

    # ------------------------------------------------------------------ helpers
    def _sync_counters(self, session: ResearchSession) -> None:
        session.search_count, session.extract_count = self.budget.searches, self.budget.extractions
        session.model_call_count = self.budget.model_calls
        session.updated_at = utcnow()
        if self.repo:
            self.repo.save_session(session)

    def _recompute(self) -> None:
        self.beliefs = recompute(self.graph, self.s, self.events, self.today)

    def _lineage(self) -> None:
        sources = [s for s in self.graph.sources.values() if s.extracted]
        result = detect_lineage(sources, self.graph.assessments, self.s.heuristics.lineage_threshold)
        for e in self.graph.set_lineage(result.edges, result.root_of):
            self.events.emit(EventType.SOURCE_DEPENDENCY_DETECTED,
                             f"{e.child_source_id} derives from {e.parent_source_id} (p={e.dependency_probability:.2f}: {'; '.join(e.reasons)})",
                             child=e.child_source_id, parent=e.parent_source_id, p=e.dependency_probability)

    def _roots_with_evidence(self) -> int:
        return len({self.graph.root_of.get(e.source_id, e.source_id) for e in self.graph.evidence.values()})

    async def _collect(self, session: ResearchSession, analysis: QuestionAnalysis, queries: list[str], origin: str) -> list[Source]:
        candidates = await self.retrieval.search(queries, origin, analysis.key_entities)
        extracted = await self.retrieval.extract(candidates, self.s.extract_per_round)
        self._sync_counters(session)
        if not extracted:
            return []
        stats = await self.pipeline.ingest(extracted, analysis, session.question)
        log.info("ingested %d sources: %d new claims, %d merged, %d evidence", stats.sources, len(stats.new_claims), stats.merged_claims, stats.evidence)
        self._recompute()   # before lineage: every new source still counts as its own root
        self._lineage()     # ...then derived reporting is collapsed into provenance clusters
        self._recompute()
        self._sync_counters(session)
        return extracted

    def _snapshot_posteriors(self) -> dict[str, float]:
        snap = {c.id: c.truth_probability for c in self.graph.claims.values()}
        snap.update({h.id: h.posterior_probability for h in self.graph.hypotheses.values()})
        return snap

    def _leader(self) -> str | None:
        hs = [h for h in self.graph.hypotheses.values() if not h.is_null_hypothesis]
        return max(hs, key=lambda h: h.posterior_probability).id if hs else None

    # ------------------------------------------------------------------ main loop
    async def run(self, question: str, depth: str = "standard", synthetic: bool = False) -> RunResult:
        session = ResearchSession(id=stable_id("R", question, utcnow().isoformat()), question=question, depth=depth, synthetic=synthetic)
        if self.repo:
            self.events.subscribe(lambda e: self.repo.append_event(session.id, e))
        self.events.emit(EventType.SESSION_STARTED, f"{question!r} (depth={depth}{', SYNTHETIC DEMO' if synthetic else ''})",
                         session_id=session.id, budget=self.s.budget.model_dump())

        transition(session, P.QUESTION_ANALYSIS, self.events)
        analysis = await analyze_question(self.llm, question)
        session.objective = analysis.decision_context
        self.events.emit(EventType.QUESTION_ANALYZED, f"entities={analysis.key_entities} scope={analysis.temporal_scope} "
                                                     f"assumptions={analysis.hidden_assumptions}", **analysis.model_dump())

        transition(session, P.HYPOTHESIS_GENERATION, self.events)
        hypotheses, requirements = await generate_hypotheses(self.llm, analysis)
        for h in hypotheses:
            self.graph.add_hypothesis(h)
            session.hypotheses.append(h.id)
            self.events.emit(EventType.HYPOTHESIS_CREATED, f"{h.id} {h.text} (heuristic prior {h.prior_probability:.2f})", hypothesis_id=h.id)
        for r in requirements:
            self.graph.add_requirement(r)
            self.events.emit(EventType.REQUIREMENT_CREATED, f"{r.id} for {r.hypothesis_id}: {r.description} (importance {r.importance})")

        history: list[dict[str, float]] = []
        adversarial_done_for: str | None = None
        selected_gaps = []
        while True:
            session.iteration += 1
            roots_before = self._roots_with_evidence()
            exhausted = None
            try:
                transition(session, P.DISCOVERY, self.events)
                limit = min(4, self.budget.remaining_searches())
                if session.iteration == 1:
                    queries = await discovery_queries(self.llm, analysis, self.graph, self._seen_queries, limit)
                    origin = "discovery"
                else:
                    queries = await gap_queries(self.llm, analysis, selected_gaps, self._seen_queries, min(limit, len(selected_gaps) + 1))
                    origin = "gap"
                    for g in selected_gaps:
                        self.events.emit(EventType.RESEARCH_SCHEDULED, f"searching because of {g.id} [{g.gap_type}]: {g.description}", gap_id=g.id)
                transition(session, P.EVIDENCE_COLLECTION, self.events)
                await self._collect(session, analysis, queries, origin)

                transition(session, P.CLAIM_VERIFICATION, self.events)
                detect_claim_conflicts(self.graph, self.events, self._checked_pairs)
                await propose_and_verify(self.llm, self.graph, self.events, self.s.heuristics, question)
                self._recompute()

                leader = self._leader()
                if leader and leader != adversarial_done_for and self.graph.claims:
                    transition(session, P.ADVERSARIAL_RESEARCH, self.events)
                    adv = await adversarial_queries(self.llm, analysis, self.graph, self._seen_queries, min(3, self.budget.remaining_searches()))
                    self.events.emit(EventType.RESEARCH_SCHEDULED, f"adversarial search against leading hypothesis {leader}: {adv}")
                    await self._collect(session, analysis, adv, "adversarial")
                    detect_claim_conflicts(self.graph, self.events, self._checked_pairs)
                    await propose_and_verify(self.llm, self.graph, self.events, self.s.heuristics, question)
                    self._recompute()
                    adversarial_done_for = leader
            except BudgetExceeded as e:
                exhausted = e.resource
                self.events.emit(EventType.STOP_DECISION, f"budget exhausted mid-round: {e}")

            transition(session, P.GAP_ANALYSIS, self.events)
            self._sync_counters(session)
            ranked = []
            try:
                ranked = await self.gaps.update(None if exhausted else self.llm, self.graph, self.beliefs, analysis)
            except BudgetExceeded as e:
                exhausted = exhausted or e.resource
                ranked = self.gaps.ranked(self.graph)

            new_roots = self._roots_with_evidence() - roots_before
            for g in selected_gaps:  # gaps researched this round that stay open with nothing new
                live = self.graph.gaps.get(g.id)
                if live and not live.resolved and new_roots == 0 and live.attempts >= self.s.heuristics.gap_attempts_before_unresolvable:
                    live.unresolvable = True
                    self.events.emit(EventType.RESEARCH_GAP_UNRESOLVABLE, f"{g.id} unresolvable with public data after {live.attempts} attempts: {g.description}",
                                     gap_id=g.id)
            history.append(self._snapshot_posteriors())
            critical = [CriticalClaim(cid, self.graph.claims[cid].evidence_sufficiency, self.beliefs.claims[cid].contested, self.graph.claims[cid].importance)
                        for cid in self.gaps.critical_claim_ids(self.graph) if cid in self.beliefs.claims]
            decision = decide(StopInputs(
                iteration=session.iteration, max_iterations=self.s.budget.max_iterations,
                exhausted_resource=exhausted or self.budget.nearly_exhausted(), critical_claims=critical,
                posterior_history=history, new_independent_roots_last_round=new_roots,
                researchable_gaps=len(self.gaps.ranked(self.graph)),
                unresolvable_gaps=sum(1 for g in self.graph.gaps.values() if g.unresolvable and not g.resolved),
            ), self.s.min_evidence_sufficiency, self.s.heuristics)
            self.events.emit(EventType.STOP_DECISION, f"{'STOP' if decision.stop else 'CONTINUE'}"
                                                     f"{' (' + decision.reason.value + ')' if decision.reason else ''}: {decision.explanation}; "
                                                     f"new independent roots this round: {new_roots}",
                             stop=decision.stop, reason=decision.reason.value if decision.reason else None)
            if decision.stop:
                session.stop_reason, session.stop_explanation = decision.reason, decision.explanation
                break
            selected_gaps, targets = [], set()
            for g in ranked:
                if g.target_id not in targets:
                    selected_gaps.append(g)
                    targets.add(g.target_id)
                if len(selected_gaps) == GAPS_PER_ROUND:
                    break
            for g in selected_gaps:
                self.graph.gaps[g.id].attempts += 1
            session.unresolved_gap_ids = [g.id for g in ranked]

        session.unresolved_gap_ids = [g.id for g in self.gaps.ranked(self.graph)]
        transition(session, P.SYNTHESIS, self.events)
        report = await build_report(self.llm if self.budget.model_calls < self.s.budget.max_model_calls else None,
                                    self.graph, session, analysis, self.beliefs, self.gaps.critical_claim_ids(self.graph), self.s, self.events)
        transition(session, P.FINAL_REVIEW, self.events)
        _final_review(report, self.events)
        transition(session, P.COMPLETED, self.events)
        self._sync_counters(session)
        if self.repo:
            self.repo.save_session(session, report.status.value)
            self.repo.save_snapshot(session.id, self.graph.snapshot(), to_json(report), to_markdown(report))
        return RunResult(session, report, self.graph, self.events, analysis, self.beliefs)


def _final_review(report: Report, events: EventLog) -> None:
    """Last structural gate: every rendered statement cites at least one stored source."""
    cited = {c.n for c in report.citations}
    for s in report.conclusion:
        if not s.citations or not set(s.citations) <= cited:
            raise AssertionError(f"final review failed: statement without valid citation: {s.text[:80]}")
    events.emit(EventType.REPORT_GENERATED, f"final review passed: {len(report.conclusion)} statement(s), all cited")

