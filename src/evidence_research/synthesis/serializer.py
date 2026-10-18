"""Render a Report as Markdown (CLI, files) or JSON. Section order follows the report contract."""

from __future__ import annotations

from .report import ClaimView, Report


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def _cites(ns: list[int]) -> str:
    return "".join(f"[{n}]" for n in ns)


def _q(q: dict) -> str:
    if not q:
        return ""
    parts = [f"source {q['source_quality']:.2f}"]
    if q.get("study_quality") is not None:
        parts.append(f"study {q['study_quality']:.2f}")
    if q.get("replication") is not None:
        parts.append(f"replication ×{q['replication']:.2f}")
    parts += [f"independence {q['independence']:.2f}", f"LR {q['likelihood_ratio']:g}"]
    return " · ".join(parts)


def _claim_md(c: ClaimView) -> list[str]:
    lines = [f"#### {c.id}: {c.text}",
             f"- Model-estimated posterior **{_pct(c.posterior)}** · evidence sufficiency **{_pct(c.sufficiency)}** · status `{c.status}` · period: {c.period}",
             f"- Raw sources: {c.raw_sources} · independent roots: **{c.independent_roots}**"
             + (f" · history: {' → '.join(f'{p:.2f}' for p in c.history)}" if len(c.history) > 1 else "")]
    for e in c.support:
        lines.append(f"- SUPPORT [{e.citation}]{' (reported speech)' if e.reported_speech else ''}: “{e.excerpt}” — {_q(e.quality)}")
    for e in c.against:
        lines.append(f"- AGAINST [{e.citation}]: “{e.excerpt}” — {_q(e.quality)}")
    for m in c.missing:
        lines.append(f"- MISSING: {m}")
    return lines


def to_markdown(r: Report) -> str:
    out = [f"# Research report: {r.question}", ""]
    if r.synthetic:
        out += ["> **SYNTHETIC DEMO RUN** — fictional entities, scripted corpus and model responses. Not real-world evidence.", ""]
    out += ["## Executive conclusion", f"**Current evidence status: {r.status.value}**", ""]
    out += [f"- {s.text} {_cites(s.citations)}" for s in r.conclusion] or ["- (No model-written sentence passed citation verification; see structured findings below.)"]
    if r.rejected_statements:
        out += ["", f"_{len(r.rejected_statements)} draft sentence(s) were removed by the citation verifier._"]

    by_id = {h.id: h for h in r.hypotheses}
    out += ["", "## Surviving hypotheses", "| ID | Hypothesis | Prior | Posterior | Sufficiency | Inference validity | Status |", "|---|---|---|---|---|---|---|"]
    for h in r.hypotheses:
        if h.status not in ("rejected", "weakened"):
            out.append(f"| {h.id} | {h.text}{' (null)' if h.is_null else ''} | {_pct(h.prior)} | **{_pct(h.posterior)}** | {_pct(h.sufficiency)} | {_pct(h.inference_validity)} | {h.status} |")
    if r.leading_hypothesis:
        out.append(f"\nMain surviving hypothesis: **{r.leading_hypothesis}** — {by_id[r.leading_hypothesis].text}")
    if r.counter_hypothesis:
        out.append(f"Strongest counter-hypothesis: **{r.counter_hypothesis}** — {by_id[r.counter_hypothesis].text}")
    out += ["", "## Rejected / weakened hypotheses"]
    weak = [h for h in r.hypotheses if h.status in ("rejected", "weakened")]
    out += [f"- **{h.id}** {h.text}: {h.status}, posterior {_pct(h.prior)} → {_pct(h.posterior)}" for h in weak] or ["- None."]
    for h in r.hypotheses:
        for i in h.rejected_inferences:
            out.append(f"  - {h.id} inference not accepted: {i}")

    out += ["", "## Critical claims: supporting and contradicting evidence"]
    for c in r.critical_claims:
        out += _claim_md(c) + [""]

    out += ["## Source independence",
            f"**{r.raw_source_count} URLs with evidence → {r.publication_family_count} publication families → "
            f"{r.independent_root_count} independent evidence roots.**"]
    for cl in r.clusters:
        out.append(f"- Root {cl['root']} ({cl['root_title'][:60]}): {len(cl['members'])} sources {', '.join(cl['members'])}")
    if r.screened_out:
        out.append(f"- {len(r.screened_out)} source(s) screened out before extraction, e.g. "
                   + "; ".join(f"{x['source_id']} ({', '.join(x['reasons'])[:60]})" for x in r.screened_out[:3]))

    out += ["", "## Scientific study quality"]
    for st in r.studies:
        versions = ", ".join(f"{v['document_type']} ({v['source_id']})" for v in st.versions)
        out.append(f"- **{st.id}** {st.title}: {st.design or 'design n/a'}, n={st.sample_size or 'n/a'}, peer reviewed={st.peer_reviewed}, "
                   f"preregistered={st.preregistered}, quality **{st.quality:.2f}**; versions: {versions}")
        for rel in st.replication:
            out.append(f"  - {rel}")
        for res in st.results[:3]:
            out.append(f"  - result [{res['status']}]: {res['outcome']} {res['measure'] or ''}={res['effect']} CI {res['ci']} n={res['n']}")
        if st.warnings:
            out.append(f"  - methodological notes: {'; '.join(st.warnings[:5])}")
    if not r.studies:
        out.append("- No scientific studies among the sources.")

    out += ["", "## Research gaps"]
    out += [f"- **{g.level}** [{g.gap_type}] {g.description}{' — unresolvable with public data so far' if g.unresolvable else ''}" for g in r.gaps] or ["- None."]
    out += ["", "## What would change our mind"] + [f"{i}. {w}" for i, w in enumerate(r.what_would_change, 1)]
    out += ["", "## Why research stopped"] + [f"- {w}" for w in r.why_stopped]
    out += ["", "## Limitations and method"] + [f"- {m}" for m in r.method_limitations]
    out += ["", "## Citations"]
    for c in r.citations:
        out.append(f"[{c.n}] {c.title} — {c.url} ({c.publisher}; published {c.published_at or 'unknown'}; retrieved {c.retrieved_at:%Y-%m-%d}; root {c.independent_root})")
    out += ["", f"_Stats: {r.stats}_"]
    return "\n".join(out)


def to_json(r: Report) -> str:
    return r.model_dump_json(indent=2)
