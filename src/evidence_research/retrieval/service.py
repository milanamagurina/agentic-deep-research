"""Retrieval policy (section 7): search broadly, rank, dedup, select, then extract selected URLs only."""

from __future__ import annotations

import asyncio

from ..config import Settings
from ..graph.evidence_graph import EvidenceGraph
from ..models import Source, stable_id
from ..observability.events import EventLog, EventType
from ..orchestration.budget import BudgetExceeded, BudgetTracker
from .source_ranker import rank_hits
from .tavily_client import SearchClient, SearchHit
from .url_normalizer import canonicalize, registrable_domain


class RetrievalService:
    def __init__(self, client: SearchClient, graph: EvidenceGraph, budget: BudgetTracker, events: EventLog, settings: Settings) -> None:
        self.client = client
        self.graph = graph
        self.budget = budget
        self.events = events
        self.s = settings

    async def search(self, queries: list[str], origin: str, key_entities: list[str]) -> list[Source]:
        """Run queries in parallel; return NEW candidate sources (not yet extracted), best first."""
        runnable = []
        for q in queries:
            try:
                self.budget.charge_search()
            except BudgetExceeded:
                self.events.emit(EventType.STOP_DECISION, f"search budget reached; skipped query {q!r}")
                break
            runnable.append(q)
            self.events.emit(EventType.SEARCH_PLANNED, f"[{origin}] {q!r}", query=q, origin=origin)
        results = await asyncio.gather(*(self.client.search(q, self.s.search_max_results) for q in runnable))

        known = {s.canonical_url for s in self.graph.sources.values()}
        scored: list[tuple[float, Source]] = []
        for q, hits in zip(runnable, results):
            self.events.emit(EventType.SEARCH_EXECUTED, f"{q!r} → {len(hits)} result(s)", query=q, n=len(hits), origin=origin)
            for score, hit, reason in rank_hits(hits, known, key_entities):
                src = self._to_source(hit, q, origin)
                known.add(src.canonical_url)
                self.graph.add_source(src)
                scored.append((score, src))
                self.events.emit(EventType.SOURCE_FOUND, f"{src.id} {src.publisher}: {src.title[:70]} ({reason})",
                                 source_id=src.id, url=src.url, score=score)
        return [s for _, s in sorted(scored, key=lambda t: -t[0])]

    def _to_source(self, hit: SearchHit, query: str, origin: str) -> Source:
        canon = canonicalize(hit.url)
        return Source(id=stable_id("S", canon), url=hit.url, canonical_url=canon, title=hit.title,
                      publisher=registrable_domain(hit.url), published_at=hit.published_date, snippet=hit.content,
                      search_query=query, search_origin=origin, tavily_score=hit.score, raw_metadata=hit.raw)

    async def extract(self, candidates: list[Source], k: int) -> list[Source]:
        k = min(k, self.budget.remaining_extractions())
        selected = candidates[:k]
        for s in candidates[k:]:
            self.events.emit(EventType.SOURCE_REJECTED, f"{s.id} not extracted (ranked below cutoff {k})", source_id=s.id)
        if not selected:
            return []
        self.budget.charge_extractions(len(selected))
        for s in selected:
            self.events.emit(EventType.SOURCE_SELECTED, f"{s.id} selected for extraction: {s.url}", source_id=s.id)
        pages, failed = await self.client.extract([s.url for s in selected])
        by_canon = {canonicalize(p.url): p for p in pages}
        done = []
        for s in selected:
            page = by_canon.get(s.canonical_url)
            if page is None:
                self.events.emit(EventType.SOURCE_REJECTED, f"{s.id} extraction failed; snippet only", source_id=s.id)
                continue
            s.raw_text, s.extracted = page.raw_content, True
            done.append(s)
            self.events.emit(EventType.SOURCE_EXTRACTED, f"{s.id} extracted ({len(s.raw_text):,} chars)", source_id=s.id)
        return done
