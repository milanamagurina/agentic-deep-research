"""Source assessment along separate dimensions; reliability is claim-dependent (section 21).

All values are transparent heuristics by source type. There is no universal credibility score:
``reliability_for`` combines the dimensions for ONE claim category, so a regulatory filing is strong
for official revenue and weak for customer satisfaction.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from ..models import Claim, Source, SourceAssessment
from ..retrieval.url_normalizer import registrable_domain

_LISTS: dict[str, tuple[str, ...]] = {
    "regulator": ("sec.gov", "europa.eu", "companieshouse.gov.uk", "bundesanzeiger.de", "fca.org.uk", "esma.europa.eu"),
    "official_statistics": ("eurostat", "ons.gov.uk", "destatis.de", "census.gov", "bls.gov", "oecd.org", "worldbank.org", "iea.org"),
    "academic": ("arxiv.org", "doi.org", "nature.com", "science.org", "sciencedirect.com", "springer.com", "nih.gov", "acm.org", "ieee.org", "ssrn.com"),
    "major_news": ("reuters.com", "bloomberg.com", "ft.com", "wsj.com", "nytimes.com", "economist.com", "theguardian.com", "bbc.co.uk", "bbc.com", "apnews.com", "cnbc.com", "handelsblatt.com"),
    "trade_press": ("techcrunch.com", "theverge.com", "sifted.eu", "venturebeat.com", "wired.com", "arstechnica.com"),
    "press_wire": ("prnewswire.com", "businesswire.com", "globenewswire.com", "einpresswire.com", "accesswire.com", "newswire.ca"),
    "review_site": ("trustpilot.com", "g2.com", "capterra.com", "glassdoor.com", "gartner.com/reviews"),
    "blog": ("medium.com", "substack.com", "wordpress.com", "blogspot.com"),
    "social": ("reddit.com", "x.com", "twitter.com", "linkedin.com", "youtube.com", "facebook.com"),
}
# Host keyword fallbacks, checked after the explicit lists.
_KEYWORDS: list[tuple[str, str]] = [
    ("registry", "regulator"), ("filings", "regulator"), ("regulator", "regulator"),
    ("statistics", "official_statistics"), ("stats", "official_statistics"),
    ("university", "academic"), ("journal-of", "academic"),
    ("wire", "press_wire"), ("press-release", "press_wire"),
    ("reviews", "review_site"), ("blog", "blog"), ("forum", "social"),
    ("analyst", "analyst"), ("research", "analyst"),
    ("times", "major_news"), ("journal", "major_news"), ("news", "trade_press"), ("post", "trade_press"),
]

# authority, expertise, transparency, editorial_quality, primary_source_score, conflict_of_interest
_DIMENSIONS: dict[str, tuple[float, float, float, float, float, float]] = {
    "regulator":           (0.90, 0.70, 0.80, 0.80, 0.90, 0.10),
    "official_statistics": (0.90, 0.80, 0.90, 0.80, 0.90, 0.05),
    "academic":            (0.80, 0.90, 0.80, 0.80, 0.80, 0.15),
    "company":             (0.50, 0.70, 0.40, 0.50, 0.90, 0.80),
    "press_wire":          (0.30, 0.50, 0.30, 0.20, 0.60, 0.85),
    "major_news":          (0.75, 0.60, 0.60, 0.80, 0.30, 0.20),
    "trade_press":         (0.55, 0.60, 0.50, 0.55, 0.30, 0.30),
    "analyst":             (0.60, 0.75, 0.50, 0.55, 0.40, 0.35),
    "review_site":         (0.40, 0.30, 0.50, 0.30, 0.60, 0.20),
    "blog":                (0.30, 0.40, 0.30, 0.20, 0.20, 0.30),
    "social":              (0.20, 0.30, 0.20, 0.10, 0.30, 0.30),
    "other":               (0.40, 0.40, 0.40, 0.40, 0.30, 0.30),
}

# How much conflict of interest matters for each claim category.
_COI_WEIGHT = {"official_financial": 0.25, "self_reported_metric": 0.5, "customer_experience": 0.8, "market": 0.4,
               "technical": 0.4, "event": 0.2, "opinion": 0.6, "other": 0.4}
# Category fit: a source type can be especially good or bad evidence for a kind of claim.
_FIT = {("regulator", "official_financial"): 1.15, ("regulator", "customer_experience"): 0.5,
        ("review_site", "customer_experience"): 1.3, ("review_site", "official_financial"): 0.3,
        ("company", "customer_experience"): 0.6, ("academic", "technical"): 1.2,
        ("official_statistics", "market"): 1.2, ("social", "official_financial"): 0.4}

PRIMARY_THRESHOLD = 0.7


def _entity_tokens(entities: list[str]) -> list[str]:
    toks = []
    for e in entities:
        for t in re.findall(r"[a-z0-9]+", e.lower()):
            if len(t) >= 4 and t not in {"company", "group", "holdings", "corp", "limited", "inc"}:
                toks.append(t)
        joined = re.sub(r"[^a-z0-9]", "", e.lower())
        if len(joined) >= 4:
            toks.append(joined)
    return toks


def classify_domain(url: str, key_entities: list[str]) -> str:
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    full = host + urlsplit(url).path.lower()
    for stype, needles in _LISTS.items():
        if any(host == n or host.endswith("." + n) or full.startswith(n) for n in needles):
            return stype
    if host.endswith(".gov") or ".gov." in host:
        return "regulator"
    if host.endswith(".edu") or ".ac." in host:
        return "academic"
    domain_label = registrable_domain(url).split(".")[0].replace("-", "")
    if any(tok in domain_label for tok in _entity_tokens(key_entities)):
        return "company"
    for kw, stype in _KEYWORDS:
        if kw in host:
            return stype
    return "other"


def assess(source: Source, key_entities: list[str]) -> SourceAssessment:
    stype = classify_domain(source.url, key_entities)
    a, e, t, q, p, c = _DIMENSIONS[stype]
    return SourceAssessment(
        source_id=source.id, source_type=stype, authority=a, expertise=e, transparency=t,
        editorial_quality=q, primary_source_score=p, conflict_of_interest=c,
        assessment_notes=[f"heuristic prior for source type '{stype}' (by domain), not an audited rating"],
    )


def reliability_for(assessment: SourceAssessment, claim: Claim) -> float:
    """Claim-dependent reliability in [0.05, 0.95]."""
    a = assessment
    if claim.kind == "attribution":
        # Documenting that someone SAID something needs editorial care, not independence.
        rel = max(0.5 * a.editorial_quality + 0.3 * a.authority + 0.2 * a.transparency, 0.9 * a.primary_source_score)
    else:
        base = 0.3 * a.authority + 0.2 * a.expertise + 0.15 * a.transparency + 0.15 * a.editorial_quality + 0.2 * a.primary_source_score
        rel = base * (1 - _COI_WEIGHT.get(claim.category, 0.4) * a.conflict_of_interest)
        rel *= _FIT.get((a.source_type, claim.category), 1.0)
    return round(min(0.95, max(0.05, rel)), 3)


def is_primary(assessment: SourceAssessment) -> bool:
    return assessment.primary_source_score >= PRIMARY_THRESHOLD
