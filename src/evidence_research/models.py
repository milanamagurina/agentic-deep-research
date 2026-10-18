"""Typed contracts shared by every module.

Two groups:
  * Domain objects (Source, Claim, Evidence, Inference, Hypothesis, ...): owned by code.
    IDs, counts and probabilities on these are set by deterministic code only.
  * LLM output schemas (suffix ``Proposal`` / ``Output``): what a model may return.
    Models return categories and text, never truth probabilities.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def stable_id(prefix: str, *parts: str) -> str:
    """Deterministic SHA-256 based ID; identical inputs always give the same ID."""
    digest = hashlib.sha256("\x1f".join(p.strip().lower() for p in parts).encode()).hexdigest()
    return f"{prefix}_{digest[:10]}"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- session

class ResearchPhase(str, Enum):
    INITIALIZED = "INITIALIZED"
    QUESTION_ANALYSIS = "QUESTION_ANALYSIS"
    HYPOTHESIS_GENERATION = "HYPOTHESIS_GENERATION"
    DISCOVERY = "DISCOVERY"
    EVIDENCE_COLLECTION = "EVIDENCE_COLLECTION"
    CLAIM_VERIFICATION = "CLAIM_VERIFICATION"
    ADVERSARIAL_RESEARCH = "ADVERSARIAL_RESEARCH"
    GAP_ANALYSIS = "GAP_ANALYSIS"
    SYNTHESIS = "SYNTHESIS"
    FINAL_REVIEW = "FINAL_REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StopReason(str, Enum):
    SUCCESS = "SUCCESS"
    CONVERGENCE = "CONVERGENCE"
    DIMINISHING_RETURNS = "DIMINISHING_RETURNS"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    UNRESOLVABLE = "UNRESOLVABLE"


class EvidenceStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    LIKELY = "LIKELY"
    CONTESTED = "CONTESTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REFUTED = "REFUTED"
    UNRESOLVABLE_WITH_PUBLIC_DATA = "UNRESOLVABLE_WITH_PUBLIC_DATA"


class ResearchSession(Strict):
    id: str
    question: str
    objective: str | None = None
    phase: ResearchPhase = ResearchPhase.INITIALIZED
    depth: str = "standard"
    synthetic: bool = False  # True when run on the offline demo corpus

    hypotheses: list[str] = Field(default_factory=list)
    active_task_ids: list[str] = Field(default_factory=list)
    completed_task_ids: list[str] = Field(default_factory=list)

    iteration: int = 0
    search_count: int = 0
    extract_count: int = 0
    model_call_count: int = 0

    unresolved_gap_ids: list[str] = Field(default_factory=list)
    stop_reason: StopReason | None = None
    stop_explanation: str | None = None

    started_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------- question & hypotheses

class QuestionAnalysis(Strict):
    normalized_question: str
    decision_context: str | None = None
    key_entities: list[str] = Field(default_factory=list)
    temporal_scope: str | None = None
    geographic_scope: str | None = None
    hidden_assumptions: list[str] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    ambiguity_notes: list[str] = Field(default_factory=list)


HypothesisStatus = Literal["active", "supported", "weakened", "rejected", "insufficient"]


class Hypothesis(Strict):
    id: str
    text: str
    is_null_hypothesis: bool = False
    prior_probability: float  # heuristic prior, NOT ground truth
    posterior_probability: float
    evidence_sufficiency: float = 0.0
    inference_validity: float | None = None
    status: HypothesisStatus = "active"


class EvidenceRequirement(Strict):
    id: str
    hypothesis_id: str
    description: str
    importance: float
    satisfied: bool = False
    satisfaction_score: float = 0.0


class HypothesisProposal(Strict):
    key: str = Field(description="short label like H1")
    text: str
    is_null_hypothesis: bool = False
    plausibility: Literal["low", "medium", "high"] = "medium"
    requirements: list["RequirementProposal"] = Field(default_factory=list)


class RequirementProposal(Strict):
    description: str
    importance: Literal["low", "medium", "high"] = "medium"


class HypothesesOutput(Strict):
    hypotheses: list[HypothesisProposal]


# --------------------------------------------------------------------------- sources

class Source(Strict):
    id: str
    url: str
    canonical_url: str
    title: str = ""
    publisher: str = ""
    retrieved_at: datetime = Field(default_factory=utcnow)
    published_at: date | None = None  # never fabricated; None when unknown
    raw_text: str = ""
    snippet: str = ""
    search_query: str = ""
    search_origin: Literal["discovery", "gap", "adversarial", "baseline"] = "discovery"
    tavily_score: float | None = None
    extracted: bool = False
    raw_metadata: dict = Field(default_factory=dict)


class SourceAssessment(Strict):
    source_id: str
    source_type: str
    authority: float
    expertise: float
    transparency: float
    editorial_quality: float
    primary_source_score: float
    conflict_of_interest: float
    historical_reliability: float | None = None
    assessment_notes: list[str] = Field(default_factory=list)


class SourceLineage(Strict):
    child_source_id: str
    parent_source_id: str | None
    dependency_probability: float
    reasons: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- claims & evidence

class TemporalScope(Strict):
    valid_from: date | None = None
    valid_to: date | None = None
    observed_at: datetime = Field(default_factory=utcnow)


class ClaimStatus(str, Enum):
    PROPOSED = "proposed"
    SUPPORTED = "supported"
    LIKELY = "likely"
    CONTESTED = "contested"
    INSUFFICIENT = "insufficient"
    REFUTED = "refuted"


ClaimKind = Literal["fact", "attribution"]
ClaimCategory = Literal[
    "official_financial", "self_reported_metric", "customer_experience",
    "market", "technical", "event", "opinion", "other",
]


class Claim(Strict):
    id: str
    subject: str
    predicate: str
    object: str
    natural_language: str
    kind: ClaimKind = "fact"
    attributed_to: str | None = None
    category: ClaimCategory = "other"
    temporal_scope: TemporalScope | None = None
    aliases: list[str] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)

    importance: float = 0.5  # research priority ONLY; never enters truth_probability
    truth_probability: float = 0.5
    evidence_sufficiency: float = 0.0
    status: ClaimStatus = ClaimStatus.PROPOSED


Stance = Literal["supports", "contradicts", "qualifies", "neutral"]


class Evidence(Strict):
    id: str
    source_id: str
    claim_id: str
    exact_excerpt: str  # verified verbatim against Source.raw_text before storage
    stance: Stance
    entailment_probability: float
    contradiction_probability: float
    directness: float
    temporal_relevance: float
    extraction_confidence: float
    reported_speech: bool = False
    observed_at: datetime = Field(default_factory=utcnow)


class Inference(Strict):
    id: str
    premise_ids: list[str]
    conclusion_claim_id: str  # a claim ID or a hypothesis ID
    direction: Literal["supports", "contradicts"] = "supports"
    inference_type: Literal["deductive", "inductive", "abductive", "causal", "analogical", "statistical", "temporal"]
    statement: str = ""
    proposed_strength: float
    verifier_score: float = 0.0
    status: Literal["proposed", "accepted", "rejected", "needs_evidence"] = "proposed"
    failure_reason: str | None = None
    missing_premises: list[str] = Field(default_factory=list)
    confounders: list[str] = Field(default_factory=list)


GapType = Literal[
    "NO_PRIMARY_SOURCE", "NO_INDEPENDENT_SOURCE", "CONTRADICTORY_EVIDENCE", "TEMPORAL_CONFLICT",
    "INSUFFICIENT_SAMPLE", "MISSING_REQUIRED_DIMENSION", "WEAK_INFERENCE", "SOURCE_DEPENDENCE",
    "OUTDATED_EVIDENCE",
]


class ResearchGap(Strict):
    id: str
    target_id: str
    gap_type: GapType
    description: str
    importance: float
    uncertainty: float
    estimated_value: float  # heuristic expected information value, not formal EVI
    resolved: bool = False
    attempts: int = 0
    suggested_query: str | None = None
    unresolvable: bool = False


# --------------------------------------------------------------------------- LLM output schemas

class ExtractedClaimProposal(Strict):
    subject: str
    predicate: str
    object: str
    natural_language: str
    exact_excerpt: str
    attributed_to: str | None = Field(default=None, description="who made the statement if the text only reports it")
    category: ClaimCategory = "other"
    valid_from: date | None = None
    valid_to: date | None = None
    requirement_ids: list[str] = Field(default_factory=list)
    importance: Literal["low", "medium", "high"] = "medium"


class ExistingClaimEvidenceProposal(Strict):
    claim_id: str
    exact_excerpt: str


class ExtractionOutput(Strict):
    published_at: date | None = None
    publisher: str | None = None
    claims: list[ExtractedClaimProposal] = Field(default_factory=list)
    bears_on_existing: list[ExistingClaimEvidenceProposal] = Field(default_factory=list)


class StanceJudgement(Strict):
    pair_id: str
    stance: Stance
    strength: Literal["explicit", "strong", "partial", "weak"]
    directness: Literal["direct", "indirect", "tangential"]
    rationale: str = ""


class StanceOutput(Strict):
    judgements: list[StanceJudgement]


class SameClaimVerdict(Strict):
    pair_id: str
    verdict: Literal["SAME", "DIFFERENT", "UNCERTAIN"]
    reason: str = ""


class SameClaimOutput(Strict):
    results: list[SameClaimVerdict]


class InferenceProposal(Strict):
    premise_ids: list[str]
    hypothesis_id: str
    direction: Literal["supports", "contradicts"]
    inference_type: Literal["deductive", "inductive", "abductive", "causal", "analogical", "statistical", "temporal"]
    statement: str
    proposed_strength: Literal["weak", "moderate", "strong"]


class InferenceProposalOutput(Strict):
    inferences: list[InferenceProposal]


class InferenceVerdict(Strict):
    inference_id: str
    verdict: Literal["valid", "plausible", "weak", "invalid"]
    missing_premises: list[str] = Field(default_factory=list)
    confounders: list[str] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    reason: str


class InferenceVerdictOutput(Strict):
    verdicts: list[InferenceVerdict]


class QueryPlanOutput(Strict):
    queries: list[str]


class ImpactOutput(Strict):
    impacts: dict[str, Literal["low", "medium", "high"]]


class SynthesisSentence(Strict):
    text: str
    claim_ids: list[str]


class SynthesisOutput(Strict):
    conclusion: list[SynthesisSentence]
    what_would_change_our_mind: list[str]


HypothesesOutput.model_rebuild()
HypothesisProposal.model_rebuild()
