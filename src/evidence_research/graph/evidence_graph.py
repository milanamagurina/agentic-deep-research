"""Long-term Evidence Vault: an append-only evidence DAG, Data-Vault style (sections 3-4, 7).

  Hubs        stable identities: Entity, Source, Document, Study, Result, Claim, Hypothesis,
              Requirement, Evidence, Inference, Gap
  Links       typed edges in a NetworkX MultiDiGraph. Three families that are NEVER mixed:
                evidential   Evidence -SUPPORTS/CONTRADICTS/QUALIFIES-> Claim
                logical      Claim -REQUIRED_FOR-> Hypothesis/Claim,
                             Claim -SUPPORTS_HYPOTHESIS/CHALLENGES_HYPOTHESIS-> Hypothesis
                provenance   Document -DESCRIBES-> Study -PRODUCES-> Result -EXTRACTED_AS-> Evidence
                             -EXTRACTED_FROM-> Source;  Source -CITES/DERIVED_FROM/DUPLICATES-> Source;
                             Study -REPLICATES/FAILS_TO_REPLICATE/...-> Study
                semantic     Entity -RELATED_TO-> Entity, Claim -ABOUT-> Entity/Requirement
              Only evidential and logical links are ever used as support for a belief.
  Satellites  append-only, time-stamped observations: SAT_SOURCE_ASSESSMENT, SAT_STUDY_ASSESSMENT,
              SAT_CLAIM_CONFIDENCE, SAT_EVIDENCE_SCORE, SAT_HYPOTHESIS_POSTERIOR, SAT_SCREENING, ...

Rule: nothing is deleted and history is never overwritten. Excluded sources, rejected inferences and
unverified extractions all stay in the vault (negative provenance). The small working context the
models see is built from this vault by ``graph/active.py``.

Swap-out point: the only module that touches NetworkX; a Neo4j implementation can mirror its methods.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Any

import networkx as nx
from pydantic import BaseModel, Field

from ..models import (
    AgentBid, Claim, Document, Entity, Evidence, EvidenceQuality, EvidenceRequirement, Hypothesis, Inference,
    NecessityAssessment, ResearchGap, ResearchTask, ScreeningDecision, Source, SourceAssessment, SourceLineage, Study,
    StudyAssessment, StudyRelation, StudyResult, utcnow,
)


class Link(str, Enum):
    # evidential
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    QUALIFIES = "QUALIFIES"
    # logical
    REQUIRED_FOR = "REQUIRED_FOR"
    SUPPORTS_HYPOTHESIS = "SUPPORTS_HYPOTHESIS"
    CHALLENGES_HYPOTHESIS = "CHALLENGES_HYPOTHESIS"
    PREMISE_OF = "PREMISE_OF"      # claim -> inference object
    CONCLUDES = "CONCLUDES"        # inference object -> hypothesis/claim
    DEPENDS_ON = "DEPENDS_ON"      # fact claim -> the attribution claim it was reported through
    TEMPORAL_VERSION_OF = "TEMPORAL_VERSION_OF"
    # provenance
    DESCRIBES = "DESCRIBES"
    PRODUCES = "PRODUCES"
    EXTRACTED_AS = "EXTRACTED_AS"
    EXTRACTED_FROM = "EXTRACTED_FROM"
    CONTAINS = "CONTAINS"          # source -> document
    CITES = "CITES"
    DERIVED_FROM = "DERIVED_FROM"
    DUPLICATES = "DUPLICATES"
    REPLICATES = "REPLICATES"
    FAILS_TO_REPLICATE = "FAILS_TO_REPLICATE"
    EXTENDS = "EXTENDS"
    REANALYZES = "REANALYZES"
    CORRECTS = "CORRECTS"
    RETRACTS = "RETRACTS"
    # semantic (never proof)
    ABOUT = "ABOUT"
    RELATED_TO = "RELATED_TO"
    HAS_GAP = "HAS_GAP"


EVIDENTIAL = {Link.SUPPORTS, Link.CONTRADICTS, Link.QUALIFIES}
LOGICAL = {Link.REQUIRED_FOR, Link.SUPPORTS_HYPOTHESIS, Link.CHALLENGES_HYPOTHESIS, Link.PREMISE_OF, Link.CONCLUDES, Link.DEPENDS_ON}
SEMANTIC = {Link.ABOUT, Link.RELATED_TO}

SAT_SOURCE_ASSESSMENT = "SAT_SOURCE_ASSESSMENT"
SAT_STUDY_ASSESSMENT = "SAT_STUDY_ASSESSMENT"
SAT_CLAIM_CONFIDENCE = "SAT_CLAIM_CONFIDENCE"
SAT_EVIDENCE_SCORE = "SAT_EVIDENCE_SCORE"
SAT_HYPOTHESIS_POSTERIOR = "SAT_HYPOTHESIS_POSTERIOR"
SAT_SCREENING = "SAT_SCREENING"
SAT_ALIAS = "SAT_ALIAS"
SAT_INFERENCE_VERIFICATION = "SAT_INFERENCE_VERIFICATION"
SAT_NECESSITY = "SAT_NECESSITY"
CONFIDENCE_KINDS = {SAT_CLAIM_CONFIDENCE, SAT_HYPOTHESIS_POSTERIOR}


class Observation(BaseModel):
    entity_id: str
    kind: str
    value: dict[str, Any]
    observed_at: datetime = Field(default_factory=utcnow)
    reason: str = ""


STANCE_LINK = {"supports": Link.SUPPORTS, "contradicts": Link.CONTRADICTS, "qualifies": Link.QUALIFIES, "neutral": Link.QUALIFIES}
STUDY_LINK = {r: Link(r) for r in ("REPLICATES", "FAILS_TO_REPLICATE", "EXTENDS", "REANALYZES", "CORRECTS", "RETRACTS")}


class EvidenceGraph:
    def __init__(self) -> None:
        self.g = nx.MultiDiGraph()
        self.entities: dict[str, Entity] = {}
        self.sources: dict[str, Source] = {}
        self.assessments: dict[str, SourceAssessment] = {}
        self.screening: dict[str, ScreeningDecision] = {}
        self.documents: dict[str, Document] = {}
        self.studies: dict[str, Study] = {}
        self.study_assessments: dict[str, StudyAssessment] = {}
        self.results: dict[str, StudyResult] = {}
        self.study_relations: dict[str, StudyRelation] = {}
        self.claims: dict[str, Claim] = {}
        self.evidence: dict[str, Evidence] = {}
        self.evidence_quality: dict[str, EvidenceQuality] = {}
        self.inferences: dict[str, Inference] = {}
        self.necessity: dict[tuple[str, str], NecessityAssessment] = {}
        self.hypotheses: dict[str, Hypothesis] = {}
        self.requirements: dict[str, EvidenceRequirement] = {}
        self.gaps: dict[str, ResearchGap] = {}
        self.tasks: dict[str, ResearchTask] = {}
        self.bids: list[tuple[int, list[AgentBid]]] = []
        self.lineage: list[SourceLineage] = []
        self.root_of: dict[str, str] = {}
        self.family_of: dict[str, str] = {}
        self.observations: list[Observation] = []
        self._by_canonical_url: dict[str, str] = {}

    # ------------------------------------------------------------------ primitives
    def _node(self, node_id: str, kind: str, label: str) -> None:
        if node_id not in self.g:
            self.g.add_node(node_id, kind=kind, label=label[:80])

    def _link(self, a: str, b: str, link: Link, **attrs: Any) -> None:
        if not any(d.get("type") == link.value for d in self.g.get_edge_data(a, b, default={}).values()):
            self.g.add_edge(a, b, key=link.value, type=link.value, **attrs)

    def link(self, a: str, b: str, link: Link, **attrs: Any) -> None:
        self._link(a, b, link, **attrs)

    link_claims = link  # backwards-compatible name

    def observe(self, entity_id: str, kind: str, value: dict[str, Any], reason: str = "") -> None:
        self.observations.append(Observation(entity_id=entity_id, kind=kind, value=value, reason=reason))

    def history(self, entity_id: str, kind: str | None = None) -> list[Observation]:
        kinds = {kind} if kind else CONFIDENCE_KINDS
        return [o for o in self.observations if o.entity_id == entity_id and o.kind in kinds]

    # ------------------------------------------------------------------ hubs
    def add_entity(self, e: Entity) -> None:
        self.entities.setdefault(e.id, e)
        self._node(e.id, "entity", e.name)

    def add_source(self, s: Source) -> Source:
        if s.canonical_url in self._by_canonical_url:
            return self.sources[self._by_canonical_url[s.canonical_url]]
        self.sources[s.id] = s
        self._by_canonical_url[s.canonical_url] = s.id
        self._node(s.id, "source", s.title or s.url)
        return s

    def source_by_url(self, canonical_url: str) -> Source | None:
        sid = self._by_canonical_url.get(canonical_url)
        return self.sources.get(sid) if sid else None

    def set_assessment(self, a: SourceAssessment) -> None:
        self.assessments[a.source_id] = a
        self.observe(a.source_id, SAT_SOURCE_ASSESSMENT, a.model_dump(), "heuristic by source type")

    def set_screening(self, d: ScreeningDecision) -> None:
        self.screening[d.source_id] = d  # latest decision; every decision stays in the satellite history
        self.observe(d.source_id, SAT_SCREENING, d.model_dump(mode="json"), "; ".join(d.reasons))

    def add_document(self, d: Document) -> None:
        self.documents[d.id] = d
        self._node(d.id, "document", d.title or d.document_type)
        self._link(d.source_id, d.id, Link.CONTAINS)

    def add_study(self, st: Study, assessment: StudyAssessment) -> None:
        if st.id in self.studies:
            known = self.studies[st.id]
            for doc in st.document_ids:
                if doc not in known.document_ids:
                    known.document_ids.append(doc)
            st = known
        else:
            self.studies[st.id] = st
            self._node(st.id, "study", st.title)
        for doc in st.document_ids:
            self._link(doc, st.id, Link.DESCRIBES)
        self.study_assessments[st.id] = assessment
        self.observe(st.id, SAT_STUDY_ASSESSMENT, assessment.model_dump(), f"quality {assessment.quality_score:.2f}")

    def add_result(self, r: StudyResult) -> None:
        self.results[r.id] = r
        self._node(r.id, "result", r.outcome)
        self._link(r.study_id, r.id, Link.PRODUCES)

    def add_study_relation(self, rel: StudyRelation) -> None:
        self.study_relations[rel.id] = rel
        self._link(rel.from_study_id, rel.to_study_id, STUDY_LINK[rel.relation], excerpt=rel.exact_excerpt)

    def add_hypothesis(self, h: Hypothesis) -> None:
        self.hypotheses[h.id] = h
        self._node(h.id, "hypothesis", h.text)
        self.observe(h.id, SAT_HYPOTHESIS_POSTERIOR, {"p": h.posterior_probability, "prior": h.prior_probability}, "heuristic prior")

    def add_requirement(self, r: EvidenceRequirement) -> None:
        self.requirements[r.id] = r
        self._node(r.id, "requirement", r.description)
        self._link(r.id, r.hypothesis_id, Link.ABOUT)

    def add_claim(self, c: Claim) -> Claim:
        if c.id in self.claims:
            return self.claims[c.id]
        self.claims[c.id] = c
        self._node(c.id, "claim", c.natural_language)
        for rid in c.requirement_ids:
            if rid in self.requirements:
                self._link(c.id, rid, Link.ABOUT)
        self.observe(c.id, SAT_CLAIM_CONFIDENCE, {"p": c.truth_probability, "sufficiency": c.evidence_sufficiency}, "created at prior")
        return c

    def add_alias(self, claim_id: str, text: str, requirement_ids: list[str]) -> None:
        c = self.claims[claim_id]
        if text != c.natural_language and text not in c.aliases:
            c.aliases.append(text)
            self.observe(claim_id, SAT_ALIAS, {"text": text}, "merged by claim normalizer")
        for rid in requirement_ids:
            if rid in self.requirements and rid not in c.requirement_ids:
                c.requirement_ids.append(rid)
                self._link(claim_id, rid, Link.ABOUT)

    def add_evidence(self, e: Evidence) -> bool:
        if e.id in self.evidence:
            return False
        if e.source_id not in self.sources or e.claim_id not in self.claims:
            raise KeyError("evidence must reference an existing source and claim")
        self.evidence[e.id] = e
        self._node(e.id, "evidence", e.exact_excerpt)
        self._link(e.id, e.source_id, Link.EXTRACTED_FROM)
        if e.verification_status == "verified":
            self._link(e.id, e.claim_id, STANCE_LINK[e.stance])
        if e.result_id and e.result_id in self.results:
            self._link(e.result_id, e.id, Link.EXTRACTED_AS)
        return True

    def set_evidence_quality(self, q: EvidenceQuality) -> None:
        old = self.evidence_quality.get(q.evidence_id)
        self.evidence_quality[q.evidence_id] = q
        if old is None or abs(old.strength - q.strength) >= 0.005:
            self.observe(q.evidence_id, SAT_EVIDENCE_SCORE, q.model_dump(), "recomputed")

    def add_inference(self, inf: Inference) -> None:
        self.inferences[inf.id] = inf
        self._node(inf.id, "inference", inf.statement or inf.inference_type)
        for pid in inf.premise_ids:
            self._link(pid, inf.id, Link.PREMISE_OF)
        self._link(inf.id, inf.conclusion_claim_id, Link.CONCLUDES, direction=inf.direction)

    def accept_inference(self, inf: Inference) -> None:
        """Only verified inferences create logical claim -> hypothesis edges."""
        link = Link.SUPPORTS_HYPOTHESIS if inf.direction == "supports" else Link.CHALLENGES_HYPOTHESIS
        for pid in inf.premise_ids:
            self._link(pid, inf.conclusion_claim_id, link, inference_id=inf.id)

    def set_necessity(self, a: NecessityAssessment) -> None:
        self.necessity[(a.hypothesis_id, a.premise_id)] = a
        self.observe(a.premise_id, SAT_NECESSITY, a.model_dump(), a.reason)
        if a.necessary:
            self._link(a.premise_id, a.hypothesis_id, Link.REQUIRED_FOR, method=a.method)

    def upsert_gap(self, gap: ResearchGap) -> bool:
        """Returns True when the gap is new."""
        new = gap.id not in self.gaps
        if not new:
            gap.attempts = self.gaps[gap.id].attempts
            gap.unresolvable = self.gaps[gap.id].unresolvable
        self.gaps[gap.id] = gap
        if new:
            self._node(gap.id, "gap", gap.description)
            if gap.target_id in self.g:
                self._link(gap.target_id, gap.id, Link.HAS_GAP)
        return new

    def add_task(self, t: ResearchTask) -> None:
        self.tasks[t.id] = t

    def set_lineage(self, edges: list[SourceLineage], root_of: dict[str, str], family_of: dict[str, str] | None = None) -> list[SourceLineage]:
        """Store lineage; returns edges not seen before. Independence is written onto assessments."""
        known = {(e.child_source_id, e.parent_source_id) for e in self.lineage}
        fresh = [e for e in edges if (e.child_source_id, e.parent_source_id) not in known]
        self.lineage = edges
        self.root_of = root_of
        if family_of is not None:
            self.family_of = family_of
        for e in fresh:
            if e.parent_source_id:
                self._link(e.child_source_id, e.parent_source_id,
                           Link.DUPLICATES if e.kind == "same_work_version" else Link.DERIVED_FROM, p=e.dependency_probability)
        dep = {e.child_source_id: e.dependency_probability for e in edges}
        for sid, a in self.assessments.items():
            a.independence = round(1 - dep.get(sid, 0.0), 3)
        return fresh

    # ------------------------------------------------------------------ queries
    def evidence_for(self, claim_id: str, verified_only: bool = True) -> list[Evidence]:
        return [e for e in self.evidence.values() if e.claim_id == claim_id and (e.verification_status == "verified" or not verified_only)]

    def sources_for_claim(self, claim_id: str) -> list[Source]:
        """Walk claim <- (evidential link) evidence -EXTRACTED_FROM-> source through the graph."""
        out = []
        for ev_id, _, data in self.g.in_edges(claim_id, data=True):
            if self.g.nodes[ev_id].get("kind") != "evidence" or data.get("type") not in {l.value for l in EVIDENTIAL}:
                continue
            for _, src_id, d2 in self.g.out_edges(ev_id, data=True):
                if d2.get("type") == Link.EXTRACTED_FROM.value and src_id in self.sources:
                    out.append(self.sources[src_id])
        return out

    def roots_for_claim(self, claim_id: str) -> set[str]:
        return {self.root_of.get(s.id, s.id) for s in self.sources_for_claim(claim_id)}

    def claims_for_requirement(self, req_id: str) -> list[Claim]:
        return [self.claims[a] for a, _, d in self.g.in_edges(req_id, data=True) if a in self.claims and d.get("type") == Link.ABOUT.value]

    def requirements_for(self, hypothesis_id: str) -> list[EvidenceRequirement]:
        return [r for r in self.requirements.values() if r.hypothesis_id == hypothesis_id]

    def contradiction_pairs(self) -> list[tuple[str, str]]:
        return [(a, b) for a, b, d in self.g.edges(data=True) if d.get("type") == Link.CONTRADICTS.value and a in self.claims and b in self.claims]

    def temporal_versions(self, claim_id: str) -> list[str]:
        return [b for _, b, d in self.g.out_edges(claim_id, data=True) if d.get("type") == Link.TEMPORAL_VERSION_OF.value] + \
               [a for a, _, d in self.g.in_edges(claim_id, data=True) if d.get("type") == Link.TEMPORAL_VERSION_OF.value]

    def inferences_for(self, conclusion_id: str) -> list[Inference]:
        return [i for i in self.inferences.values() if i.conclusion_claim_id == conclusion_id]

    def study_for_source(self, source_id: str) -> Study | None:
        docs = {d.id for d in self.documents.values() if d.source_id == source_id}
        return next((s for s in self.studies.values() if docs & set(s.document_ids)), None)

    def study_relations_to(self, study_id: str) -> list[StudyRelation]:
        return [r for r in self.study_relations.values() if r.to_study_id == study_id]

    def stats(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for _, d in self.g.nodes(data=True):
            counts[d.get("kind", "?")] += 1
        counts["edges"] = self.g.number_of_edges()
        counts["screened_out"] = sum(1 for d in self.screening.values() if d.decision == "exclude")
        counts["unverified_evidence"] = sum(1 for e in self.evidence.values() if e.verification_status != "verified")
        return dict(counts)

    # ------------------------------------------------------------------ serialization
    def snapshot(self) -> dict[str, Any]:
        dump = lambda d: [v.model_dump(mode="json") for v in d.values()]  # noqa: E731
        return {
            "sources": [s.model_dump(mode="json", exclude={"raw_text"}) | {"raw_text_chars": len(s.raw_text)} for s in self.sources.values()],
            "assessments": dump(self.assessments), "screening": dump(self.screening), "documents": dump(self.documents),
            "studies": dump(self.studies), "study_assessments": dump(self.study_assessments), "results": dump(self.results),
            "study_relations": dump(self.study_relations), "claims": dump(self.claims), "evidence": dump(self.evidence),
            "evidence_quality": dump(self.evidence_quality), "inferences": dump(self.inferences),
            "necessity": [v.model_dump(mode="json") for v in self.necessity.values()], "hypotheses": dump(self.hypotheses),
            "requirements": dump(self.requirements), "gaps": dump(self.gaps), "tasks": dump(self.tasks),
            "bids": [{"iteration": i, "bids": [b.model_dump() for b in bs]} for i, bs in self.bids],
            "lineage": [e.model_dump(mode="json") for e in self.lineage], "root_of": self.root_of, "family_of": self.family_of,
            "observations": [o.model_dump(mode="json") for o in self.observations],
            "links": [{"from": a, "to": b, "type": d.get("type")} for a, b, d in self.g.edges(data=True)],
        }
