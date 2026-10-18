"""Scientific source handling: version resolution, study quality, replication factors."""


from evidence_research.evidence.lineage import detect_lineage
from evidence_research.evidence.source_classifier import assess, classify_domain
from evidence_research.models import Document, StudyProposal, StudyRelation
from evidence_research.science.quality import assess_study, merge_assessments, replication_factor
from evidence_research.science.resolver import find_arxiv_ids, find_dois, resolve_versions

from .conftest import make_source

TITLE = "Adaptive Spaced Retrieval Improves University Exam Performance"


def test_identifier_extraction():
    assert find_arxiv_ids("see arXiv:2403.01234v2 and https://arxiv.org/abs/2101.00001") == {"2403.01234", "2101.00001"}
    assert find_dois("DOI: 10.5555/jlr.2025.0042. Next") == {"10.5555/jlr.2025.0042"}


def test_arxiv_is_a_preprint_server_not_a_journal():
    assert classify_domain("https://arxiv.org/abs/2403.01234", []) == "preprint"
    a = assess(make_source("https://arxiv.org/abs/2403.01234"), [])
    assert a.editorial_quality < 0.5  # moderated, not peer reviewed


def _doc(sid: str, doc_type: str, arxiv=None, doi=None, title=TITLE, authors=("Mara Lind", "Tobi Okafor")) -> Document:
    return Document(id=f"D_{sid}", source_id=sid, document_type=doc_type, title=title, authors=list(authors), arxiv_id=arxiv, doi=doi)


def test_preprint_conference_journal_are_one_work_and_one_root():
    pre = make_source("https://preprints.example/abs/2403.01234", "arXiv:2403.01234 " + TITLE)
    conf = make_source("https://proceedings.example/2024/17", "Also available as arXiv:2403.01234. " + TITLE)
    jour = make_source("https://journal-of-x.example/a/1", "DOI: 10.5555/x.1. An earlier version appeared as arXiv:2403.01234.")
    other = make_source("https://journal-of-y.example/b/2", "A different study of something else entirely.")
    docs = [_doc(pre.id, "preprint", arxiv="2403.01234"), _doc(conf.id, "conference_paper", arxiv="2403.01234"),
            _doc(jour.id, "peer_reviewed_article", doi="10.5555/x.1"),
            _doc(other.id, "peer_reviewed_article", title="Sleep and memory in adolescents", authors=("A. Nwosu",))]
    sources = {s.id: s for s in (pre, conf, jour, other)}
    edges = resolve_versions(docs, sources)
    assert {e.child_source_id for e in edges} == {pre.id, conf.id}
    assert all(e.parent_source_id == jour.id and e.kind == "same_work_version" for e in edges)  # journal is the final version
    lineage = detect_lineage(list(sources.values()), {s.id: assess(s, []) for s in sources.values()}, version_edges=edges)
    assert len(lineage.independent_roots(set(sources))) == 2
    assert len(lineage.families(set(sources))) == 2


def test_peer_review_alone_does_not_make_a_study_strong():
    weak = assess_study("s1", StudyProposal(title="pilot", peer_reviewed=True, study_design="observational study", sample_size=12,
                                            control_group=False, attrition="high"))
    strong = assess_study("s2", StudyProposal(title="rct", peer_reviewed=False, study_design="randomized controlled trial",
                                              sample_size=1180, control_group=True, randomized=True, preregistered=True))
    assert weak.quality_score < 0.3 < strong.quality_score
    assert any("no control group" in n for n in weak.notes)


def test_conflict_of_interest_and_missing_methods_lower_quality():
    clean = assess_study("a", StudyProposal(title="t", study_design="rct", sample_size=400, control_group=True))
    conflicted = assess_study("b", StudyProposal(title="t", study_design="rct", sample_size=400, control_group=True, conflict_of_interest="material"))
    unknown = assess_study("c", StudyProposal(title="t"))
    assert conflicted.quality_score < clean.quality_score
    assert unknown.study_design is None and unknown.sample_size is None


def test_merging_versions_keeps_peer_review_from_final_version():
    pre = assess_study("s", StudyProposal(title="t", peer_reviewed=False, study_design="rct", sample_size=412))
    jour = assess_study("s", StudyProposal(title="t", peer_reviewed=True, study_design="rct", sample_size=412))
    merged = merge_assessments(pre, jour)
    assert merged.peer_reviewed is True and merged.quality_score == max(pre.quality_score, jour.quality_score)


def test_replication_factor():
    def rel(r):
        return StudyRelation(id=r, from_study_id="B", to_study_id="A", relation=r, exact_excerpt="x", source_id="S")
    assert replication_factor([rel("REPLICATES")])[0] > 1
    assert replication_factor([rel("FAILS_TO_REPLICATE")])[0] < 1
    assert replication_factor([rel("REPLICATES"), rel("RETRACTS")])[0] == 0


def test_a_cited_doi_in_a_reference_list_is_not_a_version_link():
    rct = make_source("https://journal-a.example/rct", "DOI: 10.1/rct.1. Fasting trial results.")
    meta = make_source("https://journal-b.example/meta", "Meta-analysis. References: 12. Smith et al. 2020. doi:10.1/rct.1")
    docs = [_doc(rct.id, "randomized_controlled_trial", doi="10.1/rct.1", title="Fasting trial"),
            _doc(meta.id, "meta_analysis", doi="10.1/meta.9", title="Fasting meta-analysis")]
    assert resolve_versions(docs, {rct.id: rct, meta.id: meta}) == []


def test_different_study_designs_are_never_versions():
    a = make_source("https://a.example/1", "x")
    b = make_source("https://b.example/2", "y")
    docs = [_doc(a.id, "randomized_controlled_trial", title=TITLE), _doc(b.id, "meta_analysis", title=TITLE)]
    assert resolve_versions(docs, {a.id: a, b.id: b}) == []
