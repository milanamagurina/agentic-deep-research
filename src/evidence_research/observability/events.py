"""Structured research events: the audit trail. No hidden model reasoning is ever stored here."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..models import utcnow

log = logging.getLogger("evidence_research")


class EventType(str, Enum):
    SESSION_STARTED = "SESSION_STARTED"
    PHASE_CHANGED = "PHASE_CHANGED"
    QUESTION_ANALYZED = "QUESTION_ANALYZED"
    HYPOTHESIS_CREATED = "HYPOTHESIS_CREATED"
    HYPOTHESIS_UPDATED = "HYPOTHESIS_UPDATED"
    REQUIREMENT_CREATED = "REQUIREMENT_CREATED"
    SEARCH_PLANNED = "SEARCH_PLANNED"
    SEARCH_EXECUTED = "SEARCH_EXECUTED"
    SOURCE_FOUND = "SOURCE_FOUND"
    SOURCE_SELECTED = "SOURCE_SELECTED"
    SOURCE_REJECTED = "SOURCE_REJECTED"
    SOURCE_EXTRACTED = "SOURCE_EXTRACTED"
    CLAIM_CREATED = "CLAIM_CREATED"
    CLAIM_MERGED = "CLAIM_MERGED"
    EVIDENCE_ATTACHED = "EVIDENCE_ATTACHED"
    EVIDENCE_REJECTED = "EVIDENCE_REJECTED"
    SOURCE_DEPENDENCY_DETECTED = "SOURCE_DEPENDENCY_DETECTED"
    INFERENCE_PROPOSED = "INFERENCE_PROPOSED"
    INFERENCE_ACCEPTED = "INFERENCE_ACCEPTED"
    INFERENCE_REJECTED = "INFERENCE_REJECTED"
    CONTRADICTION_FOUND = "CONTRADICTION_FOUND"
    TEMPORAL_VERSION_DETECTED = "TEMPORAL_VERSION_DETECTED"
    CLAIM_POSTERIOR_UPDATED = "CLAIM_POSTERIOR_UPDATED"
    RESEARCH_GAP_CREATED = "RESEARCH_GAP_CREATED"
    RESEARCH_GAP_RESOLVED = "RESEARCH_GAP_RESOLVED"
    RESEARCH_GAP_UNRESOLVABLE = "RESEARCH_GAP_UNRESOLVABLE"
    RESEARCH_SCHEDULED = "RESEARCH_SCHEDULED"
    MODEL_CALL = "MODEL_CALL"
    STOP_DECISION = "STOP_DECISION"
    STATEMENT_REJECTED = "STATEMENT_REJECTED"
    REPORT_GENERATED = "REPORT_GENERATED"
    ERROR = "ERROR"


class ResearchEvent(BaseModel):
    seq: int
    ts: datetime = Field(default_factory=utcnow)
    type: EventType
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


Subscriber = Callable[[ResearchEvent], None]


class EventLog:
    """Append-only. Subscribers (UI, CLI, SQLite) receive every event as it happens."""

    def __init__(self) -> None:
        self.events: list[ResearchEvent] = []
        self._subscribers: list[Subscriber] = []

    def subscribe(self, fn: Subscriber) -> None:
        self._subscribers.append(fn)

    def emit(self, type: EventType, message: str, **data: Any) -> ResearchEvent:
        event = ResearchEvent(seq=len(self.events) + 1, type=type, message=message, data=data)
        self.events.append(event)
        log.debug("%s %s", type.value, message)
        for fn in self._subscribers:
            fn(event)
        return event

    def of_type(self, *types: EventType) -> list[ResearchEvent]:
        return [e for e in self.events if e.type in types]


def format_event(e: ResearchEvent) -> str:
    return f"{e.ts:%H:%M:%S} {e.type.value:<26} {e.message}"
