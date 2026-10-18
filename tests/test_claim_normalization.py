from datetime import date

from evidence_research.evidence.claim_normalizer import canonical_key, candidates, normalize_text, same_slot
from evidence_research.models import Claim, TemporalScope

FY25 = TemporalScope(valid_from=date(2025, 1, 1), valid_to=date(2025, 12, 31))


def test_currency_magnitude_and_fiscal_year_normalize():
    tokens = lambda s: set(normalize_text(s).split())  # noqa: E731
    assert tokens("€47.5m") == tokens("EUR 47.5 million") == tokens("47,5 Mio. euros") == {"eur", "47500000"}
    assert "fy2025" in normalize_text("FY25 revenue").replace(" ", "")
    assert normalize_text("1,200 customers") == "1200 customers"


def test_same_fact_same_canonical_key():
    a = canonical_key("Acme", "revenue", "€47.5m", FY25)
    b = canonical_key("acme", "Revenue", "EUR 47.5 million", FY25)
    assert a == b
    assert a != canonical_key("Acme", "revenue", "€47.5m", TemporalScope(valid_from=date(2024, 1, 1), valid_to=date(2024, 12, 31)))


def test_attribution_is_a_different_claim_from_the_fact():
    fact = canonical_key("Acme", "revenue growth", "200%", None)
    said = canonical_key("Acme", "revenue growth", "200%", None, kind="attribution", attributed_to="Acme CEO")
    assert fact != said


def _claim(cid: str, text: str, obj: str = "x") -> Claim:
    return Claim(id=cid, subject="Acme", predicate="revenue", object=obj, natural_language=text)


def test_candidate_retrieval_finds_paraphrases_only():
    existing = [_claim("c1", "Acme earned €47.5m revenue in 2025"), _claim("c2", "Acme opened an office in Lisbon")]
    found = candidates(_claim("new", "Acme 2025 revenue was EUR 47.5 million"), existing)
    assert [c.id for _, c in found] == ["c1"]


def test_same_slot_detects_comparable_claims():
    assert same_slot(_claim("a", "t", "47.5m"), _claim("b", "t", "52m"))
