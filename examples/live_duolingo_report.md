# Research report: Does Duolingo have strong product-market fit?

## Executive conclusion
**Current evidence status: INSUFFICIENT_EVIDENCE**

- Duolingo reports large and growing user, booking, and subscription metrics, but those metrics alone do not establish strong product-market fit. [1][2][3][6]
- Retention, engagement-ratio, revenue-growth, and learning-outcome claims are limited, market-specific, or marked insufficient, so they do not close the evidence gap. [2][4][5]
- Overall, the evidence is insufficient to conclude that Duolingo has strong product-market fit, and the supported position is that public financial and user metrics are insufficient proxies for that conclusion. [1][2][3][4][5][6]

## Surviving hypotheses
| ID | Hypothesis | Prior | Posterior | Sufficiency | Inference validity | Status |
|---|---|---|---|---|---|---|
| H5 | Public financial and user metrics are insufficient proxies to establish whether Duolingo has strong product-market fit. (null) | 35% | **75%** | 100% | n/a | supported |
| H1 | Duolingo demonstrates strong product-market fit across its core language-learning market, supported by durable engagement, retention, monetization, and organic growth. | 50% | **50%** | 23% | n/a | insufficient |
| H3 | Duolingo has strong product-market fit among casual or beginner learners but weak fit among serious, advanced, or paid learners. | 35% | **35%** | 23% | n/a | insufficient |
| H4 | Duolingo currently shows strong usage metrics, but product-market fit is eroding due to AI-enabled competitors and content commoditization. | 35% | **35%** | 25% | n/a | insufficient |
| H2 | Duolingo's apparent success reflects gamification-driven engagement rather than durable language-learning value, with weak long-term retention, completion, and monetization. | 20% | **20%** | 23% | n/a | insufficient |

Main surviving hypothesis: **H1** — Duolingo demonstrates strong product-market fit across its core language-learning market, supported by durable engagement, retention, monetization, and organic growth.
Strongest counter-hypothesis: **H3** — Duolingo has strong product-market fit among casual or beginner learners but weak fit among serious, advanced, or paid learners.

## Rejected / weakened hypotheses
- None.
  - H1 inference not accepted: I_f338f103c5 (needs_evidence): Monthly churn declined from 47% in mid-2020 to a record low of 28% by late 2023 and is reported at 16% in 2025, indicating improving retention. — Churn decline supports improving retention at most, but the conclusion asserts broad product-market fit across engagement, monetization, and organic growth, which these premises do not establish.; R1: premise not established (weakest posterior 0.50)
  - H1 inference not accepted: I_8aff46b673 (rejected): A 28.6% DAU/MAU ratio, 36% year-over-year DAU growth, and nearly 2 billion daily exercises indicate durable engagement. — The premises indicate high usage and growth, but growth alone does not establish quality, and they do not support the broader product-market-fit conclusion.
  - H1 inference not accepted: I_ede04142fb (rejected): Revenue growth of 16% from 2024 to 2025 indicates monetization strength. — A 16% revenue increase is consistent with monetization strength but, by itself and with an insufficiently supported premise, does not establish it.
  - H1 inference not accepted: I_1d817216e5 (rejected): Duolingo's 59% year-over-year DAU growth and unusually high DAU/MAU ratio indicate durable engagement and organic growth in its core market. — The premises show engagement and user growth, but the conclusion also requires retention, monetization, organic growth, and durability, which are not established.
  - H1 inference not accepted: I_3a8d318742 (rejected): Monthly churn fell from 47% in mid-2020 to a record low of 28% in Western markets by late 2023, indicating improving retention. — The premises show improved churn in Western markets over time, but the conclusion requires broader retention, engagement, monetization, and organic growth evidence.
  - H1 inference not accepted: I_2330671fbf (rejected): Revenue growth plus strong growth in total and subscription bookings indicates expanding monetization. — The premises show monetization growth, but the conclusion also requires durable engagement, retention, and organic growth, which are not established.
  - H3 inference not accepted: I_f518e1d538 (needs_evidence): A 100M free MAU base and more than $50M of foregone bookings invested in the free experience suggest stronger fit among free or casual learners than paid learners. — Free-user scale and foregone bookings do not establish stronger fit among free or casual learners than among paid learners.; R1: premise not established (weakest posterior 0.50)
  - H4 inference not accepted: I_68fd9a2775 (rejected): Over 100M MAUs and 58.7M average DAUs in Q2 2026 show currently strong usage metrics, though they do not address possible erosion. — The premises support currently strong usage metrics but do not support the claim that product-market fit is eroding.
  - H4 inference not accepted: I_001ebaa295 (rejected): Duolingo averaged 58.7 million DAUs in Q2 2026 and scaled to more than 130 million MAUs by late 2025, contradicting the claim that product-market fit is currently eroding. — The premises show strong current usage, but they do not establish that product-market fit is not eroding or address AI competitors and commoditization.
  - H2 inference not accepted: I_648eb63920 (rejected): Cited studies found Duolingo learners matched or exceeded university and classroom language proficiency, contradicting the claim that engagement is merely gamification without durable learning value. — The premises report proficiency outcomes that conflict with the conclusion's claim that success reflects gamification without durable learning value.
  - H2 inference not accepted: I_4fa1f0955e (needs_evidence): Cited studies showing Duolingo learners achieve proficiency comparable to or better than traditional instruction contradict the claim that its engagement lacks durable language-learning value. — The cited studies partially challenge the claim that engagement lacks durable learning value, but they do not address retention, completion, or monetization and are subject to selection and citation bias.; R3: causal/abductive inference with unexcluded confounders

## Critical claims: supporting and contradicting evidence
#### C_312cc68851: Duolingo's daily active users (DAUs) were 34.1 million in Q2 2024, an increase of 59% from the prior year quarter.
- Model-estimated posterior **67%** · evidence sufficiency **50%** · status `likely` · period: 2024-04-01 → 2024-06-30
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [1]: “Daily active users (DAUs) were 34.1 million, an increase of 59% from the prior year quarter and monthly active users (MAUs) were 103.6 million, an increase of 4” — source 0.36 · independence 0.20 · LR 2

#### C_163a892fbf: Duolingo scaled to more than 130 million monthly active users for the three months ended December 31, 2025.
- Model-estimated posterior **80%** · evidence sufficiency **50%** · status `likely` · period: 2025-10-01 → 2025-12-31
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.80
- SUPPORT [2]: “This has allowed us to scale to more than 130 million MAUs for the three months ended December 31, 2025” — source 0.60 · independence 1.00 · LR 4

#### C_0a297fecad: Duolingo's total bookings were $190.1 million in Q2 2024, an increase of 38% from the prior year quarter.
- Model-estimated posterior **67%** · evidence sufficiency **50%** · status `likely` · period: 2024-04-01 → 2024-06-30
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [1]: “Total bookings were $190.1 million, an increase of 38% from the prior year quarter;” — source 0.48 · independence 0.20 · LR 2

#### C_24d04957c0: Duolingo's daily active users (DAU) were 52.7 million in Q4 2025.
- Model-estimated posterior **80%** · evidence sufficiency **50%** · status `likely` · period: 2025-10-01 → 2025-12-31
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.80
- SUPPORT [3]: “Daily Active Users | 40.5M | 52.7M |
|  |  | 30% YoY” — source 0.60 · independence 0.40 · LR 4

#### C_343b1e9793: Duolingo's subscription bookings were $156.5 million in Q2 2024, an increase of 47% from the prior year quarter.
- Model-estimated posterior **67%** · evidence sufficiency **50%** · status `likely` · period: 2024-04-01 → 2024-06-30
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [1]: “Subscription bookings were $156.5 million, an increase of 47% from the prior year quarter;” — source 0.48 · independence 0.20 · LR 2

#### C_24911db1bb: Duolingo's DAU/MAU ratio is 28.6%, which is high for a non-social app where most education apps sit closer to 10-15%.
- Model-estimated posterior **56%** · evidence sufficiency **35%** · status `insufficient` · period: period unknown
- Raw sources: 2 · independent roots: **1** · history: 0.50 → 0.56
- SUPPORT [4]: “The DAU/MAU ratio of 28.6% is also high for a non-social app, where most education apps sit closer to 10-15%” — source 0.24 · independence 1.00 · LR 1.25
- MISSING: C_24911db1bb: no primary source for 'Duolingo's DAU/MAU ratio is 28.6%, which is high for a non-social app where most education apps sit closer to 10-15%.'
- MISSING: C_24911db1bb: 2 sources but only 1 independent root

#### C_062263e8bc: Duolingo's monthly churn rate reached a record low of 28% in Western markets by late 2023.
- Model-estimated posterior **67%** · evidence sufficiency **35%** · status `likely` · period: 2023-07-01 → 2023-12-31
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [5]: “reaching a record low of 28% in Western markets by late 2023” — source 0.47 · independence 1.00 · LR 2
- MISSING: C_062263e8bc: no independent confirmation of 'Duolingo's monthly churn rate reached a record low of 28% in Western markets by late 2023.'

#### C_071585e27c: Duolingo's revenue grew 16% from 2024 to 2025.
- Model-estimated posterior **56%** · evidence sufficiency **35%** · status `insufficient` · period: 2024-01-01 → 2025-12-31
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.56
- SUPPORT [4]: “Downloads grew about 6% year over year from 2024 to 2025, while revenue grew 16% over the same period” — source 0.26 · independence 1.00 · LR 1.25
- MISSING: C_071585e27c: no independent confirmation of 'Duolingo's revenue grew 16% from 2024 to 2025.'
- MISSING: C_071585e27c: no primary source for 'Duolingo's revenue grew 16% from 2024 to 2025.'

#### C_0a435da87f: Duolingo's monthly churn rate was 47% in mid-2020.
- Model-estimated posterior **67%** · evidence sufficiency **35%** · status `likely` · period: 2020-06-01 → 2020-12-31
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [5]: “Monthly churn dropped from 47% in mid-2020 to 37% by early 2023” — source 0.47 · independence 1.00 · LR 2
- MISSING: C_0a435da87f: no independent confirmation of 'Duolingo's monthly churn rate was 47% in mid-2020.'

#### C_310da5a9a2: Duolingo averaged 58.7 million daily active users in Q2 2026.
- Model-estimated posterior **67%** · evidence sufficiency **35%** · status `likely` · period: 2026-04-01 → 2026-06-30
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [6]: “Duolingo averaged **58.7 million** daily active users in Q2 2026, up **23%** from **47.7 million** a year earlier, according to its Q2 2026 shareholder letter” — source 0.47 · independence 1.00 · LR 2
- MISSING: C_310da5a9a2: no independent confirmation of 'Duolingo averaged 58.7 million daily active users in Q2 2026.'

#### C_0cdf35a686: Independent studies cited in Duolingo's FY2025 10-K found that users learning English on Duolingo outperformed students in traditional classroom settings on standardized language proficiency tests.
- Model-estimated posterior **56%** · evidence sufficiency **34%** · status `insufficient` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.56
- SUPPORT [2] (reported speech): “Independent studies corroborate this finding: Duolingo learners’ speaking skills were found to match those of university students, and users learning English on Duolingo outperformed students in traditional classroom settings on standardized language proficiency tests” — source 0.60 · independence 1.00 · LR 1.25
- MISSING: C_0cdf35a686: no independent confirmation of 'Independent studies cited in Duolingo's FY2025 10-K found that users learning English on Duolingo outperformed students in traditional classroom settings on standardized language proficiency tests.'

#### C_0b18375a05: According to an internal study cited in Duolingo's FY2025 10-K, learners who completed five sections of Duolingo achieved proficiency comparable to five university semesters of language education.
- Model-estimated posterior **56%** · evidence sufficiency **34%** · status `insufficient` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.56
- SUPPORT [2] (reported speech): “According to an internal study, learners who completed five sections of Duolingo achieved proficiency comparable to five university semesters of language education” — source 0.60 · independence 1.00 · LR 1.25
- MISSING: C_0b18375a05: no independent confirmation of 'According to an internal study cited in Duolingo's FY2025 10-K, learners who completed five sections of Duolingo achieved proficiency comparable to five university semesters of language education.'

## Source independence
**9 URLs with evidence → 8 publication families → 6 independent evidence roots.**
- Root S_ee11172712 (Duolingo Hits 100M MAUs, Reports 59% DAU growth and 41% Reve): 4 sources S_4fef278d61, S_b725c17610, S_b7ee29621f, S_ee11172712
- 24 source(s) screened out before extraction, e.g. S_6e0143a99e (Study focuses on motivation and self-perceived speaking prof); S_3d826369ab (Thesis on gamification design elements and user experience; ); S_5f7dfef22e (Study evaluates Duolingo's effectiveness for Spanish learnin)

## Scientific study quality
- No scientific studies among the sources.

## Research gaps
- **HIGH** [WEAK_INFERENCE] I_f338f103c5 → H1: needs evidence on 'engagement metrics'
- **HIGH** [WEAK_INFERENCE] I_f338f103c5 → H1: needs evidence on 'monetization metrics'
- **HIGH** [WEAK_INFERENCE] I_8aff46b673 → H1: needs evidence on 'retention cohorts'
- **HIGH** [WEAK_INFERENCE] I_8aff46b673 → H1: needs evidence on 'monetization or paid-conversion evidence'
- **HIGH** [WEAK_INFERENCE] I_ede04142fb → H1: needs evidence on 'revenue per user'
- **HIGH** [WEAK_INFERENCE] I_ede04142fb → H1: needs evidence on 'paid conversion rate'
- **HIGH** [WEAK_INFERENCE] I_1d817216e5 → H1: needs evidence on 'retention or churn evidence'
- **HIGH** [WEAK_INFERENCE] I_1d817216e5 → H1: needs evidence on 'monetization evidence'
- **HIGH** [WEAK_INFERENCE] I_3a8d318742 → H1: needs evidence on 'global churn or retention data'
- **HIGH** [WEAK_INFERENCE] I_2330671fbf → H1: needs evidence on 'retention or churn evidence'

## What would change our mind
1. Cohort-level retention and churn data across markets and learner segments, including long-term retention and course completion rates.
2. Monetization evidence such as paid conversion, average revenue per user, lifetime value, and price sensitivity by learner segment.
3. Organic versus paid acquisition metrics, including referral, viral, and word-of-mouth growth evidence.
4. Independent, replicated learning-outcome studies with clearly defined learner populations and long-term follow-up.
5. Evidence resolving: I_f338f103c5 → H1: needs evidence on 'engagement metrics'
6. Evidence resolving: I_f338f103c5 → H1: needs evidence on 'monetization metrics'
7. Evidence resolving: I_8aff46b673 → H1: needs evidence on 'retention cohorts'

## Why research stopped
- BUDGET_EXHAUSTED: search budget exhausted
- Final agent bids: IndependenceResearcher 1.00, GapResearcher 1.00, AdversarialResearcher 0.72, PrimarySourceResearcher 0.66, GeneralResearcher 0.17, ContradictionResearcher 0.00, ReplicationResearcher 0.00, Synthesis 0.00

## Limitations and method
- Hypothesis-first research: competing hypotheses and evidence requirements were generated before searching.
- LLMs proposed claims, stances and inferences; code verified excerpts verbatim, counted sources and computed every score.
- Probabilities are model-estimated evidence beliefs from heuristic likelihood ratios, NOT calibrated probabilities.
- Evidence from one provenance cluster counts once; derivatives add 15% of their weight.
- Source credibility uses heuristic priors by source type, adjusted per claim category; no audited ratings.
- Scientific evidence is weighted by a deterministic study-quality score and replication factors; peer review alone is not decisive.
- Research agents were chosen each round by heuristic utility bids, not by a fixed pipeline.
- 24 source(s) were screened out before extraction; reasons are preserved (negative provenance).
- Stop reason: BUDGET_EXHAUSTED — search budget exhausted

## Citations
[1] Duolingo Hits 100M MAUs, Reports 59% DAU growth and 41% Revenue Growth in Second Quarter 2024 - Duolingo, Inc. — http://investors.duolingo.com/news-releases/news-release-details/duolingo-hits-100m-maus-reports-59-dau-growth-and-41-revenue (duolingo.com; published 2024-08-07; retrieved 2026-10-18; root S_ee11172712)
[2] duol-20251231 — https://www.sec.gov/Archives/edgar/data/1562088/000162828026012494/duol-20251231.htm (sec.gov; published unknown; retrieved 2026-10-18; root S_ee11172712)
[3] Document — https://www.sec.gov/Archives/edgar/data/1562088/000162828026012246/q4fy25duolingo12-31x25shar.htm (sec.gov; published unknown; retrieved 2026-10-18; root S_ee11172712)
[4] Duolingo Statistics (2026): Users, Revenue, Downloads — https://www.blog.udonis.co/mobile-marketing/mobile-apps/duolingo (udonis.co; published unknown; retrieved 2026-10-18; root S_94747c9d21)
[5] Duolingo gamification explained | StriveCloud — https://www.strivecloud.io/duolingo-gamification-explained (strivecloud.io; published unknown; retrieved 2026-10-18; root S_aa6dec0f68)
[6] Duolingo Statistics 2026: Users, Revenue and Languages — https://sqmagazine.co.uk/duolingo-statistics (sqmagazine.co.uk; published unknown; retrieved 2026-10-18; root S_e77c766899)

_Stats: {'iterations': 2, 'searches': 10, 'extractions': 10, 'model_calls': 34, 'hypothesis': 5, 'requirement': 16, 'source': 62, 'claim': 107, 'evidence': 114, 'inference': 11, 'gap': 32, 'edges': 511, 'screened_out': 24, 'unverified_evidence': 3}_