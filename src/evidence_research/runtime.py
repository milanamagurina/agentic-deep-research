"""Composition root: wires settings, gateway, retrieval and persistence for live or synthetic runs."""

from __future__ import annotations

from collections.abc import Callable

from .config import Depth, Settings
from .graph.repository import Repository
from .observability.events import EventLog, ResearchEvent
from .orchestration.budget import BudgetTracker
from .orchestration.orchestrator import Orchestrator, RunResult


def build(settings: Settings, depth: Depth, demo: str | None, on_event: Callable[[ResearchEvent], None] | None = None,
          persist: bool = True) -> tuple[Orchestrator, Settings]:
    """``demo``: None for a live run, or a synthetic scenario name ("business", "science")."""
    settings = settings.with_depth(depth)
    budget = BudgetTracker(settings.budget)
    events = EventLog()
    if on_event:
        events.subscribe(on_event)
    repo = Repository(settings.data_dir / "research.sqlite") if persist else None
    if demo:
        from .demo import FakeSearch, ScriptedLLM, get_scenario

        sc = get_scenario(demo)
        return Orchestrator(settings, ScriptedLLM(sc, budget), FakeSearch(sc.pages), budget, events, repo, today=sc.today), settings
    settings.require_live()
    from .llm.gateway import NebiusGateway
    from .retrieval.tavily_client import TavilyResearchClient

    return Orchestrator(settings, NebiusGateway(settings, budget, events), TavilyResearchClient(settings), budget, events, repo), settings


async def research(question: str | None, settings: Settings, depth: Depth = Depth.STANDARD, demo: str | None = None,
                   on_event: Callable[[ResearchEvent], None] | None = None, persist: bool = True) -> RunResult:
    orch, _ = build(settings, depth, demo, on_event, persist)
    if demo and not question:
        from .demo import get_scenario

        question = get_scenario(demo).question
    return await orch.run(question, depth.value, synthetic=bool(demo))
