"""LLM gateway: the only place that talks to Nebius Token Factory.

* role-based model routing (FAST / REASONING / VERIFIER / SYNTHESIS)
* structured output only: JSON validated against a Pydantic schema, one repair retry
* bounded retries with backoff on transport errors
* every call is charged to the budget and recorded (model, operation, latency, tokens, ok)
* hidden reasoning (<think> blocks) is stripped and never stored

CLI:  python -m evidence_research.llm.gateway --list-models | --ping
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import time
from enum import Enum
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from ..config import ConfigError, Settings, load_dotenv_if_present
from ..observability.events import EventLog, EventType
from ..orchestration.budget import BudgetTracker
from .prompts import UNTRUSTED_BOUNDARY

log = logging.getLogger("evidence_research.llm")
T = TypeVar("T", bound=BaseModel)


class ModelRole(str, Enum):
    FAST = "fast"
    REASONING = "reasoning"
    VERIFIER = "verifier"
    SYNTHESIS = "synthesis"


class LLMError(RuntimeError):
    pass


class CallRecord(BaseModel):
    operation: str
    role: str
    model: str
    latency_s: float
    ok: bool
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    error: str | None = None


class LLMGateway(Protocol):
    records: list[CallRecord]

    async def structured(self, op: str, role: ModelRole, system: str, payload: dict[str, Any], schema: type[T]) -> T: ...


_THINK = re.compile(r"<think>.*?</think>", re.S | re.I)
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def extract_json(text: str) -> Any:
    text = _THINK.sub("", text or "").strip()
    if m := _FENCE.search(text):
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def build_user_message(payload: dict[str, Any], schema: type[BaseModel]) -> str:
    return (
        f"{UNTRUSTED_BOUNDARY}\n\n"
        "TASK INPUT (JSON):\n"
        f"{json.dumps(payload, ensure_ascii=False, default=str)}\n\n"
        "Respond with ONE JSON object only, no prose, matching this JSON schema:\n"
        f"{json.dumps(schema.model_json_schema(), separators=(',', ':'))}"
    )


class NebiusGateway:
    def __init__(self, settings: Settings, budget: BudgetTracker, events: EventLog | None = None) -> None:
        from openai import AsyncOpenAI

        if settings.nebius_api_key is None:
            raise ConfigError("NEBIUS_API_KEY is not set.")
        self.settings = settings
        self.budget = budget
        self.events = events
        self.records: list[CallRecord] = []
        self._client = AsyncOpenAI(
            api_key=settings.nebius_api_key.get_secret_value(),
            base_url=settings.nebius_base_url,
            timeout=settings.llm_timeout_s,
            max_retries=0,  # retries are ours, so they are bounded and logged
        )
        self._sem = asyncio.Semaphore(settings.llm_concurrency)

    def model_for(self, role: ModelRole) -> str:
        if role is not ModelRole.FAST and self.settings.nebius_reasoning_model:
            return self.settings.nebius_reasoning_model
        return self.settings.nebius_model

    async def structured(self, op: str, role: ModelRole, system: str, payload: dict[str, Any], schema: type[T]) -> T:
        messages = [{"role": "system", "content": system}, {"role": "user", "content": build_user_message(payload, schema)}]
        last_error = ""
        for repair in range(2):  # second attempt shows the model its validation error
            raw = await self._complete(op, role, messages)
            try:
                return schema.model_validate(extract_json(raw))
            except (json.JSONDecodeError, ValidationError) as e:
                last_error = str(e)[:800]
                self._dump_failure(op, repair, raw, last_error)
                log.warning("Invalid structured output for %s (attempt %d): %s", op, repair + 1, last_error[:200])
                # One fresh user turn quoting the bad output. Replaying it as an assistant turn breaks models
                # that require their reasoning to be sent back (e.g. reflection/beam).
                messages = messages[:2] + [{"role": "user", "content": (
                    f"Your previous reply was not valid for the schema.\nReply (truncated):\n{_THINK.sub('', raw)[:3000]}\n\n"
                    f"Validation errors:\n{last_error}\n\nReturn only the corrected JSON object.")}]
        raise LLMError(f"{op}: model output failed schema validation twice: {last_error[:300]}")

    def _dump_failure(self, op: str, attempt: int, raw: str, error: str) -> None:
        """Keep every invalid model reply for audit (data/llm_failures/); never secrets, only the reply."""
        folder = self.settings.data_dir / "llm_failures"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%dT%H%M%S")
        (folder / f"{stamp}-{op}-{attempt}.txt").write_text(
            f"finish_reason: {getattr(self, '_last_finish', None)}\nchars: {len(raw)}\nerror: {error}\n\n{raw}", encoding="utf-8")

    async def _complete(self, op: str, role: ModelRole, messages: list[dict[str, str]]) -> str:
        from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

        model = self.model_for(role)
        delay = 2.0
        for attempt in range(self.settings.llm_max_retries):
            self.budget.charge_model_call(final=role is ModelRole.SYNTHESIS)
            t0 = time.monotonic()
            try:
                async with self._sem:
                    resp = await self._client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=0.1,
                        max_tokens=self.settings.llm_max_tokens,
                        response_format={"type": "json_object"},
                    )
            except (APIConnectionError, APITimeoutError, RateLimitError, APIStatusError) as e:
                retryable = not isinstance(e, APIStatusError) or e.status_code >= 500 or e.status_code == 429
                self._record(op, role, model, t0, ok=False, error=f"{type(e).__name__}")
                if not retryable or attempt + 1 == self.settings.llm_max_retries:
                    raise LLMError(f"{op}: Token Factory call failed: {type(e).__name__}: {getattr(e, 'message', e)}") from e
                await asyncio.sleep(delay)
                delay *= 2
                continue
            usage = resp.usage
            self._record(op, role, model, t0, ok=True,
                         prompt_tokens=getattr(usage, "prompt_tokens", None),
                         completion_tokens=getattr(usage, "completion_tokens", None))
            choice = resp.choices[0]
            self._last_finish = getattr(choice, "finish_reason", None)
            return choice.message.content or ""
        raise LLMError(f"{op}: no attempts made")

    def _record(self, op: str, role: ModelRole, model: str, t0: float, ok: bool, **kw: Any) -> None:
        rec = CallRecord(operation=op, role=role.value, model=model, latency_s=round(time.monotonic() - t0, 2), ok=ok, **kw)
        self.records.append(rec)
        if self.events:
            self.events.emit(EventType.MODEL_CALL, f"{op} via {model} ({rec.latency_s}s{'' if ok else ', FAILED'})", **rec.model_dump())


async def _list_models(settings: Settings) -> list[str]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.nebius_api_key.get_secret_value(), base_url=settings.nebius_base_url)
    page = await client.models.list()
    return sorted(m.id for m in page.data)


async def _ping(settings: Settings) -> str:
    class Pong(BaseModel):
        ok: bool

    gw = NebiusGateway(settings, BudgetTracker(settings.budget))
    out = await gw.structured("ping", ModelRole.FAST, 'Return {"ok": true}.', {"ping": True}, Pong)
    rec = gw.records[-1]
    return f"ok={out.ok} model={rec.model} latency={rec.latency_s}s tokens={rec.prompt_tokens}/{rec.completion_tokens}"


def main() -> int:
    p = argparse.ArgumentParser(description="Token Factory utilities")
    p.add_argument("--list-models", action="store_true")
    p.add_argument("--ping", action="store_true", help="one structured-output call with the configured model")
    args = p.parse_args()
    load_dotenv_if_present()
    settings = Settings.from_env()
    if settings.nebius_api_key is None:
        print("NEBIUS_API_KEY is not set.")
        return 2
    if args.list_models:
        for m in asyncio.run(_list_models(settings)):
            print(m)
    if args.ping or not args.list_models:
        print(asyncio.run(_ping(settings)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
