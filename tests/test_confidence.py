"""Answer-policy additions: question-type-aware substantive answers, confidence from used claims only,
and the narrow-don't-delete verifier (spec sections 1, 3, 5, 6, 13)."""

from evidence_research.graph.evidence_graph import EvidenceGraph
from evidence_research.models import Evidence, stable_id
from evidence_research.probability.confidence import answer_confidence
from evidence_research.probability.engine import BeliefState, ClaimBelief
from evidence_research.verification.citation_verifier import CitationVerifier

from .conftest import make_claim, make_source

TEXT = "Acme Fleet today announced results. Revenue grew 70% to EUR 47.5 million, driven by demand."


def _belief(cid, roots=2, contested=False):
    return ClaimBelief(cid, update=None, raw_sources=roots, independent_roots=roots, has_primary=True, contested=contested)


def _graph_with_claim(importance=0.9, posterior=0.8, sufficiency=0.8):
    g = EvidenceGraph()
    c = g.add_claim(make_claim(importance=importance))
    c.truth_probability, c.evidence_sufficiency = posterior, sufficiency
    return g, c.id


# ---------------------------------------------------------------- confidence (sections 5, 6)

def test_confidence_uses_only_used_claims_weighted_by_importance():
    g, cid = _graph_with_claim(importance=1.0, posterior=0.9, sufficiency=0.9)
    # a second, unused, low-posterior claim must NOT drag the answer confidence down
    low = g.add_claim(make_claim(text="Acme churn is high", importance=1.0))
    low.truth_probability, low.evidence_sufficiency = 0.1, 0.9
    beliefs = BeliefState(claims={cid: _belief(cid), low.id: _belief(low.id)})
    used = answer_confidence(g, beliefs, [cid])
    ignored = answer_confidence(g, beliefs, [cid, low.id])
    assert used.confidence > 0.6 and used.used_claims == 1
    assert ignored.confidence < used.confidence  # including the weak claim lowers it; unused claims never counted


def test_contradiction_and_thin_independence_penalize_confidence():
    g, cid = _graph_with_claim(posterior=0.8, sufficiency=0.8)
    clean = answer_confidence(g, BeliefState(claims={cid: _belief(cid, roots=2, contested=False)}), [cid])
    contested = answer_confidence(g, BeliefState(claims={cid: _belief(cid, roots=1, contested=True)}), [cid])
    assert contested.confidence < clean.confidence
    assert any("contradiction" in p for p in contested.penalties)
    assert any("independent" in p for p in contested.penalties)


def test_weak_inference_penalizes_confidence():
    g, cid = _graph_with_claim(posterior=0.8, sufficiency=0.8)
    beliefs = BeliefState(claims={cid: _belief(cid)})
    strong = answer_confidence(g, beliefs, [cid], inference_validity=0.9)
    weak = answer_confidence(g, beliefs, [cid], inference_validity=0.3)
    assert weak.confidence < strong.confidence and any("weak inference" in p for p in weak.penalties)


def test_confidence_never_zero_or_one_with_evidence():
    g, cid = _graph_with_claim(posterior=0.99, sufficiency=1.0)
    cb = answer_confidence(g, BeliefState(claims={cid: _belief(cid, roots=3)}), [cid])
    assert 0.05 <= cb.confidence <= 0.95


# ---------------------------------------------------------------- narrow, don't delete (section 3)

def _verifier_for(excerpt="Revenue grew 70% to EUR 47.5 million, driven by demand."):
    g = EvidenceGraph()
    s = g.add_source(make_source("https://acme.example/press", TEXT))
    c = g.add_claim(make_claim())
    g.add_evidence(Evidence(id=stable_id("E", s.id, c.id), source_id=s.id, claim_id=c.id, exact_excerpt=excerpt, stance="supports",
                            entailment_probability=0.95, contradiction_probability=0.05, directness=1, temporal_relevance=1, extraction_confidence=0.9))
    return CitationVerifier(g), c.id


def test_supported_statement_is_accepted_as_is():
    v, cid = _verifier_for()
    r = v.check_or_narrow("Revenue grew 70%.", [cid])
    assert r.ok and r.decision == "accept" and r.supported_rewrite is None


def test_overclaimed_figure_is_narrowed_not_deleted():
    v, cid = _verifier_for()
    r = v.check_or_narrow("Revenue grew 85% last year.", [cid])  # 85% is not in the evidence (70% is)
    assert r.ok and r.decision == "narrow"
    assert "85%" not in r.supported_rewrite and r.supported_rewrite.startswith("Revenue grew")


def test_ungrounded_claim_and_url_are_hard_rejects_not_narrowed():
    v, cid = _verifier_for()
    assert v.check_or_narrow("Revenue grew 70% (see https://x.example).", [cid]).decision == "reject"
    assert v.check_or_narrow("Acme is the market leader.", ["C_doesnotexist"]).decision == "reject"
