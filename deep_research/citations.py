"""Deterministic citation audit.

The judge test is "click three citations at random and they hold up". This module
runs that test on EVERY citation, with no model in the loop:

  VERIFIED     URL was returned by Tavily during this run AND the quoted text
               appears in what Tavily returned for that URL.
  URL_ONLY     URL was retrieved, but the quote is missing or not found verbatim.
  UNRETRIEVED  URL never appeared in any tool result: likely fabricated.

It also flags citation markers in the body with no matching source entry.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass

from .trace import SourceLedger

VERIFIED, URL_ONLY, UNRETRIEVED = "VERIFIED", "URL_ONLY", "UNRETRIEVED"

_URL = re.compile(r"https?://[^\s<>()\[\]\"']+")
_SOURCE_LINE = re.compile(r"^\s*(?:[-*]\s*)?\[(\d+)\]\s*(.*)$")
_MARKER = re.compile(r"\[(\d+)\]")
_QUOTE = re.compile(r"[\"“”](.+?)[\"“”]")


@dataclass
class CitationCheck:
    n: int
    url: str
    title: str
    quote: str
    status: str
    note: str = ""


@dataclass
class Audit:
    checks: list[CitationCheck]
    dangling_markers: list[int]
    unused_sources: list[int]

    @property
    def counts(self) -> dict[str, int]:
        out = {VERIFIED: 0, URL_ONLY: 0, UNRETRIEVED: 0}
        for c in self.checks:
            out[c.status] += 1
        return out

    def to_json(self) -> dict:
        return {
            "counts": self.counts,
            "dangling_markers": self.dangling_markers,
            "unused_sources": self.unused_sources,
            "checks": [asdict(c) for c in self.checks],
        }

    def to_markdown(self) -> str:
        c = self.counts
        lines = [
            "## Citation audit (automatic, no model involved)",
            f"{len(self.checks)} sources: {c[VERIFIED]} verified (URL retrieved + quote found verbatim), "
            f"{c[URL_ONLY]} URL retrieved only, {c[UNRETRIEVED]} not retrieved in this run.",
            "",
            "| # | Status | Source |",
            "|---|---|---|",
        ]
        for ch in self.checks:
            label = {VERIFIED: "✅ verified", URL_ONLY: "⚠️ url only", UNRETRIEVED: "❌ not retrieved"}[ch.status]
            lines.append(f"| [{ch.n}] | {label} | {ch.url} |")
        if self.dangling_markers:
            lines.append("")
            lines.append("Markers with no source entry: " + ", ".join(f"[{n}]" for n in self.dangling_markers))
        return "\n".join(lines)


def _norm_text(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).lower()
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"[^\w%$€.,]+", " ", s)
    return " ".join(s.split())


def split_sources(report: str) -> tuple[str, str]:
    """Return (body, sources_section). The heading match is case-insensitive."""
    m = re.search(r"^#{1,3}\s*(sources|references)\s*$", report, flags=re.I | re.M)
    if not m:
        return report, ""
    rest = report[m.end():]
    nxt = re.search(r"^#{1,3}\s", rest, flags=re.M)
    return report[: m.start()], rest[: nxt.start()] if nxt else rest


def parse_sources(section: str) -> list[tuple[int, str, str, str]]:
    """Parse ``[n] Title - URL`` lines, each optionally followed by ``> "quote"`` lines."""
    entries: list[list] = []
    for line in section.splitlines():
        m = _SOURCE_LINE.match(line)
        if m:
            n, rest = int(m.group(1)), m.group(2)
            url_m = _URL.search(rest)
            url = url_m.group(0).rstrip(".,;") if url_m else ""
            title = rest[: url_m.start()].strip(" -–—:|") if url_m else rest.strip()
            inline_q = _QUOTE.search(rest[url_m.end():] if url_m else "")
            entries.append([n, url, title, inline_q.group(1) if inline_q else ""])
        elif entries and line.lstrip().startswith(">"):
            text = line.lstrip()[1:].strip()
            q = _QUOTE.search(text)
            piece = q.group(1) if q else text
            entries[-1][3] = (entries[-1][3] + " " + piece).strip()
            if not entries[-1][1] and (u := _URL.search(text)):
                entries[-1][1] = u.group(0)
    return [tuple(e) for e in entries]


def audit_report(report: str, ledger: SourceLedger) -> Audit:
    body, section = split_sources(report)
    sources = parse_sources(section)
    checks = []
    for n, url, title, quote in sources:
        src = ledger.get(url) if url else None
        if src is None:
            checks.append(CitationCheck(n, url, title, quote, UNRETRIEVED, "URL not seen in any tool result"))
            continue
        haystack = _norm_text("\n".join(src.texts))
        needle = _norm_text(quote)
        if needle and needle in haystack:
            checks.append(CitationCheck(n, url, title, quote, VERIFIED))
        else:
            note = "no quote given" if not needle else "quote not found verbatim in retrieved text"
            checks.append(CitationCheck(n, url, title, quote, URL_ONLY, note))
    listed = {c.n for c in checks}
    used = {int(x) for x in _MARKER.findall(body)}
    return Audit(checks, sorted(used - listed), sorted(listed - used))
