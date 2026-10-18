"""Search query generation: discovery, gap-targeted and adversarial (sections 7, 20, 28).

The model writes query text; code decides how many queries, for which targets, and dedups them.
"""

from __future__ import annotations

from ..graph.evidence_graph import EvidenceGraph
from ..llm.gateway import LLMGateway, ModelRole
from ..llm.prompts import ADVERSARIAL_RESEARCHER, QUERY_PLANNER
from ..models import QueryPlanOutput, QuestionAnalysis, ResearchGap


def _dedup(queries: list[str], seen: set[str], limit: int) -> list[str]:
    out = []
    for q in queries:
        key = " ".join(q.lower().split())
        if key and key not in seen:
            seen.add(key)
            out.append(q.strip())
        if len(out) >= limit:
            break
    return out


async def discovery_queries(llm: LLMGateway, analysis: QuestionAnalysis, graph: EvidenceGraph, seen: set[str], limit: int) -> list[str]:
    targets = [{"target": r.description, "hypothesis": graph.hypotheses[r.hypothesis_id].text}
               for r in sorted(graph.requirements.values(), key=lambda r: -r.importance)]
    payload = {"question": analysis.normalized_question, "entities": analysis.key_entities,
               "temporal_scope": analysis.temporal_scope, "targets": targets[:8], "max_queries": limit}
    out = await llm.structured("plan_discovery_queries", ModelRole.FAST, QUERY_PLANNER, payload, QueryPlanOutput)
    return _dedup(out.queries, seen, limit)


async def gap_queries(llm: LLMGateway, analysis: QuestionAnalysis, gaps: list[ResearchGap], seen: set[str], limit: int) -> list[str]:
    payload = {"question": analysis.normalized_question, "entities": analysis.key_entities,
               "targets": [{"gap_id": g.id, "gap_type": g.gap_type, "need": g.description, "hint": g.suggested_query} for g in gaps],
               "max_queries": limit}
    out = await llm.structured("plan_gap_queries", ModelRole.FAST, QUERY_PLANNER, payload, QueryPlanOutput)
    return _dedup(out.queries, seen, limit)


async def adversarial_queries(llm: LLMGateway, analysis: QuestionAnalysis, graph: EvidenceGraph, seen: set[str], limit: int) -> list[str]:
    leading = max((h for h in graph.hypotheses.values() if not h.is_null_hypothesis), key=lambda h: h.posterior_probability, default=None)
    targets = sorted(graph.claims.values(), key=lambda c: (-c.importance, -c.truth_probability))[:6]
    payload = {
        "question": analysis.normalized_question, "entities": analysis.key_entities,
        "leading_hypothesis": leading.text if leading else None,
        "target_claims": [{"id": c.id, "text": c.natural_language, "posterior": round(c.truth_probability, 2)} for c in targets],
        "max_queries": limit,
    }
    out = await llm.structured("plan_adversarial_queries", ModelRole.REASONING, ADVERSARIAL_RESEARCHER, payload, QueryPlanOutput)
    return _dedup(out.queries, seen, limit)
