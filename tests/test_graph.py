from datetime import date

from evidence_research.graph.evidence_graph import EvidenceGraph, Link
from evidence_research.models import Claim, TemporalScope, stable_id

from .conftest import make_claim, make_evidence, make_source


def test_source_evidence_claim_path():
    g = EvidenceGraph()
    s = g.add_source(make_source("https://a.example/report"))
    c = g.add_claim(make_claim())
    e = make_evidence(s, c)
    assert g.add_evidence(e) is True
    assert g.add_evidence(e) is False  # idempotent
    assert [x.id for x in g.sources_for_claim(c.id)] == [s.id]
    assert g.g.has_edge(e.id, c.id) and g.g.has_edge(e.id, s.id)


def test_duplicate_url_is_one_source():
    g = EvidenceGraph()
    a = g.add_source(make_source("https://www.a.example/report/?utm_source=x"))
    b = g.add_source(make_source("https://a.example/report"))
    assert a.id == b.id or g.source_by_url(b.canonical_url).id == a.id
    assert len(g.sources) == 1


def test_contradiction_edge():
    g = EvidenceGraph()
    s = g.add_source(make_source("https://a.example/x"))
    c = g.add_claim(make_claim())
    g.add_evidence(make_evidence(s, c, stance="contradicts"))
    other = g.add_claim(make_claim("Acme FY2025 revenue increased 20% YoY"))
    g.link_claims(c.id, other.id, Link.CONTRADICTS)
    assert (c.id, other.id) in g.contradiction_pairs()
    types = {d["type"] for _, _, d in g.g.in_edges(c.id, data=True)}
    assert "CONTRADICTS" in types


def test_temporal_versions_are_preserved_not_contradictions():
    g = EvidenceGraph()

    def ceo(name: str, year: int) -> Claim:
        return Claim(id=stable_id("C", name, str(year)), subject="Acme", predicate="CEO", object=name,
                     natural_language=f"{name} was CEO of Acme in {year}",
                     temporal_scope=TemporalScope(valid_from=date(year, 1, 1), valid_to=date(year, 12, 31)))

    alice, bob = g.add_claim(ceo("Alice", 2025)), g.add_claim(ceo("Bob", 2026))
    g.link_claims(bob.id, alice.id, Link.TEMPORAL_VERSION_OF)
    assert g.temporal_versions(alice.id) == [bob.id]
    assert g.contradiction_pairs() == []
    assert len(g.claims) == 2


def test_confidence_history_is_append_only():
    g = EvidenceGraph()
    c = g.add_claim(make_claim())
    g.observe(c.id, "posterior", {"p": 0.6})
    g.observe(c.id, "posterior", {"p": 0.4})
    assert [o.value["p"] for o in g.history(c.id)] == [0.5, 0.6, 0.4]
