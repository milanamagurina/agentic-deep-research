from deep_research.citations import UNRETRIEVED, URL_ONLY, VERIFIED, audit_report, parse_sources, split_sources
from deep_research.trace import SourceLedger

from .fakes import QUOTE_A, QUOTE_B, REPORT, URL_A, URL_B


def _ledger() -> SourceLedger:
    ledger = SourceLedger()
    ledger.add(URL_A, "Iron-air pilot", "Intro. " + QUOTE_A + " More text.")
    ledger.add(URL_B, "Flow", "Unrelated snippet only.")
    return ledger


def test_parse_sources_section():
    _, section = split_sources(REPORT)
    entries = parse_sources(section)
    assert [(n, url) for n, url, _, _ in entries] == [(1, URL_A), (2, URL_B)]
    assert entries[0][3] == QUOTE_A


def test_statuses():
    audit = audit_report(REPORT, _ledger())
    assert [c.status for c in audit.checks] == [VERIFIED, URL_ONLY]


def test_fabricated_url_is_flagged():
    report = REPORT.replace(URL_B, "https://made-up.example/never-retrieved")
    audit = audit_report(report, _ledger())
    assert audit.checks[1].status == UNRETRIEVED


def test_edited_quote_is_not_verified():
    report = REPORT.replace("1.5 MW", "15 MW")
    assert audit_report(report, _ledger()).checks[0].status == URL_ONLY


def test_url_normalization_and_typographic_quotes():
    ledger = SourceLedger()
    ledger.add("https://www.example.org/storage/iron-air-pilot/", "", QUOTE_A)
    report = REPORT.replace(f'"{QUOTE_A}"', f"“{QUOTE_A}”")
    assert audit_report(report, ledger).checks[0].status == VERIFIED


def test_dangling_and_unused_markers():
    report = REPORT.replace("[1][2].", "[1][2][7].")
    audit = audit_report(report, _ledger())
    assert audit.dangling_markers == [7]
    assert audit.unused_sources == []
    assert "[7]" in audit.to_markdown()


def test_report_without_sources_section():
    audit = audit_report("# T\n\nNo sources here [1].", SourceLedger())
    assert audit.checks == [] and audit.dangling_markers == [1]


def test_quote_b_is_verified_when_full_text_retrieved():
    ledger = _ledger()
    ledger.add(URL_B, "", QUOTE_B)
    assert audit_report(REPORT, ledger).counts == {VERIFIED: 2, URL_ONLY: 0, UNRETRIEVED: 0}
