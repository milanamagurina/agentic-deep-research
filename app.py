"""CLI entrypoint.

    python app.py "Does Company X have strong product-market fit?" --depth standard
    python app.py --demo                       # offline synthetic run, no API keys
    python app.py "question" --baseline        # simple search -> one-shot synthesis, for comparison
    python app.py --check                      # Token Factory + Tavily connectivity checks

stdout: the report (Markdown). stderr: the live research trace.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from evidence_research.config import ConfigError, Depth, Settings, load_dotenv_if_present  # noqa: E402
from evidence_research.observability.events import EventType, format_event  # noqa: E402

QUIET = {EventType.MODEL_CALL, EventType.PHASE_CHANGED, EventType.SOURCE_REJECTED, EventType.SEARCH_PLANNED}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Probabilistic evidence deep research (Nebius Token Factory + Tavily)")
    p.add_argument("question", nargs="?", help="research question (omit with --demo)")
    p.add_argument("--depth", choices=[d.value for d in Depth], default="standard")
    p.add_argument("--demo", action="store_true", help="offline SYNTHETIC scenario: scripted model + fictional corpus")
    p.add_argument("--baseline", action="store_true", help="naive baseline: Tavily search + one LLM synthesis")
    p.add_argument("--check", action="store_true", help="verify Token Factory and Tavily connectivity")
    p.add_argument("--json", type=Path, help="also write the report as JSON to this path")
    p.add_argument("--md", type=Path, help="also write the report as Markdown to this path")
    p.add_argument("-v", "--verbose", action="store_true", help="show every event, including model calls")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    load_dotenv_if_present()
    try:
        settings = Settings.from_env()
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 2

    if args.check:
        return _check(settings)

    from evidence_research.demo.scenario import QUESTION

    question = args.question or (QUESTION if args.demo else None)
    if not question:
        p.error("a question is required (or use --demo)")

    try:
        if args.baseline:
            from evidence_research.evaluation.baseline import run_baseline

            settings.require_live()
            print(asyncio.run(run_baseline(question, settings)))
            return 0

        from evidence_research.runtime import research
        from evidence_research.synthesis.serializer import to_json, to_markdown

        def on_event(e) -> None:
            if args.verbose or e.type not in QUIET:
                print(format_event(e), file=sys.stderr, flush=True)

        result = asyncio.run(research(question, settings, Depth(args.depth), demo=args.demo, on_event=on_event))
    except ConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # surface the failure; never print a fabricated report
        print(f"Research run failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    md = to_markdown(result.report)
    print(md)
    if args.json:
        args.json.write_text(to_json(result.report), encoding="utf-8")
    if args.md:
        args.md.write_text(md, encoding="utf-8")
    return 0


def _check(settings: Settings) -> int:
    from evidence_research.llm.gateway import _ping as nebius_ping
    from evidence_research.retrieval.tavily_client import _ping as tavily_ping

    ok = True
    for name, missing, fn in (("Token Factory", settings.nebius_api_key is None, nebius_ping),
                              ("Tavily", settings.tavily_api_key is None, tavily_ping)):
        if missing:
            print(f"{name}: SKIPPED (key not set)")
            ok = False
            continue
        try:
            result = asyncio.run(fn(settings))
            print(f"{name}: OK {result or ''}")
        except Exception as e:
            print(f"{name}: FAILED {type(e).__name__}: {e}")
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
