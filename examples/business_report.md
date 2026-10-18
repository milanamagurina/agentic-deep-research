# Research report: Does Acme Fleet have strong product-market fit?

> **SYNTHETIC DEMO RUN** — fictional entities, scripted corpus and model responses. Not real-world evidence.

## Executive conclusion
**Current evidence status: LIKELY**

- Acme Fleet's revenue growth of 70% in fiscal year 2025 is supported by its filed annual accounts, not only by its own press release. [2][3][5][6][7]
- An independent benchmark reports 81% gross logo retention for 2025, below the 90% segment median, which contradicts the company-reported 95% retention. [1][2][3]
- Around 45% of new customers in 2025 joined through a 50% first-year discount, so growth quality is uncertain. [1]

_2 draft sentence(s) were removed by the citation verifier._

## Surviving hypotheses
| ID | Hypothesis | Prior | Posterior | Sufficiency | Inference validity | Status |
|---|---|---|---|---|---|---|
| H4 | Acme Fleet's growth is real but customer retention is weak | 35% | **81%** | 59% | 78% | active |
| H2 | Acme Fleet's growth is primarily discount-driven | 35% | **52%** | 42% | 65% | active |
| H5 | Public information is insufficient to establish Acme Fleet's product-market fit (null) | 20% | **41%** | 100% | n/a | active |
| H3 | Acme Fleet's growth is primarily acquisition-driven (M&A) | 20% | **20%** | 0% | n/a | insufficient |

Main surviving hypothesis: **H4** — Acme Fleet's growth is real but customer retention is weak
Strongest counter-hypothesis: **H2** — Acme Fleet's growth is primarily discount-driven

## Rejected / weakened hypotheses
- **H1** Acme Fleet has strong, genuine product-market fit: rejected, posterior 35% → 12%
  - H2 inference not accepted: I_b36257a175 (rejected): EUR 9.1m of discounts suggests discount-driven growth — Absolute discount volume says nothing about the share of growth it drove.
  - H1 inference not accepted: I_528956a95b (rejected): 70% revenue growth indicates strong product-market fit — Revenue growth is consistent with PMF but also with discounting or M&A; retention is not established.
  - H1 inference not accepted: I_cc8eb032ec (rejected): 95% customer retention indicates strong product-market fit — Retention bears on PMF if the figure is reliable.; R2: all premises rest on one interested source (self-reported)

## Critical claims: supporting and contradicting evidence
#### C_5b93e6c990: Acme Fleet retained 95% of its customers in 2025
- Model-estimated posterior **45%** · evidence sufficiency **88%** · status `contested` · period: 2025-01-01 → 2025-12-31
- Raw sources: 4 · independent roots: **3** · history: 0.50 → 0.71 → 0.67 → 0.62 → 0.45
- SUPPORT [2]: “Acme Fleet retained 95% of its customers during 2025” — source 0.36 · independence 1.00 · LR 2
- SUPPORT [3] (reported speech): “Acme Fleet also said it retained 95% of its customers” — source 0.55 · independence 0.18 · LR 1.25
- AGAINST [1]: “Acme Fleet's gross logo retention was 81% in 2025, below the segment median of 90%” — source 0.47 · independence 1.00 · LR 0.5
- AGAINST [4]: “Great routing, but many couriers in our network churned after the first year” — source 0.38 · independence 1.00 · LR 0.8
- MISSING: C_5b93e6c990: independent sources disagree on 'Acme Fleet retained 95% of its customers in 2025'

#### C_294c7b4974: Acme Fleet revenue grew 70% in fiscal year 2025
- Model-estimated posterior **95%** · evidence sufficiency **75%** · status `supported` · period: 2025-01-01 → 2025-12-31
- Raw sources: 5 · independent roots: **2** · history: 0.50 → 0.97 → 0.95
- SUPPORT [5]: “Turnover increased by 70.0% compared with the previous financial year” — source 0.93 · independence 1.00 · LR 8
- SUPPORT [2]: “Revenue grew 70% to EUR 47.5 million, driven by strong demand for its route optimisation platform” — source 0.48 · independence 1.00 · LR 2
- SUPPORT [3] (reported speech): “Acme Fleet announced that revenue grew 70% to EUR 47.5 million in 2025, driven by strong demand for its route optimisation platform, according to a company press release” — source 0.58 · independence 0.18 · LR 1.25
- SUPPORT [6] (reported speech): “According to a press release published on Tuesday, Acme Fleet said revenue grew 70% to EUR 47.5 million, driven by strong demand for its route optimisation platform” — source 0.47 · independence 0.03 · LR 1.25

#### C_d391b908f5: Acme Fleet revenue in fiscal year 2025 was EUR 47,512,000
- Model-estimated posterior **94%** · evidence sufficiency **75%** · status `supported` · period: 2025-01-01 → 2025-12-31
- Raw sources: 2 · independent roots: **2** · history: 0.50 → 0.94
- SUPPORT [5]: “Turnover for the financial year 2025: EUR 47,512,000” — source 0.93 · independence 1.00 · LR 8
- SUPPORT [2]: “Revenue grew 70% to EUR 47.5 million, driven by strong demand for its route optimisation platform” — source 0.48 · independence 1.00 · LR 2

#### C_3b7fea686b: Acme Fleet's gross logo retention was 81% in 2025, below the segment median of 90%
- Model-estimated posterior **67%** · evidence sufficiency **35%** · status `likely` · period: 2025-01-01 → 2025-12-31
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [1]: “Acme Fleet's gross logo retention was 81% in 2025, below the segment median of 90%” — source 0.49 · independence 1.00 · LR 2
- MISSING: C_3b7fea686b: no independent confirmation of 'Acme Fleet's gross logo retention was 81% in 2025, below the segment median of 90%'
- MISSING: C_3b7fea686b: no primary source for 'Acme Fleet's gross logo retention was 81% in 2025, below the segment median of 90%'

#### C_52ed1e545f: Around 45% of Acme Fleet's new customers in 2025 joined through a 50% first-year discount promotion
- Model-estimated posterior **67%** · evidence sufficiency **35%** · status `likely` · period: 2025-01-01 → 2025-12-31
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [1]: “Around 45% of Acme Fleet's new customers in 2025 joined through a 50% first-year discount promotion” — source 0.49 · independence 1.00 · LR 2
- MISSING: C_52ed1e545f: no independent confirmation of 'Around 45% of Acme Fleet's new customers in 2025 joined through a 50% first-year discount promotion'
- MISSING: C_52ed1e545f: no primary source for 'Around 45% of Acme Fleet's new customers in 2025 joined through a 50% first-year discount promotion'

#### C_e5e830f2c6: Acme Fleet customers cancelled when the renewal price doubled after an introductory 50% discount
- Model-estimated posterior **56%** · evidence sufficiency **24%** · status `insufficient` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.56
- SUPPORT [4] (reported speech): “We joined on the introductory 50% discount and cancelled when the renewal price doubled” — source 0.46 · independence 1.00 · LR 1.25
- MISSING: C_e5e830f2c6: no independent confirmation of 'Acme Fleet customers cancelled when the renewal price doubled after an introductory 50% discount'
- MISSING: C_e5e830f2c6: no primary source for 'Acme Fleet customers cancelled when the renewal price doubled after an introductory 50% discount'

#### C_bd2869744d: Acme Fleet granted EUR 9,140,000 in sales discounts and promotional credits in 2025
- Model-estimated posterior **89%** · evidence sufficiency **50%** · status `likely` · period: 2025-01-01 → 2025-12-31
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.89
- SUPPORT [5]: “Sales discounts and promotional credits granted in 2025: EUR 9,140,000” — source 0.93 · independence 1.00 · LR 8
- MISSING: C_bd2869744d: no independent confirmation of 'Acme Fleet granted EUR 9,140,000 in sales discounts and promotional credits in 2025'

## Source independence
**8 URLs with evidence → 8 publication families → 5 independent evidence roots.**
- Root S_c315c04e06 (Acme Fleet reports record FY2025 results): 4 sources S_063e7f2bb7, S_51c37b97e5, S_900d18c910, S_c315c04e06

## Scientific study quality
- No scientific studies among the sources.

## Research gaps
- **HIGH** [NO_INDEPENDENT_SOURCE] C_e5e830f2c6: no independent confirmation of 'Acme Fleet customers cancelled when the renewal price doubled after an introductory 50% discount'
- **HIGH** [CONTRADICTORY_EVIDENCE] C_5b93e6c990: independent sources disagree on 'Acme Fleet retained 95% of its customers in 2025'
- **HIGH** [NO_PRIMARY_SOURCE] C_e5e830f2c6: no primary source for 'Acme Fleet customers cancelled when the renewal price doubled after an introductory 50% discount'
- **HIGH** [NO_INDEPENDENT_SOURCE] C_3b7fea686b: no independent confirmation of 'Acme Fleet's gross logo retention was 81% in 2025, below the segment median of 90%'
- **HIGH** [NO_INDEPENDENT_SOURCE] C_52ed1e545f: no independent confirmation of 'Around 45% of Acme Fleet's new customers in 2025 joined through a 50% first-year discount promotion'
- **HIGH** [NO_PRIMARY_SOURCE] C_3b7fea686b: no primary source for 'Acme Fleet's gross logo retention was 81% in 2025, below the segment median of 90%'
- **HIGH** [NO_PRIMARY_SOURCE] C_52ed1e545f: no primary source for 'Around 45% of Acme Fleet's new customers in 2025 joined through a 50% first-year discount promotion'
- **MEDIUM** [NO_INDEPENDENT_SOURCE] C_bd2869744d: no independent confirmation of 'Acme Fleet granted EUR 9,140,000 in sales discounts and promotional credits in 2025'
- **MEDIUM** [MISSING_REQUIRED_DIMENSION] H3.R1 (H3): no evidence yet on 'acquisitions made by Acme Fleet in 2025'
- **MEDIUM** [WEAK_INFERENCE] I_528956a95b → H1: needs evidence on 'independent customer retention data'

## What would change our mind
1. Independently verified retention above the 90% segment median
2. Evidence that discounted 2025 cohorts renewed at full price
3. A restatement of the FY2025 turnover in the filed accounts
4. Evidence resolving: C_e5e830f2c6: no independent confirmation of 'Acme Fleet customers cancelled when the renewal price doubled after an introductory 50% discount'
5. Evidence resolving: C_5b93e6c990: independent sources disagree on 'Acme Fleet retained 95% of its customers in 2025'
6. Evidence resolving: C_e5e830f2c6: no primary source for 'Acme Fleet customers cancelled when the renewal price doubled after an introductory 50% discount'

## Why research stopped
- DIMINISHING_RETURNS: last research round produced no new independent evidence root
- Final agent bids: IndependenceResearcher 0.93, PrimarySourceResearcher 0.78, ContradictionResearcher 0.73, GapResearcher 0.37, GeneralResearcher 0.22, AdversarialResearcher 0.10, Synthesis 0.04, ReplicationResearcher 0.00

## Limitations and method
- SYNTHETIC DEMO: the corpus and model responses are scripted fixtures, not real-world evidence.
- Hypothesis-first research: competing hypotheses and evidence requirements were generated before searching.
- LLMs proposed claims, stances and inferences; code verified excerpts verbatim, counted sources and computed every score.
- Probabilities are model-estimated evidence beliefs from heuristic likelihood ratios, NOT calibrated probabilities.
- Evidence from one provenance cluster counts once; derivatives add 15% of their weight.
- Source credibility uses heuristic priors by source type, adjusted per claim category; no audited ratings.
- Scientific evidence is weighted by a deterministic study-quality score and replication factors; peer review alone is not decisive.
- Research agents were chosen each round by heuristic utility bids, not by a fixed pipeline.
- 0 source(s) were screened out before extraction; reasons are preserved (negative provenance).
- Stop reason: DIMINISHING_RETURNS — last research round produced no new independent evidence root

## Citations
[1] Route optimisation software benchmark 2026 — https://industry-analyst.example/route-optimisation-benchmark-2026 (industry-analyst.example; published 2026-05-15; retrieved 2026-10-18; root S_a92afe4598)
[2] Acme Fleet reports record FY2025 results — https://acmefleet.example/press/fy2025-results (acmefleet.example; published 2026-02-03; retrieved 2026-10-18; root S_c315c04e06)
[3] Route-planning start-up Acme Fleet says revenue jumped 70% — https://logistics-times.example/acme-fleet-growth (logistics-times.example; published 2026-02-05; retrieved 2026-10-18; root S_c315c04e06)
[4] Acme Fleet reviews — https://fleet-reviews.example/acme-fleet (fleet-reviews.example; published 2026-06-12; retrieved 2026-10-18; root S_ab67bdf197)
[5] Acme Fleet GmbH: annual accounts 2025 — https://business-registry.example/acme-fleet-gmbh/annual-accounts-2025 (business-registry.example; published 2026-04-30; retrieved 2026-10-18; root S_114e02b136)
[6] Acme Fleet posts record year — https://fleetnews.example/2026/02/acme-fleet-record-year (fleetnews.example; published 2026-02-04; retrieved 2026-10-18; root S_c315c04e06)
[7] Acme Fleet: 70% growth! — https://dailyfreight-blog.example/acme-fleet-70-percent (dailyfreight-blog.example; published 2026-02-06; retrieved 2026-10-18; root S_c315c04e06)

_Stats: {'iterations': 3, 'searches': 10, 'extractions': 8, 'model_calls': 30, 'hypothesis': 5, 'requirement': 9, 'source': 8, 'claim': 14, 'evidence': 24, 'inference': 7, 'gap': 13, 'edges': 115, 'screened_out': 0, 'unverified_evidence': 0}_