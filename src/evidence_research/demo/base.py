"""Shared machinery for SYNTHETIC offline scenarios (fictional entities on reserved ``.example`` domains).

Only the two external dependencies are replaced; everything else is the real pipeline:
  * ``FakeSearch``  - a keyword-triggered corpus standing in for Tavily search/extract;
  * ``ScriptedLLM`` - deterministic answers per semantic operation, computed only from the structured
                      payload the real code sends, so parallel calls and ordering cannot change results.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, TypeVar

from pydantic import BaseModel

from ..evidence.claim_normalizer import normalize_text
from ..llm.gateway import CallRecord, ModelRole
from ..models import (
    ExistingClaimEvidenceProposal, ExtractedClaimProposal, ExtractionOutput, HypothesesOutput, ImpactOutput, InferenceProposal,
    InferenceProposalOutput, InferenceVerdict, InferenceVerdictOutput, NecessityJudgement, NecessityOutput, QueryPlanOutput,
    QuestionAnalysis, SameClaimOutput, SameClaimVerdict, ScientificReviewOutput, ScreeningJudgement, ScreeningOutput,
    StanceJudgement, StanceOutput, SynthesisOutput,
)
from ..orchestration.budget import BudgetTracker
from ..retrieval.tavily_client import ExtractedPage, SearchHit

T = TypeVar("T", bound=BaseModel)


@dataclass
class PageClaim:
    nl: str
    subject: str
    predicate: str
    obj: str
    excerpt: str
    category: str = "other"
    period: tuple[date, date] | None = None
    req_keywords: tuple[str, ...] = ()
    importance: str = "medium"
    attributed_to: str | None = None


@dataclass
class Page:
    url: str
    title: str
    published: date | None
    text: str
    triggers: tuple[tuple[str, ...], ...]
    score: float
    claims: list[PageClaim] = field(default_factory=list)
    bears_on: list[tuple[tuple[str, ...], str]] = field(default_factory=list)  # (keywords of an existing claim, excerpt)
    doc_type: str = "unknown"
    review: ScientificReviewOutput | None = None
    screen: tuple[str, list[str]] | None = None  # override (decision, reasons)

    def __post_init__(self) -> None:
        for c in self.claims:  # a scenario bug, not a runtime condition: fail at import
            assert c.excerpt in self.text, f"excerpt not in page {self.url}: {c.excerpt[:60]}"
        for _, ex in self.bears_on:
            assert ex in self.text, f"excerpt not in page {self.url}: {ex[:60]}"


class FakeSearch:
    """A query hits a page when all words of one trigger tuple occur in it."""

    def __init__(self, pages: list[Page]) -> None:
        self.pages = pages
        self.by_url = {p.url: p for p in pages}
        self.queries: list[str] = []
        self.extracted: list[str] = []

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        self.queries.append(query)
        words = set(re.findall(r"[a-z0-9%]+", query.lower()))
        hits = [p for p in self.pages if any(set(t) <= words for t in p.triggers)]
        return [SearchHit(url=p.url, title=p.title, content=p.text[:300], score=p.score, published_date=p.published, raw={"synthetic": True})
                for p in sorted(hits, key=lambda p: -p.score)[:max_results]]

    async def extract(self, urls: list[str]) -> tuple[list[ExtractedPage], list[str]]:
        self.extracted += urls
        return [ExtractedPage(url=u, raw_content=self.by_url[u].text) for u in urls if u in self.by_url], [u for u in urls if u not in self.by_url]


def find(items: list[dict], *keywords: str, key: str = "text") -> str | None:
    for it in items:
        text = it.get(key, "").lower()
        if all(k.lower() in text for k in keywords):
            return it["id"]
    return None


def _sig(text: str) -> set[str]:
    out = set()
    for tok in normalize_text(text).split():
        try:
            v = float(tok)
        except ValueError:
            continue
        if v > 100 and not 1900 <= v <= 2100:
            out.add(f"{v:.3g}")
    return out


class Scenario:
    """Override the data attributes and the three reasoning hooks in a concrete scenario."""
    name = "base"
    question = ""
    today = date(2026, 10, 18)
    pages: list[Page] = []
    query_table: dict[str, list[tuple[str, str]]] = {}   # agent -> [(keyword in target, query)]
    default_queries: dict[str, list[str]] = {}            # agent -> queries when no keyword matches
    stances: list[tuple[str, str, str, str, str]] = []    # (excerpt fragment, claim keyword, stance, strength, directness)
    high_impact: tuple[str, ...] = ()
    necessary_keywords: tuple[str, ...] = ()

    def analysis(self) -> QuestionAnalysis: raise NotImplementedError
    def hypotheses(self) -> HypothesesOutput: raise NotImplementedError
    def propose(self, claims: list[dict]) -> list[InferenceProposal]: raise NotImplementedError
    def verify(self, inf: dict) -> InferenceVerdict: raise NotImplementedError
    def synthesize(self, claims: list[dict]) -> SynthesisOutput: raise NotImplementedError


class ScriptedLLM:
    """Deterministic LLMGateway for a synthetic scenario. Charges the budget like the real gateway."""

    def __init__(self, scenario: Scenario, budget: BudgetTracker | None = None) -> None:
        self.sc = scenario
        self.by_url = {p.url: p for p in scenario.pages}
        self.budget = budget
        self.records: list[CallRecord] = []
        self.calls: list[str] = []

    async def structured(self, op: str, role: ModelRole, system: str, payload: dict[str, Any], schema: type[T]) -> T:
        if self.budget:
            self.budget.charge_model_call(final=role is ModelRole.SYNTHESIS)
        self.calls.append(op)
        result = getattr(self, f"_{op}")(payload)
        self.records.append(CallRecord(operation=op, role=role.value, model=f"scripted-{self.sc.name}", latency_s=0.0, ok=True))
        return schema.model_validate(result.model_dump() if isinstance(result, BaseModel) else result)

    def _analyze_question(self, p: dict) -> QuestionAnalysis:
        return self.sc.analysis()

    def _generate_hypotheses(self, p: dict) -> HypothesesOutput:
        return self.sc.hypotheses()

    def _plan_queries(self, p: dict) -> QueryPlanOutput:
        agent, queries = p["agent"], []
        table = self.sc.query_table.get(agent, [])
        for t in p["targets"]:
            text = " ".join(str(v) for v in t.values() if isinstance(v, str)).lower()
            q = next((q for k, q in table if k in text), None)
            if q and q not in queries:
                queries.append(q)
        if not queries:
            queries = list(self.sc.default_queries.get(agent, []))
        return QueryPlanOutput(queries=queries[: p["max_queries"]])

    def _screen_sources(self, p: dict) -> ScreeningOutput:
        out = []
        for r in p["results"]:
            page = self.by_url.get(r["url"])
            if page and page.screen:
                decision, reasons = page.screen
            else:
                decision, reasons = "include", ["directly reports evidence on the question"]
            out.append(ScreeningJudgement(source_id=r["source_id"], decision=decision, reasons=reasons, relevance="high",
                                          document_type=page.doc_type if page else "unknown"))
        return ScreeningOutput(decisions=out)

    def _extract_claims(self, p: dict) -> ExtractionOutput:
        page = self.by_url[p["source_url"]]
        claims = []
        for c in page.claims:
            req_ids = [r["id"] for r in p["requirements"] if any(k in r["description"].lower() for k in c.req_keywords)]
            claims.append(ExtractedClaimProposal(
                subject=c.subject, predicate=c.predicate, object=c.obj, natural_language=c.nl, exact_excerpt=c.excerpt,
                attributed_to=c.attributed_to, category=c.category, valid_from=c.period[0] if c.period else None,
                valid_to=c.period[1] if c.period else None, requirement_ids=req_ids, importance=c.importance))
        bears = [ExistingClaimEvidenceProposal(claim_id=cid, exact_excerpt=ex)
                 for kws, ex in page.bears_on if (cid := find(p["existing_claims"], *kws))]
        return ExtractionOutput(published_at=page.published, claims=claims, bears_on_existing=bears)

    def _review_study(self, p: dict) -> ScientificReviewOutput:
        page = self.by_url[p["source_url"]]
        return page.review or ScientificReviewOutput(is_empirical_study=False)

    def _match_claims(self, p: dict) -> SameClaimOutput:
        return SameClaimOutput(results=[SameClaimVerdict(pair_id=x["pair_id"], verdict="SAME" if _sig(x["a"]) and _sig(x["a"]) == _sig(x["b"]) else "DIFFERENT")
                                        for x in p["pairs"]])

    def _judge_stance(self, p: dict) -> StanceOutput:
        out = []
        for pair in p["pairs"]:
            stance, strength, directness = "supports", "explicit", "direct"
            for frag, claim_kw, st, sg, dr in self.sc.stances:
                if frag in pair["excerpt"] and claim_kw in pair["claim"]:
                    stance, strength, directness = st, sg, dr
            if pair["excerpt_is_reported_speech"] and stance == "supports":
                strength, directness = "strong", "indirect"
            out.append(StanceJudgement(pair_id=pair["pair_id"], stance=stance, strength=strength, directness=directness))
        return StanceOutput(judgements=out)

    def _propose_inferences(self, p: dict) -> InferenceProposalOutput:
        return InferenceProposalOutput(inferences=self.sc.propose([c for c in p["claims"] if c["kind"] == "fact"]))

    def _verify_inferences(self, p: dict) -> InferenceVerdictOutput:
        return InferenceVerdictOutput(verdicts=[self.sc.verify(i) for i in p["inferences"]])

    def _assess_necessity(self, p: dict) -> NecessityOutput:
        out = []
        for prem in p["premises"]:
            needed = any(k in prem["text"].lower() for k in self.sc.necessary_keywords)
            out.append(NecessityJudgement(premise_id=prem["id"], still_justified_without_it=not needed,
                                          reason="the remaining premises do not establish the conclusion" if needed
                                          else "other premises carry the conclusion without it"))
        return NecessityOutput(judgements=out)

    def _rate_gap_impact(self, p: dict) -> ImpactOutput:
        def rate(d: str) -> str:
            d = d.lower()
            return "high" if any(k in d for k in self.sc.high_impact) else "low" if "outdated" in d else "medium"
        return ImpactOutput(impacts={g["id"]: rate(g["description"]) for g in p["gaps"]})

    def _synthesize(self, p: dict) -> SynthesisOutput:
        return self.sc.synthesize(p["claims"])
