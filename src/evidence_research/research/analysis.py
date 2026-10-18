"""Question analysis and hypothesis-first planning (sections 10-12)."""

from __future__ import annotations

from ..llm.gateway import LLMGateway, ModelRole
from ..llm.prompts import HYPOTHESIS_GENERATOR, QUESTION_ANALYZER
from ..models import EvidenceRequirement, Hypothesis, HypothesesOutput, QuestionAnalysis

# Coarse plausibility -> heuristic prior. These are starting beliefs, not ground truth.
PLAUSIBILITY_PRIOR = {"low": 0.2, "medium": 0.35, "high": 0.5}
IMPORTANCE = {"low": 0.3, "medium": 0.6, "high": 1.0}


async def analyze_question(llm: LLMGateway, question: str) -> QuestionAnalysis:
    return await llm.structured("analyze_question", ModelRole.FAST, QUESTION_ANALYZER, {"question": question}, QuestionAnalysis)


async def generate_hypotheses(llm: LLMGateway, analysis: QuestionAnalysis) -> tuple[list[Hypothesis], list[EvidenceRequirement]]:
    out = await llm.structured("generate_hypotheses", ModelRole.REASONING, HYPOTHESIS_GENERATOR,
                               {"analysis": analysis.model_dump()}, HypothesesOutput)
    proposals = out.hypotheses[:6]
    if not any(p.is_null_hypothesis for p in proposals):
        # The system must always be able to conclude "insufficient evidence".
        from ..models import HypothesisProposal
        proposals.append(HypothesisProposal(key="null", text="Public information is insufficient to answer this question with confidence.",
                                            is_null_hypothesis=True, plausibility="low"))
    hypotheses, requirements = [], []
    for i, p in enumerate(proposals, start=1):
        hid = f"H{i}"
        prior = PLAUSIBILITY_PRIOR[p.plausibility]
        hypotheses.append(Hypothesis(id=hid, text=p.text, is_null_hypothesis=p.is_null_hypothesis,
                                     prior_probability=prior, posterior_probability=prior))
        if p.is_null_hypothesis:
            continue
        for j, r in enumerate(p.requirements[:5], start=1):
            requirements.append(EvidenceRequirement(id=f"{hid}.R{j}", hypothesis_id=hid, description=r.description,
                                                    importance=IMPORTANCE[r.importance]))
    return hypotheses, requirements
