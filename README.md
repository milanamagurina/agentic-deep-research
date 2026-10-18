# Probabilistic Evidence Research

Most deep-research agents ask:

> "What information can I find about this question?"

We ask:

> "What do we currently believe, what evidence supports it, what would falsify it,
> and which missing piece of evidence is most likely to change the conclusion?"

An auditable research process for the Nebius × Tavily **Agentic Deep Research** challenge. Inference runs on
**Nebius Token Factory** (OpenAI-compatible API, role-routed models, `reflection/beam` supported as the reasoning
model) and retrieval on **Tavily** (search → screen → extract selected pages only).

```
LLM proposes.  Verifier checks.  Evidence vault remembers.  Probability engine updates.  Policy engine decides what to research next.
```

**The core thesis:** the LLM may propose hypotheses, interpretations and reasoning steps, but it is not allowed to
establish truth by itself. Confidence comes from source-grounded evidence, provenance, independence, lineage,
study quality, verified inference, contradiction and temporal consistency, aggregated by code.

Ten websites repeating one press release are not ten pieces of evidence. Neither are an arXiv preprint and its
conference and journal versions. This system detects both, shows it, and changes its confidence because of it.

---

## Quick start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env              # fill NEBIUS_API_KEY and TAVILY_API_KEY

uv run pytest                     # 85 offline tests: stubbed model and Tavily, real pipeline
uv run python app.py --check      # live connectivity: one Token Factory call, one Tavily search + extract
uv run streamlit run ui/streamlit_app.py          # the jury demo
uv run jupyter lab notebooks/debug.ipynb          # developer debug view of the same engine
```

Re-check every citation of a saved report against the live web pages (the judges' test, done for all of them):

```bash
uv run python -m evidence_research.verification.citation_audit report.json
```

No keys? Two **synthetic** offline scenarios (fictional entities, scripted model, fake corpus, labelled as such in
every output) exercise the whole real pipeline:

```bash
uv run python app.py --demo business      # "Does Acme Fleet have strong product-market fit?"
uv run python app.py --demo science       # "Does the MemoLoop app materially improve university exam scores?"
uv run python -m evidence_research.evaluation.benchmark     # hackathon evaluation + baseline comparison
```

Live CLI:

```bash
uv run python app.py "Does Duolingo have strong product-market fit?" --depth fast --md report.md --json report.json
uv run python app.py "your question" --baseline          # naive search + one summary, for comparison
uv run python -m evidence_research.llm.gateway --list-models
```

The report goes to stdout and the research trace to stderr. Sessions, every event and graph snapshots are stored in
SQLite (`data/research.sqlite`). Without uv: `pip install -e . pytest` (or `PYTHONPATH=src python app.py …`).

---

## Architecture

A modular monolith. Each box is a module behind a narrow interface; NetworkX, SQLite and the model/search clients
can later be swapped for Neo4j, Postgres or a queue without touching research logic.

```
USER QUESTION
 │
QUESTION ANALYZER ──────────── entities, scope, hidden assumptions, dimensions
 │
HYPOTHESIS GENERATOR ───────── competing, distinguishable hypotheses + a null hypothesis
 │
EVIDENCE REQUIREMENTS ──────── what each hypothesis needs before it can be "supported"
 │
ACTIVE RESEARCH GRAPH ◄──────── small working context rebuilt each round from the LONG-TERM EVIDENCE VAULT
 │
RESEARCH POLICY ENGINE ─────── every agent bids "utility of acting now"; the top bids run
 ├── GeneralResearcher        ├── PrimarySourceResearcher   ├── IndependenceResearcher
 ├── ContradictionResearcher  ├── GapResearcher             ├── ReplicationResearcher
 └── AdversarialResearcher    └── (Synthesis bid: readiness to stop, shown for transparency)
 │
TAVILY SERVICE ─── search (advanced) → rank → SCREENING (include / exclude / uncertain, reasons kept) → extract
 │
SOURCE STORE ─── authority · expertise · transparency · editorial · primary · independence · conflict of interest
 │
SCIENTIFIC SOURCE RESOLUTION ─ Document → Study → Result; preprint / conference / journal = ONE work
 │                              study quality (design, n, control, randomization, preregistration, attrition, COI)
 │                              replication graph (REPLICATES, FAILS_TO_REPLICATE, CORRECTS, RETRACTS …)
CLAIM EXTRACTION ───────────── atomic claims; excerpts LOCATED in the page by code (never the model's string);
 │                              reported speech split into attribution + fact
CLAIM NORMALIZATION ────────── canonical key (numbers, units, currency, fiscal year) → model SAME/DIFFERENT
 │
EVIDENCE DAG ───────────────── evidential · logical · provenance · semantic links, never mixed
 │
 ├── EVIDENCE JUDGE (stance)   ├── CONTRADICTION / TEMPORAL VALIDATOR   ├── LOGIC RULES R1-R3
 └──────────────┬──────────────┘
INFERENCE VERIFIER ── proposer and verifier are separate calls; DELETION TEST finds necessary premises
 │
PROBABILITY ENGINE ─────────── heuristic likelihood ratios, provenance-cluster-aware Bayesian odds update
 │
UNCERTAINTY ANALYZER ───────── truth posterior · evidence sufficiency · inference validity (never merged)
 │
GAP ENGINE ─────────────────── 13 typed gaps ranked by heuristic expected research value
 │
STOP POLICY ── research ───► back to the policy engine
 │ stop
SYNTHESIS → CITATION VALIDATION → FINAL REVIEW → REPORT
```

### Who does what

| LLMs do (semantic, typed output only) | Code does (control) |
|---|---|
| analyze the question, propose hypotheses and requirements | own `ResearchSession`, the phase machine and the budgets |
| write queries for the agent that won the bid | compute bids, pick agents, dedup queries and URLs |
| screen search results, classify document type | keep every screening decision; select what to extract |
| extract claims and excerpts; review study methods and results | **locate every excerpt in the page**; store unverifiable ones as UNVERIFIED |
| classify stance, match claims, propose and verify inferences, answer the deletion test | lineage, version resolution, study-quality scores, every probability |
| rate a gap's decision impact; write the final prose | rank gaps, decide to stop, **delete ungrounded sentences** |

No model is ever asked for a confidence number. Every state-changing output is a Pydantic schema; hidden
reasoning (`<think>`) is stripped and never stored. Web text is evidence, not instructions, in every prompt.

### Research objects

`ResearchQuestion (session) · Hypothesis · EvidenceRequirement · Entity · Source · Document · Study · StudyResult ·
Evidence · Claim · Inference · NecessityAssessment · ResearchGap · ResearchTask · AgentBid · ResearchEvent`

A paper is not evidence. `Document -DESCRIBES-> Study -PRODUCES-> Result -EXTRACTED_AS-> Evidence -SUPPORTS-> Claim`.
A news article quoting a CEO supports *"the CEO stated X"* strongly and *X* only weakly (directness capped at 0.35).

### Evidence DAG (`graph/evidence_graph.py`)

| family | links | used as support? |
|---|---|---|
| evidential | Evidence `SUPPORTS / CONTRADICTS / QUALIFIES` Claim | yes |
| logical | Claim `REQUIRED_FOR / SUPPORTS_HYPOTHESIS / CHALLENGES_HYPOTHESIS` Hypothesis (only after verification) | yes |
| provenance | `DESCRIBES, PRODUCES, EXTRACTED_AS, EXTRACTED_FROM, CITES, DERIVED_FROM, DUPLICATES`, `REPLICATES, FAILS_TO_REPLICATE, EXTENDS, REANALYZES, CORRECTS, RETRACTS` | shapes weights |
| semantic | `ABOUT, RELATED_TO` | **never** (tested) |

Data-Vault style: hubs (stable IDs), links, and append-only satellites `SAT_SOURCE_ASSESSMENT`, `SAT_STUDY_ASSESSMENT`,
`SAT_CLAIM_CONFIDENCE`, `SAT_EVIDENCE_SCORE`, `SAT_HYPOTHESIS_POSTERIOR`, `SAT_SCREENING`. **History is never overwritten**.
Claims are bitemporal: valid time (true in the world) vs observation time (when we learned it). "CEO = Alice (2025)" and
"CEO = Bob (2026)" are temporal versions, not a contradiction; undated differing values are not called contradictions.

### Long-term vault vs active graph

The **vault** keeps everything: every source, search, screening decision (including exclusions: negative provenance),
extraction (including unverified ones), rejected inference, confidence update and event. The **active graph**
(`graph/active.py`) is rebuilt from it after every round: active hypotheses, the ~14 claims that carry the argument,
their strongest evidence, critical contradictions, top gaps and recent updates. Models only see the active graph.

### Source independence and scientific resolution

**Lineage** (`evidence/lineage.py`) uses these signals, combined noisy-OR:
- explicit link to the parent URL;
- same publisher (except on multi-publisher hosts such as sec.gov, arXiv or press wires);
- an explicit report of the parent's announcement;
- 6-word text reuse;
- shared quotations (quoted *titles* of cited works don't count);
- timing.

**Resolver** (`science/resolver.py`) matches versions of one work by arXiv ID, DOI, explicit cross-reference, title
similarity and author overlap. Two groupings are reported side by side: **URLs → publication families → independent
evidence roots**.

**Is arXiv trustworthy?** arXiv is a *preprint server*: moderated, **not peer reviewed**. It is classified as
`preprint` (moderate authority, low editorial score). A preprint earns weight through its *study*: design, sample,
controls, preregistration, conflicts of interest and replication. If the same work later appears at a conference or in
a journal, all versions collapse into one research lineage, which counts once and records the peer-reviewed status.
Peer review alone is not decisive either: a peer-reviewed n=12 study without a control group scores 0.15.

### Dynamic agent selection (`orchestration/policy.py`)

There is no fixed planner → researcher → writer chain. Each round, each capability bids a heuristic utility from the
active graph, mostly the value of the gaps it is built to close:
- **PrimarySource:** no primary source, unverified extraction.
- **Independence:** source dependence.
- **Contradiction:** conflicting evidence.
- **Replication:** no or failed replication, missing methods, small samples.
- **Gap:** missing requirements, weak inferences.
- **Adversarial:** an unchallenged leading hypothesis.

An agent whose last task found nothing new is discounted ×0.5. The top two bids run. Every bid and its reasons are
in the trace, e.g. `Next agent: ReplicationResearcher (utility 0.86). Reason: [FAILED_REPLICATION] …`.

---

## Probability engine (all heuristic, all in `config.py`)

> All values are **model-estimated evidence beliefs based on explicit heuristic assumptions**, not calibrated
> probabilities. Future calibration could use Brier score, ECE and labelled fact-verification datasets.

**Evidence strength.** Dimensions are kept separate and shown in the UI. Only their product picks a likelihood ratio:

```
effective source quality = reliability(source, claim category) × (0.4 + 0.6 · study quality) × replication factor × result quality
strength = p_stance × (0.4 + 0.6 · directness) × (0.5 + 0.5 · temporal relevance) × effective source quality × (0.5 + 0.5 · extraction confidence)
```

| bucket (strength ≥) | 0.70 very strong | 0.50 strong | 0.30 moderate | 0.12 weak | below: neutral |
|---|---|---|---|---|---|
| support LR | 8 | 4 | 2 | 1.25 | 1 |
| contradiction LR | 0.125 | 0.25 | 0.5 | 0.8 | 1 |

**Bayesian update:**
- `posterior odds = prior odds × Π LR`, computed in log space.
- **Correlated evidence:** within one independent root, the strongest support and the strongest contradiction count
  in full, and each derivative adds 15% of its log-LR (`DEPENDENT_EVIDENCE_DISCOUNT`).
- Across roots, contributions combine normally.

**Replication factor:** ×1.2 per replication, ×0.6 per failed replication, ×0.8 per correction, and 0 if retracted.

**Credibility is claim-dependent.** A filing is strong evidence for reported revenue and weak evidence for customer
satisfaction. SEC filings are typed `company_filing`: legally attested, but self-reported.

**Four quantities, never merged:**
- **Truth posterior:** from the Bayesian update above.
- **Evidence sufficiency:** for claims, `(1 − 0.5^roots) × (0.7 + 0.3 · primary) × (0.5 + 0.5 · directness)`. For
  hypotheses, half requirement coverage and half the weakest accepted premise.
- **Inference validity:** from the verifier's verdict.
- **Importance:** research priority only. A test asserts it never touches truth.

**Research priority (heuristic expected research value)** = importance × uncertainty × decision impact × searchability,
where uncertainty = max(1 − |2P − 1|, 1 − sufficiency). A confident claim resting on one study is still uncertain.

**Inference verification.** The proposer and the verifier are separate calls. Verdicts map to scores: valid 0.9,
plausible 0.65, weak 0.35, invalid 0.05, and an inference is accepted at ≥ 0.6. Code rules apply on top:
- **R1:** premises must be established (posterior ≥ 0.55).
- **R2:** premises resting only on one *interested* root are capped at weak.
- **R3:** causal or abductive inferences with confounders still open need evidence.

Missing premises and confounders become `WEAK_INFERENCE` gaps.

**Deletion test.** For the leading hypothesis, each accepted premise is removed in turn, and the model judges whether
the remaining premises still justify the conclusion. It is recorded as a *model-based necessity assessment*.
Necessary premises get `REQUIRED_FOR` links and research priority.

**Gap types:** NO_PRIMARY_SOURCE, NO_INDEPENDENT_SOURCE, SOURCE_DEPENDENCE, CONTRADICTORY_EVIDENCE, TEMPORAL_CONFLICT,
WEAK_INFERENCE, MISSING_REQUIRED_DIMENSION, OUTDATED_EVIDENCE, NO_REPLICATION, FAILED_REPLICATION,
MISSING_METHOD_INFORMATION, INSUFFICIENT_SAMPLE, UNVERIFIED_EXTRACTION.

**Stop policy:** budget → evidence sufficient with no critical contradiction → posterior convergence (< 0.03 for 2
rounds) → diminishing returns (no new independent root) → only unresolvable gaps left → no agent bid above threshold.
Final states: `SUPPORTED · LIKELY · CONTESTED · INSUFFICIENT_EVIDENCE · REFUTED · UNRESOLVABLE_WITH_PUBLIC_DATA`.
"We don't know" is a valid answer.

**Citation guarantee:** final statement → claim IDs → evidence IDs → exact excerpt → source. Before rendering, the
verifier requires:
- verified, non-neutral evidence whose excerpt occurs verbatim in a stored page;
- every number in the sentence to be present in that evidence;
- no free-form URL.

Failing sentences are removed and logged; the system never "fixes" them. A final review re-checks the chain.

---

## What the synthetic scenarios show (`examples/`)

**Business** ([report](examples/business_report.md), [trace](examples/business_trace.txt)):
1. Hypotheses and requirements come first; sources are screened before anything is extracted.
2. Five URLs support "revenue grew 70%". Four derive from one press release, so there are **2 independent roots**,
   counting the registry filing.
3. The verifier rejects "70% growth ⇒ PMF" (confounders: discounting, acquisitions). "95% retention ⇒ PMF" is
   rejected by R2, because only the company says it.
4. The policy engine picks an adversarial researcher and a gap researcher. They find churn reviews and an
   independent 81% retention benchmark, and the 95% claim falls from 0.71 to 0.45 (`contested`).
5. The 2021 customer count is a temporal version, not a contradiction. A prompt-injection line on a review page has
   no effect.
6. Final status: **LIKELY**: "growth is real but retention is weak". Two invented draft sentences are removed by the
   citation verifier.

**Science** ([report](examples/science_report.md), [trace](examples/science_trace.txt)):
1. An arXiv-style preprint, a conference paper and a journal article are resolved as **one work** (same arXiv ID plus
   explicit cross-reference). A campus news story and a blog derive from the preprint: **6 URLs → 4 publication
   families → 2 independent roots**.
2. The original RCT (n=412, authors are co-founders) lifts "material effect" from 0.35 to 0.68. A peer-reviewed pilot
   (n=12, no control, high attrition) scores quality 0.15, and its inference is rejected.
3. The policy engine picks gap and adversarial researchers. They find a preregistered multi-site replication
   (`REPLICATES`, 0.12 SD) and a preregistered direct replication with no significant effect (`FAILS_TO_REPLICATE`,
   0.02 SD).
4. "Material effect" falls to 0.01. "Small positive effect" leads at 0.85, and the final status is **LIKELY**.

## Hackathon evaluation (`python -m evidence_research.evaluation.benchmark`)

This is a small, synthetic evaluation; no statistical claims are made. All 23 behaviour checks pass: 14 for the
business success scenario (section 42) and 9 for the scientific scenario (section 43). Lineage accuracy against the
constructed source families is 1.0 in both.

Comparison with the naive baseline (Tavily → one LLM summary → cite everything) on the same corpora:

| | business: baseline | business: system | science: baseline | science: system |
|---|---|---|---|---|
| cited "sources" | 6 | 8 | 6 | 8 |
| actual independent roots | 3 | 5 | 3 | 4 |
| contradictions discovered | 0 | 2 | 0 | 3 |
| research gaps discovered | 0 | 13 | 0 | 18 |
| unsupported statements removed | 0 | 2 | 0 | 1 |
| abstains where evidence is missing | no | yes | no | yes |

The baseline repeats the contradicted 95% retention figure, and "confirmed by 6 independent sources" for an
unreplicated trial. The Brier score on a handful of claims that are true *by construction* (0.11 in both scenarios) is
a sanity check, not calibration. `--live` runs [examples/sample_questions.md](examples/sample_questions.md) against the
real APIs, producing metrics only.

## UI (`streamlit run ui/streamlit_app.py`)

The header shows the evidence status, the truth posterior and sufficiency of the main surviving hypothesis, and
independent roots (with URLs and families). A live trace streams while the run executes.

| tab | contents |
|---|---|
| Overview | **Minto pyramid**: the answer first, then MECE reasons, then the facts under each; caveats, what would change our mind, and the decision trace |
| Citation Check | **every** cited source and **every** quote the report relies on, each link opening the page at that text; a one-click button re-fetches all pages and confirms each quote is still there |
| Hypotheses | prior and posterior history, deletion-test results, accepted and rejected inferences |
| Claims & Evidence | per claim: posterior, sufficiency, inference validity, raw sources vs roots, support, contradiction, missing; every evidence line with its quality dimensions |
| Scientific Studies | versions, design, n, peer review, quality, replication graph, verified results, methodological notes |
| Source Lineage | URLs → families → independent roots, every dependency with its signals |
| Research Trace | filterable auditable events, plus agent bids per round |
| Evidence DAG | focused hypothesis → inference → claim → evidence → source / study view |
| Sources | screening decision and reasons (including exclusions), type, independence, conflict of interest, root |

## Docker

```bash
docker build -t evidence-research .
docker run --rm -p 8501:8501 --env-file .env evidence-research          # UI on :8501
docker run --rm -e EVIDENCE_NO_DOTENV=1 evidence-research pytest -q     # tests, no keys
docker run --rm evidence-research python app.py --demo science
```

## Shared engine, two front-ends

No business logic lives in either front-end; both call `evidence_research.runtime.research`.

```
         core Python package (evidence_research)
          same research engine, one source of truth
             /                               \
   notebooks/debug.ipynb              ui/streamlit_app.py
   developer debugging                the jury demo
   (search, claims, graph,            (answer, live trace, claims,
    Bayesian steps, lineage)           clickable + re-checkable citations)
```

## Layout

```
app.py                       CLI: live, --demo business|science, --baseline, --check
ui/streamlit_app.py          9-tab jury demo UI (incl. Citation Check)
notebooks/debug.ipynb        developer debug notebook (same engine)
src/evidence_research/
  config.py models.py runtime.py
  orchestration/  orchestrator, policy (agent bids), state_machine, budget (synthesis reserve), stop_policy
  llm/            gateway (AsyncOpenAI → Token Factory, roles, structured output, repair), prompts (one per task/agent)
  retrieval/      tavily_client, service, screening, source_ranker, url_normalizer
  research/       analysis (question + hypotheses), query_planner (per agent), gap_analyzer
  evidence/       extractor (ingestion), excerpts (locate/align, passage selection), claim_normalizer,
                  source_classifier, lineage, temporal
  science/        resolver (versions of one work), quality (study + replication), reviewer (Document/Study/Result)
  graph/          evidence_graph (vault, NetworkX), active (working context), repository (SQLite), queries (UI)
  verification/   entailment (stance judge), inference_verifier, necessity (deletion test), contradiction,
                  citation_verifier, citation_audit (live re-check of every quote)
  probability/    evidence_score, bayesian, uncertainty, engine (recompute + evidence-quality breakdown)
  synthesis/      report, serializer
  observability/  events (audit trail)
  demo/           base, business, science (SYNTHETIC)
  evaluation/     baseline, benchmark
tests/            85 offline tests
examples/         sample questions, synthetic reports and traces, live run notes
```

## Status and limitations

- **Verified live** on 2026-10-18 with MiniMax-M3 (fast role) and `reflection/beam` (reasoning role) on a business and
  a scientific question; reports, traces and what the live runs changed are in [examples/live_runs.md](examples/live_runs.md).
  Real models phrase things differently from the scripted ones. The matcher, judge and verifier prompts are where
  tuning pays off.
- **Heuristic numbers:** likelihood ratios, source priors, study-design priors and agent utilities are hand-set,
  documented heuristics, not calibrated or audited.
- **Lineage is text- and metadata-based.** It misses paraphrased derivation and syndication deals, and a company's
  own documents (10-K, press releases) are correctly *one* interested root, which can make independent evidence look scarce.
- **Not built (stretch):** perspective decomposition, a dedicated NLI model, calibration, cross-session source
  reputation, and monitoring re-runs.
