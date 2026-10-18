import pytest

from evidence_research.config import Heuristics
from evidence_research.evidence.source_classifier import assess, reliability_for
from evidence_research.graph.evidence_graph import EvidenceGraph
from evidence_research.observability.events import EventLog
from evidence_research.probability.bayesian import update_claim
from evidence_research.probability.engine import recompute
from evidence_research.probability.evidence_score import evidence_strength
from evidence_research.probability.uncertainty import claim_sufficiency, research_priority, uncertainty

from .conftest import TODAY, make_claim, make_evidence, make_source

H = Heuristics()


def _items(pairs):
    return [(e, s, root) for e, s, root in pairs]


def test_strong_independent_evidence_raises_posterior():
    c = make_claim()
    e1 = make_evidence(make_source("https://a.example/1"), c)
    e2 = make_evidence(make_source("https://b.example/2"), c)
    one = update_claim(0.5, [(e1, 0.8, "r1")], H)
    two = update_claim(0.5, [(e1, 0.8, "r1"), (e2, 0.8, "r2")], H)
    assert 0.5 < one.posterior < two.posterior
    assert two.posterior == pytest.approx(8 * 8 / (1 + 8 * 8), abs=1e-3)  # prior odds 1 x LR 8 x LR 8


def test_contradiction_lowers_posterior():
    c = make_claim()
    sup = make_evidence(make_source("https://a.example/1"), c)
    con = make_evidence(make_source("https://b.example/2"), c, stance="contradicts")
    before = update_claim(0.5, [(sup, 0.6, "r1")], H).posterior
    after = update_claim(0.5, [(sup, 0.6, "r1"), (con, 0.6, "r2")], H).posterior
    assert after < before
    assert after == pytest.approx(0.5, abs=1e-3)  # LR 4 and LR 0.25 cancel


def test_dependent_evidence_is_discounted():
    c = make_claim()
    evs = [make_evidence(make_source(f"https://site{i}.example/x"), c) for i in range(5)]
    same_root = update_claim(0.5, [(e, 0.8, "press-release") for e in evs], H)
    independent = update_claim(0.5, [(e, 0.8, f"root{i}") for i, e in enumerate(evs)], H)
    single = update_claim(0.5, [(evs[0], 0.8, "press-release")], H)
    assert single.posterior < same_root.posterior < independent.posterior
    assert same_root.independent_roots == 1 and independent.independent_roots == 5
    assert [c.weight for c in same_root.contributions] == [1.0] + [H.dependent_evidence_discount] * 4


def test_importance_does_not_alter_truth_probability(settings):
    results = []
    for importance in (0.1, 1.0):
        g = EvidenceGraph()
        s = g.add_source(make_source("https://registry.example.gov/filing", "text"))
        g.set_assessment(assess(s, ["Acme"]))
        c = g.add_claim(make_claim(importance=importance))
        g.add_evidence(make_evidence(s, c))
        recompute(g, settings, EventLog(), TODAY)
        results.append((c.truth_probability, c.evidence_sufficiency))
    assert results[0] == results[1]
    # ...while importance DOES change research priority.
    assert research_priority(0.1, 0.5, 1, 1) < research_priority(1.0, 0.5, 1, 1)


def test_reported_speech_is_weaker_than_direct_evidence():
    c = make_claim()
    s = make_source("https://reuters.com/x")
    a = assess(s, ["Acme"])
    direct = evidence_strength(make_evidence(s, c, directness=1.0), reliability_for(a, c))
    reported = evidence_strength(make_evidence(s, c, directness=H.reported_speech_directness), reliability_for(a, c))
    assert reported < direct


def test_credibility_is_claim_dependent():
    filing = assess(make_source("https://registry.example.gov/acme"), ["Acme"])
    revenue = make_claim(category="official_financial")
    satisfaction = make_claim("Acme customers are satisfied", category="customer_experience")
    assert reliability_for(filing, revenue) > 2 * reliability_for(filing, satisfaction)


def test_sufficiency_and_uncertainty_shapes():
    assert claim_sufficiency(0, True, 1) == 0
    assert claim_sufficiency(1, True, 1) < claim_sufficiency(2, True, 1) < claim_sufficiency(3, True, 1)
    assert claim_sufficiency(2, False, 1) < claim_sufficiency(2, True, 1)
    assert uncertainty(0.5) == 1 and uncertainty(0.0) == 0 and uncertainty(1.0) == 0
