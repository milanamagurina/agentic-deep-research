# Deep Research Team: planner, parallel researchers, adversarial fact-checker

A multi-agent research system that turns a question into a **sourced, verifiable report**.
Inference runs on **Nebius Token Factory**, retrieval on **Tavily**, orchestration on **deepagents**.

The core goal: a judge clicks three citations at random and they hold up. The system
does not just ask for citations; it **audits every one after the run, with no model involved**.

```
                    ┌──────────────────────── lead (Token Factory) ───────────────────────┐
question ──▶ scope (≤2 searches) ─▶ plan (todos + /plan.md) ─▶ delegate ─▶ assess ─▶ draft ─▶ challenge ─▶ revise ─▶ report
                                                                 │  ▲                          │   ▲
                                         parallel  ┌─────────────┘  │ /findings/*.md          │   │ /review.md
                                                   ▼                │                          ▼   │
                                     researcher × N (search + extract, verbatim quotes)   fact-checker (tries to REFUTE each claim)
                                                                                                    │
                    every Tavily result ──▶ SourceLedger ──▶ deterministic citation audit ◀──── final report
```

## What makes it different from the cookbook

| Cookbook agent | This project |
|---|---|
| One agent, one loop | **Lead + parallel researchers + adversarial fact-checker** (orchestrator-workers with a red team) |
| Citations are whatever the model writes | **Deterministic citation audit**: each source is `VERIFIED` (URL was returned by Tavily in this run *and* the quote appears verbatim in the retrieved text), `URL_ONLY`, or `UNRETRIEVED` (likely fabricated) |
| No confidence signal | **Per-claim confidence** (High/Medium/Low) from a written rubric, plus the fact-checker's verdict (Confirmed/Weakened/Refuted) |
| Search snippets only | Researchers call `tavily_extract` to read the page, so quotes come from the page, not a snippet |
| Opaque run | **Decision trace**: every agent's reasoning line, tool choice, delegation and result, live on stderr and saved as JSONL |
| One model | **Per-role models**: e.g. a different model as fact-checker for an independent second opinion |
| Script-like | The lead decides when evidence is enough (evidence bar per sub-question, at most one follow-up round) and logs each decision in `/plan.md` |

## Quick start (local)

Requires Python 3.12+ (tested on 3.13), a [Token Factory](https://tokenfactory.nebius.com) API key and a [Tavily](https://tavily.com) API key.

```bash
git clone https://github.com/SirPhlittes/Agentic-Deep-Research-with-Token-Factory-and-Tavily.git
cd Agentic-Deep-Research-with-Token-Factory-and-Tavily
git checkout milanamagurina

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then put your two keys in .env
```

### 1. Run the tests (offline, no keys, no API calls)

```bash
pytest -q
```

Expected: `22 passed`. The tests stub both the model (`tests/fakes.py::ScriptedChatModel`, a real
`BaseChatModel` scripted per role) and Tavily, but run the **real deepagents graph**: the lead, two
parallel researchers, the fact-checker, the file system, the trace and the audit.

### 2. Run one research session

```bash
python app.py "Which grid-scale storage technologies besides lithium-ion reached commercial deployment by 2026, and what does the evidence say about cost per kWh?"
```

With no argument it runs a built-in demo question. Options: `--quiet` (no trace), `--no-save` (no artifacts).

- **stdout**: the report, starting with exactly `Deep research report:`, followed by the citation audit table.
- **stderr**: the live decision trace (abridged example):

```
[    0.1s] lead                     decide  Dispatching researchers in parallel.  ⇒ task, task
[    0.1s] lead                     tool    delegate → researcher: Iron-air deployments. findings_file /findings/iron-air.md
[    0.1s] researcher:iron-air      tool    search  'iron-air commercial 2025'
[    0.1s] researcher:flow          tool    search  'vanadium flow battery installed capacity'
[    0.1s] fact-checker             decide  Trying to refute C2.  ⇒ tavily_search
[    0.1s] audit                    check   2 verified, 0 url-only, 0 unretrieved
```

- **`runs/<UTC timestamp>/`**: `report.md` (report + audit), `trace.jsonl`, `citations.json`,
  `sources.json` (every URL Tavily returned, and which agent found it), and `workspace/` with the agents'
  own files: `plan.md` (with decision log), `findings/*.md`, `draft.md`, `review.md`.

## Configuration

| Variable | Required | Default |
|---|---|---|
| `NEBIUS_API_KEY` | yes | |
| `TAVILY_API_KEY` | yes | |
| `NEBIUS_BASE_URL` | no | `https://api.tokenfactory.nebius.com/v1` |
| `NEBIUS_MODEL` | no | `MiniMaxAI/MiniMax-M3` (lead; default for all roles) |
| `NEBIUS_WORKER_MODEL` | no | `NEBIUS_MODEL` (researchers) |
| `NEBIUS_CHECKER_MODEL` | no | `NEBIUS_MODEL` (fact-checker) |
| `MAX_PARALLEL_RESEARCHERS` | no | `4` |
| `RECURSION_LIMIT` | no | `250` (graph step cap for the lead) |
| `RUNS_DIR` | no | `runs` |

Real environment variables take precedence over `.env`. Keys are held as `SecretStr` and never printed;
a test checks that neither key appears on stdout or stderr. Use any tool-calling model from the Token
Factory catalog (MiniMax-M3, Nemotron 3 Super/Nano, Reflection's Beam): copy the exact model ID from the catalog.

## Docker

```bash
docker build -t deep-research .
docker run --rm --env-file .env deep-research                                # default question
docker run --rm --env-file .env deep-research python app.py "your question"  # custom question
docker run --rm --env-file .env -v "$PWD/runs:/app/runs" deep-research       # keep run artifacts
docker run --rm deep-research pytest -q                                      # tests in the container, no keys needed
```

The container's default command is `python app.py`: it completes one research run, prints the report,
and exits 0. Exit codes: `0` success, `1` the run failed (no report is printed), `2` missing configuration.
`.env` is excluded from the image by `.dockerignore`; credentials enter only at `docker run`.

## Verify it worked

1. `pytest -q` → `22 passed`.
2. `python app.py` exits with code 0 (`echo $?`), and stdout starts with `Deep research report:`.
3. The stderr trace shows `delegate → researcher` (several, in parallel) and `delegate → fact-checker`.
4. The `Citation audit` section at the end of the report: ideally every source is ✅ verified.
   Open `runs/<id>/citations.json` and click any three URLs: the quoted text is on the page.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Configuration error: Missing required environment variable(s)` (exit 2) | Set the keys in `.env` or export them in the same shell. |
| `401` / `AuthenticationError` | Wrong or expired Token Factory key, or `NEBIUS_BASE_URL` is wrong. |
| `404` / model not found | The model ID must match the Token Factory catalog exactly (case-sensitive). |
| Report has no sources / audit shows `0 sources` | Tavily did not run: check `TAVILY_API_KEY`, and look for `error` lines in the trace. |
| Many `URL_ONLY` citations | The model paraphrased quotes. Try a stronger model for the lead (`NEBIUS_MODEL`), or a lower temperature. |
| `UNRETRIEVED` citations | The model cited a URL that Tavily never returned. Treat these claims as unsupported. |
| `GraphRecursionError` | The run hit the step cap. Raise `RECURSION_LIMIT` or narrow the question. |
| Tavily rate limit / `432` errors | Reduce `MAX_PARALLEL_RESEARCHERS`, or check your plan's credits. |
| `ModuleNotFoundError` | Activate the venv (`source .venv/bin/activate`) and rerun `pip install -r requirements.txt`. |

## Cleanup

```bash
deactivate                          # leave the venv
rm -rf .venv runs .pytest_cache     # local environment and run artifacts
docker rmi deep-research            # the image
```

## Project layout

```
app.py                     CLI entrypoint (prints "Deep research report:")
deep_research/
  config.py                env → Settings (SecretStr keys, per-role models)
  prompts.py               lead / researcher / fact-checker prompts, report contract, confidence rubric
  agents.py                ChatNebius + TavilySearch/TavilyExtract, create_deep_agent with subagents
  trace.py                 Tracer middleware (per role) + thread-safe SourceLedger
  citations.py             deterministic citation audit
  runner.py                one run: invoke, pick report, audit, save artifacts
tests/                     offline tests: scripted model + fake Tavily, real agent graph
```

## Design notes

- **Why the audit is deterministic.** A model checking its own citations is still a model. The
  `SourceLedger` records what Tavily actually returned, across all parallel agents. The audit compares
  each cited URL and quote against that record, with Unicode/quote/whitespace normalization only.
  An edited number in a quote (`1.5 MW` → `15 MW`) fails, and so does an invented URL.
- **Why an adversarial checker.** Researchers are rewarded for finding support; the checker is told to
  assume each claim is wrong and run counter-searches. Its verdicts drive the confidence downgrades and
  the "Contested or refuted" section.
- **Bounded by design.** At most 2 scoping searches, 2-N researchers, one follow-up round, a search
  budget per role, and a graph step cap, so runs finish and cost stays predictable.
- **Web text is untrusted.** Retrieved content is data for the agents, never instructions; agent file
  paths are confined to the run's `workspace/` folder when saved.
