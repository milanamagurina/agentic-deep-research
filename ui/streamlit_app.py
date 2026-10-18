"""Streamlit demo UI.   streamlit run ui/streamlit_app.py"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from evidence_research.config import ConfigError, Depth, Settings, load_dotenv_if_present  # noqa: E402
from evidence_research.demo.scenario import QUESTION as DEMO_QUESTION  # noqa: E402
from evidence_research.evidence.source_classifier import is_primary  # noqa: E402
from evidence_research.graph.queries import focus_nodes, to_dot  # noqa: E402
from evidence_research.observability.events import EventType, format_event  # noqa: E402
from evidence_research.runtime import research  # noqa: E402
from evidence_research.synthesis.serializer import to_markdown  # noqa: E402

st.set_page_config(page_title="Probabilistic Evidence Research", page_icon="🔎", layout="wide")
load_dotenv_if_present()

HIGHLIGHT = {EventType.SOURCE_DEPENDENCY_DETECTED, EventType.INFERENCE_REJECTED, EventType.CONTRADICTION_FOUND,
             EventType.CLAIM_POSTERIOR_UPDATED, EventType.RESEARCH_GAP_CREATED, EventType.RESEARCH_SCHEDULED, EventType.STOP_DECISION,
             EventType.HYPOTHESIS_CREATED, EventType.SEARCH_EXECUTED, EventType.INFERENCE_ACCEPTED, EventType.STATEMENT_REJECTED,
             EventType.TEMPORAL_VERSION_DETECTED, EventType.RESEARCH_GAP_UNRESOLVABLE}

with st.sidebar:
    st.header("Run settings")
    settings = Settings.from_env()
    live_ready = settings.nebius_api_key is not None and settings.tavily_api_key is not None
    mode = st.radio("Mode", ["Synthetic demo (offline)", "Live (Token Factory + Tavily)"], index=1 if live_ready else 0,
                    help="The synthetic demo uses a fictional company, a scripted model and a fake corpus. It needs no keys.")
    demo = mode.startswith("Synthetic")
    if not demo and not live_ready:
        st.error("NEBIUS_API_KEY and TAVILY_API_KEY are required for live mode (see .env.example).")
    st.caption(f"Model: `{settings.nebius_model}`" + (f" · reasoning: `{settings.nebius_reasoning_model}`" if settings.nebius_reasoning_model else ""))
    st.divider()
    st.markdown("**How to read the numbers**\n\n*Posterior* and *sufficiency* are model-estimated evidence beliefs from "
                "heuristic likelihood ratios. They are **not calibrated probabilities**.")

st.title("Probabilistic Evidence Research")
st.caption("LLM proposes · verifier checks · evidence graph remembers · probability engine updates · gap engine decides what to research next")

question = st.text_input("Research question", value=DEMO_QUESTION if demo else "", placeholder="Does Company X have strong product-market fit?")
depth = st.radio("Research depth", [d.value.capitalize() for d in Depth], index=1, horizontal=True)
start = st.button("Start Research", type="primary", disabled=not question or (not demo and not live_ready))

if start:
    lines: list[str] = []
    with st.status("Researching…", expanded=True) as status:
        box = st.empty()

        def on_event(e) -> None:
            if e.type in HIGHLIGHT:
                lines.append(format_event(e))
                box.code("\n".join(lines[-28:]), language=None)
            if e.type is EventType.PHASE_CHANGED:
                status.update(label=f"Phase: {e.data['to']}")

        try:
            st.session_state.result = asyncio.run(research(question, settings, Depth(depth.lower()), demo=demo, on_event=on_event))
            status.update(label="Research complete", state="complete", expanded=False)
        except ConfigError as e:
            status.update(label="Configuration error", state="error")
            st.error(str(e))
        except Exception as e:
            status.update(label="Research failed", state="error")
            st.error(f"{type(e).__name__}: {e}")

r = st.session_state.get("result")
if r is None:
    st.info("Enter a question and start a run. With no API keys, choose **Synthetic demo** in the sidebar.")
    st.stop()

rep, g = r.report, r.graph
if rep.synthetic:
    st.warning("SYNTHETIC DEMO RUN: fictional company, scripted corpus and model responses. Not real-world evidence.")
lead = next((h for h in rep.hypotheses if h.id == rep.leading_hypothesis), None)
st.subheader("Decision / conclusion")
cols = st.columns(5)
cols[0].metric("Evidence status", rep.status.value.replace("_", " "))
cols[1].metric("Truth confidence (lead)", f"{lead.posterior:.0%}" if lead else "n/a", help="model-estimated posterior of the leading hypothesis")
cols[2].metric("Evidence sufficiency", f"{lead.sufficiency:.0%}" if lead else "n/a")
cols[3].metric("Independent sources", f"{rep.independent_root_count} roots", f"{rep.raw_source_count} raw sources", delta_color="off")
cols[4].metric("Unresolved critical gaps", sum(1 for x in rep.gaps if x.level == "HIGH"))

tabs = st.tabs(["Overview", "Hypotheses", "Claims & Evidence", "Research Trace", "Evidence Graph", "Sources"])

with tabs[0]:
    for s in rep.conclusion:
        st.markdown(f"- {s.text} " + "".join(f"`[{n}]`" for n in s.citations))
    if rep.rejected_statements:
        with st.expander(f"{len(rep.rejected_statements)} draft sentence(s) removed by the citation verifier"):
            for x in rep.rejected_statements:
                st.markdown(f"- ~~{x['text']}~~ — *{x['reason']}*")
    a, b = st.columns(2)
    with a:
        st.markdown("**Surviving hypotheses**")
        for h in rep.hypotheses:
            if h.status not in ("rejected",):
                st.markdown(f"- **{h.id}** {h.text} — {h.posterior:.0%} ({h.status})")
        contested = [c for c in rep.critical_claims if c.against]
        if contested:
            c = max(contested, key=lambda c: len(c.against))
            st.markdown("**Biggest contradiction**")
            st.markdown(f"{c.text} — posterior {' → '.join(f'{p:.2f}' for p in c.history)}")
            st.caption(f"“{c.against[0].excerpt}” [{c.against[0].citation}]")
    with b:
        st.markdown("**Research debt**")
        for x in rep.gaps[:6]:
            st.markdown(f"- **{x.level}** [{x.gap_type}] {x.description}" + (" — *unresolvable with public data*" if x.unresolvable else ""))
        st.markdown("**What would change our mind**")
        for i, w in enumerate(rep.what_would_change, 1):
            st.markdown(f"{i}. {w}")
    st.caption(f"Stop reason: **{rep.stop_reason}** — {rep.stop_explanation}")
    st.download_button("Download report (Markdown)", to_markdown(rep), file_name="evidence_report.md")

with tabs[1]:
    st.dataframe(pd.DataFrame([{"ID": h.id, "Hypothesis": h.text, "Prior": h.prior, "Posterior": h.posterior, "Sufficiency": h.sufficiency,
                                "Inference validity": h.inference_validity, "Status": h.status} for h in rep.hypotheses]),
                 hide_index=True, width="stretch",
                 column_config={k: st.column_config.ProgressColumn(k, min_value=0, max_value=1, format="%.2f")
                                for k in ("Prior", "Posterior", "Sufficiency", "Inference validity")})
    hist = {h.id: pd.Series(h.history) for h in rep.hypotheses}
    st.markdown("**Posterior history** (one point per observation; never overwritten)")
    st.line_chart(pd.DataFrame(hist))
    for h in rep.hypotheses:
        if h.accepted_inferences or h.rejected_inferences:
            with st.expander(f"{h.id} inferences"):
                for i in h.accepted_inferences:
                    st.markdown(f"- ✅ {i}")
                for i in h.rejected_inferences:
                    st.markdown(f"- ❌ {i}")

with tabs[2]:
    for c in rep.critical_claims:
        with st.expander(f"{c.id} · {c.text}", expanded=c is rep.critical_claims[0]):
            m = st.columns(4)
            m[0].metric("Posterior", f"{c.posterior:.0%}")
            m[1].metric("Sufficiency", f"{c.sufficiency:.0%}")
            m[2].metric("Independent roots", c.independent_roots)
            m[3].metric("Raw sources", c.raw_sources)
            st.caption(f"Status `{c.status}` · {c.kind} · period {c.period} · history {' → '.join(f'{p:.2f}' for p in c.history)}")
            st.markdown("**SUPPORT**")
            for e in c.support:
                st.markdown(f"> {e.excerpt} `[{e.citation}]`" + (" *(reported speech)*" if e.reported_speech else ""))
            st.markdown("**AGAINST**")
            for e in c.against or []:
                st.markdown(f"> {e.excerpt} `[{e.citation}]`")
            if not c.against:
                st.caption("none found")
            if c.missing:
                st.markdown("**MISSING**")
                for x in c.missing:
                    st.markdown(f"- {x}")

with tabs[3]:
    types = sorted({e.type.value for e in r.events.events})
    default = [t for t in types if t not in ("MODEL_CALL", "PHASE_CHANGED", "SOURCE_REJECTED", "SEARCH_PLANNED")]
    chosen = st.multiselect("Event types", types, default=default)
    st.dataframe(pd.DataFrame([{"time": e.ts.strftime("%H:%M:%S"), "#": e.seq, "event": e.type.value, "message": e.message}
                               for e in r.events.events if e.type.value in chosen]),
                 hide_index=True, width="stretch", height=520)

with tabs[4]:
    c1, c2, c3 = st.columns([2, 1, 1])
    hid = c1.selectbox("Hypothesis", [None] + [h.id for h in rep.hypotheses], format_func=lambda x: "All" if x is None else x,
                       index=1 + [h.id for h in rep.hypotheses].index(rep.leading_hypothesis) if rep.leading_hypothesis else 0)
    show_ev = c2.checkbox("Evidence nodes", True)
    show_src = c3.checkbox("Source nodes", True)
    st.graphviz_chart(to_dot(g, focus_nodes(g, hid, show_ev, show_src)), width="stretch")
    st.caption("green = supports · red = contradicts · dotted = derived from (provenance) · diamond = verified inference")

with tabs[5]:
    rows = []
    for s in g.sources.values():
        a = g.assessments.get(s.id)
        root = g.root_of.get(s.id, s.id)
        rows.append({"id": s.id, "title": s.title, "url": s.url, "type": a.source_type if a else "", "primary": bool(a and is_primary(a)),
                     "conflict of interest": a.conflict_of_interest if a else None, "published": s.published_at,
                     "origin": s.search_origin, "extracted": s.extracted, "independent root": root if root != s.id else "(root)"})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={"url": st.column_config.LinkColumn("url")})
    st.markdown(f"**{rep.raw_source_count} raw sources with evidence → {rep.independent_root_count} independent roots**")
    for cl in rep.clusters:
        st.markdown(f"- Cluster rooted at `{cl['root']}` ({cl['root_title'][:60]}): {len(cl['members'])} sources")
    with st.expander("Citations"):
        for c in rep.citations:
            st.markdown(f"[{c.n}] [{c.title}]({c.url}) — {c.publisher}, published {c.published_at or 'unknown'}")
