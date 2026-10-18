"""HACKATHON EVALUATION (section 44). Small, synthetic and labelled as such; no statistical claims.

Offline (default): both synthetic scenarios, each checked against the behaviour the brief requires,
plus metrics and a side-by-side comparison with the naive baseline (search -> one summary -> citations)
on the same corpus. Ground truth exists only because the fictional corpora are constructed:
  * lineage accuracy: pairwise same-root agreement with the constructed source families;
  * Brier score: on a few claims whose truth is fixed by construction (a sanity check, not calibration).

Live: ``--live`` runs examples/sample_questions.md with Token Factory + Tavily (metrics only; no ground truth).

    python -m evidence_research.evaluation.benchmark [--live]
"""

from __future__ import annotations

import argparse
import asyncio
import itertools
import json
import re
import sys
from pathlib import Path

from ..config import Depth, Settings, load_dotenv_if_present
from ..demo import FakeSearch, get_scenario
from ..evidence.lineage import detect_lineage
from ..evidence.source_classifier import assess
from ..models import Source, stable_id
from ..observability.events import EventType
from ..orchestration.orchestrator import RunResult
from ..retrieval.url_normalizer import canonicalize
from ..runtime import research
from ..verification.citation_verifier import CitationVerifier
from .baseline import baseline

# Constructed ground truth (fictional worlds).
TRUE_ROOT_GROUPS = {
    "business": [{"https://acmefleet.example/press/fy2025-results", "https://fleetnews.example/2026/02/acme-fleet-record-year",
                  "https://logistics-times.example/acme-fleet-growth", "https://dailyfreight-blog.example/acme-fleet-70-percent"}],
    "science": [{"https://preprints-archive.example/abs/2403.01234", "https://las-proceedings.example/2024/paper-17",
                 "https://journal-of-learning-research.example/article/10.5555/jlr.2025.0042",
                 "https://campus-news.example/2024/memoloop-boosts-grades", "https://edtech-blog.example/memoloop-a-third-better"}],
}
TRUE_LABELS = {
    "business": {"grew 70%": 1, "retained 95%": 0, "logo retention was 81%": 1, "45%": 1, "4,800 customers": 1},
    "science": {"0.12 standard": 1, "0.02 sd": 1, "0.8 standard": 0},
}
BASELINE_TEXT = {
    "business": "Acme Fleet shows strong product-market fit: revenue grew 70% and 95% of customers were retained, as reported by {n} sources {c}.",
    "science": "MemoLoop improves exam scores by 0.31 SD, confirmed by {n} independent sources {c}.",
}


def _fact(r: RunResult, needle: str):
    return next((c for c in r.graph.claims.values() if c.kind == "fact" and needle.lower() in c.natural_language.lower()), None)


def metrics(r: RunResult) -> dict:
    g, ev = r.graph, r.events
    verifier = CitationVerifier(g)
    facts = [c for c in g.claims.values() if c.kind == "fact"]
    grounded = [c for c in facts if verifier.claim_is_grounded(c.id)[0]]
    req = list(g.requirements.values())
    return {
        "status": r.report.status.value, "stop_reason": r.session.stop_reason.value if r.session.stop_reason else None,
        "citation_validity": round(sum(bool(s.evidence_ids) for s in r.report.conclusion) / len(r.report.conclusion), 3) if r.report.conclusion else None,
        "unsupported_statements_removed": len(r.report.rejected_statements),
        "fact_claims": len(facts), "unsupported_fact_claims": len(facts) - len(grounded),
        "unverified_extractions": g.stats().get("unverified_evidence", 0),
        "requirement_coverage": round(sum(bool(g.claims_for_requirement(q.id)) for q in req) / len(req), 3) if req else None,
        "urls_with_evidence": r.report.raw_source_count, "publication_families": r.report.publication_family_count,
        "independent_roots": r.report.independent_root_count,
        "screened_out": len(r.report.screened_out),
        "contradictions_found": len(ev.of_type(EventType.CONTRADICTION_FOUND)),
        "gaps_discovered": len(g.gaps), "inferences_rejected": len(ev.of_type(EventType.INFERENCE_REJECTED)),
        "studies": len(g.studies), "study_relations": len(g.study_relations),
        "agents_run": [t.agent_type for t in g.tasks.values()],
        "iterations": r.session.iteration, "searches": r.session.search_count, "model_calls": r.session.model_call_count,
    }


def lineage_accuracy(r: RunResult, truth: list[set[str]]) -> float:
    """Pairwise agreement: are two evidence-bearing sources in the same independent root, as constructed?"""
    g = r.graph
    used = sorted({e.source_id for e in g.evidence.values() if e.verification_status == "verified"})
    url = {sid: g.sources[sid].url for sid in used}
    true_group = {u: i for i, grp in enumerate(truth) for u in grp}
    pairs = list(itertools.combinations(used, 2))
    if not pairs:
        return 1.0
    ok = 0
    for a, b in pairs:
        same_true = url[a] in true_group and true_group.get(url[a]) == true_group.get(url[b])
        ok += (g.root_of.get(a, a) == g.root_of.get(b, b)) == same_true
    return round(ok / len(pairs), 3)


def brier(r: RunResult, labels: dict[str, int]) -> float | None:
    rows = [(c.truth_probability, y) for needle, y in labels.items() if (c := _fact(r, needle))]
    return round(sum((p - y) ** 2 for p, y in rows) / len(rows), 4) if rows else None


def business_checks(r: RunResult) -> dict[str, bool]:
    g, ev = r.graph, r.events
    growth, ret95 = _fact(r, "grew 70%"), _fact(r, "retained 95%")
    growth_sources = {e.source_id for e in g.evidence_for(growth.id)} if growth else set()
    selected = [e.data["agent"] for e in ev.of_type(EventType.AGENT_SELECTED)]
    return {
        "1-3 hypotheses, requirements, Tavily search": len(g.hypotheses) >= 4 and bool(g.requirements) and bool(ev.of_type(EventType.SEARCH_EXECUTED)),
        "4 sources screened": bool(ev.of_type(EventType.SOURCE_SCREENED)),
        "5-7 verbatim evidence on atomic claims in a DAG": all(e.exact_excerpt in g.sources[e.source_id].raw_text for e in g.evidence.values()
                                                               if e.verification_status == "verified"),
        "8-10 five sources support growth, only two independent roots": len(growth_sources) == 5 and growth is not None and len(g.roots_for_claim(growth.id)) == 2,
        "11-12 verifier rejects growth => PMF": any(i.status != "accepted" and "70%" in i.statement for i in g.inferences.values()),
        "13 gaps created for retention": any("retention" in x.description for x in g.gaps.values()),
        "14 a targeted researcher is selected dynamically": any(a != "GeneralResearcher" for a in selected),
        "15-16 retention search finds contradicting evidence": bool(ret95 and any(e.stance == "contradicts" for e in g.evidence_for(ret95.id))),
        "17 claim posterior falls": bool(ret95 and ret95.truth_probability < 0.5),
        "19 final status is LIKELY / CONTESTED / INSUFFICIENT": r.report.status.value in {"LIKELY", "CONTESTED", "INSUFFICIENT_EVIDENCE"},
        "20 explains unknowns and what would change our mind": bool(r.report.gaps and r.report.what_would_change),
        "outdated 2021 count is a temporal version": bool(ev.of_type(EventType.TEMPORAL_VERSION_DETECTED)),
        "abstains on the acquisition hypothesis": g.hypotheses["H3"].status == "insufficient",
        "prompt injection had no effect": not any("99%" in c.natural_language for c in g.claims.values()),
    }


def science_checks(r: RunResult) -> dict[str, bool]:
    g, ev = r.graph, r.events
    orig = max(g.studies.values(), key=lambda s: len(s.document_ids))
    pilot = next(s for s in g.studies.values() if "pilot" in s.title.lower())
    h1 = [o.value["p"] for o in g.history("H1")]
    return {
        "preprint, conference and journal resolved as ONE work": len(orig.document_ids) == 3 and bool(ev.of_type(EventType.SCIENTIFIC_VERSION_RESOLVED)),
        "versions + derived press count as one root": r.report.independent_root_count < r.report.raw_source_count,
        "peer-reviewed n=12 pilot still scores low quality": g.study_assessments[pilot.id].quality_score < 0.3,
        "conflict of interest recorded for the original study": any("conflict" in n for n in g.study_assessments[orig.id].notes),
        "independent replication found (REPLICATES)": any(x.relation == "REPLICATES" for x in g.study_relations.values()),
        "failed replication found (FAILS_TO_REPLICATE)": any(x.relation == "FAILS_TO_REPLICATE" for x in g.study_relations.values()),
        "H1 (material effect) rose, then fell after replication": len(h1) >= 3 and max(h1) > h1[0] and h1[-1] < h1[0],
        "results are verified against the source text": all(x.verification_status == "verified" for x in g.results.values()),
        "final status is LIKELY / CONTESTED / INSUFFICIENT": r.report.status.value in {"LIKELY", "CONTESTED", "INSUFFICIENT_EVIDENCE"},
    }


class _NaiveLLM:
    """The baseline 'LLM': summarizes the search results and cites all of them, as such systems do."""

    def __init__(self, template: str) -> None:
        self.template, self.records = template, []

    async def structured(self, op, role, system, payload, schema):
        n = len(payload["results"])
        return schema(report=self.template.format(n=n, c="".join(f"[{i}]" for i in range(1, n + 1))), cited_result_numbers=list(range(1, n + 1)))


async def baseline_comparison(name: str, system: RunResult) -> dict:
    sc = get_scenario(name)
    search = FakeSearch(sc.pages)
    query = " ".join(sc.default_queries["GeneralResearcher"])
    out, hits = await baseline(query, _NaiveLLM(BASELINE_TEXT[name]), search)
    by_url = {p.url: p for p in sc.pages}
    sources = [Source(id=stable_id("S", canonicalize(h.url)), url=h.url, canonical_url=canonicalize(h.url), title=h.title,
                      published_at=h.published_date, raw_text=by_url[h.url].text, extracted=True) for h in hits]
    lineage = detect_lineage(sources, {s.id: assess(s, sc.analysis().key_entities) for s in sources})
    cited = {sources[n - 1].id for n in out.cited_result_numbers if 0 < n <= len(sources)}
    m = metrics(system)
    return {
        "metric": ["cited 'sources'", "actual independent roots behind them", "contradictions discovered", "research gaps discovered",
                   "unsupported statements removed", "abstains where evidence is missing"],
        "baseline": [len(cited), len(lineage.independent_roots(cited)), 0, 0, 0, False],
        "system": [m["urls_with_evidence"], m["independent_roots"], m["contradictions_found"], m["gaps_discovered"],
                   m["unsupported_statements_removed"], any(h.status == "insufficient" for h in system.graph.hypotheses.values())],
        "baseline_report": out.report,
    }


async def run_offline(settings: Settings) -> dict:
    out = {"label": "HACKATHON EVALUATION on two SYNTHETIC scenarios (fictional corpora); not a statistical benchmark"}
    for name, checks in (("business", business_checks), ("science", science_checks)):
        r = await research(None, settings, Depth.STANDARD, demo=name, persist=False)
        out[name] = {"checks": checks(r), "metrics": metrics(r), "lineage_accuracy": lineage_accuracy(r, TRUE_ROOT_GROUPS[name]),
                     "brier_sanity_check": brier(r, TRUE_LABELS[name]), "baseline_vs_system": await baseline_comparison(name, r)}
    return out


async def run_live(settings: Settings, path: Path) -> list[dict]:
    from .baseline import run_baseline

    questions = [m.group(1).strip() for m in re.finditer(r"^\d+\.\s+\*\*.*?\*\*\s*[—-]\s*(.+)$", path.read_text(), re.M)]
    out = []
    for q in questions:
        r = await research(q, settings, Depth.FAST)
        out.append({"question": q, "metrics": metrics(r), "baseline_report": await run_baseline(q, settings)})
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
        print(json.dumps(asyncio.run(run_live(settings, args.questions)), indent=2, default=str))
        return 0
    result = asyncio.run(run_offline(settings))
    print(json.dumps(result, indent=2, default=str))
    failed = [f"{n}: {k}" for n in ("business", "science") for k, v in result[n]["checks"].items() if not v]
    if failed:
        print("FAILED checks:\n  " + "\n  ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
