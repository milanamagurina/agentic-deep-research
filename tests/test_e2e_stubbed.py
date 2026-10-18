"""End-to-end with stubbed model and Tavily on both SYNTHETIC scenarios: the real pipeline, no network."""

import asyncio
import json

import pytest

import app
from evidence_research.config import Depth, Settings
from evidence_research.evaluation.benchmark import business_checks, lineage_accuracy, science_checks, TRUE_ROOT_GROUPS
from evidence_research.graph.repository import Repository
from evidence_research.models import ResearchPhase
from evidence_research.observability.events import EventType
from evidence_research.runtime import research


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    out = {}
    for name in ("business", "science"):
        settings = Settings.from_env({"DATA_DIR": str(tmp_path_factory.mktemp(name))})
        out[name] = (asyncio.run(research(None, settings, Depth.STANDARD, demo=name)), settings)
    return out


@pytest.mark.parametrize("name,checks", [("business", business_checks), ("science", science_checks)])
def test_required_behaviour(runs, name, checks):
    r, _ = runs[name]
    failed = [k for k, v in checks(r).items() if not v]
    assert not failed, failed
    assert r.session.phase is ResearchPhase.COMPLETED and r.session.stop_reason is not None
    assert lineage_accuracy(r, TRUE_ROOT_GROUPS[name]) == 1.0


@pytest.mark.parametrize("name", ["business", "science"])
def test_every_statement_has_a_full_citation_chain(runs, name):
    r, _ = runs[name]
    assert r.report.conclusion
    for s in r.report.conclusion:
        assert s.claim_ids and s.evidence_ids and s.citations
        for eid in s.evidence_ids:
            e = r.graph.evidence[eid]
            assert e.claim_id in s.claim_ids and e.verification_status == "verified"
            assert e.exact_excerpt in r.graph.sources[e.source_id].raw_text
    assert r.report.rejected_statements  # the scenarios contain ungrounded drafts that must be removed


@pytest.mark.parametrize("name", ["business", "science"])
def test_trace_shows_decisions_not_a_script(runs, name):
    r, _ = runs[name]
    types = {e.type for e in r.events.events}
    assert {EventType.AGENT_BIDS, EventType.AGENT_SELECTED, EventType.SOURCE_SCREENED, EventType.INFERENCE_REJECTED,
            EventType.RESEARCH_GAP_CREATED, EventType.STOP_DECISION, EventType.INDEPENDENCE_SUMMARY} <= types
    agents = [t.agent_type for t in r.graph.tasks.values()]
    assert agents[0] == "GeneralResearcher" and len(set(agents)) >= 3  # different agents chosen by utility, not a fixed order
    assert r.graph.bids and all(b.reasons for _, bids in r.graph.bids for b in bids)


def test_scientific_objects_and_provenance_links(runs):
    r, _ = runs["science"]
    g = r.graph
    link_types = {d["type"] for _, _, d in g.g.edges(data=True)}
    assert {"DESCRIBES", "PRODUCES", "EXTRACTED_AS", "EXTRACTED_FROM", "DUPLICATES", "REPLICATES", "FAILS_TO_REPLICATE",
            "SUPPORTS_HYPOTHESIS", "CHALLENGES_HYPOTHESIS", "REQUIRED_FOR"} <= link_types
    orig = max(g.studies.values(), key=lambda s: len(s.document_ids))
    assert {g.documents[d].document_type for d in orig.document_ids} == {"preprint", "conference_paper", "peer_reviewed_article"}
    assert g.study_assessments[orig.id].peer_reviewed is True  # from the journal version, while the preprint itself is not
    pre = next(d for d in g.documents.values() if d.document_type == "preprint")
    assert pre.peer_reviewed is False
    assert any(q.study_quality is not None and q.replication is not None and q.replication < 1 for q in g.evidence_quality.values())


def test_confidence_history_is_never_overwritten(runs):
    r, _ = runs["business"]
    ret = next(c for c in r.graph.claims.values() if "retained 95%" in c.natural_language and c.kind == "fact")
    history = [o.value["p"] for o in r.graph.history(ret.id)]
    assert len(history) >= 4 and max(history) - history[-1] > 0.15
    for c in r.graph.claims.values():
        assert all("importance" not in o.value for o in r.graph.history(c.id))


def test_negative_provenance_is_kept(runs):
    r, _ = runs["business"]
    rejected = [i for i in r.graph.inferences.values() if i.status != "accepted"]
    assert rejected and all(i.failure_reasons for i in rejected)
    assert r.graph.screening  # every screening decision is stored


def test_events_and_snapshot_persisted(runs):
    r, settings = runs["science"]
    saved = Repository(settings.data_dir / "research.sqlite").load(r.session.id)
    assert saved and saved["report"]["status"] == r.report.status.value
    assert len(saved["events"]) == len(r.events.events)
    assert saved["graph"]["studies"] and saved["graph"]["screening"] and saved["graph"]["bids"]


@pytest.mark.parametrize("scenario", ["business", "science"])
def test_cli_demo(capsys, tmp_path, monkeypatch, scenario):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    out_json = tmp_path / "r.json"
    assert app.main(["--demo", scenario, "--json", str(out_json)]) == 0
    out, err = capsys.readouterr()
    assert out.startswith("# Research report:") and "SYNTHETIC DEMO RUN" in out and "## Why research stopped" in out
    assert "AGENT_SELECTED" in err and "SOURCE_DEPENDENCY_DETECTED" in err
    assert json.loads(out_json.read_text())["synthetic"] is True


def test_cli_live_without_keys_fails_cleanly(capsys, monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.setattr("app.load_dotenv_if_present", lambda: None)
    assert app.main(["Is X true?"]) == 2
    assert "NEBIUS_API_KEY" in capsys.readouterr().err
