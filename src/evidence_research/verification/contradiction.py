"""Claim-level contradiction vs temporal versioning (sections 14, 28). Deterministic.

Two claims about the same subject + predicate with different values:
  * valid periods known and disjoint  -> TEMPORAL_VERSION_OF (both can be true)
  * periods overlap or are unknown    -> CONTRADICTS (a temporal conflict if both are dated)
"""

from __future__ import annotations

from ..evidence.claim_normalizer import same_slot, values_consistent
from ..evidence.temporal import describe, periods_overlap
from ..graph.evidence_graph import EvidenceGraph, Link
from ..observability.events import EventLog, EventType


def detect_claim_conflicts(graph: EvidenceGraph, events: EventLog, checked: set[tuple[str, str]]) -> list[tuple[str, str, str]]:
    """Returns new (claim_a, claim_b, kind) with kind in {'contradiction', 'temporal_conflict', 'temporal_version'}."""
    found = []
    claims = sorted(graph.claims.values(), key=lambda c: c.id)
    for i, a in enumerate(claims):
        for b in claims[i + 1 :]:
            key = (a.id, b.id)
            if key in checked or not same_slot(a, b):
                continue
            checked.add(key)
            if values_consistent(a.object, b.object):
                continue
            overlap = periods_overlap(a.temporal_scope, b.temporal_scope)
            if overlap is False:
                older, newer = sorted((a, b), key=lambda c: c.temporal_scope.valid_from or c.temporal_scope.valid_to)
                graph.link_claims(newer.id, older.id, Link.TEMPORAL_VERSION_OF)
                events.emit(EventType.TEMPORAL_VERSION_DETECTED,
                            f"{newer.id} ({describe(newer.temporal_scope)}) supersedes {older.id} ({describe(older.temporal_scope)}): not a contradiction",
                            newer=newer.id, older=older.id)
                found.append((newer.id, older.id, "temporal_version"))
            else:
                kind = "temporal_conflict" if overlap else "contradiction"
                graph.link_claims(a.id, b.id, Link.CONTRADICTS, kind=kind)
                events.emit(EventType.CONTRADICTION_FOUND,
                            f"{a.id} '{a.object}' vs {b.id} '{b.object}' for {a.subject} / {a.predicate}"
                            + (" (overlapping periods)" if overlap else " (period unknown)"),
                            a=a.id, b=b.id, kind=kind)
                found.append((a.id, b.id, kind))
    return found
