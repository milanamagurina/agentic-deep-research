from datetime import date

from evidence_research.evidence.lineage import detect_lineage
from evidence_research.evidence.source_classifier import assess

from .conftest import make_source

RELEASE = (
    "Acme Fleet today announced record results. Revenue for fiscal year 2025 grew 70 percent to EUR 47.5 million, "
    "driven by strong demand for its route optimisation platform. \"We are seeing customers adopt Acme faster than "
    "ever before in our history,\" said chief executive Mara Lind. The company now serves 4,800 customers."
)


def _derivative(i: int) -> str:
    return (f"Logistics roundup #{i}. In other news, " + RELEASE.replace("today announced", "announced")
            + f" Analysts at outlet {i} said the figures were impressive.")


def test_three_derivative_articles_are_one_root():
    release = make_source("https://acmefleet.example/press/fy2025", RELEASE, date(2026, 2, 1), "Press release", "Acme Fleet")
    copies = [make_source(f"https://outlet{i}.example/news/acme", _derivative(i), date(2026, 2, 2 + i)) for i in range(3)]
    independent = make_source("https://business-registry.example/acme/annual-accounts",
                              "Annual accounts filed by Acme Fleet GmbH. Turnover for the 2025 financial year: 47,512,000 EUR.", date(2026, 4, 30))
    sources = [release, *copies, independent]
    assessments = {s.id: assess(s, ["Acme Fleet"]) for s in sources}

    result = detect_lineage(sources, assessments)

    roots = result.independent_roots({s.id for s in sources})
    assert len(roots) == 2  # the press-release cluster + the registry filing
    assert result.root_of[copies[0].id] == release.id
    assert {e.child_source_id for e in result.edges} >= {c.id for c in copies}
    assert all(e.dependency_probability >= 0.5 and e.reasons for e in result.edges)


def test_unrelated_sources_stay_independent():
    a = make_source("https://a.example/x", "Battery prices fell in 2025 according to the survey of manufacturers.")
    b = make_source("https://b.example/y", "The port authority reported container volumes rose modestly last quarter.")
    result = detect_lineage([a, b], {s.id: assess(s, []) for s in (a, b)})
    assert result.edges == [] and len(result.independent_roots({a.id, b.id})) == 2


def test_same_publisher_is_dependent():
    a = make_source("https://acmefleet.example/blog/1", "Our customers love the new routing features in spring.")
    b = make_source("https://acmefleet.example/blog/2", "We launched an analytics dashboard for fleet managers.")
    result = detect_lineage([a, b], {s.id: assess(s, ["Acme Fleet"]) for s in (a, b)})
    assert len(result.independent_roots({a.id, b.id})) == 1
