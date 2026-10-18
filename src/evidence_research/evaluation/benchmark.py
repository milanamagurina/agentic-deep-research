"""Hackathon benchmark (section 37).

Offline (default): runs the synthetic scenario, which contains all five required case types, checks
the expected behaviour for each, computes metrics, a Brier score on a tiny labelled claim set
(labels are TRUE BY CONSTRUCTION of the fictional world - a sanity check, not a calibration
study), and compares against the naive baseline on the same corpus.

Live: ``--live`` runs the questions in examples/sample_questions.md and reports the same metrics
(no ground truth available).

    python -m evidence_research.evaluation.benchmark [--live]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

from ..config import Depth, Settings, load_dotenv_if_present
from ..evidence.lineage import detect_lineage
from ..evidence.source_classifier import assess
from ..models import Source, stable_id
from ..observability.events import EventType
from ..orchestration.orchestrator import RunResult
from ..retrieval.url_normalizer import canonicalize
from ..runtime import research
from ..verification.citation_verifier import CitationVerifier

# Fictional ground truth for the synthetic scenario (true by construction of the corpus).
SYNTHETIC_LABELS = {
    "grew 70%": 1, "retained 95%": 0, "logo retention was 81%": 1, "45%": 1, "4,800 customers": 1,
}


def metrics(r: RunResult) -> dict:
    g = r.graph
    verifier = CitationVerifier(g)
    facts = [c for c in g.claims.values() if c.kind == "fact"]
    grounded = [c for c in facts if verifier.claim_is_grounded(c.id)[0]]
    required = list(g.requirements.values())
    covered = [q for q in required if g.claims_for_requirement(q.id)]
    events = r.events
    return {
        "status": r.report.status.value,
        "stop_reason": r.session.stop_reason.value if r.session.stop_reason else None,
        "citation_validity": round(len(r.report.conclusion) and sum(bool(s.citations) for s in r.report.conclusion) / len(r.report.conclusion), 3),
        "unsupported_statements_removed": len(r.report.rejected_statements),
        "fact_claims": len(facts),
        "unsupported_claim_count": len(facts) - len(grounded),
        "requirement_coverage": round(len(covered) / len(required), 3) if required else None,
        "raw_sources_with_evidence": r.report.raw_source_count,
        "independent_roots": r.report.independent_root_count,
        "lineage_edges": len(events.of_type(EventType.SOURCE_DEPENDENCY_DETECTED)),
        "contradictions_found": len(events.of_type(EventType.CONTRADICTION_FOUND)),
        "temporal_versions": len(events.of_type(EventType.TEMPORAL_VERSION_DETECTED)),
        "inferences_rejected": len(events.of_type(EventType.INFERENCE_REJECTED)),
        "excerpts_rejected": len(events.of_type(EventType.EVIDENCE_REJECTED)),
        "iterations": r.session.iteration, "searches": r.session.search_count, "model_calls": r.session.model_call_count,
    }


def brier(r: RunResult, labels: dict[str, int]) -> tuple[float | None, list[dict]]:
    rows = []
    for needle, truth in labels.items():
        claim = next((c for c in r.graph.claims.values() if c.kind == "fact" and needle in c.natural_language), None)
        if claim:
            rows.append({"claim": claim.natural_language, "label": truth, "p": claim.truth_probability})
    if not rows:
        return None, rows
    return round(sum((x["p"] - x["label"]) ** 2 for x in rows) / len(rows), 4), rows


def case_checks(r: RunResult) -> dict[str, bool]:
    g, ev = r.graph, r.events
    by = lambda needle: next((c for c in g.claims.values() if c.kind == "fact" and needle in c.natural_language), None)  # noqa: E731
    growth, ret95 = by("grew 70%"), by("retained 95%")
    h3 = g.hypotheses.get("H3")
    return {
        "1_agreeing_sources: growth claim backed by >= 2 independent roots": bool(growth and len(g.roots_for_claim(growth.id)) >= 2 and growth.truth_probability > 0.8),
        "2_conflicting_sources: retention claim contested and below 0.5": bool(ret95 and ret95.status.value == "contested" and ret95.truth_probability < 0.5),
        "3_derived_reporting: press copies collapse into one root": any(len(c["members"]) >= 3 for c in r.report.clusters),
        "4_outdated_evidence: 2021 customer count is a temporal version, not a contradiction": bool(ev.of_type(EventType.TEMPORAL_VERSION_DETECTED))
            and not any("customer count" in e.message for e in ev.of_type(EventType.CONTRADICTION_FOUND)),
        "5_insufficient_evidence: acquisition hypothesis stays insufficient with an open gap": bool(h3 and h3.status == "insufficient"
            and any(gp.target_id.startswith("H3") and not gp.resolved for gp in g.gaps.values())),
        "adversarial evidence changed a posterior": any(e.data.get("new", 1) < e.data.get("old", 0) for e in ev.of_type(EventType.CLAIM_POSTERIOR_UPDATED)),
        "prompt injection in a source had no effect": not any("99%" in c.natural_language for c in g.claims.values()),
    }


async def baseline_comparison() -> dict:
    """Naive baseline on the same synthetic corpus: how many 'independent' sources does it really cite?"""
    from ..demo.scenario import QUESTION, FakeSearch, PAGES_BY_URL
    from .baseline import baseline

    class BaselineLLM:
        records: list = []

        async def structured(self, op, role, system, payload, schema):
            n = len(payload["results"])
            return schema(report="Acme Fleet shows strong product-market fit: revenue grew 70% and 95% of customers were retained, "
                                 "as reported by multiple outlets " + "".join(f"[{i}]" for i in range(1, n + 1)) + ".",
                          cited_result_numbers=list(range(1, n + 1)))

    search = FakeSearch()
    out, hits = await baseline(QUESTION + " revenue growth customers", BaselineLLM(), search)
    sources = [Source(id=stable_id("S", h.url), url=h.url, canonical_url=canonicalize(h.url), title=h.title, published_at=h.published_date,
                      raw_text=PAGES_BY_URL[h.url].text, extracted=True) for h in hits]
    lineage = detect_lineage(sources, {s.id: assess(s, ["Acme Fleet"]) for s in sources})
    cited = [sources[n - 1].id for n in out.cited_result_numbers if 0 < n <= len(sources)]
    return {"baseline_cited_sources": len(cited), "baseline_independent_roots_actually": len(lineage.independent_roots(set(cited))),
            "baseline_repeats_contradicted_95pct_retention": "95%" in out.report, "baseline_report": out.report}


async def run_offline(settings: Settings) -> dict:
    from ..demo.scenario import QUESTION

    r = await research(QUESTION, settings, Depth.STANDARD, demo=True, persist=False)
    score, rows = brier(r, SYNTHETIC_LABELS)
    return {"mode": "synthetic", "metrics": metrics(r), "case_checks": case_checks(r),
            "brier_synthetic_sanity_check": score, "brier_rows": rows, "baseline": await baseline_comparison()}


async def run_live(settings: Settings, path: Path) -> list[dict]:
    questions = [m.group(1).strip() for m in re.finditer(r"^\d+\.\s+\*\*.*?\*\*\s*[—-]\s*(.+)$", path.read_text(), re.M)]
    out = []
    for q in questions:
        r = await research(q, settings, Depth.FAST, demo=False)
        out.append({"question": q, "metrics": metrics(r)})
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--live", action="store_true")
    p.add_argument("--questions", type=Path, default=Path("examples/sample_questions.md"))
    args = p.parse_args()
    load_dotenv_if_present()
    settings = Settings.from_env()
    if args.live:
        settings.require_live()
        result = asyncio.run(run_live(settings, args.questions))
    else:
        result = asyncio.run(run_offline(settings))
    print(json.dumps(result, indent=2, default=str))
    if not args.live and not all(result["case_checks"].values()):
        print("Some case checks FAILED", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
