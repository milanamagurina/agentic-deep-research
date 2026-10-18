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
    """Domain objects: built by code, so unknown fields are a bug."""
    model_config = ConfigDict(extra="forbid")


class ModelOutput(BaseModel):
    """LLM output schemas: unknown extra keys (a model adding "title") are dropped, never stored as state."""
    model_config = ConfigDict(extra="ignore")


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

class QuestionAnalysis(ModelOutput):
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


class HypothesisProposal(ModelOutput):
    key: str = Field(description="short label like H1")
    text: str
    is_null_hypothesis: bool = False
    plausibility: Literal["low", "medium", "high"] = "medium"
    requirements: list["RequirementProposal"] = Field(default_factory=list)


class RequirementProposal(ModelOutput):
    description: str
    importance: Literal["low", "medium", "high"] = "medium"


class HypothesesOutput(ModelOutput):
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
    search_origin: str = "GeneralResearcher"  # the agent whose search found it
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
    independence: float = 1.0  # 1 - dependency on another source; set by lineage analysis
    conflict_of_interest: float
    historical_reliability: float | None = None
    assessment_notes: list[str] = Field(default_factory=list)


class SourceLineage(Strict):
    child_source_id: str
    parent_source_id: str | None
    dependency_probability: float
    evidence: list[str] = Field(default_factory=list)  # the lineage signals observed
    kind: Literal["derived_reporting", "same_work_version", "same_publisher"] = "derived_reporting"


class ScreeningDecision(Strict):
    source_id: str
    decision: Literal["include", "exclude", "uncertain"]
    reasons: list[str]
    relevance_score: float
    document_type: str = "unknown"
    decided_by: Literal["rule", "model"] = "model"
    decided_at: datetime = Field(default_factory=utcnow)


# --------------------------------------------------------------------------- entities, documents, studies, results

class Entity(Strict):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)


DocumentType = Literal[
    "peer_reviewed_article", "conference_paper", "preprint", "systematic_review", "meta_analysis",
    "randomized_controlled_trial", "prospective_cohort", "observational_study", "case_control_study",
    "retrospective_study", "case_report", "government_publication", "regulator_publication",
    "official_statistics", "company_filing", "company_press_release", "industry_report", "company_whitepaper",
    "news_article", "blog", "social_media", "forum", "review_site", "unknown",
]
SCIENTIFIC_DOCUMENT_TYPES = {
    "peer_reviewed_article", "conference_paper", "preprint", "systematic_review", "meta_analysis",
    "randomized_controlled_trial", "prospective_cohort", "observational_study", "case_control_study",
    "retrospective_study", "case_report",
}


class Document(Strict):
    """What a Source (URL) contains. A document is not itself evidence."""
    id: str
    source_id: str
    document_type: str = "unknown"
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    doi: str | None = None
    arxiv_id: str | None = None
    venue: str | None = None
    year: int | None = None
    peer_reviewed: bool | None = None


class Study(Strict):
    id: str
    title: str
    document_ids: list[str] = Field(default_factory=list)  # every version (preprint, conference, journal)
    design: str | None = None
    research_lineage_id: str | None = None


class StudyAssessment(Strict):
    study_id: str
    study_design: str | None = None
    sample_size: int | None = None
    control_group: bool | None = None
    randomized: bool | None = None
    blinded: bool | None = None
    preregistered: bool | None = None
    statistical_power: float | None = None
    attrition_risk: float | None = None
    conflict_of_interest: float | None = None
    reproducibility_score: float | None = None
    code_available: bool | None = None
    data_available: bool | None = None
    peer_reviewed: bool | None = None
    quality_score: float = 0.5  # deterministic, from the fields above (science/quality.py)
    notes: list[str] = Field(default_factory=list)


class StudyResult(Strict):
    id: str
    study_id: str
    outcome: str
    effect_size: float | None = None
    effect_measure: str | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    p_value: float | None = None
    sample_size: int | None = None
    exact_excerpt: str
    location: str | None = None
    source_id: str = ""
    verification_status: Literal["verified", "unverified"] = "unverified"


StudyRelationType = Literal["REPLICATES", "FAILS_TO_REPLICATE", "EXTENDS", "REANALYZES", "CORRECTS", "RETRACTS"]


class StudyRelation(Strict):
    id: str
    from_study_id: str
    to_study_id: str
    relation: StudyRelationType
    exact_excerpt: str
    source_id: str


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
    exact_excerpt: str  # always the source's own characters (located by code, never the model's string)
    location: str | None = None
    verification_status: Literal["verified", "unverified", "inferred"] = "verified"
    result_id: str | None = None  # set when this evidence is a scientific study result
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
    failure_reasons: list[str] = Field(default_factory=list)
    missing_premises: list[str] = Field(default_factory=list)
    confounders: list[str] = Field(default_factory=list)


class NecessityAssessment(Strict):
    """Deletion test: is this premise needed for the conclusion? A model-based assessment, not a proof."""
    hypothesis_id: str
    premise_id: str
    necessary: bool
    reason: str
    method: str = "model-based necessity assessment"


class EvidenceQuality(Strict):
    """Dimensions behind one evidence item's strength, kept separate for display (section 28)."""
    evidence_id: str
    source_quality: float
    study_quality: float | None
    result_quality: float | None
    entailment: float
    replication: float | None
    independence: float
    temporal_relevance: float
    directness: float
    strength: float
    likelihood_ratio: float
    bucket: str


class AgentBid(Strict):
    agent_type: str
    utility: float
    reasons: list[str]
    target_ids: list[str] = Field(default_factory=list)


class ResearchTask(Strict):
    id: str
    agent_type: str
    target_ids: list[str]
    reason: str
    queries: list[str] = Field(default_factory=list)
    iteration: int = 0
    status: Literal["planned", "running", "done", "failed"] = "planned"
    new_sources: int = 0


GapType = Literal[
    "NO_PRIMARY_SOURCE", "NO_INDEPENDENT_SOURCE", "CONTRADICTORY_EVIDENCE", "TEMPORAL_CONFLICT",
    "INSUFFICIENT_SAMPLE", "MISSING_REQUIRED_DIMENSION", "WEAK_INFERENCE", "SOURCE_DEPENDENCE",
    "OUTDATED_EVIDENCE", "NO_REPLICATION", "FAILED_REPLICATION", "MISSING_METHOD_INFORMATION", "UNVERIFIED_EXTRACTION",
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

class ExtractedClaimProposal(ModelOutput):
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


class ExistingClaimEvidenceProposal(ModelOutput):
    claim_id: str
    exact_excerpt: str


class ExtractionOutput(ModelOutput):
    published_at: date | None = None
    publisher: str | None = None
    claims: list[ExtractedClaimProposal] = Field(default_factory=list)
    bears_on_existing: list[ExistingClaimEvidenceProposal] = Field(default_factory=list)


class StanceJudgement(ModelOutput):
    pair_id: str
    stance: Stance
    strength: Literal["explicit", "strong", "partial", "weak"]
    directness: Literal["direct", "indirect", "tangential"]
    rationale: str = ""


class StanceOutput(ModelOutput):
    judgements: list[StanceJudgement]


class ScreeningJudgement(ModelOutput):
    source_id: str
    decision: Literal["include", "exclude", "uncertain"]
    reasons: list[str]
    relevance: Literal["low", "medium", "high"]
    document_type: DocumentType = "unknown"


class ScreeningOutput(ModelOutput):
    decisions: list[ScreeningJudgement]


class StudyProposal(ModelOutput):
    title: str
    authors: list[str] = Field(default_factory=list)
    venue: str | None = None
    year: int | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    peer_reviewed: bool | None = None
    study_design: str | None = None
    sample_size: int | None = None
    control_group: bool | None = None
    randomized: bool | None = None
    blinded: bool | None = None
    preregistered: bool | None = None
    attrition: Literal["low", "medium", "high", "unknown"] = "unknown"
    conflict_of_interest: Literal["none_declared", "possible", "material", "unknown"] = "unknown"
    code_available: bool | None = None
    data_available: bool | None = None
    methodological_warnings: list[str] = Field(default_factory=list)


class ResultProposal(ModelOutput):
    outcome: str
    effect_size: float | None = None
    effect_measure: str | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    p_value: float | None = None
    sample_size: int | None = None
    exact_excerpt: str


class StudyRelationProposal(ModelOutput):
    other_study_title: str = Field(description="title or citation of the OTHER study, as written in the text")
    relation: StudyRelationType = Field(description="relation of THIS study to the other one")
    exact_excerpt: str


class ScientificReviewOutput(ModelOutput):
    is_empirical_study: bool
    study: StudyProposal | None = None
    results: list[ResultProposal] = Field(default_factory=list)
    relations: list[StudyRelationProposal] = Field(default_factory=list)


class NecessityJudgement(ModelOutput):
    premise_id: str
    still_justified_without_it: bool
    reason: str


class NecessityOutput(ModelOutput):
    judgements: list[NecessityJudgement]


class SameClaimVerdict(ModelOutput):
    pair_id: str
    verdict: Literal["SAME", "DIFFERENT", "UNCERTAIN"]
    reason: str = ""


class SameClaimOutput(ModelOutput):
    results: list[SameClaimVerdict]


class InferenceProposal(ModelOutput):
    premise_ids: list[str]
    hypothesis_id: str
    direction: Literal["supports", "contradicts"]
    inference_type: Literal["deductive", "inductive", "abductive", "causal", "analogical", "statistical", "temporal"]
    statement: str
    proposed_strength: Literal["weak", "moderate", "strong"]


class InferenceProposalOutput(ModelOutput):
    inferences: list[InferenceProposal]


class InferenceVerdict(ModelOutput):
    inference_id: str
    verdict: Literal["valid", "plausible", "weak", "invalid"]
    missing_premises: list[str] = Field(default_factory=list)
    confounders: list[str] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    reason: str


class InferenceVerdictOutput(ModelOutput):
    verdicts: list[InferenceVerdict]


class QueryPlanOutput(ModelOutput):
    queries: list[str]


class ImpactOutput(ModelOutput):
    impacts: dict[str, Literal["low", "medium", "high"]]


class PyramidPoint(ModelOutput):
    text: str
    claim_ids: list[str] = Field(default_factory=list)


class KeyLine(ModelOutput):
    text: str = Field(description="one reason that directly supports the governing thought")
    claim_ids: list[str] = Field(default_factory=list)
    support: list[PyramidPoint] = Field(default_factory=list, description="1-3 facts proving this key line")


class SynthesisOutput(ModelOutput):
    """Minto pyramid: answer first, then MECE key lines, then the facts under each."""
    governing_thought: PyramidPoint
    key_lines: list[KeyLine]
    what_would_change_our_mind: list[str]


HypothesesOutput.model_rebuild()
HypothesisProposal.model_rebuild()
