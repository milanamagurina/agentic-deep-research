"""Deterministic study-quality and replication factors (sections 11, 24, 28).

Design priors are a default for empirical research and are configurable; quality interpretation is
domain-dependent, so no universal hierarchy is claimed. Peer review is ONE factor, never sufficient:
a peer-reviewed n=12 study without a control group and with high attrition still scores low.
"""

from __future__ import annotations

from ..models import StudyAssessment, StudyProposal, StudyRelation

DESIGN_PRIOR = {
    "meta_analysis": 0.85, "systematic_review": 0.80, "randomized_controlled_trial": 0.80, "rct": 0.80,
    "prospective_cohort": 0.65, "cohort": 0.60, "observational_study": 0.55, "observational": 0.55,
    "case_control_study": 0.50, "case_control": 0.50, "retrospective_study": 0.50, "retrospective": 0.50,
    "quasi_experimental": 0.60, "benchmark_evaluation": 0.60, "simulation": 0.45, "case_report": 0.25,
    "survey": 0.45, "qualitative": 0.40,
}
ATTRITION = {"low": 0.1, "medium": 0.35, "high": 0.7, "unknown": None}
COI = {"none_declared": 0.1, "possible": 0.4, "material": 0.8, "unknown": None}


def _design_key(design: str | None) -> str | None:
    if not design:
        return None
    d = design.lower().replace("-", "_").replace(" ", "_")
    if "meta" in d:
        return "meta_analysis"
    if "systematic" in d:
        return "systematic_review"
    if "random" in d or d.startswith("rct"):
        return "randomized_controlled_trial"
    for key in DESIGN_PRIOR:
        if key in d:
            return key
    return d


def assess_study(study_id: str, p: StudyProposal) -> StudyAssessment:
    notes: list[str] = []
    design = _design_key(p.study_design)
    score = DESIGN_PRIOR.get(design or "", 0.5)
    notes.append(f"design prior {score:.2f} ({design or 'design not reported'})")
    n = p.sample_size
    if n is None:
        score *= 0.85
        notes.append("sample size not reported (×0.85)")
    elif n < 30:
        score *= 0.6
        notes.append(f"very small sample n={n} (×0.6)")
    elif n < 100:
        score *= 0.8
        notes.append(f"small sample n={n} (×0.8)")
    elif n >= 1000:
        score *= 1.05
        notes.append(f"large sample n={n} (×1.05)")
    if p.control_group is False:
        score *= 0.7
        notes.append("no control group (×0.7)")
    if p.randomized:
        score *= 1.05
    if p.blinded:
        score *= 1.03
    if p.preregistered:
        score *= 1.08
        notes.append("preregistered (×1.08)")
    attr = ATTRITION[p.attrition]
    if attr is not None and attr >= 0.35:
        score *= 1 - 0.5 * attr
        notes.append(f"{p.attrition} attrition (×{1 - 0.5 * attr:.2f})")
    coi = COI[p.conflict_of_interest]
    if coi is not None and coi >= 0.4:
        score *= 1 - 0.3 * coi
        notes.append(f"{p.conflict_of_interest} conflict of interest (×{1 - 0.3 * coi:.2f})")
    if p.peer_reviewed is False:
        score *= 0.9
        notes.append("not peer reviewed (×0.9)")
    if p.code_available or p.data_available:
        score *= 1.03
    notes += p.methodological_warnings
    reproducibility = None
    if p.code_available is not None or p.data_available is not None:
        reproducibility = 0.5 * bool(p.code_available) + 0.5 * bool(p.data_available)
    return StudyAssessment(
        study_id=study_id, study_design=design, sample_size=n, control_group=p.control_group, randomized=p.randomized,
        blinded=p.blinded, preregistered=p.preregistered, attrition_risk=attr, conflict_of_interest=coi,
        reproducibility_score=reproducibility, code_available=p.code_available, data_available=p.data_available,
        peer_reviewed=p.peer_reviewed, quality_score=round(min(0.95, max(0.05, score)), 3), notes=notes,
    )


def merge_assessments(a: StudyAssessment, b: StudyAssessment) -> StudyAssessment:
    """Two versions of one work: keep known facts from either, peer review if any version was reviewed."""
    data = a.model_dump()
    for k, v in b.model_dump().items():
        if data.get(k) is None and v is not None:
            data[k] = v
    data["peer_reviewed"] = bool(a.peer_reviewed or b.peer_reviewed) if (a.peer_reviewed is not None or b.peer_reviewed is not None) else None
    data["quality_score"] = max(a.quality_score, b.quality_score) if data["peer_reviewed"] else min(a.quality_score, b.quality_score)
    data["notes"] = list(dict.fromkeys(a.notes + b.notes + ["merged across versions of the same work"]))
    return StudyAssessment(**data)


def replication_factor(relations_to_study: list[StudyRelation]) -> tuple[float, list[str]]:
    """How later studies change the weight of THIS study's evidence."""
    factor, notes = 1.0, []
    for r in relations_to_study:
        if r.relation == "RETRACTS":
            return 0.0, [f"retracted by {r.from_study_id}"]
        if r.relation == "REPLICATES":
            factor *= 1.2
            notes.append(f"replicated by {r.from_study_id} (×1.2)")
        elif r.relation == "FAILS_TO_REPLICATE":
            factor *= 0.6
            notes.append(f"failed replication by {r.from_study_id} (×0.6)")
        elif r.relation == "CORRECTS":
            factor *= 0.8
            notes.append(f"corrected by {r.from_study_id} (×0.8)")
    return round(min(1.5, factor), 3), notes
