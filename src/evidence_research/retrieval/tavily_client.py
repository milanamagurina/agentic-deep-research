"""Tavily behind a small interface, so tests and the offline demo can swap it out.

CLI:  python -m evidence_research.retrieval.tavily_client --ping
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import date, datetime
from typing import Any, Protocol

from pydantic import BaseModel, Field

from ..config import ConfigError, Settings, load_dotenv_if_present

log = logging.getLogger("evidence_research.tavily")


class SearchHit(BaseModel):
    url: str
    title: str = ""
    content: str = ""
    score: float | None = None
    published_date: date | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class ExtractedPage(BaseModel):
    url: str
    raw_content: str
    raw: dict[str, Any] = Field(default_factory=dict)


class RetrievalError(RuntimeError):
    pass


class SearchClient(Protocol):
    async def search(self, query: str, max_results: int) -> list[SearchHit]: ...
    async def extract(self, urls: list[str]) -> tuple[list[ExtractedPage], list[str]]: ...


def parse_date(value: Any) -> date | None:
    """Tavily dates come in several formats; unparseable means unknown, never today."""
    if not value or not isinstance(value, str):
        return None
    for fmt in ("%Y-%m-%d", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).date()
    except ValueError:
        return None


class TavilyResearchClient:
    def __init__(self, settings: Settings) -> None:
        from tavily import AsyncTavilyClient

        if settings.tavily_api_key is None:
            raise ConfigError("TAVILY_API_KEY is not set.")
        self._client = AsyncTavilyClient(api_key=settings.tavily_api_key.get_secret_value())
        self._sem = asyncio.Semaphore(settings.tavily_concurrency)

    async def _retry(self, what: str, fn, *args, **kwargs) -> dict:
        delay = 2.0
        for attempt in range(3):
            try:
                async with self._sem:
                    return await fn(*args, **kwargs)
            except Exception as e:  # SDK raises several unrelated error types
                if attempt == 2:
                    raise RetrievalError(f"Tavily {what} failed after 3 attempts: {type(e).__name__}: {e}") from e
                log.warning("Tavily %s failed (attempt %d): %s", what, attempt + 1, type(e).__name__)
                await asyncio.sleep(delay)
                delay *= 2
        raise RetrievalError(f"Tavily {what}: unreachable")

    async def search(self, query: str, max_results: int) -> list[SearchHit]:
        resp = await self._retry("search", self._client.search, query=query, search_depth="advanced", max_results=max_results)
        return [
            SearchHit(
                url=r["url"], title=r.get("title") or "", content=r.get("content") or "", score=r.get("score"),
                published_date=parse_date(r.get("published_date")),
                raw={k: v for k, v in r.items() if k not in ("raw_content",)},
            )
            for r in resp.get("results", []) if r.get("url")
        ]

    async def extract(self, urls: list[str]) -> tuple[list[ExtractedPage], list[str]]:
        if not urls:
            return [], []
        resp = await self._retry("extract", self._client.extract, urls=urls, extract_depth="advanced")
        pages = [ExtractedPage(url=r["url"], raw_content=r.get("raw_content") or "", raw={"url": r["url"]})
                 for r in resp.get("results", []) if r.get("raw_content")]
        failed = [f.get("url", "") if isinstance(f, dict) else str(f) for f in resp.get("failed_results", [])]
        return pages, failed


async def _ping(settings: Settings) -> None:
    client = TavilyResearchClient(settings)
    hits = await client.search("Nebius Token Factory", max_results=3)
    print(f"search ok: {len(hits)} results")
    if hits:
        pages, failed = await client.extract([hits[0].url])
        print(f"extract ok: {len(pages)} page(s), {sum(len(p.raw_content) for p in pages)} chars, {len(failed)} failed")


def main() -> int:
    argparse.ArgumentParser(description="Tavily connectivity check").add_argument("--ping", action="store_true")
    load_dotenv_if_present()
    settings = Settings.from_env()
    if settings.tavily_api_key is None:
        print("TAVILY_API_KEY is not set.")
        return 2
    asyncio.run(_ping(settings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
