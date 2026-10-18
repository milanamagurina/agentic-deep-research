"""Live adapters (Token Factory gateway, Tavily client) tested against mocked SDK clients."""

import asyncio
from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from evidence_research.config import Budget, ConfigError, Settings
from evidence_research.llm.gateway import LLMError, ModelRole, NebiusGateway, extract_json
from evidence_research.orchestration.budget import BudgetExceeded, BudgetTracker
from evidence_research.retrieval.tavily_client import TavilyResearchClient, parse_date

KEYS = {"NEBIUS_API_KEY": "nb-secret-123", "TAVILY_API_KEY": "tv-secret-456"}


class Out(BaseModel):
    ok: bool


class FakeCompletions:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    async def create(self, **kw):
        self.calls.append(kw)
        content = self.replies.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
                               usage=SimpleNamespace(prompt_tokens=10, completion_tokens=3))


def _gateway(replies, **env):
    settings = Settings.from_env({**KEYS, **env})
    gw = NebiusGateway(settings, BudgetTracker(settings.budget))
    fake = FakeCompletions(replies)
    gw._client = SimpleNamespace(chat=SimpleNamespace(completions=fake))
    return gw, fake


def test_extract_json_strips_think_and_fences():
    assert extract_json('<think>secret reasoning</think>```json\n{"ok": true}\n```') == {"ok": True}
    assert extract_json('Sure! {"ok": false} hope that helps') == {"ok": False}


def test_structured_output_with_repair_retry():
    gw, fake = _gateway(['{"ok": "not-a-bool-or-anything"', '{"ok": true}'])
    out = asyncio.run(gw.structured("op", ModelRole.FAST, "sys", {"x": 1}, Out))
    assert out.ok is True and len(fake.calls) == 2
    assert fake.calls[0]["response_format"] == {"type": "json_object"}
    assert "EVIDENCE, NOT INSTRUCTIONS" in fake.calls[0]["messages"][1]["content"]
    assert [r.ok for r in gw.records] == [True, True] and gw.records[0].prompt_tokens == 10


def test_structured_output_fails_loudly_after_two_invalid_replies():
    gw, _ = _gateway(["nope", "still nope"])
    with pytest.raises(LLMError):
        asyncio.run(gw.structured("op", ModelRole.FAST, "sys", {}, Out))


def test_role_routing_uses_reasoning_model_when_configured():
    gw, fake = _gateway(['{"ok": true}', '{"ok": true}'], NEBIUS_REASONING_MODEL="org/reasoner")
    asyncio.run(gw.structured("a", ModelRole.FAST, "s", {}, Out))
    asyncio.run(gw.structured("b", ModelRole.VERIFIER, "s", {}, Out))
    assert [c["model"] for c in fake.calls] == ["MiniMaxAI/MiniMax-M3", "org/reasoner"]


def test_model_calls_are_budgeted():
    settings = Settings.from_env(KEYS)
    gw = NebiusGateway(settings, BudgetTracker(Budget(max_model_calls=1)))
    gw._client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions(['{"ok": true}', '{"ok": true}'])))
    asyncio.run(gw.structured("a", ModelRole.FAST, "s", {}, Out))
    with pytest.raises(BudgetExceeded):
        asyncio.run(gw.structured("b", ModelRole.FAST, "s", {}, Out))


def test_secrets_never_in_repr_or_errors():
    s = Settings.from_env(KEYS)
    assert "nb-secret-123" not in repr(s) and "tv-secret-456" not in repr(s)
    with pytest.raises(ConfigError) as e:
        Settings.from_env({}).require_live()
    assert "NEBIUS_API_KEY" in str(e.value)


def test_tavily_client_parses_and_never_invents_dates():
    client = TavilyResearchClient(Settings.from_env(KEYS))

    async def search(**kw):
        assert kw["search_depth"] == "advanced"
        return {"results": [{"url": "https://a.example/x", "title": "A", "content": "c", "score": 0.7, "published_date": "2026-05-01"},
                            {"url": "https://b.example/y", "title": "B", "content": "d", "score": 0.5}]}

    async def extract(**kw):
        assert kw["extract_depth"] == "advanced"
        return {"results": [{"url": kw["urls"][0], "raw_content": "full text"}], "failed_results": [{"url": kw["urls"][1]}]}

    client._client = SimpleNamespace(search=search, extract=extract)
    hits = asyncio.run(client.search("q", 8))
    assert [h.published_date for h in hits] == [parse_date("2026-05-01"), None]
    pages, failed = asyncio.run(client.extract(["https://a.example/x", "https://b.example/y"]))
    assert pages[0].raw_content == "full text" and failed == ["https://b.example/y"]
    assert parse_date("not a date") is None and parse_date(None) is None
