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


def test_repair_retry_never_replays_an_assistant_turn():
    """Reasoning models (e.g. reflection/beam) reject assistant turns sent back without their reasoning."""
    gw, fake = _gateway(['{"ok": "nope"', '{"ok": true}'])
    asyncio.run(gw.structured("op", ModelRole.REASONING, "sys", {}, Out))
    assert [m["role"] for m in fake.calls[1]["messages"]] == ["system", "user", "user"]


def test_model_outputs_ignore_extra_keys_but_domain_objects_do_not():
    from evidence_research.models import Claim, HypothesisProposal

    h = HypothesisProposal.model_validate({"key": "H1", "text": "t", "title": "extra from the model"})
    assert not hasattr(h, "title")
    with pytest.raises(Exception):
        Claim.model_validate({"id": "c", "subject": "s", "predicate": "p", "object": "o", "natural_language": "n", "bogus": 1})


def test_invalid_replies_are_kept_for_audit(tmp_path):
    gw, _ = _gateway(["not json", '{"ok": true}'], DATA_DIR=str(tmp_path))
    asyncio.run(gw.structured("judge_stance", ModelRole.VERIFIER, "sys", {}, Out))
    dumps = list((tmp_path / "llm_failures").glob("*judge_stance*"))
    assert len(dumps) == 1 and "not json" in dumps[0].read_text()


def test_a_failed_judge_batch_degrades_visibly_instead_of_aborting():
    from evidence_research.verification.entailment import CHUNK, JudgePair, judge_pairs

    class Flaky:
        records: list = []
        calls = 0

        async def structured(self, op, role, system, payload, schema):
            Flaky.calls += 1
            if Flaky.calls == 1:
                raise LLMError("model returned garbage")
            return schema(judgements=[{"pair_id": p["pair_id"], "stance": "supports", "strength": "explicit", "directness": "direct"}
                                      for p in payload["pairs"]])

    pairs = [JudgePair(f"P{i}", "c", "claim", "s", "excerpt") for i in range(CHUNK + 3)]
    errors: list[str] = []
    out = asyncio.run(judge_pairs(Flaky(), pairs, on_error=errors.append))
    assert len(out) == 3 and len(errors) == 1 and "stay unjudged" in errors[0]
