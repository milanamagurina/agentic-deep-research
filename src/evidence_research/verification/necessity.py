"""Necessity / deletion test (section 18): which premises does a conclusion actually rest on?

For the leading hypotheses, each accepted premise is removed in turn and the model judges whether the
conclusion is still justified by the REMAINING premises. This is recorded as a model-based necessity
assessment, not a proof. A sole accepted premise is necessary by structure (no model call).

Necessary premises get a REQUIRED_FOR link and research priority (importance), never truth.
"""

from __future__ import annotations

from ..graph.evidence_graph import EvidenceGraph
from ..llm.gateway import LLMError, LLMGateway, ModelRole
from ..llm.prompts import NECESSITY_TESTER
from ..models import NecessityAssessment, NecessityOutput
from ..observability.events import EventLog, EventType


async def deletion_test(llm: LLMGateway, graph: EvidenceGraph, events: EventLog, tested: set[tuple[str, frozenset]],
                        max_hypotheses: int = 1) -> list[NecessityAssessment]:
    out: list[NecessityAssessment] = []
    hyps = sorted((h for h in graph.hypotheses.values() if not h.is_null_hypothesis), key=lambda h: -h.posterior_probability)
    for h in hyps[:max_hypotheses]:
        premises = sorted({p for i in graph.inferences_for(h.id) if i.status == "accepted" for p in i.premise_ids if p in graph.claims})
        key = (h.id, frozenset(premises))
        if not premises or key in tested:
            continue
        tested.add(key)
        if len(premises) == 1:
            results = [NecessityAssessment(hypothesis_id=h.id, premise_id=premises[0], necessary=True,
                                           reason="sole accepted premise for this hypothesis", method="structural (sole premise)")]
        else:
            payload = {"conclusion": h.text, "premises": [{"id": p, "text": graph.claims[p].natural_language,
                                                           "model_estimated_posterior": round(graph.claims[p].truth_probability, 2)} for p in premises]}
            try:
                res = await llm.structured("assess_necessity", ModelRole.VERIFIER, NECESSITY_TESTER, payload, NecessityOutput)
            except LLMError as e:
                events.emit(EventType.ERROR, f"necessity assessment failed for {h.id}: {e}")
                continue
            results = [NecessityAssessment(hypothesis_id=h.id, premise_id=j.premise_id, necessary=not j.still_justified_without_it, reason=j.reason)
                       for j in res.judgements if j.premise_id in premises]
        for a in results:
            graph.set_necessity(a)
            if a.necessary:
                graph.claims[a.premise_id].importance = max(graph.claims[a.premise_id].importance, 0.9)
            events.emit(EventType.NECESSITY_ASSESSED,
                        f"{a.premise_id} is {'a NECESSARY' if a.necessary else 'NOT a necessary'} dependency of {h.id} ({a.method}): {a.reason}",
                        hypothesis_id=h.id, premise_id=a.premise_id, necessary=a.necessary)
        out += results
    return out
