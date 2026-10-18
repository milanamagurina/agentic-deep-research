import json
from types import SimpleNamespace

from langchain_core.messages import ToolMessage

from deep_research.trace import RunTrace, SourceLedger, Tracer, parse_tool_payload

from .fakes import SEARCH_RESULTS, URL_A


def _tracer(tmp_path):
    trace = RunTrace(tmp_path / "trace.jsonl", stream=None)
    return Tracer("researcher", trace, SourceLedger()), trace


def test_search_results_are_harvested_into_ledger(tmp_path):
    tracer, trace = _tracer(tmp_path)
    request = SimpleNamespace(tool_call={"name": "tavily_search", "args": {"query": "q"}, "id": "1"})
    msg = ToolMessage(content=json.dumps(SEARCH_RESULTS), tool_call_id="1")
    assert tracer.wrap_tool_call(request, lambda r: msg) is msg
    assert len(tracer.ledger) == 2
    assert tracer.ledger.get(URL_A).found_by == "researcher"
    kinds = [json.loads(line)["kind"] for line in (tmp_path / "trace.jsonl").read_text().splitlines()]
    assert kinds == ["tool", "result"]


def test_tool_error_is_traced_not_harvested(tmp_path):
    tracer, trace = _tracer(tmp_path)
    request = SimpleNamespace(tool_call={"name": "tavily_search", "args": {"query": "q"}, "id": "1"})
    msg = ToolMessage(content=json.dumps({"error": "rate limited"}), tool_call_id="1")
    tracer.wrap_tool_call(request, lambda r: msg)
    assert len(tracer.ledger) == 0
    assert trace.events[-1]["kind"] == "error"


def test_parse_tool_payload_variants():
    assert parse_tool_payload({"a": 1}) == {"a": 1}
    assert parse_tool_payload('{"a": 1}') == {"a": 1}
    assert parse_tool_payload([{"type": "text", "text": '{"a": 1}'}]) == {"a": 1}
    assert parse_tool_payload("not json") is None
