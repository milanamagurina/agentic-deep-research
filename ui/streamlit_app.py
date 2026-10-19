"""Streamlit demo UI.   streamlit run ui/streamlit_app.py"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evidence_research.config import ConfigError, Depth, Settings, load_dotenv_if_present  # noqa: E402
from evidence_research.demo import get_scenario  # noqa: E402
from evidence_research.evidence.source_classifier import is_primary  # noqa: E402
from evidence_research.graph.queries import focus_nodes, to_dot  # noqa: E402
from evidence_research.observability.events import EventType, format_event  # noqa: E402
from evidence_research.runtime import research  # noqa: E402
from evidence_research.synthesis.serializer import to_markdown  # noqa: E402
from evidence_research.verification.citation_audit import audit, summary  # noqa: E402

st.set_page_config(page_title="Deep Search Agentic Orchestration", page_icon="🔎", layout="wide")
load_dotenv_if_present()
# On Streamlit Community Cloud there is no .env; let dashboard secrets fill the env Settings reads.
# Local .env still wins (set only if unset). Without any secrets, the app runs the offline demos.
try:
    for _k, _v in st.secrets.items():
        os.environ.setdefault(_k, str(_v))
except Exception:
    pass

LIVE_TRACE = {EventType.HYPOTHESIS_CREATED, EventType.AGENT_SELECTED, EventType.SEARCH_EXECUTED, EventType.SOURCE_SCREENED,
              EventType.SCIENTIFIC_VERSION_RESOLVED, EventType.STUDY_ASSESSED, EventType.STUDY_RELATION_FOUND,
              EventType.SOURCE_DEPENDENCY_DETECTED, EventType.INDEPENDENCE_SUMMARY, EventType.INFERENCE_ACCEPTED, EventType.INFERENCE_REJECTED,
              EventType.NECESSITY_ASSESSED, EventType.CONTRADICTION_FOUND, EventType.CLAIM_POSTERIOR_UPDATED, EventType.HYPOTHESIS_UPDATED,
              EventType.RESEARCH_GAP_CREATED, EventType.STOP_DECISION, EventType.STATEMENT_REJECTED, EventType.TEMPORAL_VERSION_DETECTED}
MODES = {"Synthetic demo: business (offline)": "business", "Synthetic demo: science (offline)": "science", "Live (Token Factory + Tavily)": None}

with st.sidebar:
    st.header("Run settings")
    settings = Settings.from_env()
    live_ready = settings.nebius_api_key is not None and settings.tavily_api_key is not None
    mode_label = st.radio("Mode", list(MODES), index=2 if live_ready else 0,
                          help="Synthetic demos use fictional entities, a scripted model and a fake corpus. They need no keys.")
    demo = MODES[mode_label]
    if demo is None and not live_ready:
        st.error("NEBIUS_API_KEY and TAVILY_API_KEY are required for live mode (see .env.example).")
    st.caption(f"Model: `{settings.nebius_model}`" + (f" · reasoning: `{settings.nebius_reasoning_model}`" if settings.nebius_reasoning_model else ""))
    st.divider()
    st.markdown(
        "**How it works**\n\n"
        "1. **Plan** — your question becomes a few possible answers and what evidence each one needs.\n"
        "2. **Search** — a lead coordinator sends out specialist research agents to find and filter sources.\n"
        "3. **Challenge** — a critic agent actively hunts for evidence that would prove the answer wrong.\n"
        "4. **Verify** — every sentence in the answer is tied to an exact quote from a real source you can click and check.\n"
        "5. **Score** — a confidence level reflects how much independent, trustworthy evidence backs the answer.\n\n"
        "The AI only *proposes*; the system checks the facts. Nothing is stated unless a real source backs it."
    )

st.title("Deep Search Agentic Orchestration")
st.caption("**Re-checking everything an AI tells you is a painful time sink** — especially after a hallucination, a weak model, "
           "or a sloppy prompt. So this doesn't just answer: it **researches like a scientist** — builds a knowledge graph of what "
           "is genuinely supported, tests each **hypothesis against its anti-hypothesis**, verifies every claim, and ties each "
           "sentence to a real source you can click. You read the answer instead of re-checking it.")

default_q = get_scenario(demo).question if demo else ""
question = st.text_input("Research question", value=default_q, placeholder="Does Company X have strong product-market fit?",
                         disabled=demo is not None, key=f"q_{demo}")
depth = st.radio("Research depth", [d.value.capitalize() for d in Depth], index=1, horizontal=True)
start = st.button("Start Research", type="primary", disabled=not question or (demo is None and not live_ready))

if start:
    lines: list[str] = []
    with st.status("Researching…", expanded=True) as status:
        box = st.empty()

        def on_event(e) -> None:
            if e.type in LIVE_TRACE:
                lines.append(format_event(e))
                box.code("\n".join(lines[-30:]), language=None)
            if e.type is EventType.PHASE_CHANGED:
                status.update(label=f"Phase: {e.data['to']}")

        try:
            st.session_state.result = asyncio.run(research(question if demo is None else None, settings, Depth(depth.lower()),
                                                           demo=demo, on_event=on_event))
            status.update(label="Research complete", state="complete", expanded=False)
        except ConfigError as e:
            status.update(label="Configuration error", state="error")
            st.error(str(e))
        except Exception as e:
            status.update(label="Research failed", state="error")
            st.error(f"{type(e).__name__}: {e}")

r = st.session_state.get("result")
if r is None:
    st.info("Enter a question and start a run. Without API keys, choose a **Synthetic demo** in the sidebar.")
    st.stop()

rep, g = r.report, r.graph
hyp = {h.id: h for h in rep.hypotheses}
if rep.synthetic:
    st.warning("SYNTHETIC DEMO RUN: fictional entities, scripted corpus and model responses. Not real-world evidence.")
lead = hyp.get(rep.leading_hypothesis)

# The public contract (sections 1, 11): a substantive answer and one confidence number, up top.
st.subheader("Research answer")
st.markdown(rep.answer.answer)
ac, qc = st.columns([1, 3])
ac.metric("Confidence", f"{rep.answer.confidence:.0%}", help="How strongly the evidence we found and verified supports this answer.")
if rep.qualification:
    qc.info(rep.qualification)

with st.expander("Research diagnostics", expanded=False):
    cols = st.columns(5)
    cols[0].metric("Evidence status", rep.status.value.replace("_", " "))
    cols[1].metric("Truth posterior (lead)", f"{lead.posterior:.0%}" if lead else "n/a", help="model-estimated posterior of the main surviving hypothesis")
    cols[2].metric("Evidence sufficiency", f"{lead.sufficiency:.0%}" if lead else "n/a")
    cols[3].metric("Independent evidence roots", rep.independent_root_count, f"{rep.raw_source_count} URLs · {rep.publication_family_count} families",
                   delta_color="off")
    cols[4].metric("Critical unresolved gaps", sum(1 for x in rep.gaps if x.level == "HIGH"))
    pen = rep.confidence_breakdown.get("penalties", [])
    st.caption(f"Question type: `{rep.question_type}` · confidence from {rep.confidence_breakdown.get('used_claims', 0)} used claim(s), "
               f"penalized for: {'; '.join(pen) if pen else 'nothing'}.")
    st.caption(f"Stop reason: **{rep.stop_reason}** — {rep.stop_explanation}")

TAB_NAMES = ["Overview", "Citation Check", "Hypotheses", "Claims & Evidence", "Scientific Studies", "Source Lineage", "Research Trace",
             "Evidence DAG", "Sources"]
tabs = dict(zip(TAB_NAMES, st.tabs(TAB_NAMES)))

with tabs["Overview"]:
    # Minto pyramid: answer first, then MECE reasons, then the facts under each.
    g0 = rep.governing_thought
    st.markdown(f"### {g0.text} " + "".join(f"`[{n}]`" for n in g0.citations))
    if rep.governing_is_system_summary:
        st.caption("System summary: no model-written answer passed citation verification.")
    st.markdown("#### Why — each factor with its own confidence")
    for i, kl in enumerate(rep.key_lines, 1):
        st.markdown(f"**{i}. {kl.statement.text}** &nbsp; `confidence {kl.confidence:.0%}` "
                    + "".join(f"`[{n}]`" for n in kl.statement.citations))
        for sp in kl.support:
            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;- {sp.text} " + "".join(f"`[{n}]`" for n in sp.citations))
    if rep.rejected_statements:
        with st.expander(f"{len(rep.rejected_statements)} draft statement(s) removed by the citation verifier"):
            for x in rep.rejected_statements:
                st.markdown(f"- ~~{x['text']}~~ — *{x.get('level', 'statement')}: {x['reason']}*")
    a, b = st.columns(2)
    with a:
        st.markdown("#### Caveats")
        for c in rep.caveats:
            st.markdown(f"- {c}")
        st.markdown("#### What would change our mind")
        for i, w in enumerate(rep.what_would_change, 1):
            st.markdown(f"{i}. {w}")
    with b:
        st.markdown("#### Sources cited")
        st.caption("Every quote, with a link that opens the page at it: see the **Citation Check** tab.")
        for c in rep.citations:
            st.markdown(f"**[{c.n}]** [{c.title[:70]}]({c.url}) — {len(c.uses)} quote(s)")
    with st.expander("How the agent decided (decisions made by code, in order)", expanded=True):
        for i, d in enumerate(rep.decision_trace, 1):
            st.markdown(f"{i}. {d}")
    st.caption(f"Stop reason: **{rep.stop_reason}** — {rep.stop_explanation}")
    st.download_button("Download report (Markdown)", to_markdown(rep), file_name="evidence_report.md")

with tabs["Citation Check"]:
    uses = [(c, u) for c in rep.citations for u in c.uses]
    st.markdown(f"**All {len(rep.citations)} cited sources and all {len(uses)} quotes this report relies on.** "
                "Each quote link opens the source page at that exact text (Chrome / Edge text fragments).")
    st.dataframe(pd.DataFrame([{"#": c.n, "stance": u["stance"], "claim": u["claim"], "quote (verbatim)": " ".join(u["excerpt"].split()),
                                "open at quote": u["deep_link"], "source": c.url} for c, u in uses]),
                 hide_index=True, width="stretch",
                 column_config={"open at quote": st.column_config.LinkColumn("open at quote", display_text="open ↗"),
                                "source": st.column_config.LinkColumn("source")})
    st.markdown("**Re-check every citation now.** Fetches each cited page again and confirms every quote is still on it.")
    if st.button("Re-check all citations", key="audit"):
        if rep.synthetic:
            from evidence_research.demo import FakeSearch, get_scenario

            sc = next(n for n in ("business", "science") if get_scenario(n).question == rep.question)
            client = FakeSearch(get_scenario(sc).pages)
            st.caption("Synthetic run: pages come from the fictional corpus.")
        else:
            from evidence_research.retrieval.tavily_client import TavilyResearchClient

            client = TavilyResearchClient(settings)
        with st.spinner("Fetching every cited page…"):
            checks = asyncio.run(audit(rep.model_dump(mode="json"), client))
        st.session_state.audit_result = checks
    if "audit_result" in st.session_state:
        checks = st.session_state.audit_result
        ok = all(c.status.startswith("found") for c in checks)
        (st.success if ok else st.warning)(summary(checks))
        st.dataframe(pd.DataFrame([{"#": c.citation, "status": c.status, "stance": c.stance, "quote": " ".join(c.excerpt.split())[:200],
                                    "url": c.url} for c in checks]), hide_index=True, width="stretch",
                     column_config={"url": st.column_config.LinkColumn("url")})

with tabs["Hypotheses"]:
    st.dataframe(pd.DataFrame([{"ID": h.id, "Hypothesis": h.text, "Prior": h.prior, "Posterior": h.posterior, "Sufficiency": h.sufficiency,
                                "Inference validity": h.inference_validity, "Status": h.status} for h in rep.hypotheses]),
                 hide_index=True, width="stretch",
                 column_config={k: st.column_config.ProgressColumn(k, min_value=0, max_value=1, format="%.2f")
                                for k in ("Prior", "Posterior", "Sufficiency", "Inference validity")})
    st.markdown("**Posterior history** (append-only satellite observations; never overwritten)")
    st.line_chart(pd.DataFrame({h.id: pd.Series(h.history) for h in rep.hypotheses}))
    nec = [a for a in g.necessity.values()]
    if nec:
        st.markdown("**Deletion test** (model-based necessity assessment, not a proof)")
        for a in nec:
            st.markdown(f"- {a.premise_id} is {'**necessary**' if a.necessary else 'not necessary'} for {a.hypothesis_id}: {a.reason} *({a.method})*")
    for h in rep.hypotheses:
        if h.accepted_inferences or h.rejected_inferences:
            with st.expander(f"{h.id} inferences"):
                for i in h.accepted_inferences:
                    st.markdown(f"- ✅ {i}")
                for i in h.rejected_inferences:
                    st.markdown(f"- ❌ {i}")

with tabs["Claims & Evidence"]:
    for c in rep.critical_claims:
        with st.expander(f"{c.id} · {c.text}", expanded=c is rep.critical_claims[0]):
            m = st.columns(5)
            m[0].metric("Posterior", f"{c.posterior:.0%}")
            m[1].metric("Sufficiency", f"{c.sufficiency:.0%}")
            accepted = [i for i in g.inferences.values() if c.id in i.premise_ids and i.status == "accepted"]
            m[2].metric("Inference validity", f"{sum(i.verifier_score for i in accepted) / len(accepted):.0%}" if accepted else "n/a",
                        help="mean verifier score of accepted inferences that use this claim")
            m[3].metric("Independent roots", c.independent_roots)
            m[4].metric("Raw sources", c.raw_sources)
            st.caption(f"Status `{c.status}` · {c.kind} · period {c.period} · history {' → '.join(f'{p:.2f}' for p in c.history)}")
            for label, lines_ in (("SUPPORT", c.support), ("CONTRADICTION", c.against)):
                st.markdown(f"**{label}**")
                if not lines_:
                    st.caption("none found")
                for e in lines_:
                    st.markdown(f"> {e.excerpt} `[{e.citation}]`" + (" *(reported speech)*" if e.reported_speech else ""))
                    if e.quality:
                        q = e.quality
                        st.caption(" · ".join(f"{k.replace('_', ' ')} {v:.2f}" if isinstance(v, float) else f"{k} {v}"
                                              for k, v in q.items() if v is not None and k not in ("bucket",)))
            if c.missing:
                st.markdown("**MISSING**")
                for x in c.missing:
                    st.markdown(f"- {x}")

with tabs["Scientific Studies"]:
    if not rep.studies:
        st.info("No scientific studies among the sources.")
    for s in rep.studies:
        with st.expander(f"{s.id} · {s.title}", expanded=len(s.versions) > 1):
            m = st.columns(4)
            m[0].metric("Study quality", f"{s.quality:.2f}")
            m[1].metric("Design", s.design or "n/a")
            m[2].metric("Sample size", s.sample_size or "n/a")
            m[3].metric("Peer reviewed", {True: "yes", False: "no", None: "unknown"}[s.peer_reviewed])
            st.markdown("**Publication versions** (one research lineage)")
            for v in s.versions:
                st.markdown(f"- {v['document_type']} — {v['url']} (peer reviewed: {v['peer_reviewed']})")
            if s.replication:
                st.markdown("**Replication graph**")
                for x in s.replication:
                    st.markdown(f"- {x}")
            st.markdown("**Results**")
            st.dataframe(pd.DataFrame(s.results), hide_index=True, width="stretch")
            if s.warnings:
                st.markdown("**Methodological notes**")
                for w in s.warnings:
                    st.markdown(f"- {w}")

with tabs["Source Lineage"]:
    c1, c2, c3 = st.columns(3)
    c1.metric("URLs with evidence", rep.raw_source_count)
    c2.metric("Publication families", rep.publication_family_count)
    c3.metric("Independent evidence roots", rep.independent_root_count)
    st.markdown("Ten websites repeating one press release are not ten independent pieces of evidence.")
    rows = [{"child": e.child_source_id, "relation": e.kind, "parent": e.parent_source_id, "p(dependent)": e.dependency_probability,
             "signals": "; ".join(e.evidence)} for e in g.lineage]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    for cl in rep.clusters:
        st.markdown(f"- Root `{cl['root']}` ({cl['root_title'][:60]}): {len(cl['members'])} sources")

with tabs["Research Trace"]:
    types = sorted({e.type.value for e in r.events.events})
    default = [t for t in types if t not in ("MODEL_CALL", "PHASE_CHANGED", "SOURCE_REJECTED", "SEARCH_PLANNED", "SOURCE_FOUND")]
    chosen = st.multiselect("Event types", types, default=default)
    st.dataframe(pd.DataFrame([{"time": e.ts.strftime("%H:%M:%S"), "#": e.seq, "event": e.type.value, "message": e.message}
                               for e in r.events.events if e.type.value in chosen]),
                 hide_index=True, width="stretch", height=520)
    if g.bids:
        st.markdown("**Agent bids per round** (heuristic utility of acting now)")
        st.dataframe(pd.DataFrame([{"round": it, "agent": b.agent_type, "utility": b.utility, "reason": b.reasons[0] if b.reasons else ""}
                                   for it, bids in g.bids for b in bids]), hide_index=True, width="stretch")

with tabs["Evidence DAG"]:
    c1, c2, c3 = st.columns([2, 1, 1])
    ids = [h.id for h in rep.hypotheses]
    hid = c1.selectbox("Hypothesis", [None] + ids, format_func=lambda x: "All" if x is None else x,
                       index=1 + ids.index(rep.leading_hypothesis) if rep.leading_hypothesis else 0)
    show_ev = c2.checkbox("Evidence nodes", True)
    show_src = c3.checkbox("Source nodes", True)
    st.graphviz_chart(to_dot(g, focus_nodes(g, hid, show_ev, show_src)), width="stretch")
    st.caption("green = supports · red = contradicts · dotted = provenance (derived from) · diamond = verified inference. "
               "Semantic links are never drawn as proof.")

with tabs["Sources"]:
    rows = []
    for s in g.sources.values():
        a, scr = g.assessments.get(s.id), g.screening.get(s.id)
        rows.append({"id": s.id, "title": s.title, "url": s.url, "screening": scr.decision if scr else "", "screening reasons":
                     "; ".join(scr.reasons) if scr else "", "type": a.source_type if a else "", "primary": bool(a and is_primary(a)),
                     "independence": a.independence if a else None, "conflict of interest": a.conflict_of_interest if a else None,
                     "published": s.published_at, "found by": s.search_origin, "extracted": s.extracted,
                     "root": g.root_of.get(s.id, s.id)})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={"url": st.column_config.LinkColumn("url")})
    st.caption(f"{len(rep.screened_out)} source(s) excluded at screening; reasons kept as negative provenance.")
    with st.expander("Citations"):
        for c in rep.citations:
            st.markdown(f"[{c.n}] [{c.title}]({c.url}) — {c.publisher}, published {c.published_at or 'unknown'}")
