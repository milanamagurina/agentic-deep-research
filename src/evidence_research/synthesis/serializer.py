"""Render a Report as Markdown (CLI, files) or JSON."""

from __future__ import annotations

from .report import ClaimView, Report


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def _cites(ns: list[int]) -> str:
    return "".join(f"[{n}]" for n in ns)


def _claim_md(c: ClaimView) -> list[str]:
    lines = [f"#### {c.id}: {c.text}",
             f"- Model-estimated posterior **{_pct(c.posterior)}** · evidence sufficiency **{_pct(c.sufficiency)}** · status `{c.status}` · period: {c.period}",
             f"- Raw sources: {c.raw_sources} · independent roots: **{c.independent_roots}**"
             + (f" · history: {' → '.join(f'{p:.2f}' for p in c.history)}" if len(c.history) > 1 else "")]
    for e in c.support:
        lines.append(f"- SUPPORT [{e.citation}]{' (reported speech)' if e.reported_speech else ''}: “{e.excerpt}”")
    for e in c.against:
        lines.append(f"- AGAINST [{e.citation}]: “{e.excerpt}”")
    for m in c.missing:
        lines.append(f"- MISSING: {m}")
    return lines


def to_markdown(r: Report) -> str:
    out = [f"# Research report: {r.question}", ""]
    if r.synthetic:
        out += ["> **SYNTHETIC DEMO RUN** — fictional company, scripted corpus and model responses. Not real-world evidence.", ""]
    out += ["## Conclusion", f"**Overall evidence status: {r.status.value}**", ""]
    out += [f"- {s.text} {_cites(s.citations)}" for s in r.conclusion] or ["- (No model-written sentence passed citation verification; see structured findings below.)"]
    if r.rejected_statements:
        out += ["", f"_{len(r.rejected_statements)} draft sentence(s) were removed by the citation verifier._"]

    out += ["", "## Hypotheses", "| ID | Hypothesis | Prior | Posterior | Sufficiency | Inference validity | Status |", "|---|---|---|---|---|---|---|"]
    for h in r.hypotheses:
        out.append(f"| {h.id} | {h.text}{' (null)' if h.is_null else ''} | {_pct(h.prior)} | **{_pct(h.posterior)}** | {_pct(h.sufficiency)} | {_pct(h.inference_validity)} | {h.status} |")
    for h in r.hypotheses:
        for i in h.rejected_inferences:
            out.append(f"- {h.id} rejected/needs evidence: {i}")

    out += ["", "## Critical claims and evidence"]
    for c in r.critical_claims:
        out += _claim_md(c) + [""]

    out += ["## Source independence",
            f"{r.raw_source_count} raw sources with evidence → **{r.independent_root_count} independent roots**."]
    for cl in r.clusters:
        out.append(f"- Cluster rooted at {cl['root']} ({cl['root_title'][:60]}): {len(cl['members'])} sources {', '.join(cl['members'])}")

    out += ["", "## Research debt (unresolved gaps)"]
    out += [f"- **{g.level}** [{g.gap_type}] {g.description}{' — unresolvable with public data so far' if g.unresolvable else ''}" for g in r.gaps] or ["- None."]
    out += ["", "## What would change our mind"] + [f"{i}. {w}" for i, w in enumerate(r.what_would_change, 1)]
    out += ["", "## Method and limitations"] + [f"- {m}" for m in r.method_limitations]
    out += ["", "## Citations"]
    for c in r.citations:
        out.append(f"[{c.n}] {c.title} — {c.url} ({c.publisher}; published {c.published_at or 'unknown'}; retrieved {c.retrieved_at:%Y-%m-%d}; root {c.independent_root})")
    out += ["", f"_Stats: {r.stats}_"]
    return "\n".join(out)


def to_json(r: Report) -> str:
    return r.model_dump_json(indent=2)
