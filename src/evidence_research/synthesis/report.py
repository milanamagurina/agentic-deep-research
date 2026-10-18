"""Final report (section 31). Structure and numbers come from the graph; only the executive prose
comes from the model, and every sentence of it must pass the CitationVerifier or it is dropped."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from ..config import Settings
from ..evidence.temporal import describe
from ..graph.evidence_graph import EvidenceGraph
from ..llm.gateway import LLMError, LLMGateway, ModelRole
from ..llm.prompts import SYNTHESIZER
from ..models import EvidenceStatus, QuestionAnalysis, ResearchSession, SynthesisOutput
from ..observability.events import EventLog, EventType
from ..probability.engine import BeliefState
from ..probability.uncertainty import overall_status
from ..verification.citation_verifier import CitationVerifier


class Citation(BaseModel):
    n: int
    source_id: str
    title: str
    url: str
    publisher: str
    published_at: date | None
    retrieved_at: datetime
    independent_root: str


class EvidenceLine(BaseModel):
    evidence_id: str
    stance: str
    excerpt: str
    citation: int
    directness: float
    reported_speech: bool


class ClaimView(BaseModel):
    id: str
    text: str
    kind: str
    period: str
    posterior: float
    sufficiency: float
    status: str
    raw_sources: int
    independent_roots: int
    support: list[EvidenceLine] = Field(default_factory=list)
    against: list[EvidenceLine] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    history: list[float] = Field(default_factory=list)


class HypothesisView(BaseModel):
    id: str
    text: str
    is_null: bool
    prior: float
    posterior: float
    sufficiency: float
    inference_validity: float | None
    status: str
    accepted_inferences: list[str]
    rejected_inferences: list[str]
    history: list[float]


class Statement(BaseModel):
    text: str
    claim_ids: list[str]
    citations: list[int] = Field(default_factory=list)


class GapView(BaseModel):
    id: str
    gap_type: str
    description: str
    value: float
    level: str
    attempts: int
    unresolvable: bool


class Report(BaseModel):
    question: str
    synthetic: bool
    status: EvidenceStatus
    stop_reason: str | None
    stop_explanation: str | None
    leading_hypothesis: str | None
    conclusion: list[Statement]
    rejected_statements: list[dict]
    hypotheses: list[HypothesisView]
    critical_claims: list[ClaimView]
    raw_source_count: int
    independent_root_count: int
    clusters: list[dict]
    gaps: list[GapView]
    what_would_change: list[str]
    method_limitations: list[str]
    citations: list[Citation]
    stats: dict


def _debt(value: float) -> str:
    return "HIGH" if value >= 0.35 else "MEDIUM" if value >= 0.15 else "LOW"


async def build_report(llm: LLMGateway | None, graph: EvidenceGraph, session: ResearchSession, analysis: QuestionAnalysis,
                       beliefs: BeliefState, critical_ids: set[str], settings: Settings, events: EventLog) -> Report:
    verifier = CitationVerifier(graph)
    citations: dict[str, Citation] = {}

    def cite(source_id: str) -> int:
        if source_id not in citations:
            s = graph.sources[source_id]
            citations[source_id] = Citation(n=len(citations) + 1, source_id=s.id, title=s.title or s.url, url=s.url,
                                            publisher=s.publisher, published_at=s.published_at, retrieved_at=s.retrieved_at,
                                            independent_root=graph.root_of.get(s.id, s.id))
        return citations[source_id].n

    hyps = sorted(graph.hypotheses.values(), key=lambda x: -x.posterior_probability)
    non_null = [x for x in hyps if not x.is_null_hypothesis]
    lead = non_null[0] if non_null else None
    contested = any(beliefs.claims[c].contested for c in critical_ids if c in beliefs.claims)
    status = overall_status(lead.posterior_probability if lead else 0.0, lead.evidence_sufficiency if lead else 0.0,
                            contested, session.stop_reason, settings.min_claim_confidence, settings.min_evidence_sufficiency)

    open_gaps = sorted([g for g in graph.gaps.values() if not g.resolved], key=lambda g: -g.estimated_value)

    claim_views = []
    ranked_claims = sorted((graph.claims[c] for c in critical_ids if c in graph.claims and graph.evidence_for(c)),
                           key=lambda c: (-c.importance, -c.evidence_sufficiency))
    for c in ranked_claims[:12]:
        b = beliefs.claims.get(c.id)
        lines = {"supports": [], "contradicts": []}
        for e in sorted(graph.evidence_for(c.id), key=lambda e: -e.directness):
            if e.stance in lines:
                lines[e.stance].append(EvidenceLine(evidence_id=e.id, stance=e.stance, excerpt=e.exact_excerpt, citation=cite(e.source_id),
                                                    directness=e.directness, reported_speech=e.reported_speech))
        claim_views.append(ClaimView(
            id=c.id, text=c.natural_language, kind=c.kind, period=describe(c.temporal_scope), posterior=c.truth_probability,
            sufficiency=c.evidence_sufficiency, status=c.status.value, raw_sources=b.raw_sources if b else 0,
            independent_roots=b.independent_roots if b else 0, support=lines["supports"][:4], against=lines["contradicts"][:4],
            missing=[g.description for g in open_gaps if g.target_id == c.id][:3],
            history=[o.value["p"] for o in graph.history(c.id)],
        ))

    hyp_views = [HypothesisView(
        id=x.id, text=x.text, is_null=x.is_null_hypothesis, prior=x.prior_probability, posterior=x.posterior_probability,
        sufficiency=x.evidence_sufficiency, inference_validity=x.inference_validity, status=x.status,
        accepted_inferences=[f"{i.id}: {i.statement}" for i in graph.inferences_for(x.id) if i.status == "accepted"],
        rejected_inferences=[f"{i.id} ({i.status}): {i.statement} — {i.failure_reason}" for i in graph.inferences_for(x.id) if i.status != "accepted"],
        history=[o.value["p"] for o in graph.history(x.id)],
    ) for x in hyps]

    # Executive prose: model writes, verifier gates.
    conclusion: list[Statement] = []
    rejected: list[dict] = []
    change: list[str] = []
    if llm is not None:
        payload = {
            "question": session.question, "overall_status": status.value,
            "hypotheses": [{"id": h.id, "text": h.text, "model_estimated_posterior": round(h.posterior, 2),
                            "evidence_sufficiency": round(h.sufficiency, 2), "status": h.status} for h in hyp_views],
            "claims": [{"id": c.id, "text": c.text, "posterior": round(c.posterior, 2), "sufficiency": round(c.sufficiency, 2),
                        "status": c.status, "independent_roots": c.independent_roots, "raw_sources": c.raw_sources} for c in claim_views],
            "top_gaps": [g.description for g in open_gaps[:5]],
        }
        try:
            out = await llm.structured("synthesize", ModelRole.SYNTHESIS, SYNTHESIZER, payload, SynthesisOutput)
            change = out.what_would_change_our_mind[:4]
            for sent in out.conclusion:
                check = verifier.check(sent.text, sent.claim_ids)
                if check.ok:
                    cites = sorted({cite(e.source_id) for cid in sent.claim_ids for e in graph.evidence_for(cid) if e.stance != "neutral"})
                    conclusion.append(Statement(text=sent.text, claim_ids=sent.claim_ids, citations=cites))
                else:
                    rejected.append({"text": sent.text, "claim_ids": sent.claim_ids, "reason": check.reason})
                    events.emit(EventType.STATEMENT_REJECTED, f"report sentence dropped ({check.reason}): {sent.text[:90]}")
        except LLMError as e:
            events.emit(EventType.ERROR, f"synthesis failed, using structured summary only: {e}")
    change += [f"Evidence resolving: {g.description}" for g in open_gaps[:3] if g.estimated_value >= 0.15]

    raw = len({e.source_id for e in graph.evidence.values()})
    roots = len({graph.root_of.get(e.source_id, e.source_id) for e in graph.evidence.values()})
    clusters = [{"root": r, "root_title": graph.sources[r].title, "members": m}
                for r, m in sorted(_clusters(graph).items(), key=lambda kv: -len(kv[1])) if len(m) > 1]
    method = [
        "Hypothesis-first research: competing hypotheses and evidence requirements were generated before searching.",
        "LLMs proposed claims, stances and inferences; code verified excerpts verbatim, counted sources and computed every score.",
        "Probabilities are model-estimated evidence beliefs from heuristic likelihood ratios, NOT calibrated probabilities.",
        f"Evidence from one provenance cluster counts once; derivatives add {settings.heuristics.dependent_evidence_discount:.0%} of their weight.",
        "Source credibility uses heuristic priors by source type, adjusted per claim category; no audited ratings.",
        f"Stop reason: {session.stop_reason.value if session.stop_reason else 'n/a'} — {session.stop_explanation or ''}",
    ]
    if session.synthetic:
        method.insert(0, "SYNTHETIC DEMO: the corpus and model responses are scripted fixtures, not real-world evidence.")

    report = Report(
        question=session.question, synthetic=session.synthetic, status=status,
        stop_reason=session.stop_reason.value if session.stop_reason else None, stop_explanation=session.stop_explanation,
        leading_hypothesis=lead.id if lead else None, conclusion=conclusion, rejected_statements=rejected,
        hypotheses=hyp_views, critical_claims=claim_views, raw_source_count=raw, independent_root_count=roots,
        clusters=clusters,
        gaps=[GapView(id=g.id, gap_type=g.gap_type, description=g.description, value=g.estimated_value, level=_debt(g.estimated_value),
                      attempts=g.attempts, unresolvable=g.unresolvable) for g in open_gaps[:10]],
        what_would_change=change, method_limitations=method,
        citations=sorted(citations.values(), key=lambda c: c.n),
        stats={"iterations": session.iteration, "searches": session.search_count, "extractions": session.extract_count,
               "model_calls": session.model_call_count, **graph.stats()},
    )
    events.emit(EventType.REPORT_GENERATED, f"report: {status.value}, {len(conclusion)} verified sentence(s), {len(rejected)} rejected, "
                                            f"{len(report.citations)} citation(s)", status=status.value)
    return report


def _clusters(graph: EvidenceGraph) -> dict[str, list[str]]:
    used = {e.source_id for e in graph.evidence.values()}
    out: dict[str, list[str]] = {}
    for sid in used:
        out.setdefault(graph.root_of.get(sid, sid), []).append(sid)
    return {k: sorted(v) for k, v in out.items()}
