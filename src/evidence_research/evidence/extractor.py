"""Ingestion pipeline: extracted pages -> atomic claims -> verified evidence in the graph.

Per round (LLM calls: one extraction per source + one matcher batch + one judge batch):
  A. extract atomic claims with verbatim excerpts (model);
  B. code rejects any excerpt that is not in the retrieved text;
  C. reported speech is split into an ATTRIBUTION claim (strongly evidenced) and the underlying
     FACT claim (evidence capped at low directness) - section 22;
  D. claim normalization: canonical-key match, else candidate retrieval + model SAME/DIFFERENT;
  E. the evidence judge classifies stance for every (claim, excerpt) pair (model, categorical);
  F. code converts categories to numbers and stores Evidence linked source -> evidence -> claim.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date

from ..config import Settings
from ..graph.evidence_graph import EvidenceGraph, Link
from ..llm.gateway import LLMError, LLMGateway, ModelRole
from ..llm.prompts import CLAIM_EXTRACTOR, CLAIM_MATCHER
from ..models import (
    Claim, Evidence, ExtractedClaimProposal, ExtractionOutput, QuestionAnalysis, SameClaimOutput, Source, TemporalScope, stable_id,
)
from ..observability.events import EventLog, EventType
from ..verification.citation_verifier import excerpt_in_text
from ..verification.entailment import JudgePair, judge_pairs, score
from .claim_normalizer import canonical_key, candidates
from .source_classifier import assess
from .temporal import temporal_relevance

IMPORTANCE = {"low": 0.3, "medium": 0.6, "high": 1.0}
MAX_SOURCE_CHARS = 12_000


@dataclass
class IngestStats:
    sources: int = 0
    new_claims: list[str] = field(default_factory=list)
    merged_claims: int = 0
    evidence: int = 0
    rejected_excerpts: int = 0


@dataclass
class _Pending:
    claim: Claim
    source: Source
    excerpt: str
    reported_speech: bool
    depends_on_key: str | None = None  # fact claim -> its attribution claim (by key)
    key: str = ""


class EvidencePipeline:
    def __init__(self, llm: LLMGateway, graph: EvidenceGraph, events: EventLog, settings: Settings, today: date) -> None:
        self.llm, self.graph, self.events, self.s, self.today = llm, graph, events, settings, today
        self.key_to_claim: dict[str, str] = {}

    async def _extract(self, src: Source, analysis: QuestionAnalysis, question: str) -> ExtractionOutput | None:
        existing = sorted(self.graph.claims.values(), key=lambda c: -c.importance)[:8]
        payload = {
            "question": question, "source_url": src.url, "source_title": src.title,
            "requirements": [{"id": r.id, "description": r.description} for r in self.graph.requirements.values()],
            "existing_claims": [{"id": c.id, "text": c.natural_language} for c in existing],
            "source_text": src.raw_text[:MAX_SOURCE_CHARS],
        }
        try:
            return await self.llm.structured("extract_claims", ModelRole.FAST, CLAIM_EXTRACTOR, payload, ExtractionOutput)
        except LLMError as e:
            self.events.emit(EventType.ERROR, f"claim extraction failed for {src.id}: {e}", source_id=src.id)
            return None

    def _claim_from(self, cp: ExtractedClaimProposal, attribution: bool) -> Claim:
        scope = TemporalScope(valid_from=cp.valid_from, valid_to=cp.valid_to) if (cp.valid_from or cp.valid_to) else None
        reqs = [] if attribution else [r for r in cp.requirement_ids if r in self.graph.requirements]
        if attribution:
            subj, pred, obj = cp.attributed_to, "stated", cp.natural_language
            text, kind = f"{cp.attributed_to} stated that {cp.natural_language[0].lower()}{cp.natural_language[1:]}", "attribution"
        else:
            subj, pred, obj, text, kind = cp.subject, cp.predicate, cp.object, cp.natural_language, "fact"
        key = canonical_key(subj, pred, obj, scope, kind, cp.attributed_to if attribution else None)
        return Claim(id=stable_id("C", key), subject=subj, predicate=pred, object=obj, natural_language=text, kind=kind,
                     attributed_to=cp.attributed_to if attribution else None, category=cp.category, temporal_scope=scope,
                     requirement_ids=reqs, importance=IMPORTANCE[cp.importance] * (0.6 if attribution else 1.0))

    async def ingest(self, sources: list[Source], analysis: QuestionAnalysis, question: str) -> IngestStats:
        stats = IngestStats(sources=len(sources))
        outputs = await asyncio.gather(*(self._extract(s, analysis, question) for s in sources))

        pending: list[_Pending] = []
        existing_pairs: list[tuple[str, Source, str]] = []
        for src, out in zip(sources, outputs):
            if src.id not in self.graph.assessments:
                self.graph.set_assessment(assess(src, analysis.key_entities))
            if out is None:
                continue
            if src.published_at is None and out.published_at and str(out.published_at.year) in src.raw_text:
                src.published_at = out.published_at  # only if the year is actually on the page
            for cp in out.claims:
                if not excerpt_in_text(cp.exact_excerpt, src.raw_text):
                    stats.rejected_excerpts += 1
                    self.events.emit(EventType.EVIDENCE_REJECTED, f"{src.id}: excerpt not found verbatim in source, claim dropped: {cp.natural_language[:80]}",
                                     source_id=src.id)
                    continue
                fact = self._claim_from(cp, attribution=False)
                if cp.attributed_to:
                    att = self._claim_from(cp, attribution=True)
                    pending.append(_Pending(att, src, cp.exact_excerpt, False, key=att.id))
                    pending.append(_Pending(fact, src, cp.exact_excerpt, True, depends_on_key=att.id, key=fact.id))
                else:
                    pending.append(_Pending(fact, src, cp.exact_excerpt, False, key=fact.id))
            for b in out.bears_on_existing:
                if b.claim_id in self.graph.claims and excerpt_in_text(b.exact_excerpt, src.raw_text):
                    existing_pairs.append((b.claim_id, src, b.exact_excerpt))
                else:
                    stats.rejected_excerpts += 1

        resolved = await self._resolve(pending, stats)

        pairs: list[JudgePair] = []
        for p in pending:
            cid = resolved[p.key]
            if p.depends_on_key:
                self.graph.link_claims(cid, resolved[p.depends_on_key], Link.DEPENDS_ON)
            pairs.append(JudgePair(stable_id("P", cid, p.source.id, p.excerpt), cid, self.graph.claims[cid].natural_language,
                                   p.source.id, p.excerpt, p.reported_speech))
        for cid, src, excerpt in existing_pairs:
            pairs.append(JudgePair(stable_id("P", cid, src.id, excerpt), cid, self.graph.claims[cid].natural_language, src.id, excerpt))
        pairs = list({p.pair_id: p for p in pairs}.values())

        judgements = await judge_pairs(self.llm, pairs)
        for pair in pairs:
            j = judgements.get(pair.pair_id)
            if j is None:
                self.events.emit(EventType.EVIDENCE_REJECTED, f"no stance judgement for {pair.claim_id} / {pair.source_id}")
                continue
            sc = score(j, self.s.heuristics, pair.reported_speech)
            src, claim = self.graph.sources[pair.source_id], self.graph.claims[pair.claim_id]
            ev = Evidence(
                id=stable_id("E", pair.source_id, pair.claim_id, pair.excerpt), source_id=pair.source_id, claim_id=pair.claim_id,
                exact_excerpt=pair.excerpt, stance=sc.stance, entailment_probability=sc.entailment_probability,
                contradiction_probability=sc.contradiction_probability, directness=sc.directness,
                temporal_relevance=temporal_relevance(src.published_at, claim.temporal_scope, self.today),
                extraction_confidence=0.9, reported_speech=pair.reported_speech,
            )
            if self.graph.add_evidence(ev):
                stats.evidence += 1
                p = ev.entailment_probability if ev.stance == "supports" else ev.contradiction_probability
                self.events.emit(EventType.EVIDENCE_ATTACHED,
                                 f"{ev.id} → {claim.id} STANCE: {ev.stance.upper()} p={p:.2f} directness={ev.directness:.2f}"
                                 + (" (reported speech)" if ev.reported_speech else "") + f" from {src.id}",
                                 evidence_id=ev.id, claim_id=claim.id, source_id=src.id, stance=ev.stance)
                if ev.stance == "contradicts":
                    self.events.emit(EventType.CONTRADICTION_FOUND, f"{src.id} contradicts {claim.id}: \"{ev.exact_excerpt[:90]}\"",
                                     claim_id=claim.id, source_id=src.id)
        return stats

    async def _resolve(self, pending: list[_Pending], stats: IngestStats) -> dict[str, str]:
        """Map each pending claim key to a graph claim id, merging duplicates (section 16)."""
        resolved: dict[str, str] = {}
        to_match: list[tuple[_Pending, Claim]] = []
        batch_new: dict[str, Claim] = {}
        for p in pending:
            if p.key in resolved:
                continue
            if p.key in self.graph.claims:
                resolved[p.key] = p.key
                continue
            if p.key in batch_new:
                continue
            pool = list(self.graph.claims.values()) + list(batch_new.values())
            cands = candidates(p.claim, pool, limit=1)
            if cands:
                to_match.append((p, cands[0][1]))
            batch_new[p.key] = p.claim

        same: dict[str, str] = {}
        if to_match:
            payload = {"pairs": [{"pair_id": p.key, "a": p.claim.natural_language, "b": c.natural_language} for p, c in to_match]}
            try:
                result = await self.llm.structured("match_claims", ModelRole.FAST, CLAIM_MATCHER, payload, SameClaimOutput)
                verdicts = {r.pair_id: r.verdict for r in result.results}
            except LLMError as e:
                self.events.emit(EventType.ERROR, f"claim matching failed, keeping claims separate: {e}")
                verdicts = {}
            for p, c in to_match:
                if verdicts.get(p.key) == "SAME":
                    same[p.key] = c.id

        final: dict[str, str | None] = {}
        for key in batch_new:
            target, hops = same.get(key), 0
            while target in same and hops < 10:  # chained merges inside one batch
                target, hops = same[target], hops + 1
            final[key] = target
        for key, claim in batch_new.items():  # create genuinely new claims first...
            if final[key] is None:
                self.graph.add_claim(claim)
                resolved[key] = claim.id
                stats.new_claims.append(claim.id)
                self.events.emit(EventType.CLAIM_CREATED, f"{claim.id} [{claim.kind}] {claim.natural_language}", claim_id=claim.id)
        for key, claim in batch_new.items():  # ...then merge duplicates into them as aliases
            target = final[key]
            if target is None:
                continue
            resolved[key] = target
            self.graph.add_alias(target, claim.natural_language, claim.requirement_ids)
            self.graph.claims[target].importance = max(self.graph.claims[target].importance, claim.importance)
            stats.merged_claims += 1
            self.events.emit(EventType.CLAIM_MERGED, f"'{claim.natural_language[:70]}' merged into {target}", claim_id=target)
        for p in pending:
            resolved.setdefault(p.key, p.key)
        return resolved
