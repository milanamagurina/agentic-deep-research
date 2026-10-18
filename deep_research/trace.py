"""Run trace and source ledger.

``Tracer`` is a middleware attached to the lead AND to every subagent (parent
middleware does not reach subagents, so each role gets its own instance). It
records:
  - each model turn: the role's short reasoning text and the tools it chose,
  - each tool call: arguments, duration, and the URLs it returned.

``SourceLedger`` keeps every URL and page text that Tavily actually returned
during the run. After the run, ``citations.py`` checks the report against it,
so a hallucinated URL or an edited quote is caught without another API call.
"""

from __future__ import annotations

import json
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TextIO

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

SEARCH_TOOLS = {"tavily_search", "tavily_extract"}
_FINDINGS = re.compile(r"/findings/([\w-]+)\.md")


@dataclass
class Source:
    url: str
    title: str = ""
    texts: list[str] = field(default_factory=list)
    found_by: str = ""


class SourceLedger:
    """Thread-safe record of everything retrieval returned. Parallel subagents share it."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sources: dict[str, Source] = {}

    def add(self, url: str, title: str = "", text: str = "", found_by: str = "") -> None:
        if not url:
            return
        key = normalize_url(url)
        with self._lock:
            src = self._sources.setdefault(key, Source(url=url, title=title, found_by=found_by))
            if title and not src.title:
                src.title = title
            if text:
                src.texts.append(text)

    def get(self, url: str) -> Source | None:
        with self._lock:
            return self._sources.get(normalize_url(url))

    def __len__(self) -> int:
        with self._lock:
            return len(self._sources)

    def to_json(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {"url": s.url, "title": s.title, "found_by": s.found_by, "chars": sum(map(len, s.texts))}
                for s in self._sources.values()
            ]


def normalize_url(url: str) -> str:
    url = url.strip().rstrip(").,;]>\"'")
    for prefix in ("https://", "http://"):
        if url.startswith(prefix):
            url = url[len(prefix):]
    if url.startswith("www."):
        url = url[4:]
    return url.split("#", 1)[0].rstrip("/").lower()


def parse_tool_payload(content: Any) -> dict[str, Any] | None:
    """Tavily tools return a dict; LangChain serializes it to JSON in the ToolMessage."""
    if isinstance(content, dict):
        return content
    if isinstance(content, list):  # content blocks
        content = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    if isinstance(content, str):
        try:
            data = json.loads(content)
        except (ValueError, TypeError):
            return None
        return data if isinstance(data, dict) else None
    return None


class RunTrace:
    """Append-only event log: JSONL on disk, one readable line per event on a stream."""

    def __init__(self, path: Path | None, stream: TextIO | None = sys.stderr) -> None:
        self._lock = threading.Lock()
        self._path = path
        self._stream = stream
        self._t0 = time.monotonic()
        self.events: list[dict[str, Any]] = []
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, role: str, kind: str, text: str, **data: Any) -> None:
        event = {"t": round(time.monotonic() - self._t0, 2), "role": role, "kind": kind, "text": text, **data}
        with self._lock:
            self.events.append(event)
            if self._path:
                with self._path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(event, default=str, ensure_ascii=False) + "\n")
            if self._stream:
                print(f"[{event['t']:>7.1f}s] {role:<24} {kind:<7} {text}", file=self._stream, flush=True)


def _short(value: Any, limit: int = 160) -> str:
    s = value if isinstance(value, str) else json.dumps(value, default=str, ensure_ascii=False)
    s = " ".join(s.split())
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _describe_call(name: str, args: dict[str, Any]) -> str:
    if name == "task":
        return f"delegate → {args.get('subagent_type', '?')}: {_short(args.get('description', ''), 140)}"
    if name == "tavily_search":
        return f"search  {_short(args.get('query', ''), 140)!r}"
    if name == "tavily_extract":
        return f"extract {_short(args.get('urls', ''), 140)}"
    if name == "write_todos":
        todos = args.get("todos") or []
        return "plan    " + _short(" | ".join(t.get("content", "") for t in todos if isinstance(t, dict)), 150)
    if name in ("write_file", "edit_file", "read_file"):
        return f"{name} {args.get('file_path', args.get('path', ''))}"
    return f"{name}({_short(args, 120)})"


def _messages(state: Any) -> list[Any]:
    if isinstance(state, dict):
        return state.get("messages") or []
    return getattr(state, "messages", None) or []


class Tracer(AgentMiddleware):
    """Records one role's decisions and harvests retrieved sources into the ledger."""

    def __init__(self, role: str, trace: RunTrace, ledger: SourceLedger) -> None:
        super().__init__()
        self.role = role
        self.trace = trace
        self.ledger = ledger

    @property
    def name(self) -> str:  # unique per role so it can sit next to other middleware
        return f"Tracer[{self.role}]"

    def _label(self, state: Any) -> str:
        """Tell parallel instances of one role apart by the findings file in their task."""
        if self.role != "researcher":
            return self.role
        for m in _messages(state):
            if isinstance(m, HumanMessage) and (hit := _FINDINGS.search(str(m.text))):
                return f"{self.role}:{hit.group(1)}"
        return self.role

    def after_model(self, state: Any, runtime: Any) -> None:
        messages = _messages(state)
        if not messages or not isinstance(messages[-1], AIMessage):
            return None
        role = self._label(state)
        msg = messages[-1]
        thought = str(msg.text)
        calls = [c["name"] for c in msg.tool_calls]
        if calls:
            self.trace.emit(role, "decide", (_short(thought, 120) + "  ⇒ " if thought.strip() else "⇒ ") + ", ".join(calls))
        elif thought.strip():
            self.trace.emit(role, "answer", _short(thought, 120), chars=len(thought))
        return None

    def wrap_tool_call(self, request: Any, handler: Any) -> Any:
        call = request.tool_call
        name, args = call.get("name", "tool"), call.get("args") or {}
        role = self._label(getattr(request, "state", None))
        self.trace.emit(role, "tool", _describe_call(name, args), tool=name, args=args)
        start = time.monotonic()
        result = handler(request)
        if name in SEARCH_TOOLS and isinstance(result, ToolMessage):
            self._harvest(role, name, result)
        elif name == "task":
            self.trace.emit(role, "return", f"{args.get('subagent_type', '?')} done in {time.monotonic() - start:.1f}s")
        return result

    def _harvest(self, role: str, tool: str, result: ToolMessage) -> None:
        payload = parse_tool_payload(result.content) or {}
        if payload.get("error"):
            self.trace.emit(role, "error", f"{tool}: {_short(payload['error'], 140)}")
            return
        urls = []
        for r in payload.get("results") or []:
            if not isinstance(r, dict):
                continue
            text = "\n".join(x for x in (r.get("content"), r.get("raw_content")) if isinstance(x, str))
            self.ledger.add(r.get("url", ""), r.get("title", ""), text, found_by=role)
            urls.append(r.get("url", ""))
        self.trace.emit(role, "result", f"{tool}: {len(urls)} result(s)", urls=urls)
