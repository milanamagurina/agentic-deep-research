"""Locating model-proposed excerpts in the real source text, and choosing which passages to show the model.

``locate_excerpt`` never trusts the model's excerpt string. It finds the span in the retrieved text
and returns THAT span (the stored excerpt is always the source's own characters):
  1. exact match after normalization (case, whitespace, quotes, dashes, markdown table/emphasis
     characters)  -> method "exact";
  2. token alignment: the best window of source tokens matching the excerpt's tokens in order
     (difflib ratio >= 0.85, numbers must all be present) -> method "aligned". This recovers
     excerpts the model re-flowed from tables or lists;
  3. otherwise None -> the caller stores the extraction as UNVERIFIED (zero evidential weight).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

_MAP = {"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", " ": " "}
_STRIP = set("|*#_`>~")
_TOKEN = re.compile(r"[a-z0-9]+(?:[.,][0-9]+)*%?|\$|€|£")
ALIGN_THRESHOLD = 0.85


@dataclass
class Located:
    span: str
    start: int
    end: int
    method: str  # "exact" | "aligned"

    @property
    def location(self) -> str:
        return f"chars {self.start}-{self.end} ({self.method})"


def _normalize_with_map(text: str) -> tuple[str, list[int]]:
    """Normalized text plus, for each normalized char, its index in the original."""
    out, idx = [], []
    prev_space = True
    for i, ch in enumerate(text):
        ch = _MAP.get(ch, ch)
        ch = unicodedata.normalize("NFKC", ch).lower() if ord(ch) > 127 else ch.lower()
        for c in ch:
            if c in _STRIP or c.isspace():
                if not prev_space:
                    out.append(" ")
                    idx.append(i)
                    prev_space = True
                continue
            out.append(c)
            idx.append(i)
            prev_space = False
    return "".join(out), idx


def _norm(s: str) -> str:
    return _normalize_with_map(s)[0].strip(" .\"'")


def locate_excerpt(excerpt: str, text: str) -> Located | None:
    if not excerpt or not text:
        return None
    needle = _norm(excerpt)
    if len(needle) < 12:
        return None
    hay, idx = _normalize_with_map(text)
    pos = hay.find(needle)
    if pos >= 0:
        start, end = idx[pos], idx[pos + len(needle) - 1] + 1
        return Located(text[start:end], start, end, "exact")
    return _align(needle, text)


def _align(needle: str, text: str) -> Located | None:
    ntoks = _TOKEN.findall(needle)
    if len(ntoks) < 4:
        return None
    toks = [(m.group(0), m.start(), m.end()) for m in _TOKEN.finditer(text.lower())]
    words = [t[0] for t in toks]
    numbers = {t for t in ntoks if any(c.isdigit() for c in t)}
    anchor = max(ntoks, key=lambda t: (any(c.isdigit() for c in t), len(t)))  # rarest-looking token
    n = len(ntoks)
    best: tuple[float, int, int] | None = None
    for i, w in enumerate(words):
        if w != anchor:
            continue
        lo = max(0, i - n)
        for start in range(lo, i + 1):
            for length in (n - 2, n - 1, n, n + 1, n + 2, int(n * 1.3)):
                end = start + max(length, 1)
                if end > len(words):
                    continue
                window = words[start:end]
                ratio = SequenceMatcher(None, ntoks, window, autojunk=False).ratio()
                if best is None or ratio > best[0]:
                    best = (ratio, start, end)
    if best is None or best[0] < ALIGN_THRESHOLD:
        return None
    _, s, e = best
    if not numbers <= set(words[s:e]):  # a re-flowed table row must keep every number
        return None
    start, end = toks[s][1], toks[e - 1][2]
    return Located(text[start:end], start, end, "aligned")


def select_passages(text: str, terms: list[str], budget: int = 12_000, head: int = 1_500) -> str:
    """Most relevant blocks of a long page, in original order, within a character budget.

    Deterministic keyword scoring; the page head (title, date, byline) is always kept.
    """
    if len(text) <= budget:
        return text
    vocab = {w for t in terms for w in re.findall(r"[a-z0-9]{3,}", t.lower())}
    blocks = [b for b in re.split(r"\n\s*\n|\n(?=\|)", text) if b.strip()]
    scored = []
    offset = 0
    for i, b in enumerate(blocks):
        words = set(re.findall(r"[a-z0-9]{3,}", b.lower()))
        score = len(words & vocab) + (0.5 if re.search(r"\d", b) else 0)
        scored.append((score / (1 + len(b) / 2000), i, b))
        offset += len(b)
    chosen, used = set(), min(head, budget)
    for score, i, b in sorted(scored, key=lambda t: -t[0]):
        if score <= 0 or used + len(b) > budget:
            continue
        chosen.add(i)
        used += len(b) + 2
    body = "\n\n".join(b for i, b in enumerate(blocks) if i in chosen)
    return text[:head] + "\n\n[…]\n\n" + body
