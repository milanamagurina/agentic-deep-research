"""End-to-end with stubbed model and Tavily (synthetic scenario): the full MVP definition of done."""

import asyncio
import json

import pytest

import app
from evidence_research.config import Depth
from evidence_research.demo.scenario import QUESTION
from evidence_research.evaluation.benchmark import case_checks
from evidence_research.graph.repository import Repository
from evidence_research.models import ResearchPhase
from evidence_research.observability.events import EventType
from evidence_research.runtime import research


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    from evidence_research.config import Settings

    settings = Settings.from_env({"DATA_DIR": str(tmp_path_factory.mktemp("data"))})
    return asyncio.run(research(QUESTION, settings, Depth.STANDARD, demo=True)), settings


def _types(run):
    return [e.type for e in run[0].events.events]


def test_definition_of_done(run):
    r, _ = run
    types = _types(run)
    assert r.session.phase is ResearchPhase.COMPLETED
    # 1-2 hypotheses + evidence requirements
    assert len(r.graph.hypotheses) >= 4 and r.graph.requirements
    # 3-4 searches and extraction
    assert types.count(EventType.SEARCH_EXECUTED) >= 4 and EventType.SOURCE_EXTRACTED in types
    # 5-6 atomic claims in an evidence graph
    assert len(r.graph.claims) >= 8 and len(r.graph.evidence) >= 10
    # 8-10 an inference proposed, at least one weak inference rejected, creating a research gap
    rejected = [i for i in r.graph.inferences.values() if i.status != "accepted"]
    assert rejected and any(g.gap_type == "WEAK_INFERENCE" for g in r.graph.gaps.values())
    # 11 targeted additional search caused by a gap, with the reason in the trace
    assert any("because of" in e.message for e in r.events.of_type(EventType.RESEARCH_SCHEDULED))
    assert any(s.search_origin == "gap" and s.extracted for s in r.graph.sources.values())
    # 12-13 adversarial search found contrary evidence and a posterior went down
    assert any(s.search_origin == "adversarial" and s.extracted for s in r.graph.sources.values())
    assert any(e.stance == "contradicts" for e in r.graph.evidence.values())
    # 14 lineage detected derived reporting
    assert r.events.of_type(EventType.SOURCE_DEPENDENCY_DETECTED)
    assert r.report.independent_root_count < r.report.raw_source_count
    # 15 uncertainty exposed, 16 every statement linked to evidence, 17 stop reason recorded
    assert r.report.gaps and r.report.what_would_change
    assert r.report.conclusion and all(s.citations and s.claim_ids for s in r.report.conclusion)
    assert r.session.stop_reason is not None


def test_adversarial_evidence_lowers_confidence(run):
    r, _ = run
    ret = next(c for c in r.graph.claims.values() if "retained 95%" in c.natural_language and c.kind == "fact")
    history = [o.value["p"] for o in r.graph.history(ret.id)]
    assert max(history) - history[-1] > 0.15  # e.g. 0.71 -> 0.45
    assert ret.status.value == "contested"


def test_lineage_lowers_naive_confidence(run):
    r, _ = run
    drops = [e for e in r.events.of_type(EventType.CLAIM_POSTERIOR_UPDATED) if e.data["new"] < e.data["old"]]
    deps = r.events.of_type(EventType.SOURCE_DEPENDENCY_DETECTED)
    assert deps and any(d.seq > deps[0].seq for d in drops)


def test_unsupported_statements_are_removed(run):
    r, _ = run
    reasons = [s["reason"] for s in r.report.rejected_statements]
    assert any("no claim ids" in x for x in reasons) and any("85%" in x for x in reasons)
    assert not any("market leader" in s.text for s in r.report.conclusion)


def test_all_benchmark_case_checks_pass(run):
    assert all(case_checks(run[0]).values())


def test_importance_never_changes_truth(run):
    r, _ = run
    for c in r.graph.claims.values():
        for o in r.graph.history(c.id):
            assert "importance" not in o.value


def test_events_and_snapshot_persisted(run):
    r, settings = run
    repo = Repository(settings.data_dir / "research.sqlite")
    saved = repo.load(r.session.id)
    assert saved and saved["report"]["status"] == r.report.status.value
    assert len(saved["events"]) == len(r.events.events)
    assert saved["graph"]["claims"]


def test_cli_demo_prints_report(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    out_json = tmp_path / "r.json"
    assert app.main(["--demo", "--json", str(out_json)]) == 0
    out, err = capsys.readouterr()
    assert out.startswith("# Research report:") and "SYNTHETIC DEMO RUN" in out
    assert "INFERENCE_REJECTED" in err and "SOURCE_DEPENDENCY_DETECTED" in err
    assert json.loads(out_json.read_text())["synthetic"] is True


def test_cli_live_without_keys_fails_cleanly(capsys, monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setattr("app.load_dotenv_if_present", lambda: None)
    assert app.main(["Is X true?"]) == 2
    assert "NEBIUS_API_KEY" in capsys.readouterr().err
