"""End-to-end CLI run with the model and search stubbed: real deepagents graph, no network."""

import json

import pytest

import app
from deep_research import agents

from .conftest import FAKE_NEBIUS_KEY, FAKE_TAVILY_KEY
from .fakes import ScriptedChatModel, fake_toolset

QUESTION = "Which non-lithium grid storage technologies are commercial in 2026?"


@pytest.fixture
def stubbed(env, monkeypatch):
    model = ScriptedChatModel(calls=[])
    tools = fake_toolset()
    built_models = []

    def fake_build_model(settings, model_id):
        built_models.append(model_id)
        return model

    monkeypatch.setattr(agents, "build_model", fake_build_model)
    monkeypatch.setattr(agents, "build_tools", lambda: tools)
    return model, tools, built_models


def test_full_run_prints_report_and_exits_zero(stubbed, capsys, env):
    model, tools, _ = stubbed
    assert app.main([QUESTION]) == 0
    out, err = capsys.readouterr()

    assert out.startswith("Deep research report:\n")
    assert "## Sources" in out and "## Citation audit" in out
    assert "2 sources: 2 verified" in out  # both quotes appear verbatim in what the stub tools returned

    # The trace shows decisions by every role, including parallel delegation.
    assert "delegate → researcher" in err and "delegate → fact-checker" in err
    assert {"lead", "researcher", "fact-checker"} <= set(model.calls)
    assert model.calls.count("researcher") >= 8  # two researchers x four turns
    assert len(tools.search.queries) == 1 + 2 + 1  # lead scoping, two researchers, fact-checker

    # Secrets never reach stdout or stderr.
    for secret in (FAKE_NEBIUS_KEY, FAKE_TAVILY_KEY):
        assert secret not in out and secret not in err


def test_run_artifacts_are_saved(stubbed, env, capsys):
    assert app.main([QUESTION]) == 0
    (run_dir,) = (env / "runs").iterdir()
    names = {p.name for p in run_dir.iterdir()}
    assert {"report.md", "trace.jsonl", "citations.json", "sources.json", "workspace"} <= names
    assert (run_dir / "workspace" / "findings" / "iron-air.md").exists()
    assert (run_dir / "workspace" / "review.md").exists()
    roles = {json.loads(line)["role"] for line in (run_dir / "trace.jsonl").read_text().splitlines()}
    assert {"lead", "researcher:iron-air", "researcher:flow", "fact-checker", "audit"} <= roles


def test_default_question_used_without_args(stubbed, capsys):
    assert app.main(["--quiet", "--no-save"]) == 0
    out, err = capsys.readouterr()
    assert out.startswith("Deep research report:")
    assert err == ""


def test_single_model_instance_when_roles_share_a_model(stubbed):
    _, _, built = stubbed
    app.main(["--quiet", "--no-save", QUESTION])
    assert len(built) == 1


def test_missing_credentials_exit_2(env, monkeypatch, capsys):
    monkeypatch.delenv("TAVILY_API_KEY")
    assert app.main([QUESTION]) == 2
    out, err = capsys.readouterr()
    assert out == "" and "TAVILY_API_KEY" in err and FAKE_NEBIUS_KEY not in err


def test_provider_failure_exits_1_without_a_report(stubbed, monkeypatch, capsys):
    model, _, _ = stubbed

    def boom(role, messages):
        raise ConnectionError("Token Factory unreachable")

    monkeypatch.setattr(model, "policy", boom)
    assert app.main(["--quiet", QUESTION]) == 1
    out, err = capsys.readouterr()
    assert "Deep research report:" not in out
    assert "Token Factory unreachable" in err
