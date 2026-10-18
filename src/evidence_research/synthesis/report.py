"""Final report (section 31). Structure and numbers come from the graph; only the executive prose
comes from the model, and every sentence of it must pass the CitationVerifier or it is dropped."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from ..config import Settings
from ..evidence.temporal import describe
from ..graph.active import ActiveResearchGraph
from ..graph.evidence_graph import EvidenceGraph
from ..llm.gateway import LLMError, LLMGateway, ModelRole
from ..llm.prompts import SYNTHESIZER
from ..models import EvidenceStatus, QuestionAnalysis, ResearchSession, SynthesisOutput
from ..observability.events import EventLog, EventType
from ..probability.engine import BeliefState
from ..probability.uncertainty import overall_status
from ..verification.citation_verifier import CitationVerifier, strip_ids


class Citation(BaseModel):
    n: int
    source_id: str
    title: str
    url: str
    deep_link: str = ""  # URL with a text fragment that scrolls to the first quoted excerpt
    excerpts: list[str] = Field(default_factory=list)  # every verbatim excerpt this report relies on
    uses: list[dict] = Field(default_factory=list)  # per excerpt: claim it supports/contradicts, stance, deep link
    publisher: str
    published_at: date | None
    retrieved_at: datetime
    independent_root: str


class EvidenceLine(BaseModel):
    evidence_id: str
    stance: str
    excerpt: str
    location: str | None
    citation: int
    directness: float
    reported_speech: bool
    quality: dict = Field(default_factory=dict)  # separate dimensions (section 28)


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
    evidence_ids: list[str] = Field(default_factory=list)
    citations: list[int] = Field(default_factory=list)


class PyramidLine(BaseModel):
    statement: Statement
    support: list[Statement] = Field(default_factory=list)


class StudyView(BaseModel):
    id: str
    title: str
    versions: list[dict]
    design: str | None
    sample_size: int | None
    peer_reviewed: bool | None
    preregistered: bool | None
    quality: float
    replication: list[str]
    warnings: list[str]
    results: list[dict]


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
    counter_hypothesis: str | None
    # Minto pyramid: answer first, MECE key lines, facts under each. Every sentence is citation-verified.
    governing_thought: Statement | None
    governing_is_system_summary: bool
    key_lines: list[PyramidLine]
    caveats: list[str]
    decision_trace: list[str]  # the agent's decisions in order (for judges: decisions, not a script)
    conclusion: list[Statement]  # every verified pyramid sentence, flattened (for audits and tests)
    rejected_statements: list[dict]
    hypotheses: list[HypothesisView]
    critical_claims: list[ClaimView]
    raw_source_count: int
    publication_family_count: int
    independent_root_count: int
    clusters: list[dict]
    studies: list[StudyView]
    screened_out: list[dict]
    why_stopped: list[str]
    gaps: list[GapView]
    what_would_change: list[str]
    method_limitations: list[str]
    citations: list[Citation]
    stats: dict


def _debt(value: float) -> str:
    return "HIGH" if value >= 0.35 else "MEDIUM" if value >= 0.15 else "LOW"


async def build_report(llm: LLMGateway | None, graph: EvidenceGraph, session: ResearchSession, analysis: QuestionAnalysis,
                       beliefs: BeliefState, critical_ids: set[str], settings: Settings, events: EventLog,
                       active: ActiveResearchGraph | None = None) -> Report:
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
        ranked = sorted(graph.evidence_for(c.id), key=lambda e: -(graph.evidence_quality[e.id].strength if e.id in graph.evidence_quality else 0))
        lines = {"supports": [], "contradicts": []}
        for stance in lines:
            for e in [e for e in ranked if e.stance == stance][:4]:  # cite only what is shown: no citation without a quote
                q = graph.evidence_quality.get(e.id)
                lines[stance].append(EvidenceLine(evidence_id=e.id, stance=e.stance, excerpt=e.exact_excerpt, location=e.location,
                                                  citation=cite(e.source_id), directness=e.directness, reported_speech=e.reported_speech,
                                                  quality=q.model_dump(exclude={"evidence_id"}) if q else {}))
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
        rejected_inferences=[f"{i.id} ({i.status}): {i.statement} — {'; '.join(i.failure_reasons)}" for i in graph.inferences_for(x.id) if i.status != "accepted"],
        history=[o.value["p"] for o in graph.history(x.id)],
    ) for x in hyps]

    # Executive answer as a Minto pyramid: the model writes, the verifier gates every sentence.
    conclusion: list[Statement] = []
    rejected: list[dict] = []
    change: list[str] = []
    governing: Statement | None = None
    key_lines: list[PyramidLine] = []

    def verified(text: str, claim_ids: list[str], level: str) -> Statement | None:
        check = verifier.check(text, claim_ids)
        if not check.ok:
            rejected.append({"text": text, "claim_ids": claim_ids, "level": level, "reason": check.reason})
            events.emit(EventType.STATEMENT_REJECTED, f"{level} dropped ({check.reason}): {text[:90]}")
            return None
        cites = sorted({cite(graph.evidence[eid].source_id) for eid in check.evidence_ids})
        st = Statement(text=strip_ids(text), claim_ids=claim_ids, evidence_ids=check.evidence_ids, citations=cites)
        conclusion.append(st)
        return st
    if llm is not None:
        payload = {
            "question": session.question, "overall_status": status.value,
            "hypotheses": [{"id": h.id, "text": h.text, "model_estimated_posterior": round(h.posterior, 2),
                            "evidence_sufficiency": round(h.sufficiency, 2), "status": h.status} for h in hyp_views],
            "claims": [{"id": c.id, "text": c.text, "posterior": round(c.posterior, 2), "sufficiency": round(c.sufficiency, 2),
                        "status": c.status, "independent_roots": c.independent_roots, "raw_sources": c.raw_sources} for c in claim_views],
            "top_gaps": [g.description for g in open_gaps[:5]],
            "recent_updates": active.recent_updates if active else [],
        }
        try:
            out = await llm.structured("synthesize", ModelRole.SYNTHESIS, SYNTHESIZER, payload, SynthesisOutput)
            change = out.what_would_change_our_mind[:4]
            for kl in out.key_lines[:4]:
                support = [st for p in kl.support[:3] if (st := verified(p.text, p.claim_ids, "support point"))]
                # A key line without its own IDs rests on its support; it is still number-checked against them.
                ids = kl.claim_ids or sorted({c for st in support for c in st.claim_ids})
                line = verified(kl.text, ids, "key line") if support else None
                if line is None:
                    if support:
                        rejected.append({"text": kl.text, "claim_ids": ids, "level": "key line", "reason": "key line failed verification"})
                    continue
                key_lines.append(PyramidLine(statement=line, support=support))
            g_ids = out.governing_thought.claim_ids or sorted({c for kl in key_lines for c in kl.statement.claim_ids})
            governing = verified(out.governing_thought.text, g_ids, "governing thought") if key_lines else None
        except LLMError as e:
            events.emit(EventType.ERROR, f"synthesis failed, using structured summary only: {e}")
    change += [f"Evidence resolving: {g.description}" for g in open_gaps[:3] if g.estimated_value >= 0.15]
    system_summary = governing is None
    if system_summary:  # labelled, number-free fallback built by code from the leading hypothesis
        text = (f"{status.value.replace('_', ' ').capitalize()}: {lead.text}" if lead else
                f"{status.value.replace('_', ' ').capitalize()}: no hypothesis is supported by the evidence found.")
        governing = Statement(text=text, claim_ids=[])

    used = {e.source_id for e in graph.evidence.values() if e.verification_status == "verified"}
    raw = len(used)
    families = len({graph.family_of.get(s, s) for s in used})
    roots = len({graph.root_of.get(s, s) for s in used})
    counter = next((x for x in non_null[1:] if x.status != "rejected"), None)
    studies = [_study_view(graph, st) for st in graph.studies.values()]
    screened_out = [{"source_id": d.source_id, "title": graph.sources[d.source_id].title, "url": graph.sources[d.source_id].url,
                     "reasons": d.reasons} for d in graph.screening.values() if d.decision == "exclude"]
    why = [f"{session.stop_reason.value if session.stop_reason else 'n/a'}: {session.stop_explanation or ''}"]
    if graph.bids:
        it, last = graph.bids[-1]
        why.append("Final agent bids: " + ", ".join(f"{b.agent_type} {b.utility:.2f}" for b in last))
    clusters = [{"root": r, "root_title": graph.sources[r].title, "members": m}
                for r, m in sorted(_clusters(graph).items(), key=lambda kv: -len(kv[1])) if len(m) > 1]
    caveats = _caveats(graph, claim_views, open_gaps, raw, roots, used)
    # Every citation carries EVERY excerpt the report relies on, with the claim it bears on, so a reader
    # can check each one on the page (and re-check them all live: verification/citation_audit.py).
    def use(e_id: str) -> None:
        e = graph.evidence[e_id]
        cite(e.source_id)  # registers the source if this is its first use
        c = citations[e.source_id]
        if any(u["evidence_id"] == e.id for u in c.uses):
            return
        if e.exact_excerpt not in c.excerpts:
            c.excerpts.append(e.exact_excerpt)
        c.uses.append({"evidence_id": e.id, "claim_id": e.claim_id, "claim": graph.claims[e.claim_id].natural_language,
                       "stance": e.stance, "excerpt": e.exact_excerpt, "location": e.location,
                       "deep_link": text_fragment_link(c.url, e.exact_excerpt)})
    for st in conclusion:
        for eid in st.evidence_ids:
            use(eid)
    for cv in claim_views:
        for line in cv.support + cv.against:
            use(line.evidence_id)
    for c in citations.values():
        c.deep_link = c.uses[0]["deep_link"] if c.uses else c.url
    decisions = _decision_trace(events)
    method = [
        "Hypothesis-first research: competing hypotheses and evidence requirements were generated before searching.",
        "LLMs proposed claims, stances and inferences; code verified excerpts verbatim, counted sources and computed every score.",
        "Probabilities are model-estimated evidence beliefs from heuristic likelihood ratios, NOT calibrated probabilities.",
        f"Evidence from one provenance cluster counts once; derivatives add {settings.heuristics.dependent_evidence_discount:.0%} of their weight.",
        "Source credibility uses heuristic priors by source type, adjusted per claim category; no audited ratings.",
        "Scientific evidence is weighted by a deterministic study-quality score and replication factors; peer review alone is not decisive.",
        "Research agents were chosen each round by heuristic utility bids, not by a fixed pipeline.",
        f"{len(screened_out)} source(s) were screened out before extraction; reasons are preserved (negative provenance).",
        f"Stop reason: {session.stop_reason.value if session.stop_reason else 'n/a'} — {session.stop_explanation or ''}",
    ]
    if session.synthetic:
        method.insert(0, "SYNTHETIC DEMO: the corpus and model responses are scripted fixtures, not real-world evidence.")

    report = Report(
        question=session.question, synthetic=session.synthetic, status=status,
        stop_reason=session.stop_reason.value if session.stop_reason else None, stop_explanation=session.stop_explanation,
        leading_hypothesis=lead.id if lead else None, counter_hypothesis=counter.id if counter else None,
        governing_thought=governing, governing_is_system_summary=system_summary, key_lines=key_lines, caveats=caveats,
        decision_trace=decisions,
        conclusion=conclusion, rejected_statements=rejected,
        hypotheses=hyp_views, critical_claims=claim_views, raw_source_count=raw, publication_family_count=families,
        independent_root_count=roots, clusters=clusters, studies=studies, screened_out=screened_out, why_stopped=why,
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


_DECISION_EVENTS = {EventType.AGENT_SELECTED, EventType.INDEPENDENCE_SUMMARY, EventType.SCIENTIFIC_VERSION_RESOLVED,
                    EventType.STUDY_RELATION_FOUND, EventType.INFERENCE_REJECTED, EventType.INFERENCE_ACCEPTED, EventType.NECESSITY_ASSESSED,
                    EventType.CONTRADICTION_FOUND, EventType.TEMPORAL_VERSION_DETECTED, EventType.RESEARCH_GAP_UNRESOLVABLE,
                    EventType.STOP_DECISION, EventType.STATEMENT_REJECTED}
_PER_TYPE_CAP = {EventType.INFERENCE_REJECTED: 4, EventType.INFERENCE_ACCEPTED: 3, EventType.CONTRADICTION_FOUND: 3,
                 EventType.NECESSITY_ASSESSED: 2, EventType.STATEMENT_REJECTED: 3}


def _decision_trace(events: EventLog, limit: int = 28) -> list[str]:
    """The decisions code made, in order, with their reasons: which agent ran and why, what was rejected,
    where sources collapsed into one root, why research stopped."""
    out, seen = [], {}
    stops = [e for e in events.of_type(EventType.STOP_DECISION) if e.data.get("stop") is not None]
    for e in events.events:
        if e.type not in _DECISION_EVENTS:
            continue
        if e.type is EventType.STOP_DECISION and e not in stops:
            continue
        seen[e.type] = seen.get(e.type, 0) + 1
        if seen[e.type] > _PER_TYPE_CAP.get(e.type, 99):
            continue
        out.append(f"{e.type.value.replace('_', ' ').lower()}: {e.message[:220]}")
    return out[:limit] if len(out) <= limit else out[: limit - 1] + [out[-1]]


def text_fragment_link(url: str, excerpt: str) -> str:
    """https://page#:~:text=start,end — browsers that support text fragments scroll to and highlight it.
    Skipped for table excerpts (markdown pipes do not appear on the rendered page)."""
    from urllib.parse import quote

    if not excerpt or any(ch in excerpt for ch in "|*#`") or "#" in url:
        return url
    words = excerpt.split()
    if len(words) <= 8:
        frag = quote(" ".join(words), safe="")
    else:
        frag = quote(" ".join(words[:5]), safe="") + "," + quote(" ".join(words[-3:]), safe="")
    return f"{url}#:~:text={frag}"


def _caveats(graph: EvidenceGraph, claims: list[ClaimView], open_gaps, raw: int, roots: int, used: set[str]) -> list[str]:
    """Computed by code from the graph, never written by the model."""
    out = []
    interested = {graph.root_of.get(s, s) for s in used}
    interested = [r for r in interested if r in graph.assessments and graph.assessments[r].conflict_of_interest >= 0.5]
    if raw:
        line = f"Source independence: {raw} sources with evidence reduce to {roots} independent roots"
        out.append(line + (f"; {len(interested)} of these are interested parties (self-reported)." if interested else "."))
    contested = [c for c in claims if c.status == "contested"]
    if contested:
        out.append(f"Contradicted: {len(contested)} key claim(s) have independent evidence against them, e.g. \"{contested[0].text}\".")
    single = [c for c in claims if c.independent_roots <= 1]
    if single:
        out.append(f"Thinly sourced: {len(single)} of {len(claims)} key claims rest on a single independent source.")
    high = [g for g in open_gaps if _debt(g.estimated_value) == "HIGH"][:2]
    for g in high:
        out.append(f"Open gap [{g.gap_type}]: {g.description}")
    out.append("Confidence values are model-estimated evidence beliefs from explicit heuristics, not calibrated probabilities.")
    return out


def _study_view(graph: EvidenceGraph, st) -> StudyView:
    sa = graph.study_assessments[st.id]
    versions = [{"source_id": graph.documents[d].source_id, "document_type": graph.documents[d].document_type,
                 "url": graph.sources[graph.documents[d].source_id].url, "peer_reviewed": graph.documents[d].peer_reviewed}
                for d in st.document_ids if d in graph.documents]
    rel = [f"{r.from_study_id} {r.relation} {r.to_study_id}" for r in graph.study_relations.values() if st.id in (r.from_study_id, r.to_study_id)]
    results = [{"id": r.id, "outcome": r.outcome, "effect": r.effect_size, "measure": r.effect_measure, "ci": [r.ci_low, r.ci_high],
                "p": r.p_value, "n": r.sample_size, "status": r.verification_status, "excerpt": r.exact_excerpt}
               for r in graph.results.values() if r.study_id == st.id]
    return StudyView(id=st.id, title=st.title, versions=versions, design=sa.study_design, sample_size=sa.sample_size,
                     peer_reviewed=sa.peer_reviewed, preregistered=sa.preregistered, quality=sa.quality_score, replication=rel,
                     warnings=sa.notes, results=results)


def _clusters(graph: EvidenceGraph) -> dict[str, list[str]]:
    used = {e.source_id for e in graph.evidence.values() if e.verification_status == "verified"}
    out: dict[str, list[str]] = {}
    for sid in used:
        out.setdefault(graph.root_of.get(sid, sid), []).append(sid)
    return {k: sorted(v) for k, v in out.items()}
