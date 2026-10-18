"""Wiring: models, tools, and the lead agent with its subagents.

Every dependency is injectable so tests can swap in a scripted model and fake
tools without touching the network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from deepagents import create_deep_agent
from langchain.agents.middleware import TodoListMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from .config import Settings
from .prompts import FACT_CHECKER_PROMPT, LEAD_PROMPT, RESEARCHER_PROMPT
from .trace import RunTrace, SourceLedger, Tracer


@dataclass
class Toolset:
    search: BaseTool
    extract: BaseTool


def build_model(settings: Settings, model_id: str) -> BaseChatModel:
    from langchain_nebius import ChatNebius

    return ChatNebius(
        model=model_id,
        api_key=settings.nebius_api_key.get_secret_value(),
        base_url=settings.nebius_base_url,
        temperature=0.2,
        max_retries=3,
        request_timeout=180,
    )


def build_tools() -> Toolset:
    """Tavily reads TAVILY_API_KEY from the environment; it is never passed around."""
    from langchain_tavily import TavilyExtract, TavilySearch

    tavily_search = TavilySearch(max_results=5, search_depth="advanced")
    tavily_extract = TavilyExtract(extract_depth="basic")
    return Toolset(search=tavily_search, extract=tavily_extract)


def build_agent(
    model: BaseChatModel,
    tools: Toolset,
    trace: RunTrace,
    ledger: SourceLedger,
    *,
    worker_model: BaseChatModel | None = None,
    checker_model: BaseChatModel | None = None,
    max_parallel: int = 4,
) -> Any:
    tavily_search = tools.search
    researcher = {
        "name": "researcher",
        "description": (
            "Answers ONE sub-question with URL-anchored, verbatim evidence. Instruction MUST include: "
            "the sub-question, the original question, the evidence bar, sibling sub-questions, and a "
            "unique findings_file path /findings/<slug>.md. Dispatch several in parallel."
        ),
        "system_prompt": RESEARCHER_PROMPT,
        "tools": [tools.search, tools.extract],
        "model": worker_model or model,
        "middleware": [Tracer("researcher", trace, ledger)],
    }
    fact_checker = {
        "name": "fact-checker",
        "description": (
            "Adversarial reviewer. Use AFTER /draft.md exists and BEFORE the final answer. It tries to "
            "refute every claim with counter-searches and writes per-claim verdicts to /review.md."
        ),
        "system_prompt": FACT_CHECKER_PROMPT,
        "tools": [tools.search, tools.extract],
        # A different model for the checker gives an independent second opinion.
        "model": checker_model or model,
        "middleware": [Tracer("fact-checker", trace, ledger)],
    }
    return create_deep_agent(
        model=model,
        tools=[tavily_search],
        system_prompt=LEAD_PROMPT.replace("{max_parallel}", str(max_parallel)),
        subagents=[researcher, fact_checker],
        # deepagents 0.7 no longer adds a todo planner; the lead gets one explicitly.
        middleware=[TodoListMiddleware(), Tracer("lead", trace, ledger)],
        name="deep-research-lead",
    )
