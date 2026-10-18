"""Scientific source handling: Document -DESCRIBES-> Study -PRODUCES-> Result -EXTRACTED_AS-> Evidence.

Per new scientific source (one model call, SCIENTIFIC_REVIEWER prompt):
  * document metadata (title, authors, venue, DOI, arXiv ID, peer review);
  * study methods -> StudyAssessment, scored deterministically (science/quality.py);
  * results with effect sizes and verbatim excerpts -> verified by code, else UNVERIFIED;
  * relations to other studies (REPLICATES, FAILS_TO_REPLICATE, ...) with verbatim excerpts.
Versions of one work are grouped by the ScientificSourceResolver and share one Study.
"""

from __future__ import annotations

import asyncio

from ..evidence.excerpts import locate_excerpt, select_passages
from ..graph.evidence_graph import EvidenceGraph, Link
from ..llm.gateway import LLMError, LLMGateway, ModelRole
from ..llm.prompts import SCIENTIFIC_REVIEWER
from ..models import (
    SCIENTIFIC_DOCUMENT_TYPES, Document, ScientificReviewOutput, Source, SourceLineage, Study, StudyRelation, StudyResult, stable_id,
)
from ..observability.events import EventLog, EventType
from .quality import assess_study, merge_assessments
from .resolver import find_arxiv_ids, find_dois, resolve_versions, title_similarity

SCIENTIFIC_SOURCE_TYPES = {"academic", "preprint", "conference"}
_REVIEW_TERMS = ["abstract", "method", "participants", "randomized", "randomised", "sample", "control", "results", "effect",
                 "confidence interval", "replication", "replicate", "preregistered", "conflict", "funding", "arxiv", "doi",
                 "published", "version", "limitations", "attrition", "blinded"]


class ScientificReviewer:
    def __init__(self, llm: LLMGateway, graph: EvidenceGraph, events: EventLog) -> None:
        self.llm, self.graph, self.events = llm, graph, events
        self._doc_to_study: dict[str, str] = {}
        self._proposals: dict[str, object] = {}

    def is_scientific(self, s: Source) -> bool:
        screen = self.graph.screening.get(s.id)
        if screen and screen.document_type in SCIENTIFIC_DOCUMENT_TYPES:
            return True
        a = self.graph.assessments.get(s.id)
        return bool(a and a.source_type in SCIENTIFIC_SOURCE_TYPES)

    def _doc_type(self, s: Source) -> str:
        screen = self.graph.screening.get(s.id)
        if screen and screen.document_type != "unknown":
            return screen.document_type
        a = self.graph.assessments.get(s.id)
        return {"preprint": "preprint", "conference": "conference_paper"}.get(a.source_type if a else "", "peer_reviewed_article")

    async def review(self, sources: list[Source], question: str) -> list[SourceLineage]:
        todo = [s for s in sources if s.extracted and self.is_scientific(s) and stable_id("D", s.id) not in self.graph.documents]
        if todo:
            outputs = await asyncio.gather(*(self._review_one(s, question) for s in todo))
            for s, out in zip(todo, outputs):
                self._add_document(s, out)
        edges = resolve_versions(list(self.graph.documents.values()), self.graph.sources)
        self._build_studies(edges)
        self._link_results_to_evidence()
        return edges

    async def _review_one(self, s: Source, question: str) -> ScientificReviewOutput | None:
        payload = {"question": question, "source_url": s.url, "source_title": s.title,
                   "known_studies": [{"title": st.title} for st in self.graph.studies.values()][:15],
                   "source_text": select_passages(s.raw_text, _REVIEW_TERMS + [question])}
        try:
            return await self.llm.structured("review_study", ModelRole.VERIFIER, SCIENTIFIC_REVIEWER, payload, ScientificReviewOutput)
        except LLMError as e:
            self.events.emit(EventType.ERROR, f"scientific review failed for {s.id}: {e}", source_id=s.id)
            return None

    def _add_document(self, s: Source, out: ScientificReviewOutput | None) -> None:
        p = out.study if out and out.study else None
        doc_type = self._doc_type(s)
        arxiv = (p.arxiv_id if p and p.arxiv_id else None) or next(iter(find_arxiv_ids(s.url + " " + s.raw_text[:3000])), None)
        doi = (p.doi if p and p.doi else None) or next(iter(find_dois(s.url + " " + s.raw_text[:3000])), None)
        peer = False if doc_type == "preprint" else (p.peer_reviewed if p else None)
        doc = Document(id=stable_id("D", s.id), source_id=s.id, document_type=doc_type, title=(p.title if p else "") or s.title,
                       authors=p.authors if p else [], doi=doi, arxiv_id=arxiv, venue=p.venue if p else None,
                       year=p.year if p else None, peer_reviewed=peer)
        self.graph.add_document(doc)
        if out and out.is_empirical_study and p:
            if doc_type == "preprint":  # a preprint is not peer reviewed, whatever the text claims
                out = out.model_copy(update={"study": p.model_copy(update={"peer_reviewed": False})})
            self._proposals[doc.id] = out
        self.events.emit(EventType.DOCUMENT_CLASSIFIED,
                         f"{s.id} {doc_type}{' · peer reviewed' if peer else ' · NOT peer reviewed' if peer is False else ''}: {doc.title[:70]}"
                         + (f" (arXiv {arxiv})" if arxiv else "") + (f" (DOI {doi})" if doi else ""), source_id=s.id, document_type=doc_type)

    def _build_studies(self, edges: list[SourceLineage]) -> None:
        parent = {e.child_source_id: e.parent_source_id for e in edges}

        def top(sid: str) -> str:
            seen = set()
            while sid in parent and sid not in seen:
                seen.add(sid)
                sid = parent[sid]
            return sid

        groups: dict[str, list[Document]] = {}
        for d in self.graph.documents.values():
            groups.setdefault(top(d.source_id), []).append(d)
        for root_src, docs in groups.items():
            reviewed = [d for d in docs if d.id in self._proposals]
            if not reviewed:
                continue
            study_id = next((self._doc_to_study[d.id] for d in docs if d.id in self._doc_to_study), None) or stable_id("ST", docs[0].id)
            new_versions = [d for d in docs if self._doc_to_study.get(d.id) != study_id]
            if not new_versions:
                continue
            assessment = None
            for d in reviewed:
                a = assess_study(study_id, self._proposals[d.id].study)
                assessment = a if assessment is None else merge_assessments(assessment, a)
            final = max(docs, key=lambda d: (d.peer_reviewed is True, d.document_type != "preprint"))
            study = Study(id=study_id, title=final.title, document_ids=[d.id for d in docs], design=assessment.study_design,
                          research_lineage_id=root_src)
            self.graph.add_study(study, assessment)
            for d in docs:
                self._doc_to_study[d.id] = study_id
            if len(docs) > 1:
                kinds = ", ".join(f"{d.source_id} ({d.document_type})" for d in docs)
                self.events.emit(EventType.SCIENTIFIC_VERSION_RESOLVED,
                                 f"{len(docs)} documents are versions of ONE work → 1 research lineage ({study_id}): {kinds}", study_id=study_id)
            self.events.emit(EventType.STUDY_ASSESSED,
                             f"{study_id} '{study.title[:60]}': design={assessment.study_design}, n={assessment.sample_size}, "
                             f"peer_reviewed={assessment.peer_reviewed}, quality {assessment.quality_score:.2f} ({'; '.join(assessment.notes[:3])})",
                             study_id=study_id, quality=assessment.quality_score)
            for d in new_versions:
                self._add_results_and_relations(study_id, d)

    def _add_results_and_relations(self, study_id: str, doc: Document) -> None:
        out = self._proposals.get(doc.id)
        if not out:
            return
        src = self.graph.sources[doc.source_id]
        for r in out.results:
            loc = locate_excerpt(r.exact_excerpt, src.raw_text)
            res = StudyResult(id=stable_id("RS", src.id, r.outcome, r.exact_excerpt), study_id=study_id, outcome=r.outcome,
                              effect_size=r.effect_size, effect_measure=r.effect_measure, ci_low=r.ci_low, ci_high=r.ci_high,
                              p_value=r.p_value, sample_size=r.sample_size, exact_excerpt=loc.span if loc else r.exact_excerpt,
                              location=loc.location if loc else None, source_id=src.id,
                              verification_status="verified" if loc else "unverified")
            self.graph.add_result(res)
            ci = f" (95% CI {res.ci_low}–{res.ci_high})" if res.ci_low is not None else ""
            self.events.emit(EventType.RESULT_EXTRACTED, f"{res.id} {res.outcome}: {res.effect_measure or 'effect'}={res.effect_size}{ci} "
                                                         f"n={res.sample_size} [{res.verification_status.upper()}]", result_id=res.id)
        for rel in out.relations:
            loc = locate_excerpt(rel.exact_excerpt, src.raw_text)
            target = max(((title_similarity(rel.other_study_title, st.title), st) for st in self.graph.studies.values() if st.id != study_id),
                         key=lambda t: t[0], default=(0.0, None))
            if loc is None or target[1] is None or target[0] < 0.4:
                self.events.emit(EventType.EVIDENCE_REJECTED, f"study relation {rel.relation} → '{rel.other_study_title[:50]}' not recorded "
                                                              f"({'excerpt not in source' if loc is None else 'other study not in vault'})")
                continue
            sr = StudyRelation(id=stable_id("SR", study_id, target[1].id, rel.relation), from_study_id=study_id, to_study_id=target[1].id,
                               relation=rel.relation, exact_excerpt=loc.span, source_id=src.id)
            self.graph.add_study_relation(sr)
            self.events.emit(EventType.STUDY_RELATION_FOUND, f"{study_id} {rel.relation} {target[1].id}: \"{loc.span[:90]}\"",
                             relation=rel.relation, frm=study_id, to=target[1].id)

    def _link_results_to_evidence(self) -> None:
        for res in self.graph.results.values():
            if res.verification_status != "verified":
                continue
            for e in self.graph.evidence.values():
                if e.source_id == res.source_id and e.result_id is None and (e.exact_excerpt in res.exact_excerpt or res.exact_excerpt in e.exact_excerpt):
                    e.result_id = res.id
                    self.graph.link(res.id, e.id, Link.EXTRACTED_AS)
