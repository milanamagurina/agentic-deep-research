"""Excerpt location, screening, lineage edge cases, agent bidding, active graph, necessity."""

import asyncio
from datetime import date

from evidence_research.config import Heuristics
from evidence_research.evidence.excerpts import locate_excerpt, select_passages
from evidence_research.evidence.lineage import detect_lineage
from evidence_research.evidence.source_classifier import assess, classify_domain
from evidence_research.graph.active import ActiveResearchGraph
from evidence_research.graph.evidence_graph import EvidenceGraph, Link
from evidence_research.models import (
    Hypothesis, Inference, NecessityJudgement, NecessityOutput, QuestionAnalysis, ResearchGap, ScreeningJudgement, ScreeningOutput,
)
from evidence_research.observability.events import EventLog
from evidence_research.orchestration import policy
from evidence_research.probability.engine import recompute
from evidence_research.retrieval.screening import Screener, select_for_extraction
from evidence_research.verification.necessity import deletion_test

from .conftest import TODAY, make_claim, make_evidence, make_source

TABLE = "| Metric | Q2 2024 | Q2 2025 |\n|---|---|---|\n| Revenue | $178.3 million | $252.3 million |"


def test_excerpt_location_recovers_table_rows_but_not_changed_numbers():
    loc = locate_excerpt("Revenue $178.3 million $252.3 million", TABLE)
    assert loc and loc.span in TABLE and loc.method == "exact"
    assert locate_excerpt("Revenue $999.9 million $252.3 million", TABLE) is None
    aligned = locate_excerpt("“Revenue grew 70%” to EUR 47.5 million", "Acme said. Revenue grew 70% to **EUR 47.5 million**, driven")
    assert aligned and aligned.method == "aligned" and "70%" in aligned.span


def test_passage_selection_keeps_relevant_blocks_of_long_pages():
    text = "Title and date\n\n" + "\n\n".join(f"boilerplate paragraph {i} " * 30 for i in range(300)) + "\n\nRetention was 81% in 2025."
    out = select_passages(text, ["retention 2025"], budget=4000)
    assert len(out) <= 4100 and "Retention was 81% in 2025." in out and out.startswith("Title and date")


def test_sec_filings_are_self_reported_and_not_same_publisher():
    url1 = "https://www.sec.gov/Archives/edgar/data/1/a/10k.htm"
    url2 = "https://www.sec.gov/Archives/edgar/data/2/b/10q.htm"
    assert classify_domain(url1, ["Duolingo"]) == "company_filing"
    a, b = make_source(url1, "Annual report of company A about apples."), make_source(url2, "Quarterly report of company B about oranges.")
    result = detect_lineage([a, b], {s.id: assess(s, []) for s in (a, b)})
    assert len(result.independent_roots({a.id, b.id})) == 2  # sec.gov hosts many unrelated publishers


def test_quoted_titles_are_citations_not_copied_text():
    title = "\"MemoLoop: Adaptive Spaced Retrieval Improves University Exam Performance\""
    a = make_source("https://journal-a.example/x", f"A replication of Lind et al., {title}. We found a small effect in six universities.")
    b = make_source("https://journal-b.example/y", f"We failed to replicate {title}. No effect at two sites.")
    result = detect_lineage([a, b], {s.id: assess(s, []) for s in (a, b)})
    assert result.edges == []


class _ScreenLLM:
    records: list = []

    async def structured(self, op, role, system, payload, schema):
        return ScreeningOutput(decisions=[ScreeningJudgement(source_id=r["source_id"], decision="exclude" if "opinion" in r["title"] else "include",
                                                             reasons=["commentary only" if "opinion" in r["title"] else "reports the outcome"],
                                                             relevance="high", document_type="news_article") for r in payload["results"]])


def test_screening_preserves_exclusions_and_old_sources_become_uncertain():
    g = EvidenceGraph()
    fresh = g.add_source(make_source("https://a.example/1", published=date(2026, 1, 1), title="Acme results report"))
    opinion = g.add_source(make_source("https://b.example/2", published=date(2026, 1, 1), title="An opinion on Acme"))
    old = g.add_source(make_source("https://c.example/3", published=date(2015, 1, 1), title="Acme in 2015 annual"))
    analysis = QuestionAnalysis(normalized_question="q", temporal_scope="2025 to 2026")
    decisions = asyncio.run(Screener(_ScreenLLM(), g, EventLog()).screen([fresh, opinion, old], analysis, "q"))
    assert decisions[opinion.id].decision == "exclude" and g.screening[opinion.id].reasons == ["commentary only"]
    assert decisions[old.id].decision == "uncertain"
    assert [s.id for s in select_for_extraction([fresh, opinion, old], decisions, 5)] == [fresh.id, old.id]
    assert g.history(opinion.id, "SAT_SCREENING")  # negative provenance persisted


def _graph_with_gap(gap_type: str, value: float) -> tuple[EvidenceGraph, list[ResearchGap]]:
    g = EvidenceGraph()
    g.add_hypothesis(Hypothesis(id="H1", text="h", prior_probability=0.35, posterior_probability=0.6))
    s = g.add_source(make_source("https://a.example/x", "text"))
    g.set_assessment(assess(s, []))
    c = g.add_claim(make_claim())
    g.add_evidence(make_evidence(s, c))
    gap = ResearchGap(id="G1", target_id=c.id, gap_type=gap_type, description="d", importance=1, uncertainty=1, estimated_value=value)
    return g, [gap]


def test_bids_pick_the_agent_built_for_the_most_valuable_gap():
    g, gaps = _graph_with_gap("NO_PRIMARY_SOURCE", 0.9)
    bids = policy.bid(g, gaps, policy.PolicyState(adversarial_done_for="H1"), set())
    assert policy.select(bids, 1)[0].agent_type == "PrimarySourceResearcher"
    g, gaps = _graph_with_gap("FAILED_REPLICATION", 0.9)
    assert policy.select(policy.bid(g, gaps, policy.PolicyState(adversarial_done_for="H1"), set()), 1)[0].agent_type == "ReplicationResearcher"


def test_unchallenged_leader_attracts_the_adversarial_researcher_and_dry_agents_are_discounted():
    g, gaps = _graph_with_gap("NO_PRIMARY_SOURCE", 0.2)
    state = policy.PolicyState(last_yield={"PrimarySourceResearcher": 0})
    bids = {b.agent_type: b for b in policy.bid(g, gaps, state, set())}
    assert bids["AdversarialResearcher"].utility > bids["PrimarySourceResearcher"].utility
    assert any("×0.5" in r for r in bids["PrimarySourceResearcher"].reasons)
    assert policy.bid(EvidenceGraph(), [], policy.PolicyState(), set())[0].agent_type == "GeneralResearcher"


def test_active_graph_is_small_and_built_from_the_vault(settings):
    g = EvidenceGraph()
    g.add_hypothesis(Hypothesis(id="H1", text="h", prior_probability=0.35, posterior_probability=0.35))
    s = g.add_source(make_source("https://a.example/x", "text"))
    g.set_assessment(assess(s, []))
    ids = set()
    for i in range(30):
        c = g.add_claim(make_claim(f"Acme metric {i} was {i}%"))
        g.add_evidence(make_evidence(s, c))
        ids.add(c.id)
    beliefs = recompute(g, settings, EventLog(), TODAY)
    active = ActiveResearchGraph.build(g, beliefs, ids, [], max_claims=10)
    assert len(active.claims) == 10 and len(g.claims) == 30
    assert set(active.to_payload()) == {"hypotheses", "claims", "contradictions", "open_gaps", "recent_updates"}


class _NecessityLLM:
    records: list = []

    async def structured(self, op, role, system, payload, schema):
        return NecessityOutput(judgements=[NecessityJudgement(premise_id=p["id"], still_justified_without_it="retention" not in p["text"],
                                                              reason="r") for p in payload["premises"]])


def test_deletion_test_marks_necessary_premises():
    g = EvidenceGraph()
    g.add_hypothesis(Hypothesis(id="H1", text="h", prior_probability=0.35, posterior_probability=0.6))
    a, b = g.add_claim(make_claim("Acme retention was 81%")), g.add_claim(make_claim("Acme revenue grew 70%"))
    for i, c in enumerate((a, b)):
        g.add_inference(Inference(id=f"I{i}", premise_ids=[c.id], conclusion_claim_id="H1", inference_type="statistical",
                                  proposed_strength=1.0, status="accepted", verifier_score=0.9))
    out = asyncio.run(deletion_test(_NecessityLLM(), g, EventLog(), set()))
    by = {x.premise_id: x.necessary for x in out}
    assert by == {a.id: True, b.id: False}
    assert g.g.has_edge(a.id, "H1") and any(d["type"] == Link.REQUIRED_FOR.value for d in g.g.get_edge_data(a.id, "H1").values())
    assert all(x.method == "model-based necessity assessment" for x in out)


def test_semantic_links_are_never_evidence():
    g = EvidenceGraph()
    s = g.add_source(make_source("https://a.example/x", "text"))
    c = g.add_claim(make_claim())
    g.link(s.id, c.id, Link.RELATED_TO)
    assert g.sources_for_claim(c.id) == []
    assert Heuristics().dependent_evidence_discount == 0.15
