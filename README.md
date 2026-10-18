# Probabilistic Evidence Research

Most deep-research agents ask:

> "What information can I find about this question?"

We ask:

> "What do we currently believe, what evidence supports it, what would falsify it,
> and which missing piece of evidence is most likely to change the conclusion?"

Built for the Nebius × Tavily **Agentic Deep Research** challenge. Inference runs on **Nebius Token Factory**
(OpenAI-compatible API) and retrieval on **Tavily** (search, then extraction of selected pages only).

```
LLM proposes.  Verifier checks.  Evidence graph remembers.  Probability engine updates.  Gap engine decides what to research next.
```

Ten websites repeating the same press release are **not** ten independent pieces of evidence. This system
knows that, shows it, and changes its confidence because of it.

---

## Quick start

Requires Python 3.12+.

```bash
uv sync                     # or: pip install -e . pytest
cp .env.example .env        # fill NEBIUS_API_KEY and TAVILY_API_KEY

uv run pytest               # 52 offline tests, no API calls
uv run python app.py --check                     # live connectivity: Token Factory + Tavily
uv run streamlit run ui/streamlit_app.py         # the demo UI
```

No keys? Everything below also runs on an **offline synthetic scenario** (a fictional company, a scripted
model and a fake corpus, clearly labelled as such):

```bash
uv run python app.py --demo                      # full research run, report on stdout, trace on stderr
uv run python -m evidence_research.evaluation.benchmark   # benchmark + baseline comparison
```

CLI for real questions:

```bash
uv run python app.py "Does Company X have strong product-market fit?" --depth standard --md report.md --json report.json
uv run python app.py "Does Company X have strong product-market fit?" --baseline   # naive search + one synthesis, for comparison
uv run python -m evidence_research.llm.gateway --list-models                        # Token Factory model IDs
```

Without uv: `pip install -e . pytest`, then drop the `uv run` prefix. Without installing: `PYTHONPATH=src python app.py --demo`.

---

## Architecture

A modular monolith. Each box is a module with a narrow interface, so the in-memory graph, SQLite and the
model/search clients can later be swapped (Neo4j, Postgres, a queue) without touching the research logic.

```
USER QUESTION
     │
QUESTION ANALYZER ─────────────── llm: entities, scope, hidden assumptions, dimensions
     │
HYPOTHESIS GENERATOR ──────────── llm: 3-5 competing hypotheses + null hypothesis, heuristic priors
     │
EVIDENCE REQUIREMENTS ─────────── what each hypothesis would need to be established
     │
RESEARCH PLANNER / SCHEDULER ──── discovery | gap-targeted | adversarial queries (parallel, budgeted)
     │
TAVILY SERVICE ────────────────── search (advanced) → rank → dedup → select → extract (advanced)
     │
SOURCE STORE + ASSESSMENT ─────── authority, expertise, transparency, editorial, primary, conflict of interest
     │
CLAIM EXTRACTOR ───────────────── llm: atomic claims + verbatim excerpts;  code: rejects non-verbatim excerpts,
     │                                 splits reported speech into ATTRIBUTION + FACT claims
CLAIM NORMALIZER ──────────────── canonical key (numbers/units/currency/fiscal year) → llm SAME/DIFFERENT
     │
PROVENANCE / LINEAGE ──────────── link, text reuse, shared quotes, publisher, timing → independent roots
     │
EVIDENCE GRAPH (NetworkX) ─────── hubs · typed links · append-only satellites (confidence history)
     │
  ┌──┴───────────────────┐
EVIDENCE JUDGE          CONTRADICTION / TEMPORAL VALIDATOR
llm: stance category    code: same slot, overlapping vs disjoint valid time
  └──┬───────────────────┘
INFERENCE PROPOSER → INFERENCE VERIFIER ── llm proposes, separate llm call judges, code rules R1-R3 gate
     │
PROBABILITY ENGINE ────────────── heuristic likelihood ratios, cluster-aware Bayesian odds update
     │
UNCERTAINTY ENGINE ────────────── truth posterior · evidence sufficiency · inference validity
     │
GAP ENGINE ────────────────────── typed gaps ranked by heuristic expected information value
     │
STOP POLICY ── enough? ── no ──► next research round (DISCOVERY)
     │ yes
SYNTHESIS ─────────────────────── llm prose, each sentence tagged with claim IDs
     │
CITATION VERIFIER → FINAL REVIEW → VERIFIED REPORT
```

### Who does what

| LLMs do (semantic tasks) | Code does (control tasks) |
|---|---|
| decompose the question, generate hypotheses | own the `ResearchSession` state and the phase machine |
| write search queries (discovery, gap, adversarial) | dedup URLs, select what to extract, enforce budgets |
| extract atomic claims with excerpts | **verify every excerpt verbatim** against the retrieved page |
| classify stance (`supports/contradicts/qualifies/neutral`, plus a strength *category*) | map categories to numbers; count sources and **independent roots** |
| propose inferences; a separate call verifies them | apply logic rules, accept/reject, create gaps from missing premises |
| rate a gap's decision impact (low/medium/high) | compute every probability, sufficiency and priority |
| write the final prose | **delete any sentence** that is not grounded; render citations from the source store only |

No model is ever asked "how confident are you from 0 to 100". Hidden reasoning (`<think>` blocks) is stripped
and never stored; the audit trail contains structured decisions only.

### Explicit state machine

`INITIALIZED → QUESTION_ANALYSIS → HYPOTHESIS_GENERATION → DISCOVERY → EVIDENCE_COLLECTION → CLAIM_VERIFICATION →
ADVERSARIAL_RESEARCH → GAP_ANALYSIS → (DISCOVERY … | SYNTHESIS) → FINAL_REVIEW → COMPLETED`. Transitions are
validated in `orchestration/state_machine.py`; an illegal transition raises.

---

## The evidence model

**Data-Vault style graph** (`graph/evidence_graph.py`):
- *Hubs*: Source, Claim, Evidence, Hypothesis, Requirement, Inference, Gap.
- *Links*: `SUPPORTS`, `CONTRADICTS`, `QUALIFIES`, `DERIVED_FROM`, `DEPENDS_ON`, `ABOUT`, `TEMPORAL_VERSION_OF`,
  `PREMISE_OF`, `CONCLUDES`.
- *Satellites*: time-stamped observations (assessments, posteriors, aliases, verifications). **Confidence history
  is never overwritten**; each update appends an observation.

**Claims never carry URLs.** `Source → Evidence (verbatim excerpt, stance, directness, temporal relevance) → Claim`.

**Reporting vs fact.** "Reuters: the CEO said revenue grew 200%" creates two claims: *the CEO stated that revenue grew
200%* (strongly evidenced) and *revenue grew 200%* (evidence capped at directness 0.35).

**Bitemporal.** Claims have a *valid time* (when true in the world) and evidence an *observation time*. "CEO = Alice
(2025)" and "CEO = Bob (2026)" are temporal versions, not a contradiction.

**Lineage / independence** (`evidence/lineage.py`). The signals are combined noisy-OR: explicit link (0.6), same
publisher (0.5), attribution to the parent (0.35), 6-word text reuse (up to 0.8), identical quotations (0.3 each)
and timing (0.1). Pairs at or above 0.5 are dependent. Clusters are connected components, and each cluster has
one root. The UI and the report show **raw sources, independent roots and clusters** side by side.

---

## Probability engine (all heuristic, all in `config.py`)

> All probability values are **heuristic, model-estimated evidence beliefs**, not scientifically calibrated
> probabilities. No calibration experiments have been run. The UI labels them accordingly.

**Evidence strength** for one evidence item and one claim:

```
s = p_stance × (0.4 + 0.6·directness) × (0.5 + 0.5·temporal_relevance) × reliability(source, claim) × (0.5 + 0.5·extraction_confidence)
```

`p_stance` maps the judge's category: explicit 0.95 · strong 0.80 · partial 0.60 · weak 0.40.
`reliability` is **claim-dependent**. It combines the source's dimensions, penalizes conflict of interest by claim
category, and applies a fit factor. For example, a filing is strong evidence for official revenue and weak
evidence for customer satisfaction.

**Heuristic evidence likelihood ratios** by strength bucket:

| bucket | s ≥ | support LR | contradiction LR |
|---|---|---|---|
| very strong | 0.70 | 8 | 0.125 |
| strong | 0.50 | 4 | 0.25 |
| moderate | 0.30 | 2 | 0.5 |
| weak | 0.12 | 1.25 | 0.8 |
| neutral | — | 1 | 1 |

**Update.** `posterior_odds = prior_odds × Π LR`, computed in log space. **Correlated evidence:** evidence is
grouped by independent root. In each root group, the strongest support and the strongest contradiction count in
full. Every further item from the same root adds only `DEPENDENT_EVIDENCE_DISCOUNT` (0.15) of its log-LR.

**Three dimensions, never merged:**
- **Truth posterior**: as above.
- **Evidence sufficiency**: for claims, `(1 − 0.5^roots) × (0.7 + 0.3·has_primary) × (0.5 + 0.5·max_directness)`.
  For hypotheses, 0.5 × requirement coverage + 0.5 × the sufficiency of the weakest accepted premise.
- **Inference validity**: the mean verifier score of the accepted inferences.

**Importance never touches truth.** Importance only drives research priority:

```
priority (heuristic expected information value) = importance × (1 − |2P − 1|) × decision_impact × searchability
```

A test asserts that changing a claim's importance leaves its posterior unchanged.

**Inference verification** (`verification/inference_verifier.py`). Verdict valid 0.9 · plausible 0.65 · weak 0.35 ·
invalid 0.05. An inference is accepted at ≥ 0.6, plus these code rules:
- **R1:** every premise must be established (posterior ≥ 0.55).
- **R2:** premises that rest only on one *interested* root (self-reported) are capped at "weak".
- **R3:** a causal or abductive inference with confounders not ruled out needs evidence.

Missing premises and confounders become `WEAK_INFERENCE` gaps, and those gaps drive the next searches.

**Gap types:** NO_PRIMARY_SOURCE, NO_INDEPENDENT_SOURCE, CONTRADICTORY_EVIDENCE, TEMPORAL_CONFLICT,
MISSING_REQUIRED_DIMENSION, WEAK_INFERENCE, SOURCE_DEPENDENCE, OUTDATED_EVIDENCE.

**Stop policy** (`orchestration/stop_policy.py`), checked in this order:
1. **Budget:** searches, extractions, model calls or iterations exhausted.
2. **Success:** every critical claim has sufficiency ≥ 0.70 and no high-importance contradiction is open.
3. **Convergence:** beliefs moved less than 0.03 for 2 iterations.
4. **Diminishing returns:** a round produced no new independent root.
5. **Unresolvable:** only gaps already researched repeatedly without result remain.

Final statuses: `SUPPORTED · LIKELY · CONTESTED · INSUFFICIENT_EVIDENCE · REFUTED · UNRESOLVABLE_WITH_PUBLIC_DATA`.
"Insufficient evidence" is a valid result, not a failure.

**Citation guarantee.** Every report sentence must cite claim IDs. Every claim needs non-neutral evidence whose
excerpt is found verbatim in a stored source. Every number in the sentence must appear in the referenced claims,
and free-form URLs are rejected. Failing sentences are removed and logged as `STATEMENT_REJECTED`. Citations are
rendered only from the source repository.

**Prompt-injection boundary.** Every prompt states that retrieved content is evidence, not instructions. Retrieved
text can't change prompts, tools, destinations or files. The synthetic corpus contains an injection line, and a
benchmark check confirms it had no effect.

---

## The reproducible example run (synthetic)

`python app.py --demo` regenerates [examples/demo_report.md](examples/demo_report.md) and
[examples/demo_trace.txt](examples/demo_trace.txt). This is the story the run tells, and every step is a real
pipeline decision:

1. Five hypotheses are created (strong product-market fit, discount-driven, acquisition-driven, real growth with
   weak retention, insufficient information), each with evidence requirements.
2. Discovery search finds a press release, three outlets that copy it, a company-registry filing and a 2021 profile.
3. **Lineage:** the three outlets are detected as derived from the press release (p = 0.82–0.97). The 95%
   retention claim drops from **0.71 to 0.67**, and its independent roots go from 2 to 1.
4. **Temporal validator:** "900 customers (2021)" vs "4,800 customers (2025)" is a temporal version, not a contradiction.
5. **Inference rejected:** "70% revenue growth ⇒ strong product-market fit" is judged weak. The confounders are
   discounting and acquisitions, and the missing premise is independent retention data, which opens a
   `WEAK_INFERENCE` gap. "95% retention ⇒ product-market fit" is rejected by rule R2, because only the company says so.
6. **Adversarial search** against the leading hypothesis finds customer reviews about churn after a 50% discount ended.
7. **Gap-driven search** ("searching because of G_… [WEAK_INFERENCE]") finds an independent benchmark with **81%
   logo retention**. The 95% claim falls from **0.62 to 0.45** and becomes `contested`. "Strong product-market fit"
   falls from 0.35 to 0.12.
8. The stop policy ends the run on **DIMINISHING_RETURNS**. Two draft sentences are removed by the citation
   verifier: one has no claim IDs, and one invents "85%".
9. Final status: **LIKELY**. The leading hypothesis is "growth is real but retention is weak" (model-estimated
   posterior 0.81, sufficiency 0.59). The report lists research debt and what would change the conclusion.

## Evaluation

`python -m evidence_research.evaluation.benchmark` runs the synthetic scenario, which contains all five required
case types. It checks the expected behaviour for each one and reports metrics and a baseline comparison. Current output:

| check | result |
|---|---|
| agreeing sources: growth backed by ≥ 2 independent roots | ✅ |
| conflicting sources: retention claim contested, posterior < 0.5 | ✅ |
| derived reporting: press copies collapse into one root | ✅ |
| outdated evidence: 2021 count is a temporal version, not a contradiction | ✅ |
| insufficient evidence: acquisition hypothesis stays insufficient with an open gap | ✅ |
| adversarial evidence lowered a posterior | ✅ |
| prompt injection had no effect | ✅ |

Metrics:
- citation validity 1.0
- unsupported fact claims 0
- requirement coverage 0.78
- 8 raw sources → 5 independent roots
- 3 lineage edges, 2 contradictions, 1 temporal version, 3 rejected inferences
- 27 model calls

On the same corpus, the **naive baseline** cites 6 "sources" that are only 3 independent roots, and it repeats the
contradicted 95% retention figure. The Brier score on 5 labelled claims is 0.108. The labels are true *by
construction* of the fictional world, so this is a sanity check, not a calibration result.

`--live` runs the five questions in [examples/sample_questions.md](examples/sample_questions.md) (agree / conflict /
derived / outdated / insufficient) against Token Factory + Tavily and reports the same metrics. There is no ground
truth for these, so they produce metrics only.

## Streamlit UI

`streamlit run ui/streamlit_app.py`:
- **Header:** question, depth (Fast / Standard / Deep), live or synthetic mode, and a live trace while the run executes.
- **Headline metrics:** evidence status, truth confidence, evidence sufficiency, independent roots vs raw
  sources, and unresolved critical gaps.

The six tabs:
- **Overview:** verified conclusion, sentences removed by the verifier, surviving hypotheses, the biggest
  contradiction with its posterior history, research debt, and what would change our mind.
- **Hypotheses:** prior, posterior, sufficiency and inference validity, a posterior-history chart, and the
  accepted and rejected inferences.
- **Claims & Evidence:** per claim, the posterior, sufficiency, roots, raw sources, SUPPORT, AGAINST and MISSING.
- **Research Trace:** a filterable chronological event log.
- **Evidence Graph:** a focused hypothesis → inference → claim → evidence → source view (Graphviz), with filters.
- **Sources:** type, primary status, conflict of interest, origin (discovery / gap / adversarial), root and clusters.

Runs are persisted to SQLite (`data/research.sqlite`): sessions, every event as it happens, and the graph and
report snapshot.

## Docker

```bash
docker build -t evidence-research .
docker run --rm -p 8501:8501 --env-file .env evidence-research            # UI on http://localhost:8501
docker run --rm evidence-research pytest -q                               # tests, no keys
docker run --rm evidence-research python app.py --demo                    # synthetic run
```

## Layout

```
app.py                         CLI (live, --demo, --baseline, --check)
ui/streamlit_app.py            demo UI
src/evidence_research/
  config.py  models.py  runtime.py
  orchestration/   orchestrator, state_machine, budget, stop_policy   (scheduling: asyncio.gather in retrieval)
  llm/             gateway (AsyncOpenAI → Token Factory, roles, retries, structured output), prompts
  retrieval/       tavily_client, service (search→rank→dedup→select→extract), source_ranker, url_normalizer
  research/        analysis (question + hypotheses), query_planner (discovery/gap/adversarial), gap_analyzer
  evidence/        extractor (ingestion pipeline), claim_normalizer, source_classifier, lineage, temporal
  graph/           evidence_graph (NetworkX), repository (SQLite), queries (UI views)
  verification/    entailment (stance judge), inference_verifier, citation_verifier, contradiction
  probability/     evidence_score, bayesian, uncertainty, engine (recompute from graph)
  synthesis/       report, serializer
  observability/   events (audit trail)
  demo/            scenario (SYNTHETIC: scripted model + fake corpus)
  evaluation/      baseline, benchmark
tests/                         52 offline tests
examples/                      sample questions, reproducible synthetic run
```

Module boundaries follow the brief. A few files were merged where a separate file would have been empty
ceremony: the question analyzer and hypothesis generator are in `research/analysis.py`; the researcher and
adversarial researcher are the query planner plus the shared retrieval and ingestion path; the scheduler is
`asyncio.gather` with semaphores; trace logic is in `events.py`.

## Status and limitations

- **Offline:** all 52 tests pass, the synthetic demo, benchmark and UI run, and the Token Factory and Tavily
  adapters are tested against mocked SDK clients.
- **Not yet verified live:** no API keys were available while this was built. Run `python app.py --check` first;
  it calls each API once. Real models may phrase claims differently from the scripted ones, and the matcher, judge
  and verifier prompts are the most likely places to need tuning.
- **Heuristic numbers:** all priors, likelihood ratios and source assessments are hand-set heuristics, not
  calibrated or audited.
- **Lineage limits:** detection is text- and metadata-based. It misses paraphrased derivation and can't see
  syndication deals.
- **Not built (stretch):** perspective decomposition, a dedicated entailment model, calibration, cross-session
  source reputation, and monitoring re-runs.
