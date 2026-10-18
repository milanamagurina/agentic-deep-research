# Does the MemoLoop spaced-repetition app materially improve university exam scores?

> **SYNTHETIC DEMO RUN** — fictional entities, scripted corpus and model responses. Not real-world evidence.

## Answer
**MemoLoop's effect on exam scores is small at best: the large original effect did not hold up in independent replications.** [1][2]

Evidence status: **LIKELY** · model-estimated confidence 85% · evidence sufficiency 59% (H2)

## Why
**1. The large original effect comes from one conflicted study, not three.** [3][4][6]
   - The original randomized trial with 412 students reported a 0.31 SD improvement; its preprint, conference and journal versions are one study. [3][4][6]
**2. Independent preregistered replications found a much smaller effect, or none.** [1][2]
   - A multi-site replication with 1,180 students found 0.12 SD. [1]
   - A direct replication with 640 students found no statistically significant effect (0.02 SD). [2]

_1 draft statement(s) were removed by the citation verifier (no evidence, or numbers not in the evidence)._

## Caveats
- Source independence: 8 sources with evidence reduce to 4 independent roots.
- Contradicted: 2 key claim(s) have independent evidence against them, e.g. "MemoLoop improves university exam scores".
- Thinly sourced: 3 of 5 key claims rest on a single independent source.
- Open gap [FAILED_REPLICATION]: ST_518a27a363 'MemoLoop: Adaptive Spaced Retrieval Improves University Exam' has a failed replication: which result holds, and why?
- Open gap [NO_REPLICATION]: C_89d9e35122: supported by a single study (ST_c38bb3b011) with no known replication
- Confidence values are model-estimated evidence beliefs from explicit heuristics, not calibrated probabilities.

## What would change our mind
1. A third preregistered replication with an effect above 0.2 SD
2. A meta-analysis pooling all randomized MemoLoop trials
3. Evidence that the effect depends on how the app is used (dose or subgroup analyses)
4. Evidence resolving: ST_518a27a363 'MemoLoop: Adaptive Spaced Retrieval Improves University Exam' has a failed replication: which result holds, and why?
5. Evidence resolving: C_89d9e35122: supported by a single study (ST_c38bb3b011) with no known replication
6. Evidence resolving: C_5e82fb0de7: no independent confirmation of 'MemoLoop had no statistically significant effect on final exam scores in a preregistered direct replication (0.02 SD, n=640)'

## Citations you can check
_Each link opens the page at the quoted text (text fragments; plain URL where unsupported)._

**[1]** [A preregistered multi-site replication of Lind et al. (2024)](https://journal-of-open-replication.example/2025/memoloop-multisite#:~:text=MemoLoop%20users%20scored%200.12%20standard,0.03%20to%200.21%29) — journal-of-open-replication.example, published 2025-09-10
   > “MemoLoop users scored 0.12 standard deviations higher on the final exam (95% CI 0.03 to 0.21)”
   > “finds a substantially smaller effect than the original study”
**[2]** [Preregistered direct replication of MemoLoop](https://journal-of-replication-studies.example/2026/memoloop#:~:text=MemoLoop%20users%20scored%200.02%20standard,not%20statistically%20significant) — journal-of-replication-studies.example, published 2026-02-03
   > “MemoLoop users scored 0.02 standard deviations higher on the final exam (95% CI -0.08 to 0.12, p = 0.71), which is not statistically significant”
   > “We failed to replicate the effect reported by Lind et al. (2024)”
**[3]** [MemoLoop: Adaptive Spaced Retrieval Improves University Exam Performance](https://journal-of-learning-research.example/article/10.5555/jlr.2025.0042#:~:text=MemoLoop%20users%20scored%200.31%20standard,p%20%3D%200.002%29) — journal-of-learning-research.example, published 2025-01-15
   > “MemoLoop users scored 0.31 standard deviations higher on the final exam (95% CI 0.12 to 0.50, p = 0.002)”
**[4]** [MemoLoop: Adaptive Spaced Retrieval Improves University Exam Performance](https://las-proceedings.example/2024/paper-17#:~:text=students%20using%20MemoLoop%20scored%200.31,0.12%20to%200.50%29) — las-proceedings.example, published 2024-06-20
   > “students using MemoLoop scored 0.31 standard deviations higher on the final exam than controls (95% CI 0.12 to 0.50)”
**[5]** [A pilot evaluation of MemoLoop](https://journal-of-classroom-studies.example/2023/memoloop-pilot#:~:text=Exam%20scores%20of%20the%20remaining,their%20previous%20term) — journal-of-classroom-studies.example, published 2023-11-02
   > “Exam scores of the remaining students improved by 0.8 standard deviations compared with their previous term”
**[6]** [MemoLoop: Adaptive Spaced Retrieval Improves University Exam Performance](https://preprints-archive.example/abs/2403.01234#:~:text=Students%20randomly%20assigned%20to%20use,p%20%3D%200.002%29) — preprints-archive.example, published 2024-03-12
   > “Students randomly assigned to use MemoLoop for one semester scored 0.31 standard deviations higher on the final exam than the control group (95% CI 0.12 to 0.50, p = 0.002)”
**[7]** [MemoLoop boosts grades, campus study finds](https://campus-news.example/2024/memoloop-boosts-grades) — campus-news.example, published 2024-03-20
**[8]** [EdTech roundup: MemoLoop](https://edtech-blog.example/memoloop-a-third-better) — edtech-blog.example, published 2024-03-22

## How the agent decided
_Decisions made by code during the run, in order, with their reasons._

1. agent selected: Next agent: GeneralResearcher (utility 0.95). Reason: no evidence collected yet: broad discovery first
2. scientific version resolved: 3 documents are versions of ONE work → 1 research lineage (ST_518a27a363): S_1e2b2e1e82 (peer_reviewed_article), S_76bda71feb (preprint), S_8121eb0c6d (conference_paper)
3. independence summary: 6 URLs with evidence → 4 publication families → 2 independent evidence roots
4. inference accepted: I_2c1d8a1fc4 accepted (plausible, score 0.65)
5. inference rejected: I_a83a45f1c4 rejected (weak): n=12, no control group and high attrition cannot establish an effect.
6. necessity assessed: C_788364b2a2 is a NECESSARY dependency of H1 (structural (sole premise)): sole accepted premise for this hypothesis
7. agent selected: Next agent: GapResearcher (utility 0.88). Reason: [MISSING_REQUIRED_DIMENSION] H2.R2 (H2): no evidence yet on 'replication results'
8. agent selected: Next agent: AdversarialResearcher (utility 0.81). Reason: leading hypothesis H1 (posterior 0.68) has not been challenged yet
9. stop decision: CONTINUE: 2 critical claim(s) below sufficiency, 0 open contradiction(s), 11 researchable gap(s); new independent roots this round: 2
10. contradiction found: S_9f2889d604 contradicts C_788364b2a2: "finds a substantially smaller effect than the original study"
11. contradiction found: S_55c264f1cc contradicts C_2f2f8ce686: "MemoLoop users scored 0.02 standard deviations higher on the final exam (95% CI -0.08 to 0"
12. contradiction found: S_55c264f1cc contradicts C_788364b2a2: "We failed to replicate the effect reported by Lind et al. (2024)"
13. study relation found: ST_6ac4252451 REPLICATES ST_518a27a363: "This replication confirms a positive effect of MemoLoop but finds a substantially smaller "
14. study relation found: ST_dc780eea4d FAILS_TO_REPLICATE ST_518a27a363: "We failed to replicate the effect reported by Lind et al. (2024)"
15. independence summary: 8 URLs with evidence → 6 publication families → 4 independent evidence roots
16. inference accepted: I_9acf278574 accepted (valid, score 0.90)
17. inference accepted: I_9c120fb6f2 accepted (valid, score 0.90)
18. necessity assessed: C_5e82fb0de7 is NOT a necessary dependency of H2 (model-based necessity assessment): other premises carry the conclusion without it
19. agent selected: Next agent: ReplicationResearcher (utility 0.86). Reason: [FAILED_REPLICATION] ST_518a27a363 'MemoLoop: Adaptive Spaced Retrieval Improves University Exam' has a failed replication: which result holds, and why?
20. agent selected: Next agent: IndependenceResearcher (utility 0.54). Reason: [NO_INDEPENDENT_SOURCE] C_5e82fb0de7: no independent confirmation of 'MemoLoop had no statistically significant effect on final exam scores in a preregistered di
21. stop decision: CONTINUE: 3 critical claim(s) below sufficiency, 2 open contradiction(s), 13 researchable gap(s); new independent roots this round: 2
22. stop decision: STOP (DIMINISHING_RETURNS): last research round produced no new independent evidence root; new independent roots this round: 0
23. statement rejected: support point dropped (no claim ids: unsupported factual statement): Adoption keeps growing every semester.

---

# Supporting detail


## Surviving hypotheses
| ID | Hypothesis | Prior | Posterior | Sufficiency | Inference validity | Status |
|---|---|---|---|---|---|---|
| H2 | MemoLoop has a small positive effect on exam scores (below 0.2 SD) | 35% | **85%** | 59% | 90% | active |
| H4 | MemoLoop's effect depends on context (only some students or settings benefit) | 20% | **20%** | 0% | n/a | insufficient |

Main surviving hypothesis: **H2** — MemoLoop has a small positive effect on exam scores (below 0.2 SD)
Strongest counter-hypothesis: **H3** — MemoLoop has no meaningful effect on exam scores

## Rejected / weakened hypotheses
- **H5** Public evidence is insufficient to judge MemoLoop's effect on exam scores: weakened, posterior 20% → 36%
- **H3** MemoLoop has no meaningful effect on exam scores: weakened, posterior 20% → 33%
- **H1** MemoLoop materially improves university exam scores (effect of at least 0.2 SD): rejected, posterior 35% → 1%
  - H1 inference not accepted: I_a83a45f1c4 (rejected): A pilot study found a 0.8 SD improvement — n=12, no control group and high attrition cannot establish an effect.

## Critical claims: supporting and contradicting evidence
#### C_2f2f8ce686: MemoLoop improves university exam scores
- Model-estimated posterior **85%** · evidence sufficiency **94%** · status `contested` · period: period unknown
- Raw sources: 8 · independent roots: **4** · history: 0.50 → 0.96 → 0.86 → 0.85
- SUPPORT [1]: “MemoLoop users scored 0.12 standard deviations higher on the final exam (95% CI 0.03 to 0.21)” — source 0.93 · study 0.95 · replication ×1.00 · independence 1.00 · LR 8
- SUPPORT [3]: “MemoLoop users scored 0.31 standard deviations higher on the final exam (95% CI 0.12 to 0.50, p = 0.002)” — source 0.93 · study 0.64 · replication ×0.72 · independence 1.00 · LR 2
- SUPPORT [4]: “students using MemoLoop scored 0.31 standard deviations higher on the final exam than controls (95% CI 0.12 to 0.50)” — source 0.78 · study 0.64 · replication ×0.72 · independence 0.00 · LR 1.25
- SUPPORT [5]: “Exam scores of the remaining students improved by 0.8 standard deviations compared with their previous term” — source 0.93 · study 0.15 · replication ×1.00 · independence 1.00 · LR 1.25
- AGAINST [2]: “MemoLoop users scored 0.02 standard deviations higher on the final exam (95% CI -0.08 to 0.12, p = 0.71), which is not statistically significant” — source 0.93 · study 0.91 · replication ×1.00 · independence 1.00 · LR 0.25
- MISSING: C_2f2f8ce686: independent sources disagree on 'MemoLoop improves university exam scores'

#### C_788364b2a2: MemoLoop raised final exam scores by 0.31 standard deviations in the Lind et al. randomized trial (n=412)
- Model-estimated posterior **12%** · evidence sufficiency **88%** · status `contested` · period: period unknown
- Raw sources: 5 · independent roots: **3** · history: 0.50 → 0.94 → 0.83 → 0.12
- SUPPORT [3]: “MemoLoop users scored 0.31 standard deviations higher on the final exam (95% CI 0.12 to 0.50, p = 0.002)” — source 0.93 · study 0.64 · replication ×0.72 · independence 1.00 · LR 2
- SUPPORT [4]: “students using MemoLoop scored 0.31 standard deviations higher on the final exam than controls (95% CI 0.12 to 0.50)” — source 0.78 · study 0.64 · replication ×0.72 · independence 0.00 · LR 1.25
- SUPPORT [6]: “Students randomly assigned to use MemoLoop for one semester scored 0.31 standard deviations higher on the final exam than the control group (95% CI 0.12 to 0.50, p = 0.002)” — source 0.59 · study 0.64 · replication ×0.72 · independence 0.00 · LR 1.25
- AGAINST [2]: “We failed to replicate the effect reported by Lind et al. (2024)” — source 0.93 · study 0.91 · replication ×1.00 · independence 1.00 · LR 0.125
- AGAINST [1]: “finds a substantially smaller effect than the original study” — source 0.93 · study 0.95 · replication ×1.00 · independence 1.00 · LR 0.5
- MISSING: C_788364b2a2: independent sources disagree on 'MemoLoop raised final exam scores by 0.31 standard deviations in the Lind et al. randomized trial (n=412)'

#### C_6340bdec73: MemoLoop raised final exam scores by 0.12 standard deviations in a preregistered multi-site replication (n=1,180)
- Model-estimated posterior **89%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.89
- SUPPORT [1]: “MemoLoop users scored 0.12 standard deviations higher on the final exam (95% CI 0.03 to 0.21)” — source 0.93 · study 0.95 · replication ×1.00 · independence 1.00 · LR 8
- MISSING: C_6340bdec73: no independent confirmation of 'MemoLoop raised final exam scores by 0.12 standard deviations in a preregistered multi-site replication (n=1,180)'
- MISSING: C_6340bdec73: supported by a single study (ST_6ac4252451) with no known replication

#### C_5e82fb0de7: MemoLoop had no statistically significant effect on final exam scores in a preregistered direct replication (0.02 SD, n=640)
- Model-estimated posterior **89%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.89
- SUPPORT [2]: “MemoLoop users scored 0.02 standard deviations higher on the final exam (95% CI -0.08 to 0.12, p = 0.71), which is not statistically significant” — source 0.93 · study 0.91 · replication ×1.00 · independence 1.00 · LR 8
- MISSING: C_5e82fb0de7: no independent confirmation of 'MemoLoop had no statistically significant effect on final exam scores in a preregistered direct replication (0.02 SD, n=640)'
- MISSING: C_5e82fb0de7: supported by a single study (ST_dc780eea4d) with no known replication

#### C_89d9e35122: Exam scores of MemoLoop pilot students improved by 0.8 standard deviations (n=12, no control group)
- Model-estimated posterior **56%** · evidence sufficiency **50%** · status `insufficient` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.56
- SUPPORT [5]: “Exam scores of the remaining students improved by 0.8 standard deviations compared with their previous term” — source 0.93 · study 0.15 · replication ×1.00 · independence 1.00 · LR 1.25
- MISSING: C_89d9e35122: supported by a single study (ST_c38bb3b011) with no known replication
- MISSING: C_89d9e35122: no independent confirmation of 'Exam scores of MemoLoop pilot students improved by 0.8 standard deviations (n=12, no control group)'
- MISSING: C_89d9e35122: only outdated evidence

## Source independence
**8 URLs with evidence → 6 publication families → 4 independent evidence roots.**
- Root S_76bda71feb (MemoLoop: Adaptive Spaced Retrieval Improves University Exam): 5 sources S_1e2b2e1e82, S_76bda71feb, S_8121eb0c6d, S_a8ee1251f3, S_e8a705548a

## Scientific study quality
- **ST_518a27a363** MemoLoop: Adaptive Spaced Retrieval Improves University Exam Performance: randomized_controlled_trial, n=412, peer reviewed=True, preregistered=False, quality **0.64**; versions: peer_reviewed_article (S_1e2b2e1e82), preprint (S_76bda71feb), conference_paper (S_8121eb0c6d)
  - ST_6ac4252451 REPLICATES ST_518a27a363
  - ST_dc780eea4d FAILS_TO_REPLICATE ST_518a27a363
  - result [verified]: final exam score SD=0.31 CI [0.12, 0.5] n=412
  - result [verified]: final exam score SD=0.31 CI [0.12, 0.5] n=412
  - result [verified]: final exam score SD=0.31 CI [0.12, 0.5] n=412
  - methodological notes: design prior 0.80 (randomized_controlled_trial); material conflict of interest (×0.76); authors are co-founders of the product; single-site trial; not peer reviewed (×0.9)
- **ST_c38bb3b011** A pilot evaluation of MemoLoop: observational_study, n=12, peer reviewed=True, preregistered=None, quality **0.15**; versions: peer_reviewed_article (S_d658e695b2)
  - result [verified]: exam score change vs previous term SD=0.8 CI [None, None] n=7
  - methodological notes: design prior 0.55 (observational_study); very small sample n=12 (×0.6); no control group (×0.7); high attrition (×0.65); no control group
- **ST_6ac4252451** A preregistered multi-site replication of Lind et al. (2024): randomized_controlled_trial, n=1180, peer reviewed=True, preregistered=True, quality **0.95**; versions: peer_reviewed_article (S_9f2889d604)
  - ST_6ac4252451 REPLICATES ST_518a27a363
  - result [verified]: final exam score SD=0.12 CI [0.03, 0.21] n=1180
  - methodological notes: design prior 0.80 (randomized_controlled_trial); large sample n=1180 (×1.05); preregistered (×1.08)
- **ST_dc780eea4d** Preregistered direct replication of MemoLoop: randomized_controlled_trial, n=640, peer reviewed=True, preregistered=True, quality **0.91**; versions: peer_reviewed_article (S_55c264f1cc)
  - ST_dc780eea4d FAILS_TO_REPLICATE ST_518a27a363
  - result [verified]: final exam score SD=0.02 CI [-0.08, 0.12] n=640
  - methodological notes: design prior 0.80 (randomized_controlled_trial); preregistered (×1.08)

## Research gaps
- **HIGH** [FAILED_REPLICATION] ST_518a27a363 'MemoLoop: Adaptive Spaced Retrieval Improves University Exam' has a failed replication: which result holds, and why?
- **HIGH** [NO_REPLICATION] C_89d9e35122: supported by a single study (ST_c38bb3b011) with no known replication
- **HIGH** [NO_INDEPENDENT_SOURCE] C_5e82fb0de7: no independent confirmation of 'MemoLoop had no statistically significant effect on final exam scores in a preregistered direct replication (0.02 SD, n=640)'
- **HIGH** [NO_INDEPENDENT_SOURCE] C_6340bdec73: no independent confirmation of 'MemoLoop raised final exam scores by 0.12 standard deviations in a preregistered multi-site replication (n=1,180)'
- **HIGH** [NO_REPLICATION] C_5e82fb0de7: supported by a single study (ST_dc780eea4d) with no known replication
- **HIGH** [NO_REPLICATION] C_6340bdec73: supported by a single study (ST_6ac4252451) with no known replication
- **MEDIUM** [NO_INDEPENDENT_SOURCE] C_89d9e35122: no independent confirmation of 'Exam scores of MemoLoop pilot students improved by 0.8 standard deviations (n=12, no control group)'
- **MEDIUM** [MISSING_REQUIRED_DIMENSION] H4.R2 (H4): no evidence yet on 'heterogeneity of effects across sites'
- **MEDIUM** [INSUFFICIENT_SAMPLE] ST_c38bb3b011: n=12 is too small to carry the claim alone
- **MEDIUM** [CONTRADICTORY_EVIDENCE] C_788364b2a2: independent sources disagree on 'MemoLoop raised final exam scores by 0.31 standard deviations in the Lind et al. randomized trial (n=412)'

## Why research stopped
- DIMINISHING_RETURNS: last research round produced no new independent evidence root
- Final agent bids: ReplicationResearcher 0.86, IndependenceResearcher 0.54, AdversarialResearcher 0.44, GapResearcher 0.32, ContradictionResearcher 0.24, GeneralResearcher 0.23, Synthesis 0.09, PrimarySourceResearcher 0.00

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

## All citations
[1] A preregistered multi-site replication of Lind et al. (2024) — https://journal-of-open-replication.example/2025/memoloop-multisite (journal-of-open-replication.example; published 2025-09-10; retrieved 2026-10-18; root S_9f2889d604)
[2] Preregistered direct replication of MemoLoop — https://journal-of-replication-studies.example/2026/memoloop (journal-of-replication-studies.example; published 2026-02-03; retrieved 2026-10-18; root S_55c264f1cc)
[3] MemoLoop: Adaptive Spaced Retrieval Improves University Exam Performance — https://journal-of-learning-research.example/article/10.5555/jlr.2025.0042 (journal-of-learning-research.example; published 2025-01-15; retrieved 2026-10-18; root S_76bda71feb)
[4] MemoLoop: Adaptive Spaced Retrieval Improves University Exam Performance — https://las-proceedings.example/2024/paper-17 (las-proceedings.example; published 2024-06-20; retrieved 2026-10-18; root S_76bda71feb)
[5] A pilot evaluation of MemoLoop — https://journal-of-classroom-studies.example/2023/memoloop-pilot (journal-of-classroom-studies.example; published 2023-11-02; retrieved 2026-10-18; root S_d658e695b2)
[6] MemoLoop: Adaptive Spaced Retrieval Improves University Exam Performance — https://preprints-archive.example/abs/2403.01234 (preprints-archive.example; published 2024-03-12; retrieved 2026-10-18; root S_76bda71feb)
[7] MemoLoop boosts grades, campus study finds — https://campus-news.example/2024/memoloop-boosts-grades (campus-news.example; published 2024-03-20; retrieved 2026-10-18; root S_76bda71feb)
[8] EdTech roundup: MemoLoop — https://edtech-blog.example/memoloop-a-third-better (edtech-blog.example; published 2024-03-22; retrieved 2026-10-18; root S_76bda71feb)

_Stats: {'iterations': 3, 'searches': 8, 'extractions': 8, 'model_calls': 33, 'hypothesis': 5, 'requirement': 8, 'source': 8, 'claim': 6, 'evidence': 18, 'document': 6, 'study': 4, 'result': 6, 'inference': 7, 'gap': 18, 'edges': 136, 'screened_out': 0, 'unverified_evidence': 0}_