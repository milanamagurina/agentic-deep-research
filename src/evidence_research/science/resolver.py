"""ScientificSourceResolver (section 10): preprint, conference and journal versions of ONE work.

Signals (noisy-OR; >= 0.7 means "same work"):
  same arXiv ID                          0.95
  same DOI                               0.95
  explicit cross-reference               0.85   one version's text names the other's arXiv ID / DOI NEXT TO
                                                 version wording ("earlier version", "published as", ...);
                                                 an ID in a reference list is a citation, not a version link
  title similarity >= 0.85               0.80
  title similarity >= 0.6 + author overlap >= 0.5   0.75
Different empirical designs (an RCT and a meta-analysis of it) are never versions of one work.
Versions become ``same_work_version`` lineage edges, so they count as ONE independent root.
"""

from __future__ import annotations

import re

from ..models import Document, Source, SourceLineage

ARXIV = re.compile(r"(?:arxiv(?:\.org/(?:abs|pdf)/|[:\s]\s*))(\d{4}\.\d{4,5})(?:v\d+)?", re.I)
DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>(),;]+)", re.I)
_STOP = {"a", "an", "the", "of", "on", "in", "for", "and", "to", "with", "from", "by", "at", "via"}
SAME_WORK_THRESHOLD = 0.7
_VERSION_WORDING = re.compile(r"earlier version|preprint|also available|published (?:as|in)|version of record|"
                             r"accepted (?:at|in|for)|appeared (?:as|at|in)|extended version|conference version", re.I)
_DESIGN_TYPES = {"meta_analysis", "systematic_review", "randomized_controlled_trial", "prospective_cohort", "observational_study",
                 "case_control_study", "retrospective_study", "case_report"}
_COMPATIBLE = {frozenset({"meta_analysis", "systematic_review"})}  # "a systematic review and meta-analysis" is one paper
_RANK = {"peer_reviewed_article": 3, "systematic_review": 3, "meta_analysis": 3, "conference_paper": 2, "preprint": 1}


def find_arxiv_ids(text: str) -> set[str]:
    return {m.group(1) for m in ARXIV.finditer(text or "")}


def find_dois(text: str) -> set[str]:
    return {m.group(1).rstrip(".").lower() for m in DOI.finditer(text or "")}


def title_tokens(title: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", title.lower()) if w not in _STOP}


def title_similarity(a: str, b: str) -> float:
    ta, tb = title_tokens(a), title_tokens(b)
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def _surname(name: str) -> str:
    parts = re.findall(r"[a-zà-ÿ'-]+", name.lower())
    return parts[-1] if parts else ""


def author_overlap(a: list[str], b: list[str]) -> float:
    sa, sb = {_surname(x) for x in a if x}, {_surname(x) for x in b if x}
    return len(sa & sb) / min(len(sa), len(sb)) if sa and sb else 0.0


def same_work_signals(d1: Document, s1: Source, d2: Document, s2: Source) -> list[tuple[str, float]]:
    sig: list[tuple[str, float]] = []
    if d1.arxiv_id and d1.arxiv_id == d2.arxiv_id:
        sig.append((f"same arXiv ID {d1.arxiv_id}", 0.95))
    if d1.doi and d2.doi and d1.doi.lower() == d2.doi.lower():
        sig.append((f"same DOI {d1.doi}", 0.95))
    own1 = {x for x in (d1.arxiv_id, (d1.doi or "").lower()) if x}
    own2 = {x for x in (d2.arxiv_id, (d2.doi or "").lower()) if x}
    if _version_reference(s1.raw_text, own2) or _version_reference(s2.raw_text, own1):
        sig.append(("explicit cross-reference between versions", 0.85))
    ts = title_similarity(d1.title, d2.title)
    ao = author_overlap(d1.authors, d2.authors)
    if ts >= 0.85:
        sig.append((f"title similarity {ts:.2f}", 0.80))
    elif ts >= 0.6 and ao >= 0.5:
        sig.append((f"title similarity {ts:.2f} with author overlap {ao:.0%}", 0.75))
    return sig


def _version_reference(text: str, ids: set[str]) -> bool:
    """The other version's ID appears within 150 characters of version wording."""
    low = (text or "").lower()
    for ident in ids:
        for m in re.finditer(re.escape(ident.lower()), low):
            if _VERSION_WORDING.search(low[max(0, m.start() - 150) : m.end() + 150]):
                return True
    return False


def _designs_compatible(a: Document, b: Document) -> bool:
    ta, tb = a.document_type, b.document_type
    if ta in _DESIGN_TYPES and tb in _DESIGN_TYPES and ta != tb:
        return frozenset({ta, tb}) in _COMPATIBLE
    return True


def resolve_versions(docs: list[Document], sources: dict[str, Source]) -> list[SourceLineage]:
    """Group versions of one work; every version points at the most final one (journal > conference > preprint)."""
    sci = [d for d in docs if d.source_id in sources]
    parent = {d.source_id: d.source_id for d in sci}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    evidence: dict[str, tuple[float, list[str]]] = {}
    for i, a in enumerate(sci):
        for b in sci[i + 1 :]:
            if not _designs_compatible(a, b):
                continue
            sig = same_work_signals(a, sources[a.source_id], b, sources[b.source_id])
            if not sig:
                continue
            p_ind = 1.0
            for _, w in sig:
                p_ind *= 1 - w
            p = round(1 - p_ind, 3)
            if p < SAME_WORK_THRESHOLD:
                continue
            parent[find(a.source_id)] = find(b.source_id)
            for d in (a, b):
                if p > evidence.get(d.source_id, (0.0, []))[0]:
                    evidence[d.source_id] = (p, [r for r, _ in sig])

    groups: dict[str, list[Document]] = {}
    for d in sci:
        groups.setdefault(find(d.source_id), []).append(d)
    edges: list[SourceLineage] = []
    for members in groups.values():
        if len(members) < 2:
            continue
        final = max(members, key=lambda d: (_RANK.get(d.document_type, 0), d.year or 0, d.source_id))
        for d in members:
            if d is not final:
                p, why = evidence.get(d.source_id, (SAME_WORK_THRESHOLD, ["grouped with other versions"]))
                edges.append(SourceLineage(child_source_id=d.source_id, parent_source_id=final.source_id, dependency_probability=p,
                                           evidence=why, kind="same_work_version"))
    return edges
