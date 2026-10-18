"""Offline stand-ins for Token Factory and Tavily.

``ScriptedChatModel`` is a real ``BaseChatModel`` whose next message is a pure
function of the role (found in the system prompt) and the conversation so far.
That keeps parallel subagents deterministic: no shared queue to race on.
"""

from __future__ import annotations

import itertools
import re
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from deep_research.agents import Toolset

URL_A = "https://example.org/storage/iron-air-pilot"
URL_B = "https://energy.example.gov/reports/flow-batteries-2026"
URL_C = "https://news.example.com/sodium-ion-grid"
QUOTE_A = "The first 1.5 MW iron-air system entered commercial operation in 2025."
QUOTE_B = "Installed vanadium flow battery capacity reached 2 GW worldwide."

SEARCH_RESULTS = {
    "query": "stub",
    "results": [
        {"url": URL_A, "title": "Iron-air pilot", "content": QUOTE_A + " Costs were not disclosed.", "score": 0.9},
        {"url": URL_B, "title": "Flow batteries 2026", "content": QUOTE_B, "score": 0.8},
    ],
}

REPORT = f"""# Non-lithium grid storage in 2026

## Answer
Iron-air and vanadium flow batteries are commercially deployed [1][2].

## Findings
- **C1.** An iron-air system entered commercial operation in 2025 [1] - Confidence: Medium - Check: Confirmed
  - Why this confidence: one primary source.
- **C2.** Flow battery capacity reached 2 GW [2] - Confidence: Medium - Check: Weakened
  - Why this confidence: single government report.

## Contested or refuted
None.

## Gaps
Cost per kWh was not disclosed.

## Sources
[1] Iron-air pilot - {URL_A}
> "{QUOTE_A}"
[2] Flow batteries 2026 - {URL_B}
> "{QUOTE_B}"
"""

_ids = itertools.count()


def _call(name: str, **args: Any) -> dict[str, Any]:
    return {"name": name, "args": args, "id": f"call_{next(_ids)}", "type": "tool_call"}


def _role(messages: list[BaseMessage]) -> str:
    system = " ".join(str(m.text) for m in messages if isinstance(m, SystemMessage))
    if "adversarial fact-checker" in system:
        return "fact-checker"
    if "research worker" in system:
        return "researcher"
    return "lead"


def default_policy(role: str, messages: list[BaseMessage]) -> AIMessage:
    tool_results = [m for m in messages if isinstance(m, ToolMessage)]
    if role == "researcher":
        task = next(m.text for m in messages if isinstance(m, HumanMessage))
        path = re.search(r"/findings/[\w-]+\.md", task).group(0)
        if not tool_results:
            return AIMessage("Searching for primary sources.", tool_calls=[_call("tavily_search", query="iron-air commercial 2025")])
        if len(tool_results) == 1:
            return AIMessage("", tool_calls=[_call("tavily_extract", urls=[URL_A])])
        if len(tool_results) == 2:
            body = f'## Claims\n- iron-air commercial\n  - url: {URL_A}\n  - quote: "{QUOTE_A}"\n'
            return AIMessage("", tool_calls=[_call("write_file", file_path=path, content=body)])
        return AIMessage(f"Evidence is moderate. Findings in {path}.")
    if role == "fact-checker":
        if not tool_results:
            return AIMessage("Trying to refute C2.", tool_calls=[_call("tavily_search", query="flow battery capacity 2026 correction")])
        if len(tool_results) == 1:
            review = "## C1 - CONFIRMED\nreason: matches source\n## C2 - WEAKENED\nreason: single source\n"
            return AIMessage("", tool_calls=[_call("write_file", file_path="/review.md", content=review)])
        return AIMessage("1 confirmed, 1 weakened.")
    # lead: one step per completed turn
    step = sum(1 for m in messages if isinstance(m, AIMessage))
    script = [
        lambda: AIMessage("Scoping the terrain first.", tool_calls=[_call("tavily_search", query="grid storage non-lithium 2026")]),
        lambda: AIMessage("Two sub-questions.", tool_calls=[_call("write_todos", todos=[
            {"content": "iron-air deployments", "status": "in_progress"},
            {"content": "flow battery deployments", "status": "pending"},
        ])]),
        lambda: AIMessage("Dispatching researchers in parallel.", tool_calls=[
            _call("task", subagent_type="researcher", description="Iron-air deployments. findings_file /findings/iron-air.md"),
            _call("task", subagent_type="researcher", description="Flow batteries. findings_file /findings/flow.md"),
        ]),
        lambda: AIMessage("Evidence bar met; drafting.", tool_calls=[_call("write_file", file_path="/draft.md", content=REPORT)]),
        lambda: AIMessage("Challenging the draft.", tool_calls=[_call("task", subagent_type="fact-checker", description="Check /draft.md against /findings/")]),
        lambda: AIMessage("Applying verdicts.", tool_calls=[_call("write_file", file_path="/report.md", content=REPORT)]),
        lambda: AIMessage(REPORT),
    ]
    return script[min(step, len(script) - 1)]()


class ScriptedChatModel(BaseChatModel):
    policy: Any = default_policy
    calls: list[str] = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedChatModel":
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        role = _role(messages)
        self.calls.append(role)
        return ChatResult(generations=[ChatGeneration(message=self.policy(role, messages))])


class _SearchArgs(BaseModel):
    query: str


class _ExtractArgs(BaseModel):
    urls: list[str]


class FakeTavilySearch(BaseTool):
    name: str = "tavily_search"
    args_schema: type[BaseModel] = _SearchArgs
    description: str = "Search the web (offline stub)."
    queries: list[str] = []

    def _run(self, query: str, **kwargs: Any) -> dict[str, Any]:
        self.queries.append(query)
        return {**SEARCH_RESULTS, "query": query}


class FakeTavilyExtract(BaseTool):
    name: str = "tavily_extract"
    args_schema: type[BaseModel] = _ExtractArgs
    description: str = "Extract page content (offline stub)."

    def _run(self, urls: list[str], **kwargs: Any) -> dict[str, Any]:
        return {"results": [{"url": u, "raw_content": QUOTE_A + " Full page text."} for u in urls]}


def fake_toolset() -> Toolset:
    return Toolset(search=FakeTavilySearch(), extract=FakeTavilyExtract())
