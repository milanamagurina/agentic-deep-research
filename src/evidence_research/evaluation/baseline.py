"""Naive baseline (section 36): question -> Tavily search -> ONE LLM synthesis -> report.

Kept deliberately simple; its job is to be compared against the evidence-controlled pipeline.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..config import Settings
from ..llm.gateway import LLMGateway, ModelRole
from ..llm.prompts import BASELINE_SYNTHESIZER
from ..orchestration.budget import BudgetTracker
from ..retrieval.tavily_client import SearchClient, SearchHit


class BaselineReport(BaseModel):
    report: str
    cited_result_numbers: list[int] = []


async def baseline(question: str, llm: LLMGateway, search: SearchClient, max_results: int = 8) -> tuple[BaselineReport, list[SearchHit]]:
    hits = await search.search(question, max_results)
    payload = {"question": question,
               "results": [{"n": i + 1, "title": h.title, "url": h.url, "content": h.content} for i, h in enumerate(hits)]}
    out = await llm.structured("baseline_synthesize", ModelRole.SYNTHESIS, BASELINE_SYNTHESIZER, payload, BaselineReport)
    return out, hits


async def run_baseline(question: str, settings: Settings) -> str:
    from ..llm.gateway import NebiusGateway
    from ..retrieval.tavily_client import TavilyResearchClient

    out, hits = await baseline(question, NebiusGateway(settings, BudgetTracker(settings.budget)), TavilyResearchClient(settings))
    refs = "\n".join(f"[{i + 1}] {h.title} — {h.url}" for i, h in enumerate(hits))
    return f"# Baseline report (search + one synthesis)\n\n{out.report}\n\n## Results\n{refs}"
