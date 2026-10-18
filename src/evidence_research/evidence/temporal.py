"""Bitemporal helpers: VALID time (true in the world) vs OBSERVATION time (when we learned it)."""

from __future__ import annotations

from datetime import date

from ..models import TemporalScope


def periods_overlap(a: TemporalScope | None, b: TemporalScope | None) -> bool | None:
    """True/False when both periods are known enough to tell; None when undecidable."""
    if a is None or b is None:
        return None
    if not (a.valid_from or a.valid_to) or not (b.valid_from or b.valid_to):
        return None
    a_from, a_to = a.valid_from or date.min, a.valid_to or date.max
    b_from, b_to = b.valid_from or date.min, b.valid_to or date.max
    return a_from <= b_to and b_from <= a_to


def temporal_relevance(published_at: date | None, scope: TemporalScope | None, today: date) -> float:
    """How current the evidence is for its claim. Unknown dates are penalized mildly, never invented."""
    if scope and (scope.valid_from or scope.valid_to):
        # A source published before the claimed period began cannot report it as fact.
        if published_at and scope.valid_from and published_at < scope.valid_from:
            return 0.2
        return 1.0  # the claim is explicitly time-scoped; the evidence speaks to that period
    if published_at is None:
        return 0.7
    age_years = (today - published_at).days / 365.25
    if age_years <= 1:
        return 1.0
    if age_years <= 2:
        return 0.8
    if age_years <= 4:
        return 0.5
    return 0.3


def describe(scope: TemporalScope | None) -> str:
    if not scope or not (scope.valid_from or scope.valid_to):
        return "period unknown"
    return f"{scope.valid_from or '…'} → {scope.valid_to or '…'}"
