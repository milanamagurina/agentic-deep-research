"""One research run: invoke the agent, pick the report, audit it, save artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .citations import Audit, audit_report
from .trace import RunTrace, SourceLedger

_THINK = re.compile(r"<think>.*?</think>", flags=re.S | re.I)


@dataclass
class RunResult:
    report: str
    audit: Audit
    files: dict[str, str]
    run_dir: Path | None


def _text(content: Any) -> str:
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    else:
        text = str(content or "")
    return _THINK.sub("", text).strip()


def _files(state: dict[str, Any]) -> dict[str, str]:
    out = {}
    for path, data in (state.get("files") or {}).items():
        content = data.get("content", "") if isinstance(data, dict) else data
        out[path] = "\n".join(content) if isinstance(content, list) else str(content)
    return out


def pick_report(state: dict[str, Any]) -> str:
    """Prefer /report.md (the agent's deliverable); fall back to the last message."""
    files = _files(state)
    from_file = files.get("/report.md", "").strip()
    messages = state.get("messages") or []
    from_msg = _text(messages[-1].content) if messages else ""
    if from_file and len(from_file) >= 0.8 * len(from_msg):
        return from_file
    return from_msg or from_file


def run_research(
    question: str,
    agent: Any,
    ledger: SourceLedger,
    trace: RunTrace,
    run_dir: Path | None = None,
    recursion_limit: int = 250,
) -> RunResult:
    trace.emit("user", "ask", question)
    state = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        config={"recursion_limit": recursion_limit},
    )
    report = pick_report(state)
    if not report:
        raise RuntimeError("The agent finished without producing a report.")
    audit = audit_report(report, ledger)
    c = audit.counts
    trace.emit("audit", "check", f"{c['VERIFIED']} verified, {c['URL_ONLY']} url-only, {c['UNRETRIEVED']} unretrieved")
    files = _files(state)
    if run_dir:
        _save(run_dir, question, report, audit, files, ledger)
    return RunResult(report=report, audit=audit, files=files, run_dir=run_dir)


def _save(run_dir: Path, question: str, report: str, audit: Audit, files: dict[str, str], ledger: SourceLedger) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "question.txt").write_text(question + "\n", encoding="utf-8")
    (run_dir / "report.md").write_text(report + "\n\n" + audit.to_markdown() + "\n", encoding="utf-8")
    (run_dir / "citations.json").write_text(json.dumps(audit.to_json(), indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "sources.json").write_text(json.dumps(ledger.to_json(), indent=2, ensure_ascii=False), encoding="utf-8")
    ws = run_dir / "workspace"
    for path, content in files.items():
        target = (ws / path.lstrip("/")).resolve()
        if ws.resolve() in target.parents:  # agent-chosen paths stay inside the run folder
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
