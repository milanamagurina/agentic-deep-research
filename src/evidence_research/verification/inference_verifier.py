"""Inference as a first-class object (sections 18-19).

1. PROPOSE (model): premise claim IDs -> hypothesis, type, direction, coarse strength.
2. VALIDATE (code): IDs exist, no duplicates.
3. VERIFY (separate model call, VERIFIER role): verdict + missing premises + confounders.
4. LOGIC RULES (code), applied on top of the verdict:
   R1 every premise must itself be established (posterior >= 0.55), else needs_evidence;
   R2 premises resting on ONE provenance root that is an interested party cap the score at 'weak';
   R3 causal/abductive inferences with named confounders need evidence unless verdict is 'valid'.
5. Accepted inferences update hypotheses (probability/bayesian.py). Missing premises and
   confounders become WEAK_INFERENCE research gaps.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Heuristics
from ..graph.evidence_graph import EvidenceGraph
from ..llm.gateway import LLMGateway, ModelRole
from ..llm.prompts import INFERENCE_PROPOSER, INFERENCE_VERIFIER
from ..models import Inference, InferenceProposalOutput, InferenceVerdictOutput, stable_id
from ..observability.events import EventLog, EventType
from ..probability.bayesian import STRENGTH_NUM

PREMISE_MIN_POSTERIOR = 0.55


@dataclass
class VerificationRound:
    proposed: list[Inference] = field(default_factory=list)
    accepted: list[Inference] = field(default_factory=list)
    rejected: list[Inference] = field(default_factory=list)


def _claim_view(graph: EvidenceGraph, claim_id: str) -> dict:
    c = graph.claims[claim_id]
    return {"id": c.id, "text": c.natural_language, "kind": c.kind, "posterior": round(c.truth_probability, 2),
            "independent_roots": len(graph.roots_for_claim(c.id)), "status": c.status.value}


async def propose_and_verify(llm: LLMGateway, graph: EvidenceGraph, events: EventLog, h: Heuristics, question: str) -> VerificationRound:
    rnd = VerificationRound()
    evidenced = [c.id for c in graph.claims.values() if graph.evidence_for(c.id)]
    hyps = [x for x in graph.hypotheses.values() if not x.is_null_hypothesis]
    if not evidenced or not hyps:
        return rnd
    evidenced.sort(key=lambda cid: -graph.claims[cid].importance)
    payload = {
        "question": question,
        "hypotheses": [{"id": x.id, "text": x.text} for x in hyps],
        "claims": [_claim_view(graph, cid) for cid in evidenced[:20]],
        "already_decided": [{"premises": i.premise_ids, "hypothesis": i.conclusion_claim_id, "status": i.status} for i in graph.inferences.values()],
    }
    proposals = await llm.structured("propose_inferences", ModelRole.REASONING, INFERENCE_PROPOSER, payload, InferenceProposalOutput)

    fresh: list[Inference] = []
    for p in proposals.inferences:
        premises = sorted(set(p.premise_ids))
        if not premises or any(pid not in graph.claims for pid in premises) or p.hypothesis_id not in graph.hypotheses:
            events.emit(EventType.INFERENCE_REJECTED, f"proposal dropped: unknown premise or hypothesis id ({premises} → {p.hypothesis_id})")
            continue
        iid = stable_id("I", *premises, p.hypothesis_id, p.direction)
        if iid in graph.inferences:
            continue
        inf = Inference(id=iid, premise_ids=premises, conclusion_claim_id=p.hypothesis_id, direction=p.direction,
                        inference_type=p.inference_type, statement=p.statement, proposed_strength=STRENGTH_NUM[p.proposed_strength])
        graph.add_inference(inf)
        fresh.append(inf)
        events.emit(EventType.INFERENCE_PROPOSED, f"{inf.id}: {', '.join(premises)} ⇒ {p.direction} {p.hypothesis_id} ({p.inference_type}): {p.statement}",
                    inference_id=inf.id)
    rnd.proposed = fresh
    if not fresh:
        return rnd

    verify_payload = {
        "inferences": [{
            "inference_id": i.id, "type": i.inference_type, "direction": i.direction, "statement": i.statement,
            "premises": [_claim_view(graph, pid) for pid in i.premise_ids],
            "conclusion": graph.hypotheses[i.conclusion_claim_id].text,
        } for i in fresh]
    }
    verdicts = await llm.structured("verify_inferences", ModelRole.VERIFIER, INFERENCE_VERIFIER, verify_payload, InferenceVerdictOutput)
    by_id = {v.inference_id: v for v in verdicts.verdicts}

    for inf in fresh:
        v = by_id.get(inf.id)
        if v is None:
            inf.status, inf.failure_reason = "needs_evidence", "verifier returned no verdict"
            rnd.rejected.append(inf)
            continue
        score = h.inference_scores[v.verdict]
        reasons = [v.reason] if v.reason else []
        inf.missing_premises, inf.confounders = v.missing_premises, v.confounders + v.alternative_explanations

        weakest = min(graph.claims[p].truth_probability for p in inf.premise_ids)
        roots = set().union(*(graph.roots_for_claim(p) for p in inf.premise_ids))
        interested = all(graph.assessments[r].conflict_of_interest >= 0.6 for r in roots if r in graph.assessments)
        if weakest < PREMISE_MIN_POSTERIOR:
            status = "needs_evidence"
            reasons.append(f"R1: premise not established (weakest posterior {weakest:.2f})")
        elif len(roots) <= 1 and interested and inf.inference_type in ("inductive", "causal", "statistical", "abductive") and score > h.inference_scores["weak"]:
            score = h.inference_scores["weak"]
            status = "rejected"
            reasons.append("R2: all premises rest on one interested source (self-reported)")
        elif inf.inference_type in ("causal", "abductive") and inf.confounders and v.verdict != "valid":
            status = "needs_evidence"
            reasons.append("R3: causal/abductive inference with unexcluded confounders")
        else:
            status = "accepted" if score >= h.inference_accept_threshold else "rejected"

        inf.verifier_score, inf.status = score, status
        inf.failure_reason = None if status == "accepted" else "; ".join(reasons)
        graph.observe(inf.id, "verification", {"verdict": v.verdict, "score": score, "status": status}, "; ".join(reasons))
        if status == "accepted":
            rnd.accepted.append(inf)
            events.emit(EventType.INFERENCE_ACCEPTED, f"{inf.id} accepted ({v.verdict}, score {score:.2f})", inference_id=inf.id)
        else:
            rnd.rejected.append(inf)
            extra = f"; missing: {', '.join(inf.missing_premises)}" if inf.missing_premises else ""
            events.emit(EventType.INFERENCE_REJECTED, f"{inf.id} {status} ({v.verdict}): {inf.failure_reason}{extra}",
                        inference_id=inf.id, confounders=inf.confounders, missing=inf.missing_premises)
    return rnd
