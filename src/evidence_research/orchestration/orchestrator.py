"""The research loop. Code owns state and control flow; models do narrow semantic tasks.

INITIALIZED → QUESTION_ANALYSIS → HYPOTHESIS_GENERATION →
  ┌→ [DISCOVERY | ADVERSARIAL_RESEARCH] → EVIDENCE_COLLECTION   (one per selected agent task)
  │      search → screening → selective extraction → claims/evidence → scientific review → lineage
  │  → CLAIM_VERIFICATION   contradictions · inference proposal + verification · deletion test
  │  → GAP_ANALYSIS         gaps · stop policy · agent bids → highest-utility agents run next ─┐
  └──────────────────────────────────────────────────────────────────────────────────────────┘
→ SYNTHESIS → FINAL_REVIEW → COMPLETED

Models only ever receive the Active Research Graph (graph/active.py), never the full history.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from ..config import Settings
from ..evidence.extractor import EvidencePipeline
from ..evidence.lineage import detect_lineage
from ..graph.active import ActiveResearchGraph
from ..graph.evidence_graph import EvidenceGraph
from ..graph.repository import Repository
from ..llm.gateway import LLMError, LLMGateway
from ..models import (
    AgentBid, QuestionAnalysis, ResearchPhase as P, ResearchSession, ResearchTask, SourceLineage, StopReason, stable_id, utcnow,
)
from ..observability.events import EventLog, EventType
from ..probability.engine import BeliefState, recompute
from ..research.analysis import analyze_question, generate_hypotheses
from ..research.gap_analyzer import GapEngine
from ..research.query_planner import plan_queries
from ..retrieval.screening import Screener, select_for_extraction
from ..retrieval.service import RetrievalService
from ..retrieval.tavily_client import SearchClient
from ..science.reviewer import ScientificReviewer
from ..synthesis.report import Report, build_report
from ..synthesis.serializer import to_json, to_markdown
from ..verification.contradiction import detect_claim_conflicts
from ..verification.inference_verifier import propose_and_verify
from ..verification.necessity import deletion_test
from . import policy
from .budget import BudgetExceeded, BudgetTracker
from .state_machine import transition
from .stop_policy import CriticalClaim, StopInputs, decide

log = logging.getLogger("evidence_research")
AGENTS_PER_ROUND = 2


@dataclass
class RunResult:
    session: ResearchSession
    report: Report
    graph: EvidenceGraph
    events: EventLog
    analysis: QuestionAnalysis
    beliefs: BeliefState
    active: ActiveResearchGraph


class Orchestrator:
    def __init__(self, settings: Settings, llm: LLMGateway, search: SearchClient, budget: BudgetTracker,
                 events: EventLog | None = None, repository: Repository | None = None, today: date | None = None) -> None:
        self.s, self.llm, self.budget = settings, llm, budget
        self.events = events or EventLog()
        self.repo = repository
        self.today = today or date.today()
        self.graph = EvidenceGraph()
        self.retrieval = RetrievalService(search, self.graph, budget, self.events, settings)
        self.screener = Screener(llm, self.graph, self.events)
        self.pipeline = EvidencePipeline(llm, self.graph, self.events, settings, self.today)
        self.reviewer = ScientificReviewer(llm, self.graph, self.events)
        self.gaps = GapEngine(settings, self.events)
        self.policy_state = policy.PolicyState()
        self.beliefs = BeliefState()
        self.active = ActiveResearchGraph()
        self._seen_queries: set[str] = set()
        self._checked_pairs: set[tuple[str, str]] = set()
        self._tested_necessity: set = set()
        self._version_edges: list[SourceLineage] = []

    # ------------------------------------------------------------------ helpers
    def _sync(self, session: ResearchSession) -> None:
        session.search_count, session.extract_count = self.budget.searches, self.budget.extractions
        session.model_call_count = self.budget.model_calls
        session.updated_at = utcnow()
        if self.repo:
            self.repo.save_session(session)

    def _recompute(self) -> None:
        self.beliefs = recompute(self.graph, self.s, self.events, self.today)

    def _lineage(self) -> None:
        sources = [s for s in self.graph.sources.values() if s.extracted]
        result = detect_lineage(sources, self.graph.assessments, self.s.heuristics.lineage_threshold, self._version_edges)
        for e in self.graph.set_lineage(result.edges, result.root_of, result.family_of):
            label = "is a version of the same work as" if e.kind == "same_work_version" else \
                    "is from the same publisher as" if e.kind == "same_publisher" else "derives from"
            self.events.emit(EventType.SOURCE_DEPENDENCY_DETECTED,
                             f"{e.child_source_id} {label} {e.parent_source_id} (p={e.dependency_probability:.2f}: {'; '.join(e.evidence)})",
                             child=e.child_source_id, parent=e.parent_source_id, p=e.dependency_probability, kind=e.kind)
        used = {e.source_id for e in self.graph.evidence.values() if e.verification_status == "verified"}
        if used:
            fam, root_ids = len(result.families(used)), result.independent_roots(used)
            interested = [r for r in root_ids if r in self.graph.assessments and self.graph.assessments[r].conflict_of_interest >= 0.5]
            note = f"; {len(interested)} of them are interested parties (self-reported)" if interested else ""
            self.events.emit(EventType.INDEPENDENCE_SUMMARY, f"{len(used)} URLs with evidence → {fam} publication families → "
                                                            f"{len(root_ids)} independent evidence roots{note}",
                             urls=len(used), families=fam, roots=len(root_ids), interested_roots=len(interested))

    def _roots_with_evidence(self) -> int:
        return len({self.graph.root_of.get(e.source_id, e.source_id) for e in self.graph.evidence.values() if e.verification_status == "verified"})

    def _critical(self) -> set[str]:
        return self.gaps.critical_claim_ids(self.graph)

    def _rebuild_active(self) -> None:
        self.active = ActiveResearchGraph.build(self.graph, self.beliefs, self._critical(), self.gaps.ranked(self.graph), self.events)

    def _leader(self) -> str | None:
        hs = [h for h in self.graph.hypotheses.values() if not h.is_null_hypothesis]
        return max(hs, key=lambda h: h.posterior_probability).id if hs else None

    async def _run_task(self, session: ResearchSession, analysis: QuestionAnalysis, task: ResearchTask, extract_k: int) -> None:
        transition(session, P.ADVERSARIAL_RESEARCH if task.agent_type == "AdversarialResearcher" else P.DISCOVERY, self.events)
        limit = min(4 if task.agent_type == "GeneralResearcher" else 3, self.budget.remaining_searches())
        task.queries = await plan_queries(self.llm, task.agent_type, analysis, self.graph, self.gaps.ranked(self.graph),
                                          self.active, task.target_ids, self._seen_queries, limit)
        task.status = "running"
        self.events.emit(EventType.RESEARCH_TASK_CREATED, f"{task.id} {task.agent_type}: {task.reason} → queries {task.queries}",
                         task_id=task.id, agent=task.agent_type, queries=task.queries)
        roots_before = self._roots_with_evidence()
        transition(session, P.EVIDENCE_COLLECTION, self.events)
        candidates = await self.retrieval.search(task.queries, task.agent_type, analysis.key_entities)
        decisions = await self.screener.screen(candidates, analysis, session.question) if candidates else {}
        extracted = await self.retrieval.extract(select_for_extraction(candidates, decisions, extract_k))
        self._sync(session)
        if extracted:
            stats = await self.pipeline.ingest(extracted, analysis, session.question)
            log.info("%s ingested %d sources: %d claims, %d evidence", task.agent_type, stats.sources, len(stats.new_claims), stats.evidence)
            self._version_edges = await self.reviewer.review(extracted, session.question)
            self._recompute()   # before lineage: each new source still counts as its own root
            self._lineage()     # derived reporting and versions of one work collapse into one root
            self._recompute()
        task.new_sources, task.status = len(extracted), "done"
        self.policy_state.last_yield[task.agent_type] = self._roots_with_evidence() - roots_before
        if task.agent_type == "AdversarialResearcher":
            self.policy_state.adversarial_done_for = task.target_ids[0] if task.target_ids else self._leader()
        self._sync(session)

    def _emit_bids(self, iteration: int, bids: list[AgentBid], chosen: list[AgentBid]) -> None:
        self.graph.bids.append((iteration, bids))
        self.events.emit(EventType.AGENT_BIDS, " · ".join(f"{b.agent_type} {b.utility:.2f}" for b in bids),
                         bids=[b.model_dump() for b in bids])
        for b in chosen:
            self.events.emit(EventType.AGENT_SELECTED, f"Next agent: {b.agent_type} (utility {b.utility:.2f}). Reason: {b.reasons[0]}",
                             agent=b.agent_type, utility=b.utility, reasons=b.reasons)

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

        bids = policy.bid(self.graph, [], self.policy_state, set())
        chosen = policy.select(bids, 1)
        self._emit_bids(0, bids, chosen)
        history: list[dict[str, float]] = []
        while True:
            session.iteration += 1
            self.policy_state.iteration = session.iteration
            roots_before = self._roots_with_evidence()
            exhausted = None
            try:
                extract_k = max(2, self.s.extract_per_round // max(1, len(chosen)))
                for b in chosen:
                    task = ResearchTask(id=stable_id("T", b.agent_type, str(session.iteration), ",".join(b.target_ids)), agent_type=b.agent_type,
                                        target_ids=b.target_ids, reason=b.reasons[0], iteration=session.iteration)
                    self.graph.add_task(task)
                    session.active_task_ids.append(task.id)
                    try:
                        await self._run_task(session, analysis, task, extract_k)
                    except LLMError as e:  # one failed agent task degrades the round, visibly; it does not end the run
                        task.status = "failed"
                        self.events.emit(EventType.ERROR, f"{task.id} {task.agent_type} failed: {e}", task_id=task.id)
                    session.active_task_ids.remove(task.id)
                    session.completed_task_ids.append(task.id)

                transition(session, P.CLAIM_VERIFICATION, self.events)
                detect_claim_conflicts(self.graph, self.events, self._checked_pairs)
                self._rebuild_active()
                try:
                    await propose_and_verify(self.llm, self.graph, self.events, self.s.heuristics, question, focus=self.active.claim_ids)
                except LLMError as e:
                    self.events.emit(EventType.ERROR, f"inference proposal/verification failed this round: {e}")
                self._recompute()
                await deletion_test(self.llm, self.graph, self.events, self._tested_necessity)
                self._recompute()
            except BudgetExceeded as e:
                exhausted = e.resource
                self.events.emit(EventType.STOP_DECISION, f"budget exhausted mid-round: {e}")

            transition(session, P.GAP_ANALYSIS, self.events)
            self._sync(session)
            try:
                ranked = await self.gaps.update(None if exhausted else self.llm, self.graph, self.beliefs, analysis)
            except BudgetExceeded as e:
                exhausted = exhausted or e.resource
                ranked = self.gaps.ranked(self.graph)
            self._rebuild_active()

            new_roots = self._roots_with_evidence() - roots_before
            for b in chosen:  # gaps a task targeted that stay open with nothing new become unresolvable
                for gid in b.target_ids:
                    live = self.graph.gaps.get(gid)
                    if live and not live.resolved and new_roots == 0 and live.attempts >= self.s.heuristics.gap_attempts_before_unresolvable:
                        live.unresolvable = True
                        self.events.emit(EventType.RESEARCH_GAP_UNRESOLVABLE, f"{gid} unresolvable with public data after {live.attempts} attempts: "
                                                                              f"{live.description}", gap_id=gid)
            history.append({**{c.id: c.truth_probability for c in self.graph.claims.values()},
                            **{h.id: h.posterior_probability for h in self.graph.hypotheses.values()}})
            critical_ids = self._critical()
            critical = [CriticalClaim(cid, self.graph.claims[cid].evidence_sufficiency, self.beliefs.claims[cid].contested, self.graph.claims[cid].importance)
                        for cid in critical_ids if cid in self.beliefs.claims]
            # Conservative answer-readiness: only once the leader has been adversarially challenged and
            # most critical claims have at least one independent root. Never cuts off contradiction research.
            answerable = sum(1 for cid in critical_ids if cid in self.beliefs.claims and self.beliefs.claims[cid].independent_roots >= 1)
            answer_ready = (session.iteration >= 2 and self.policy_state.adversarial_done_for is not None
                            and bool(critical_ids) and answerable >= max(2, (len(critical_ids) + 1) // 2))
            decision = decide(StopInputs(
                iteration=session.iteration, max_iterations=self.s.budget.max_iterations,
                exhausted_resource=exhausted or self.budget.nearly_exhausted(), critical_claims=critical,
                posterior_history=history, new_independent_roots_last_round=new_roots,
                researchable_gaps=len(self.gaps.ranked(self.graph)),
                unresolvable_gaps=sum(1 for g in self.graph.gaps.values() if g.unresolvable and not g.resolved),
                answer_ready=answer_ready,
            ), self.s.min_evidence_sufficiency, self.s.heuristics)
            if not decision.stop:
                bids = policy.bid(self.graph, ranked, self.policy_state, self._critical())
                chosen = policy.select(bids, AGENTS_PER_ROUND)
                self._emit_bids(session.iteration, bids, chosen)
                if not chosen:
                    decision.stop, decision.reason = True, StopReason.DIMINISHING_RETURNS
                    decision.explanation = "no research agent has a useful action left (all bids below threshold)"
            self.events.emit(EventType.STOP_DECISION, f"{'STOP' if decision.stop else 'CONTINUE'}"
                                                     f"{' (' + decision.reason.value + ')' if decision.reason else ''}: {decision.explanation}; "
                                                     f"new independent roots this round: {new_roots}",
                             stop=decision.stop, reason=decision.reason.value if decision.reason else None)
            if decision.stop:
                session.stop_reason, session.stop_explanation = decision.reason, decision.explanation
                break
            for b in chosen:
                for gid in b.target_ids:
                    if gid in self.graph.gaps:
                        self.graph.gaps[gid].attempts += 1
            session.unresolved_gap_ids = [g.id for g in ranked]

        session.unresolved_gap_ids = [g.id for g in self.gaps.ranked(self.graph)]
        transition(session, P.SYNTHESIS, self.events)
        report = await build_report(self.llm, self.graph, session, analysis, self.beliefs, self._critical(), self.s, self.events, self.active)
        transition(session, P.FINAL_REVIEW, self.events)
        _final_review(report, self.events)
        transition(session, P.COMPLETED, self.events)
        self._sync(session)
        if self.repo:
            self.repo.save_session(session, report.status.value)
            self.repo.save_snapshot(session.id, self.graph.snapshot(), to_json(report), to_markdown(report))
        return RunResult(session, report, self.graph, self.events, analysis, self.beliefs, self.active)


def _final_review(report: Report, events: EventLog) -> None:
    """Last structural gate: every rendered statement cites stored evidence and sources."""
    cited = {c.n for c in report.citations}
    for s in report.conclusion:
        if not s.citations or not set(s.citations) <= cited or not s.evidence_ids:
            raise AssertionError(f"final review failed: statement without a valid evidence chain: {s.text[:80]}")
    events.emit(EventType.REPORT_GENERATED, f"final review passed: {len(report.conclusion)} statement(s), each → claim → evidence → excerpt → source")
