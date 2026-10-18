"""Citation guarantee (section 32), enforced by code.

* ``excerpt_in_text``: an evidence excerpt is stored only if it occurs verbatim in the retrieved
  source text (after whitespace/quote/case normalization). Synthesized excerpts are rejected.
* ``CitationVerifier.check``: every report statement must reference claim IDs; every claim must
  have non-neutral evidence; every evidence item must point to a stored source whose text contains
  the excerpt; numbers in the statement must appear in the referenced claims; no free-form URLs.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from ..evidence.claim_normalizer import normalize_text
from ..graph.evidence_graph import EvidenceGraph

_URL = re.compile(r"https?://|www\.", re.I)
_NUMBER = re.compile(r"(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:[.,]\d+)?)\s*(?:%|percent|million|billion|m\b|bn\b)?", re.I)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    return " ".join(s.lower().split())


def excerpt_in_text(excerpt: str, text: str) -> bool:
    ex = _norm(excerpt).strip(" .\"'")
    return len(ex) >= 12 and ex in _norm(text)


@dataclass
class StatementCheck:
    text: str
    claim_ids: list[str]
    ok: bool
    reason: str = ""


class CitationVerifier:
    def __init__(self, graph: EvidenceGraph) -> None:
        self.graph = graph

    def claim_is_grounded(self, claim_id: str) -> tuple[bool, str]:
        claim = self.graph.claims.get(claim_id)
        if claim is None:
            return False, f"unknown claim id {claim_id}"
        grounded = [
            e for e in self.graph.evidence_for(claim_id)
            if e.stance != "neutral"
            and e.source_id in self.graph.sources
            and excerpt_in_text(e.exact_excerpt, self.graph.sources[e.source_id].raw_text or self.graph.sources[e.source_id].snippet)
        ]
        return (True, "") if grounded else (False, f"{claim_id} has no verified evidence")

    def check(self, text: str, claim_ids: list[str]) -> StatementCheck:
        if not claim_ids:
            return StatementCheck(text, claim_ids, False, "no claim ids: unsupported factual statement")
        if _URL.search(text):
            return StatementCheck(text, claim_ids, False, "free-form URL in statement")
        for cid in claim_ids:
            ok, why = self.claim_is_grounded(cid)
            if not ok:
                return StatementCheck(text, claim_ids, False, why)
        grounding = " ".join(
            normalize_text(" ".join([c.natural_language, c.object, *c.aliases] + [e.exact_excerpt for e in self.graph.evidence_for(c.id)]))
            for c in (self.graph.claims[cid] for cid in claim_ids)
        )
        grounding_tokens = set(grounding.split())
        for raw in _NUMBER.findall(text):
            tokens = [t for t in normalize_text(raw).split() if any(ch.isdigit() for ch in t)]
            if tokens and not all(t in grounding_tokens for t in tokens):
                return StatementCheck(text, claim_ids, False, f"number '{raw.strip()}' not found in referenced claims")
        return StatementCheck(text, claim_ids, True)
