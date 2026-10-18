# Live runs (2026-10-18)

Real Token Factory + Tavily runs at `--depth fast`, with `NEBIUS_MODEL=MiniMaxAI/MiniMax-M3` (fast role) and
`NEBIUS_REASONING_MODEL=reflection/beam` (hypotheses, adversarial and contradiction planning, scientific review,
inference verification, deletion test, synthesis). Reports and traces are in this folder, unedited.

| | Duolingo product-market fit | Intermittent fasting vs continuous calorie restriction |
|---|---|---|
| report / trace | [report](live_duolingo_report.md) · [trace](live_duolingo_trace.txt) | [report](live_fasting_report.md) · [trace](live_fasting_trace.txt) |
| status | INSUFFICIENT_EVIDENCE | INSUFFICIENT_EVIDENCE |
| URLs → families → independent roots | 9 → 8 → 6 | 8 → 6 → 4 |
| sources screened out (reasons kept) | 24 | 14 |
| agents selected by bids | General → Independence + Gap | General → Independence + Gap |
| scientific studies assessed | 0 | 6 (all meta-analyses / reviews) |
| versions resolved as one work | – | 3 pages of one systematic review |
| verified report sentences / removed | 3 / 0 | 6 / 0 |
| stop reason | search budget (fast preset) | model-call budget (fast preset) |
| model calls | 34 | 37 |

What the live runs taught us, and what was changed because of them (all covered by tests):

- **Table rows.** Models re-flow table rows into prose, so a verbatim check rejected real figures from earnings
  tables. Excerpts are now located by code (exact, or token-aligned with every number preserved), and the stored
  excerpt is always the page's own text.
- **Huge filings.** A 412k-character 10-K was cut at its cover page. Long pages are now reduced to their most
  relevant passages before extraction.
- **Company documents.** Five Duolingo filings and releases formed one root. That is correct: they are one
  interested party. SEC EDGAR pages are now typed `company_filing` (legally attested, but self-reported), not
  `regulator`, and an IndependenceResearcher looks for third-party evidence.
- **Reasoning-model quirks (`reflection/beam`).** Extra keys in JSON are now ignored for model outputs (domain
  objects stay strict). Repair retries no longer replay an assistant turn without its reasoning. `max_tokens` is
  set explicitly. Batch stance judging runs on the fast model. Every invalid reply is kept in `data/llm_failures/`.
- **Echoed IDs.** Beam wrote claim IDs into prose, and the number check read their digits as facts. IDs are now
  ignored for verification and stripped from the displayed text.
- **False version match.** A meta-analysis citing an RCT's DOI in its references was taken as "another version of
  the same work". A cross-reference now counts only next to version wording, and different study designs are never
  versions.
