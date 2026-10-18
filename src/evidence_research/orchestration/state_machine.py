"""Explicit phase transitions (section 9). Only application code moves the session between phases."""

from __future__ import annotations

from ..models import ResearchPhase as P
from ..models import ResearchSession, utcnow
from ..observability.events import EventLog, EventType

_RESEARCH = {P.DISCOVERY, P.EVIDENCE_COLLECTION, P.CLAIM_VERIFICATION, P.ADVERSARIAL_RESEARCH}

ALLOWED: dict[P, set[P]] = {
    P.INITIALIZED: {P.QUESTION_ANALYSIS},
    P.QUESTION_ANALYSIS: {P.HYPOTHESIS_GENERATION},
    P.HYPOTHESIS_GENERATION: {P.DISCOVERY},
    P.DISCOVERY: {P.EVIDENCE_COLLECTION, P.GAP_ANALYSIS},
    P.EVIDENCE_COLLECTION: {P.CLAIM_VERIFICATION, P.GAP_ANALYSIS},
    P.CLAIM_VERIFICATION: {P.ADVERSARIAL_RESEARCH, P.GAP_ANALYSIS},
    P.ADVERSARIAL_RESEARCH: {P.GAP_ANALYSIS},
    P.GAP_ANALYSIS: {P.DISCOVERY, P.SYNTHESIS},
    P.SYNTHESIS: {P.FINAL_REVIEW},
    P.FINAL_REVIEW: {P.COMPLETED},
    P.COMPLETED: set(),
    P.FAILED: set(),
}


class IllegalTransition(RuntimeError):
    pass


def transition(session: ResearchSession, to: P, events: EventLog) -> None:
    if to is not P.FAILED and to not in ALLOWED[session.phase]:
        raise IllegalTransition(f"{session.phase.value} -> {to.value} is not allowed")
    events.emit(EventType.PHASE_CHANGED, f"{session.phase.value} → {to.value}", frm=session.phase.value, to=to.value)
    session.phase = to
    session.updated_at = utcnow()


def is_research_phase(phase: P) -> bool:
    return phase in _RESEARCH
