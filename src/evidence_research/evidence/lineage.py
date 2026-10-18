"""Heuristic source lineage: five URLs repeating one press release are ONE independent root.

Signals for "child derives from parent" (each a probability-like weight, combined noisy-OR):
  explicit link        child text contains the parent's URL                       0.60
  same publisher       same registrable domain                                    0.50
  attribution          child names the parent's publisher / "press release"       0.35
  text reuse           6-word shingle containment, scaled                         up to 0.80
  shared quotations    identical quoted passages (>= 6 words)                     0.30 each, max 0.50
  timing               child published 0-10 days after parent (only with another) 0.10

Pairs above ``lineage_threshold`` are dependent; clusters are connected components; each cluster
has one root (earliest published, else most primary). All of this is deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..models import Source, SourceAssessment, SourceLineage
from ..retrieval.url_normalizer import canonicalize, registrable_domain

_WORD = re.compile(r"[a-z0-9€$%.,]+")
_QUOTED = re.compile(r"[\"“]([^\"”]{25,400})[\"”]")


def shingles(text: str, n: int = 6) -> set[tuple[str, ...]]:
    words = _WORD.findall(text.lower())
    return {tuple(words[i : i + n]) for i in range(max(0, len(words) - n + 1))}


def _quotes(text: str) -> set[str]:
    return {" ".join(q.lower().split()) for q in _QUOTED.findall(text) if len(q.split()) >= 6}


@dataclass
class LineageResult:
    edges: list[SourceLineage] = field(default_factory=list)
    root_of: dict[str, str] = field(default_factory=dict)  # source_id -> cluster root source_id
    clusters: dict[str, list[str]] = field(default_factory=dict)  # root -> members

    def independent_roots(self, source_ids: set[str]) -> set[str]:
        return {self.root_of.get(s, s) for s in source_ids}


def _order(a: Source, b: Source, assess: dict[str, SourceAssessment]) -> tuple[Source, Source]:
    """Return (parent, child)."""
    if a.published_at and b.published_at and a.published_at != b.published_at:
        return (a, b) if a.published_at < b.published_at else (b, a)
    pa = assess[a.id].primary_source_score if a.id in assess else 0
    pb = assess[b.id].primary_source_score if b.id in assess else 0
    if pa != pb:
        return (a, b) if pa > pb else (b, a)
    return (a, b) if a.id < b.id else (b, a)


def pair_signals(parent: Source, child: Source, sh: dict[str, set], qs: dict[str, set]) -> list[tuple[str, float]]:
    signals: list[tuple[str, float]] = []
    child_text = child.raw_text.lower()
    parent_canon = canonicalize(parent.url).removeprefix("https://")
    if parent_canon and parent_canon in child_text.replace("https://", "").replace("http://", "").replace("www.", ""):
        signals.append(("explicit link to parent URL", 0.60))
    if registrable_domain(parent.url) == registrable_domain(child.url):
        signals.append(("same publisher domain", 0.50))
    pub = (parent.publisher or "").lower()
    if (pub and len(pub) >= 4 and pub in child_text) or ("press release" in child_text and "press" in (parent.title or "").lower() + parent.url):
        signals.append(("child attributes content to parent publisher / press release", 0.35))
    a, b = sh.get(parent.id, set()), sh.get(child.id, set())
    if a and b:
        containment = len(a & b) / min(len(a), len(b))
        if containment >= 0.08:
            signals.append((f"text reuse: {containment:.0%} of 6-word phrases shared", min(0.8, round(containment * 2, 2))))
    shared_q = qs.get(parent.id, set()) & qs.get(child.id, set())
    if shared_q:
        signals.append((f"{len(shared_q)} identical quotation(s)", min(0.5, 0.3 * len(shared_q))))
    if signals and parent.published_at and child.published_at and 0 <= (child.published_at - parent.published_at).days <= 10:
        signals.append(("published within 10 days after parent", 0.10))
    return signals


def detect_lineage(sources: list[Source], assessments: dict[str, SourceAssessment], threshold: float = 0.5) -> LineageResult:
    texts = [s for s in sources if s.raw_text or s.snippet]
    sh = {s.id: shingles(s.raw_text or s.snippet) for s in texts}
    qs = {s.id: _quotes(s.raw_text or s.snippet) for s in texts}
    parent_uf = {s.id: s.id for s in sources}

    def find(x: str) -> str:
        while parent_uf[x] != x:
            parent_uf[x] = parent_uf[parent_uf[x]]
            x = parent_uf[x]
        return x

    best: dict[str, SourceLineage] = {}
    for i, s1 in enumerate(texts):
        for s2 in texts[i + 1 :]:
            parent, child = _order(s1, s2, assessments)
            sigs = pair_signals(parent, child, sh, qs)
            if not sigs:
                continue
            p_ind = 1.0
            for _, w in sigs:
                p_ind *= 1 - w
            dep = round(1 - p_ind, 3)
            if dep >= threshold:
                parent_uf[find(child.id)] = find(parent.id)
                if child.id not in best or dep > best[child.id].dependency_probability:
                    best[child.id] = SourceLineage(child_source_id=child.id, parent_source_id=parent.id,
                                                   dependency_probability=dep, reasons=[r for r, _ in sigs])

    by_id = {s.id: s for s in sources}
    members: dict[str, list[str]] = {}
    for s in sources:
        members.setdefault(find(s.id), []).append(s.id)
    root_of, clusters = {}, {}
    for group in members.values():
        root = min(group, key=lambda sid: (
            by_id[sid].published_at is None, by_id[sid].published_at or 0,
            -(assessments[sid].primary_source_score if sid in assessments else 0), sid))
        clusters[root] = sorted(group)
        for sid in group:
            root_of[sid] = root
    return LineageResult(edges=sorted(best.values(), key=lambda e: e.child_source_id), root_of=root_of, clusters=clusters)
