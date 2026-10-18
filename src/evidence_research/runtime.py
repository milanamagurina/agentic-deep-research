"""Composition root: wires settings, gateway, retrieval and persistence for live or synthetic runs."""

from __future__ import annotations

from collections.abc import Callable

from .config import Depth, Settings
from .graph.repository import Repository
from .observability.events import EventLog, ResearchEvent
from .orchestration.budget import BudgetTracker
from .orchestration.orchestrator import Orchestrator, RunResult


def build(settings: Settings, depth: Depth, demo: bool, on_event: Callable[[ResearchEvent], None] | None = None,
          persist: bool = True) -> tuple[Orchestrator, Settings]:
    settings = settings.with_depth(depth)
    budget = BudgetTracker(settings.budget)
    events = EventLog()
    if on_event:
        events.subscribe(on_event)
    repo = Repository(settings.data_dir / "research.sqlite") if persist else None
    if demo:
        from .demo.scenario import TODAY, FakeSearch, ScriptedLLM

        return Orchestrator(settings, ScriptedLLM(budget), FakeSearch(), budget, events, repo, today=TODAY), settings
    settings.require_live()
    from .llm.gateway import NebiusGateway
    from .retrieval.tavily_client import TavilyResearchClient

    return Orchestrator(settings, NebiusGateway(settings, budget, events), TavilyResearchClient(settings), budget, events, repo), settings


async def research(question: str, settings: Settings, depth: Depth = Depth.STANDARD, demo: bool = False,
                   on_event: Callable[[ResearchEvent], None] | None = None, persist: bool = True) -> RunResult:
    orch, _ = build(settings, depth, demo, on_event, persist)
    return await orch.run(question, depth.value, synthetic=demo)
