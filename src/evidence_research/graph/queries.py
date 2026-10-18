"""Read-side graph queries for the UI: a focused hypothesis → inference → claim → evidence → source view."""

from __future__ import annotations

import html

from .evidence_graph import EvidenceGraph, Link

_STYLE = {
    "hypothesis": 'shape=box style="rounded,filled" fillcolor="#dbeafe"',
    "inference": 'shape=diamond style=filled fillcolor="#fef3c7" fontsize=9',
    "claim": 'shape=box style="filled" fillcolor="#f1f5f9"',
    "evidence": 'shape=note fontsize=9',
    "source": 'shape=cylinder style=filled fillcolor="#ecfccb" fontsize=9',
    "study": 'shape=folder style=filled fillcolor="#ede9fe" fontsize=9',
    "result": 'shape=note style=filled fillcolor="#f5f3ff" fontsize=9',
}
_EDGE = {
    Link.SUPPORTS.value: 'color="#16a34a"', Link.CONTRADICTS.value: 'color="#dc2626" penwidth=2',
    Link.QUALIFIES.value: 'color="#a3a3a3" style=dashed', Link.DERIVED_FROM.value: 'color="#64748b" style=dotted',
    Link.PREMISE_OF.value: 'color="#0369a1"', Link.TEMPORAL_VERSION_OF.value: 'color="#7c3aed" style=dashed',
    Link.EXTRACTED_FROM.value: 'color="#64748b" style=dotted', Link.SUPPORTS_HYPOTHESIS.value: 'color="#16a34a" penwidth=1.5',
    Link.CHALLENGES_HYPOTHESIS.value: 'color="#dc2626" penwidth=1.5', Link.REQUIRED_FOR.value: 'color="#0f172a" penwidth=2.5',
    Link.DUPLICATES.value: 'color="#7c3aed" style=dotted', Link.REPLICATES.value: 'color="#16a34a" style=bold',
    Link.FAILS_TO_REPLICATE.value: 'color="#dc2626" style=bold', Link.PRODUCES.value: 'color="#7c3aed"',
    Link.EXTRACTED_AS.value: 'color="#7c3aed" style=dashed',
}


def _label(text: str, n: int = 38) -> str:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) > n:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return html.escape("\\n".join(lines[:4]) + ("…" if len(lines) > 4 else ""), quote=True)


def focus_nodes(g: EvidenceGraph, hypothesis_id: str | None, show_evidence: bool = True, show_sources: bool = True,
                max_claims: int = 8) -> set[str]:
    nodes: set[str] = set()
    hyps = [hypothesis_id] if hypothesis_id else list(g.hypotheses)
    claims: list[str] = []
    for hid in hyps:
        nodes.add(hid)
        for inf in g.inferences_for(hid):
            nodes.add(inf.id)
            claims += inf.premise_ids
        for req in g.requirements_for(hid):
            claims += [c.id for c in g.claims_for_requirement(req.id)]
    seen = []
    for c in claims:
        if c in g.claims and c not in seen:
            seen.append(c)
    seen.sort(key=lambda cid: -g.claims[cid].importance)
    for cid in seen[:max_claims]:
        nodes.add(cid)
        for ev in g.evidence_for(cid):
            if show_evidence:
                nodes.add(ev.id)
            if show_sources:
                nodes.add(ev.source_id)
            if ev.result_id and ev.result_id in g.results:
                nodes.add(ev.result_id)
                nodes.add(g.results[ev.result_id].study_id)
    for rel in g.study_relations.values():  # replication graph between studies already shown
        if rel.to_study_id in nodes:
            nodes.add(rel.from_study_id)
    return nodes


def to_dot(g: EvidenceGraph, nodes: set[str]) -> str:
    lines = ['digraph G {', 'rankdir=LR; bgcolor="transparent"; node [fontname="Helvetica" fontsize=10]; edge [fontsize=8];']
    for n in nodes:
        data = g.g.nodes[n]
        kind = data.get("kind", "")
        if kind == "claim":
            c = g.claims[n]
            text = f"{n}\\n{c.natural_language}\\nP={c.truth_probability:.2f} S={c.evidence_sufficiency:.2f}"
        elif kind == "hypothesis":
            h = g.hypotheses[n]
            text = f"{n}: {h.text}\\nP={h.posterior_probability:.2f} ({h.status})"
        elif kind == "inference":
            i = g.inferences[n]
            text = f"{i.inference_type} · {i.status}\\nscore {i.verifier_score:.2f}"
        elif kind == "source":
            s = g.sources[n]
            root = g.root_of.get(n, n)
            text = f"{s.publisher}\\n{'root' if root == n else 'derived from ' + root}"
        else:
            text = data.get("label", n)
        lines.append(f'"{n}" [label="{_label(text) if kind not in ("claim", "hypothesis") else html.escape(text, quote=True)}" {_STYLE.get(kind, "")}];')
    for a, b, d in g.g.edges(data=True):
        if a in nodes and b in nodes:
            t = d.get("type", "")
            if t == Link.CONCLUDES.value:
                style = 'color="#16a34a"' if d.get("direction") == "supports" else 'color="#dc2626"'
            else:
                style = _EDGE.get(t, 'color="#94a3b8"')
            lines.append(f'"{a}" -> "{b}" [label="{t.lower()}" {style}];')
    lines.append("}")
    return "\n".join(lines)
