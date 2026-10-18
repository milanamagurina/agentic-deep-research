"""Source screening before extraction (section 8). Exclusions are preserved: negative provenance.

1. code rules: same-site mirrors (same title, same domain), publication date long before the requested
   period. Same title on DIFFERENT sites is kept: it may be another version of one work, which the
   ScientificSourceResolver groups instead of discarding;
2. one batched model call per round on title / URL / snippet: include | exclude | uncertain,
   reasons, relevance category and document type;
3. every decision is stored in the vault (SAT_SCREENING) and emitted as SOURCE_SCREENED.
"""

from __future__ import annotations

import re

from ..graph.evidence_graph import EvidenceGraph
from ..llm.gateway import LLMError, LLMGateway, ModelRole
from ..llm.prompts import SCREENER
from ..models import QuestionAnalysis, ScreeningDecision, ScreeningOutput, Source
from ..observability.events import EventLog, EventType
from .url_normalizer import registrable_domain

RELEVANCE = {"low": 0.3, "medium": 0.6, "high": 0.9}


def _title_key(title: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", title.lower()))


def scope_start_year(analysis: QuestionAnalysis) -> int | None:
    years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", analysis.temporal_scope or "")]
    return min(years) if years else None


class Screener:
    def __init__(self, llm: LLMGateway, graph: EvidenceGraph, events: EventLog) -> None:
        self.llm, self.graph, self.events = llm, graph, events

    def _record(self, d: ScreeningDecision) -> ScreeningDecision:
        self.graph.set_screening(d)
        self.events.emit(EventType.SOURCE_SCREENED, f"{d.source_id}: {d.decision.upper()} [{d.document_type}] ({d.decided_by}) — {'; '.join(d.reasons)}",
                         source_id=d.source_id, decision=d.decision, reasons=d.reasons, document_type=d.document_type)
        return d

    async def screen(self, candidates: list[Source], analysis: QuestionAnalysis, question: str) -> dict[str, ScreeningDecision]:
        out: dict[str, ScreeningDecision] = {}
        seen_titles = {(_title_key(self.graph.sources[sid].title), registrable_domain(self.graph.sources[sid].url)): sid
                       for sid, d in self.graph.screening.items() if d.decision == "include" and self.graph.sources[sid].title}
        start = scope_start_year(analysis)
        to_model: list[Source] = []
        for s in candidates:
            key = (_title_key(s.title), registrable_domain(s.url))
            if len(key[0]) > 20 and key in seen_titles and seen_titles[key] != s.id:
                out[s.id] = self._record(ScreeningDecision(source_id=s.id, decision="exclude", relevance_score=0.0, decided_by="rule",
                                                           reasons=[f"duplicate source: same title on the same site as {seen_titles[key]}"]))
                continue
            seen_titles.setdefault(key, s.id)
            to_model.append(s)

        verdicts = {}
        if to_model:
            payload = {"question": question, "temporal_scope": analysis.temporal_scope,
                       "results": [{"source_id": s.id, "title": s.title, "url": s.url, "published": s.published_at,
                                    "snippet": s.snippet[:400]} for s in to_model]}
            try:
                res = await self.llm.structured("screen_sources", ModelRole.FAST, SCREENER, payload, ScreeningOutput)
                verdicts = {j.source_id: j for j in res.decisions}
            except LLMError as e:
                self.events.emit(EventType.ERROR, f"screening model failed; sources marked uncertain: {e}")

        for s in to_model:
            j = verdicts.get(s.id)
            if j is None:
                d = ScreeningDecision(source_id=s.id, decision="uncertain", relevance_score=0.5, decided_by="rule",
                                      reasons=["no screening judgement returned"])
            else:
                d = ScreeningDecision(source_id=s.id, decision=j.decision, reasons=j.reasons or ["(no reason given)"],
                                      relevance_score=RELEVANCE[j.relevance], document_type=j.document_type)
            if start and s.published_at and s.published_at.year < start - 2 and d.decision == "include":
                d = d.model_copy(update={"decision": "uncertain", "reasons": d.reasons + [f"published {s.published_at.year}, before requested period ({start}+)"]})
            out[s.id] = self._record(d)
        return out


def select_for_extraction(candidates: list[Source], decisions: dict[str, ScreeningDecision], k: int) -> list[Source]:
    """Included sources by relevance (rank order breaks ties), then uncertain ones if capacity remains."""
    rank = {s.id: i for i, s in enumerate(candidates)}
    inc = [s for s in candidates if decisions.get(s.id) and decisions[s.id].decision == "include"]
    unc = [s for s in candidates if decisions.get(s.id) and decisions[s.id].decision == "uncertain"]
    key = lambda s: (-decisions[s.id].relevance_score, rank[s.id])  # noqa: E731
    return (sorted(inc, key=key) + sorted(unc, key=key))[:k]
