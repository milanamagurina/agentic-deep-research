"""Evidence judge: the model classifies stance; code maps categories to numbers (section 17)."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Heuristics
from ..llm.gateway import LLMGateway, ModelRole
from ..llm.prompts import EVIDENCE_JUDGE
from ..models import StanceJudgement, StanceOutput

DIRECTNESS = {"direct": 1.0, "indirect": 0.5, "tangential": 0.2}


@dataclass
class JudgePair:
    pair_id: str
    claim_id: str
    claim_text: str
    source_id: str
    excerpt: str
    reported_speech: bool = False


@dataclass
class ScoredStance:
    stance: str
    entailment_probability: float
    contradiction_probability: float
    directness: float
    rationale: str


def score(j: StanceJudgement, h: Heuristics, reported_speech: bool) -> ScoredStance:
    p = h.stance_strength_probability[j.strength]
    directness = DIRECTNESS[j.directness]
    if reported_speech:
        directness = min(directness, h.reported_speech_directness)
    floor = 0.05
    return ScoredStance(
        stance=j.stance,
        entailment_probability=p if j.stance == "supports" else floor,
        contradiction_probability=p if j.stance == "contradicts" else floor,
        directness=directness,
        rationale=j.rationale,
    )


async def judge_pairs(llm: LLMGateway, pairs: list[JudgePair]) -> dict[str, StanceJudgement]:
    if not pairs:
        return {}
    out: dict[str, StanceJudgement] = {}
    for start in range(0, len(pairs), 25):  # bounded prompt size
        chunk = pairs[start : start + 25]
        payload = {"pairs": [
            {"pair_id": p.pair_id, "claim": p.claim_text, "excerpt": p.excerpt, "excerpt_is_reported_speech": p.reported_speech}
            for p in chunk
        ]}
        result = await llm.structured("judge_stance", ModelRole.VERIFIER, EVIDENCE_JUDGE, payload, StanceOutput)
        out.update({j.pair_id: j for j in result.judgements if j.pair_id in {p.pair_id for p in chunk}})
    return out
