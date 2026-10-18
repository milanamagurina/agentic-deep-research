"""Search query generation per researcher agent (sections 21, 29, 32).

Each agent has its own specialized prompt (llm/prompts.py AGENT_QUERY_PROMPTS). The model writes the
query text; code decides which agent runs, for which targets, how many queries, and dedups them.
"""

from __future__ import annotations

from ..graph.active import ActiveResearchGraph
from ..graph.evidence_graph import EvidenceGraph
from ..llm.gateway import LLMGateway, ModelRole
from ..llm.prompts import AGENT_QUERY_PROMPTS
from ..models import QueryPlanOutput, QuestionAnalysis, ResearchGap

REASONING_AGENTS = {"AdversarialResearcher", "ContradictionResearcher"}


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


def targets_for(agent: str, analysis: QuestionAnalysis, graph: EvidenceGraph, gaps: list[ResearchGap],
                active: ActiveResearchGraph, target_ids: list[str]) -> list[dict]:
    if agent == "GeneralResearcher":
        reqs = [graph.requirements[t] for t in target_ids if t in graph.requirements] or \
               sorted(graph.requirements.values(), key=lambda r: -r.importance)
        return [{"target": r.description, "hypothesis": graph.hypotheses[r.hypothesis_id].text} for r in reqs[:8]]
    if agent == "AdversarialResearcher":
        leader = graph.hypotheses.get(target_ids[0]) if target_ids else None
        return [{"leading_hypothesis": leader.text if leader else None,
                 "claims_to_attack": [{"id": c["id"], "text": c["text"], "posterior": c["posterior"]} for c in active.claims[:6]]}]
    by_id = {g.id: g for g in gaps}
    out = []
    for gid in target_ids:
        g = by_id.get(gid)
        if g is None:
            continue
        t = {"gap_id": g.id, "gap_type": g.gap_type, "need": g.description, "hint": g.suggested_query}
        if g.target_id in graph.studies:
            t["study_title"] = graph.studies[g.target_id].title
        out.append(t)
    return out


async def plan_queries(llm: LLMGateway, agent: str, analysis: QuestionAnalysis, graph: EvidenceGraph, gaps: list[ResearchGap],
                       active: ActiveResearchGraph, target_ids: list[str], seen: set[str], limit: int) -> list[str]:
    if limit <= 0:
        return []
    payload = {"agent": agent, "question": analysis.normalized_question, "entities": analysis.key_entities,
               "temporal_scope": analysis.temporal_scope, "targets": targets_for(agent, analysis, graph, gaps, active, target_ids),
               "max_queries": limit}
    role = ModelRole.REASONING if agent in REASONING_AGENTS else ModelRole.FAST
    out = await llm.structured("plan_queries", role, AGENT_QUERY_PROMPTS[agent], payload, QueryPlanOutput)
    return _dedup(out.queries, seen, limit)
