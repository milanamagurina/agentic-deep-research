from evidence_research.graph.evidence_graph import EvidenceGraph
from evidence_research.models import Evidence, stable_id
from evidence_research.verification.citation_verifier import CitationVerifier, excerpt_in_text

from .conftest import make_claim, make_source

TEXT = "Acme Fleet today announced results. Revenue grew 70% to EUR 47.5 million, driven by demand. More text."


def _graph(excerpt: str = "Revenue grew 70% to EUR 47.5 million, driven by demand.") -> tuple[EvidenceGraph, str]:
    g = EvidenceGraph()
    s = g.add_source(make_source("https://acme.example/press", TEXT))
    c = g.add_claim(make_claim())
    g.add_evidence(Evidence(id=stable_id("E", s.id, c.id), source_id=s.id, claim_id=c.id, exact_excerpt=excerpt, stance="supports",
                            entailment_probability=0.95, contradiction_probability=0.05, directness=1, temporal_relevance=1, extraction_confidence=0.9))
    return g, c.id


def test_excerpt_must_be_verbatim():
    assert excerpt_in_text("revenue grew 70% to EUR 47.5   million", TEXT)
    assert excerpt_in_text("“Revenue grew 70% to EUR 47.5 million”", TEXT)
    assert not excerpt_in_text("Revenue grew 75% to EUR 47.5 million", TEXT)
    assert not excerpt_in_text("grew", TEXT)  # too short to be meaningful evidence


def test_grounded_statement_passes():
    g, cid = _graph()
    assert CitationVerifier(g).check("Acme's revenue grew 70% in 2025.", [cid]).ok


def test_statement_without_claim_ids_fails():
    g, _ = _graph()
    check = CitationVerifier(g).check("Acme is the market leader.", [])
    assert not check.ok and "unsupported" in check.reason


def test_unknown_claim_fails():
    g, _ = _graph()
    assert not CitationVerifier(g).check("Revenue grew 70%.", ["C_doesnotexist"]).ok


def test_number_not_in_evidence_fails():
    g, cid = _graph()
    check = CitationVerifier(g).check("Revenue grew 85% in 2025.", [cid])
    assert not check.ok and "85%" in check.reason


def test_free_form_url_fails():
    g, cid = _graph()
    assert not CitationVerifier(g).check("Revenue grew 70% (see https://evil.example).", [cid]).ok


def test_claim_whose_excerpt_is_not_in_source_fails():
    g, cid = _graph(excerpt="Revenue grew 70% thanks to a fabricated quote that is not on the page.")
    assert not CitationVerifier(g).check("Revenue grew 70%.", [cid]).ok


def test_ids_echoed_into_prose_are_not_numbers():
    from evidence_research.verification.citation_verifier import strip_ids

    g, cid = _graph()
    check = CitationVerifier(g).check(f"Revenue grew 70% [{cid}], consistent with H3.", [cid])
    assert check.ok, check.reason
    assert strip_ids(f"Revenue grew 70% [{cid}, C_0123456789].") == "Revenue grew 70%."
