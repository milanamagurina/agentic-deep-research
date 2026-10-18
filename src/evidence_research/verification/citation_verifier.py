"""Citation guarantee (section 39), enforced by code before anything is rendered.

Final statement → claim IDs → evidence IDs → exact excerpt → source. A statement passes only if:
  * it references claim IDs, and contains no free-form URL;
  * every claim has VERIFIED, non-neutral evidence whose excerpt is found verbatim in a stored source;
  * every number in the statement appears in the referenced claims or their excerpts.
Failing statements are removed (and logged); they are never "fixed" by the system.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..evidence.claim_normalizer import normalize_text
from ..evidence.excerpts import locate_excerpt
from ..graph.evidence_graph import EvidenceGraph

_URL = re.compile(r"https?://|www\.", re.I)
# Internal IDs a model may echo into prose: never facts, never numbers to verify.
_IDS = re.compile(r"\[?\b(?:C|E|S|H|I|G|D|ST|RS|SR|R|T|P)_[0-9a-f]{10}\b(?:,\s*)?\]?|\bH\d{1,2}(?:\.R\d+)?\b")
_ID_LISTS = re.compile(r"\s*[\[(](?:\s*(?:[A-Z]{1,2}_[0-9a-f]{10}|H\d{1,2})\s*,?)+[\])]")


def strip_ids(text: str) -> str:
    """Remove bracketed ID lists like "[C_09592e61fa, C_1771440d9d]" from display text."""
    return " ".join(_ID_LISTS.sub("", text).split())
_NUMBER = re.compile(r"(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:[.,]\d+)?)\s*(?:%|percent|million|billion|m\b|bn\b)?", re.I)


def excerpt_in_text(excerpt: str, text: str) -> bool:
    """True only for an exact (normalized) occurrence: stored excerpts are the source's own characters."""
    loc = locate_excerpt(excerpt, text)
    return loc is not None and loc.method == "exact"


@dataclass
class StatementCheck:
    text: str
    claim_ids: list[str]
    ok: bool
    reason: str = ""
    evidence_ids: list[str] = field(default_factory=list)


class CitationVerifier:
    def __init__(self, graph: EvidenceGraph) -> None:
        self.graph = graph

    def grounded_evidence(self, claim_id: str) -> list[str]:
        """Verified evidence a statement about this claim can cite: its support, or (for a claim that only
        has counter-evidence) the contradicting evidence."""
        by_stance: dict[str, list[str]] = {"supports": [], "contradicts": []}
        for e in self.graph.evidence_for(claim_id):  # verified only
            src = self.graph.sources.get(e.source_id)
            if e.stance in by_stance and src and excerpt_in_text(e.exact_excerpt, src.raw_text or src.snippet):
                by_stance[e.stance].append(e.id)
        return by_stance["supports"] or by_stance["contradicts"]

    def claim_is_grounded(self, claim_id: str) -> tuple[bool, str]:
        if claim_id not in self.graph.claims:
            return False, f"unknown claim id {claim_id}"
        return (True, "") if self.grounded_evidence(claim_id) else (False, f"{claim_id} has no verified evidence")

    def check(self, text: str, claim_ids: list[str]) -> StatementCheck:
        if not claim_ids:
            return StatementCheck(text, claim_ids, False, "no claim ids: unsupported factual statement")
        if _URL.search(text):
            return StatementCheck(text, claim_ids, False, "free-form URL in statement")
        evidence_ids: list[str] = []
        for cid in claim_ids:
            ok, why = self.claim_is_grounded(cid)
            if not ok:
                return StatementCheck(text, claim_ids, False, why)
            evidence_ids += self.grounded_evidence(cid)
        grounding = " ".join(
            normalize_text(" ".join([c.natural_language, c.object, *c.aliases] + [e.exact_excerpt for e in self.graph.evidence_for(c.id)]))
            for c in (self.graph.claims[cid] for cid in claim_ids)
        )
        tokens = set(grounding.split())
        for raw in _NUMBER.findall(_IDS.sub(" ", text)):
            nums = [t for t in normalize_text(raw).split() if any(ch.isdigit() for ch in t)]
            if nums and not all(t in tokens for t in nums):
                return StatementCheck(text, claim_ids, False, f"number '{raw.strip()}' not found in referenced claims")
        return StatementCheck(text, claim_ids, True, evidence_ids=evidence_ids)
