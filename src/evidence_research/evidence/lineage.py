"""Heuristic source lineage: five URLs repeating one press release are ONE independent root.

Signals for "child depends on parent" (probability-like weights, combined noisy-OR):
  explicit link        child text contains the parent's URL (with a real path)       0.60
  same publisher       same registrable domain (not for multi-publisher hosts)        0.50
  reported announcement child reports a company/press-wire parent's announcement      0.35
  text reuse           6-word shingle containment >= 12% (and >= 10 shared), scaled   up to 0.80
  shared quotations    identical quoted passages (>= 6 words, not quoted titles)      0.30 each, max 0.50
  timing               child published 0-10 days after parent (only with another)     0.10

Scientific versions of one work (preprint / conference / journal) come from the
ScientificSourceResolver as ``same_work_version`` edges and are merged here.

Two groupings are reported:
  publication families  same work or same publisher (versions, sister pages)
  independent roots     families PLUS derived reporting: what actually counts as independent
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..models import Source, SourceAssessment, SourceLineage
from ..retrieval.url_normalizer import canonicalize, registrable_domain

_WORD = re.compile(r"[a-z0-9€$%.,]+")
_QUOTED = re.compile(r"[\"“]([^\"”]{25,400})[\"”]")
_REPORTING = re.compile(r"press release|announced|according to (?:a |the )?(?:company|statement|release|announcement)|"
                        r"said in a statement|the company said|in a statement|company reported", re.I)
# Hosts that publish for many unrelated parties: the same domain does not mean the same publisher.
MULTI_PUBLISHER_HOSTS = {
    "sec.gov", "arxiv.org", "doi.org", "nih.gov", "sciencedirect.com", "springer.com", "nature.com", "wiley.com",
    "medium.com", "substack.com", "github.com", "youtube.com", "reddit.com", "wikipedia.org", "linkedin.com", "x.com",
    "twitter.com", "prnewswire.com", "businesswire.com", "globenewswire.com", "yahoo.com", "google.com",
    "seekingalpha.com", "researchgate.net", "ssrn.com", "acm.org", "ieee.org", "openreview.net",
}


def shingles(text: str, n: int = 6) -> set[tuple[str, ...]]:
    words = _WORD.findall(text.lower())
    return {tuple(words[i : i + n]) for i in range(max(0, len(words) - n + 1))}


def _is_title(q: str) -> bool:
    """Quoted titles of cited works ("MemoLoop: Adaptive Spaced Retrieval ...") are citations, not copied text."""
    words = [w for w in q.split() if w[:1].isalpha()]
    return bool(words) and sum(w[0].isupper() for w in words) / len(words) >= 0.6


def _quotes(text: str) -> set[str]:
    return {" ".join(q.lower().split()) for q in _QUOTED.findall(text) if len(q.split()) >= 6 and not _is_title(q)}


@dataclass
class LineageResult:
    edges: list[SourceLineage] = field(default_factory=list)
    root_of: dict[str, str] = field(default_factory=dict)    # source -> independent root
    family_of: dict[str, str] = field(default_factory=dict)  # source -> publication family
    clusters: dict[str, list[str]] = field(default_factory=dict)

    def independent_roots(self, source_ids: set[str]) -> set[str]:
        return {self.root_of.get(s, s) for s in source_ids}

    def families(self, source_ids: set[str]) -> set[str]:
        return {self.family_of.get(s, s) for s in source_ids}


def _order(a: Source, b: Source, assess: dict[str, SourceAssessment]) -> tuple[Source, Source]:
    """Return (parent, child)."""
    if a.published_at and b.published_at and a.published_at != b.published_at:
        return (a, b) if a.published_at < b.published_at else (b, a)
    pa = assess[a.id].primary_source_score if a.id in assess else 0
    pb = assess[b.id].primary_source_score if b.id in assess else 0
    if pa != pb:
        return (a, b) if pa > pb else (b, a)
    return (a, b) if a.id < b.id else (b, a)


def pair_signals(parent: Source, child: Source, sh: dict[str, set], qs: dict[str, set],
                 assess: dict[str, SourceAssessment]) -> tuple[list[tuple[str, float]], str]:
    signals: list[tuple[str, float]] = []
    kind = "derived_reporting"
    child_text = child.raw_text.lower()
    parent_canon = canonicalize(parent.url).removeprefix("https://")
    path = parent_canon.split("/", 1)[1] if "/" in parent_canon else ""
    if len(path) >= 4 and parent_canon in child_text.replace("https://", "").replace("http://", "").replace("www.", ""):
        signals.append(("explicit link to parent URL", 0.60))
    domain = registrable_domain(parent.url)
    if domain == registrable_domain(child.url) and domain not in MULTI_PUBLISHER_HOSTS:
        signals.append(("same publisher domain", 0.50))
        kind = "same_publisher"
    parent_type = assess[parent.id].source_type if parent.id in assess else ""
    if parent_type in ("company", "press_wire") and kind != "same_publisher" and _REPORTING.search(child_text):
        signals.append(("child reports the parent's announcement", 0.35))
    a, b = sh.get(parent.id, set()), sh.get(child.id, set())
    if a and b:
        shared = len(a & b)
        containment = shared / min(len(a), len(b))
        if containment >= 0.12 and shared >= 10:
            signals.append((f"text reuse: {containment:.0%} of 6-word phrases shared", min(0.8, round(containment * 2, 2))))
    shared_q = qs.get(parent.id, set()) & qs.get(child.id, set())
    if shared_q:
        signals.append((f"{len(shared_q)} identical quotation(s)", min(0.5, 0.3 * len(shared_q))))
    if signals and parent.published_at and child.published_at and 0 <= (child.published_at - parent.published_at).days <= 10:
        signals.append(("published within 10 days after parent", 0.10))
    return signals, kind


class _UF:
    def __init__(self, ids):
        self.p = {i: i for i in ids}

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, child, parent):
        self.p[self.find(child)] = self.find(parent)


def detect_lineage(sources: list[Source], assessments: dict[str, SourceAssessment], threshold: float = 0.5,
                   version_edges: list[SourceLineage] | None = None) -> LineageResult:
    texts = [s for s in sources if s.raw_text or s.snippet]
    sh = {s.id: shingles(s.raw_text or s.snippet) for s in texts}
    qs = {s.id: _quotes(s.raw_text or s.snippet) for s in texts}
    ids = [s.id for s in sources]
    roots_uf, family_uf = _UF(ids), _UF(ids)

    best: dict[str, SourceLineage] = {}
    for e in version_edges or []:
        if e.child_source_id in roots_uf.p and e.parent_source_id in roots_uf.p:
            roots_uf.union(e.child_source_id, e.parent_source_id)
            family_uf.union(e.child_source_id, e.parent_source_id)
            best[e.child_source_id] = e
    for i, s1 in enumerate(texts):
        for s2 in texts[i + 1 :]:
            parent, child = _order(s1, s2, assessments)
            sigs, kind = pair_signals(parent, child, sh, qs, assessments)
            if not sigs:
                continue
            p_ind = 1.0
            for _, w in sigs:
                p_ind *= 1 - w
            dep = round(1 - p_ind, 3)
            if dep < threshold:
                continue
            roots_uf.union(child.id, parent.id)
            if kind == "same_publisher":
                family_uf.union(child.id, parent.id)
            if child.id not in best or (best[child.id].kind != "same_work_version" and dep > best[child.id].dependency_probability):
                best[child.id] = SourceLineage(child_source_id=child.id, parent_source_id=parent.id, dependency_probability=dep,
                                               evidence=[r for r, _ in sigs], kind=kind)

    by_id = {s.id: s for s in sources}

    def pick_root(group: list[str]) -> str:
        return min(group, key=lambda sid: (by_id[sid].published_at is None, by_id[sid].published_at or 0,
                                           -(assessments[sid].primary_source_score if sid in assessments else 0), sid))

    def resolve(uf: _UF) -> tuple[dict[str, str], dict[str, list[str]]]:
        groups: dict[str, list[str]] = {}
        for sid in ids:
            groups.setdefault(uf.find(sid), []).append(sid)
        mapping, clusters = {}, {}
        for group in groups.values():
            root = pick_root(group)
            clusters[root] = sorted(group)
            for sid in group:
                mapping[sid] = root
        return mapping, clusters

    root_of, clusters = resolve(roots_uf)
    family_of, _ = resolve(family_uf)
    return LineageResult(edges=sorted(best.values(), key=lambda e: e.child_source_id), root_of=root_of,
                         family_of=family_of, clusters=clusters)
