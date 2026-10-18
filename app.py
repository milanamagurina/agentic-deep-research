"""Deep research CLI: a question in, a cited and audited report out.

    python app.py "your research question"

stdout carries only the report (prefixed with ``Deep research report:``);
the live decision trace goes to stderr, and every run is saved under runs/.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from deep_research import agents
from deep_research.config import DEFAULT_QUESTION, ConfigError, Settings
from deep_research.runner import run_research
from deep_research.trace import RunTrace, SourceLedger

REPORT_PREFIX = "Deep research report:"


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(override=False)  # real environment variables win over .env


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Multi-agent deep research on Nebius Token Factory + Tavily.")
    p.add_argument("question", nargs="?", default=DEFAULT_QUESTION, help="research question (default: a demo question)")
    p.add_argument("--quiet", action="store_true", help="do not stream the decision trace to stderr")
    p.add_argument("--no-save", action="store_true", help="do not write run artifacts under runs/")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    _load_dotenv()
    try:
        settings = Settings.from_env()
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 2

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir: Path | None = None if args.no_save else settings.runs_dir / run_id
    trace = RunTrace(run_dir / "trace.jsonl" if run_dir else None, stream=None if args.quiet else sys.stderr)
    ledger = SourceLedger()

    lead = agents.build_model(settings, settings.lead_model)
    worker = lead if settings.worker_model == settings.lead_model else agents.build_model(settings, settings.worker_model)
    checker = lead if settings.checker_model == settings.lead_model else agents.build_model(settings, settings.checker_model)
    agent = agents.build_agent(
        lead,
        agents.build_tools(),
        trace,
        ledger,
        worker_model=worker,
        checker_model=checker,
        max_parallel=settings.max_parallel_researchers,
    )

    try:
        result = run_research(args.question, agent, ledger, trace, run_dir, settings.recursion_limit)
    except Exception as e:  # surface the failure; never print a fabricated report
        print(f"Research run failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    print(REPORT_PREFIX)
    print(result.report)
    print()
    print(result.audit.to_markdown())
    if run_dir:
        print(f"\nRun artifacts: {run_dir}/", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
