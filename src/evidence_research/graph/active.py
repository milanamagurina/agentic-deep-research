"""Active Research Graph (section 7): the small working context the models see.

Rebuilt from the vault after every round. Contains only: active hypotheses, the claims that carry
the argument (most important x most uncertain, plus contested ones), their strongest evidence,
critical contradictions, top research gaps and the most recent belief updates. Models never receive
the full research history.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..models import ResearchGap
from ..observability.events import EventLog, EventType
from ..probability.engine import BeliefState
from ..probability.uncertainty import uncertainty
from .evidence_graph import EvidenceGraph


@dataclass
class ActiveResearchGraph:
    hypotheses: list[dict[str, Any]] = field(default_factory=list)
    claims: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    gaps: list[dict[str, Any]] = field(default_factory=list)
    recent_updates: list[str] = field(default_factory=list)

    @property
    def claim_ids(self) -> list[str]:
        return [c["id"] for c in self.claims]

    def to_payload(self) -> dict[str, Any]:
        return {"hypotheses": self.hypotheses, "claims": self.claims, "contradictions": self.contradictions,
                "open_gaps": self.gaps, "recent_updates": self.recent_updates}

    @classmethod
    def build(cls, graph: EvidenceGraph, beliefs: BeliefState, critical_ids: set[str], gaps: list[ResearchGap],
              events: EventLog | None = None, max_claims: int = 14) -> "ActiveResearchGraph":
        hyps = sorted(graph.hypotheses.values(), key=lambda h: -h.posterior_probability)
        hyp_view = [{"id": h.id, "text": h.text, "null": h.is_null_hypothesis, "posterior": round(h.posterior_probability, 2),
                     "sufficiency": round(h.evidence_sufficiency, 2), "status": h.status} for h in hyps if h.status != "rejected"]

        def score(cid: str) -> float:
            c = graph.claims[cid]
            b = beliefs.claims.get(cid)
            return c.importance * (0.3 + uncertainty(c.truth_probability)) + (0.5 if b and b.contested else 0.0)

        pool = [cid for cid in critical_ids if cid in graph.claims and graph.evidence_for(cid)]
        chosen = sorted(pool, key=lambda cid: -score(cid))[:max_claims]
        claims = []
        for cid in chosen:
            c, b = graph.claims[cid], beliefs.claims.get(cid)
            evs = sorted(graph.evidence_for(cid), key=lambda e: -(graph.evidence_quality[e.id].strength if e.id in graph.evidence_quality else 0))
            claims.append({
                "id": cid, "text": c.natural_language, "kind": c.kind, "posterior": round(c.truth_probability, 2),
                "sufficiency": round(c.evidence_sufficiency, 2), "status": c.status.value,
                "independent_roots": b.independent_roots if b else 0, "raw_sources": b.raw_sources if b else 0,
                "has_primary_source": b.has_primary if b else False, "contested": b.contested if b else False,
                "strongest_evidence": [{"stance": e.stance, "excerpt": e.exact_excerpt[:200],
                                        "source_type": graph.assessments[e.source_id].source_type if e.source_id in graph.assessments else "?"}
                                       for e in evs[:2]],
            })
        contradictions = [{"a": a, "b": b, "a_text": graph.claims[a].natural_language, "b_text": graph.claims[b].natural_language}
                          for a, b in graph.contradiction_pairs()][:6]
        contradictions += [{"claim": c["id"], "text": c["text"], "note": "independent sources disagree"} for c in claims if c["contested"]][:6]
        gap_view = [{"id": g.id, "type": g.gap_type, "description": g.description, "value": g.estimated_value} for g in gaps[:8]]
        recent = []
        if events:
            recent = [e.message for e in events.of_type(EventType.CLAIM_POSTERIOR_UPDATED, EventType.HYPOTHESIS_UPDATED,
                                                        EventType.INFERENCE_REJECTED, EventType.CONTRADICTION_FOUND)][-8:]
        return cls(hyp_view, claims, contradictions, gap_view, recent)
