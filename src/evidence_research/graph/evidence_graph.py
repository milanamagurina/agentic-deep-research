"""Evidence graph, Data-Vault style (section 13).

  Hubs       stable identities: Source, Document text, Claim, Hypothesis, Requirement, Inference, Evidence
  Links      typed edges in a NetworkX MultiDiGraph (SUPPORTS, CONTRADICTS, DERIVED_FROM, ...)
  Satellites append-only, time-stamped observations (assessments, posteriors, sufficiency, aliases)

Rule: confidence history is never overwritten. ``observe`` appends; current values on the hub
objects are a cache of the latest observation.

Swap-out point: this class is the only thing that touches NetworkX. A Neo4j-backed implementation
can provide the same methods later.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Any

import networkx as nx
from pydantic import BaseModel, Field

from ..models import (
    Claim, Evidence, EvidenceRequirement, Hypothesis, Inference, ResearchGap, Source, SourceAssessment,
    SourceLineage, utcnow,
)


class Link(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    QUALIFIES = "QUALIFIES"
    DERIVED_FROM = "DERIVED_FROM"      # evidence -> source; child source -> parent source
    CITES = "CITES"
    DUPLICATES = "DUPLICATES"
    DEPENDS_ON = "DEPENDS_ON"          # claim (fact) -> claim (attribution) it is reported through
    ABOUT = "ABOUT"                    # claim -> requirement, requirement -> hypothesis
    TEMPORAL_VERSION_OF = "TEMPORAL_VERSION_OF"
    PREMISE_OF = "PREMISE_OF"          # claim -> inference
    CONCLUDES = "CONCLUDES"            # inference -> hypothesis/claim
    HAS_GAP = "HAS_GAP"


class Observation(BaseModel):
    entity_id: str
    kind: str
    value: dict[str, Any]
    observed_at: datetime = Field(default_factory=utcnow)
    reason: str = ""


STANCE_LINK = {"supports": Link.SUPPORTS, "contradicts": Link.CONTRADICTS, "qualifies": Link.QUALIFIES, "neutral": Link.QUALIFIES}


class EvidenceGraph:
    def __init__(self) -> None:
        self.g = nx.MultiDiGraph()
        self.sources: dict[str, Source] = {}
        self.assessments: dict[str, SourceAssessment] = {}
        self.claims: dict[str, Claim] = {}
        self.evidence: dict[str, Evidence] = {}
        self.inferences: dict[str, Inference] = {}
        self.hypotheses: dict[str, Hypothesis] = {}
        self.requirements: dict[str, EvidenceRequirement] = {}
        self.gaps: dict[str, ResearchGap] = {}
        self.lineage: list[SourceLineage] = []
        self.root_of: dict[str, str] = {}
        self.observations: list[Observation] = []
        self._by_canonical_url: dict[str, str] = {}

    # ------------------------------------------------------------------ hubs
    def _node(self, node_id: str, kind: str, label: str) -> None:
        self.g.add_node(node_id, kind=kind, label=label[:80])

    def _link(self, a: str, b: str, link: Link, **attrs: Any) -> None:
        if not any(d.get("type") == link.value for d in self.g.get_edge_data(a, b, default={}).values()):
            self.g.add_edge(a, b, key=link.value, type=link.value, **attrs)

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
        self.observe(a.source_id, "source_assessment", a.model_dump(), "heuristic by source type")

    def add_hypothesis(self, h: Hypothesis) -> None:
        self.hypotheses[h.id] = h
        self._node(h.id, "hypothesis", h.text)
        self.observe(h.id, "posterior", {"p": h.posterior_probability, "prior": h.prior_probability}, "heuristic prior")

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
        self.observe(c.id, "posterior", {"p": c.truth_probability, "sufficiency": c.evidence_sufficiency}, "created at prior")
        return c

    def add_alias(self, claim_id: str, text: str, requirement_ids: list[str]) -> None:
        c = self.claims[claim_id]
        if text != c.natural_language and text not in c.aliases:
            c.aliases.append(text)
            self.observe(claim_id, "alias", {"text": text}, "merged by claim normalizer")
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
        self._link(e.id, e.source_id, Link.DERIVED_FROM)
        self._link(e.id, e.claim_id, STANCE_LINK[e.stance])
        return True

    def link_claims(self, a: str, b: str, link: Link, **attrs: Any) -> None:
        self._link(a, b, link, **attrs)

    def add_inference(self, inf: Inference) -> None:
        self.inferences[inf.id] = inf
        self._node(inf.id, "inference", inf.statement or inf.inference_type)
        for pid in inf.premise_ids:
            self._link(pid, inf.id, Link.PREMISE_OF)
        self._link(inf.id, inf.conclusion_claim_id, Link.CONCLUDES, direction=inf.direction)

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

    def set_lineage(self, edges: list[SourceLineage], root_of: dict[str, str]) -> list[SourceLineage]:
        """Store lineage; returns edges not seen before."""
        known = {(e.child_source_id, e.parent_source_id) for e in self.lineage}
        fresh = [e for e in edges if (e.child_source_id, e.parent_source_id) not in known]
        self.lineage = edges
        self.root_of = root_of
        for e in fresh:
            if e.parent_source_id:
                self._link(e.child_source_id, e.parent_source_id, Link.DERIVED_FROM, p=e.dependency_probability)
        return fresh

    # ------------------------------------------------------------------ satellites
    def observe(self, entity_id: str, kind: str, value: dict[str, Any], reason: str = "") -> None:
        self.observations.append(Observation(entity_id=entity_id, kind=kind, value=value, reason=reason))

    def history(self, entity_id: str, kind: str = "posterior") -> list[Observation]:
        return [o for o in self.observations if o.entity_id == entity_id and o.kind == kind]

    # ------------------------------------------------------------------ queries
    def evidence_for(self, claim_id: str) -> list[Evidence]:
        return [e for e in self.evidence.values() if e.claim_id == claim_id]

    def sources_for_claim(self, claim_id: str) -> list[Source]:
        """Walk claim <- evidence -> source through the graph (not through the dicts)."""
        out = []
        for ev_id, _, data in self.g.in_edges(claim_id, data=True):
            if self.g.nodes[ev_id].get("kind") != "evidence":
                continue
            for _, src_id, d2 in self.g.out_edges(ev_id, data=True):
                if d2.get("type") == Link.DERIVED_FROM.value and src_id in self.sources:
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

    def stats(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for _, d in self.g.nodes(data=True):
            counts[d.get("kind", "?")] += 1
        counts["edges"] = self.g.number_of_edges()
        counts["independent_roots"] = len(set(self.root_of.values())) if self.root_of else len(self.sources)
        return dict(counts)

    # ------------------------------------------------------------------ serialization
    def snapshot(self) -> dict[str, Any]:
        dump = lambda d: [v.model_dump(mode="json") for v in d.values()]  # noqa: E731
        return {
            "sources": [s.model_dump(mode="json", exclude={"raw_text"}) | {"raw_text_chars": len(s.raw_text)} for s in self.sources.values()],
            "assessments": dump(self.assessments), "claims": dump(self.claims), "evidence": dump(self.evidence),
            "inferences": dump(self.inferences), "hypotheses": dump(self.hypotheses),
            "requirements": dump(self.requirements), "gaps": dump(self.gaps),
            "lineage": [e.model_dump(mode="json") for e in self.lineage], "root_of": self.root_of,
            "observations": [o.model_dump(mode="json") for o in self.observations],
            "links": [{"from": a, "to": b, "type": d.get("type")} for a, b, d in self.g.edges(data=True)],
        }
