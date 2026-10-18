# Research report: Does intermittent fasting lead to more weight loss than continuous calorie restriction in adults?

## Executive conclusion
**Current evidence status: INSUFFICIENT_EVIDENCE**

- The available evidence is insufficient to establish that intermittent fasting leads to greater weight loss than continuous calorie restriction in adults. [6][7]
- Randomized and meta-analytic comparisons have not shown a statistically significant greater reduction in body weight or BMI with intermittent fasting than with continuous restricted diets. [6][7]
- A claim that a systematic review included 20 randomized controlled trials comparing isocaloric intermittent fasting with calorie restriction is itself insufficiently supported. [1][2]
- Most trials were short, with a median follow-up of 12 weeks and only five trials lasting at least 52 weeks, so long-term comparative effects remain uncertain. [1]
- Intermittent fasting protocols have produced body-weight reductions, and alternate-day fasting reduced weight more than whole-day fasting in one comparison, but these findings do not establish superiority over continuous calorie restriction. [1][3][5][6]
- Evidence quality was low to moderate, and compliance above 80% was reported mainly in trials shorter than three months. [5][6]

## Surviving hypotheses
| ID | Hypothesis | Prior | Posterior | Sufficiency | Inference validity | Status |
|---|---|---|---|---|---|---|
| H5 | Publicly available evidence is insufficient to establish whether intermittent fasting produces greater weight loss than continuous calorie restriction in adults. (null) | 35% | **74%** | 100% | n/a | active |
| H2 | When total calorie intake is matched, intermittent fasting and continuous calorie restriction produce equivalent weight loss; apparent differences are explained by differences in actual intake or adherence rather than by fasting itself. | 50% | **50%** | 26% | n/a | insufficient |
| H1 | Intermittent fasting produces greater weight loss than continuous calorie restriction in adults, even when total energy intake is matched, due to fasting-specific metabolic, hormonal, or behavioral advantages. | 35% | **35%** | 26% | n/a | insufficient |
| H4 | The relative weight-loss effect is not universal; it depends on the specific intermittent fasting protocol and participant characteristics, with some protocols outperforming continuous restriction in some adult populations and not in others. | 35% | **35%** | 25% | n/a | insufficient |
| H3 | Continuous calorie restriction produces greater weight loss than intermittent fasting because a steady daily deficit is more consistently maintained and less likely to trigger compensatory overeating. | 20% | **20%** | 26% | n/a | insufficient |

Main surviving hypothesis: **H2** — When total calorie intake is matched, intermittent fasting and continuous calorie restriction produce equivalent weight loss; apparent differences are explained by differences in actual intake or adherence rather than by fasting itself.
Strongest counter-hypothesis: **H1** — Intermittent fasting produces greater weight loss than continuous calorie restriction in adults, even when total energy intake is matched, due to fasting-specific metabolic, hormonal, or behavioral advantages.

## Rejected / weakened hypotheses
- None.
  - H2 inference not accepted: I_fd4eaedee5 (rejected): Pooled comparisons show intermittent fasting and continuous calorie restriction produce similar weight loss, consistent with equivalent effects when intake is matched. — The premises only report no significant difference and similar mean weight loss; they do not establish matched intake, equivalence, or that intake/adherence explains apparent differences.
  - H1 inference not accepted: I_663e2df392 (rejected): Alternate day fasting reduced body weight more than continuous energy restriction, indicating at least one fasting protocol can outperform continuous restriction. — A single alternate day fasting comparison does not justify a general claim about all intermittent fasting, matched intake, or fasting-specific mechanisms.
  - H1 inference not accepted: I_0558ea0bff (rejected): Intermittent fasting was not associated with significantly greater body weight or BMI reduction than continuous restricted diets at any time point, weighing against a universal fasting-specific advantage. — The premise states that intermittent fasting was not associated with significantly greater reduction, directly contradicting the conclusion.
  - H4 inference not accepted: I_b0ec275941 (needs_evidence): Only alternate day fasting showed a weight reduction versus continuous restriction while other intermittent fasting strategies showed little additional benefit, suggesting effects depend on protocol. — The premises support protocol-dependent differences, especially alternate day fasting versus other strategies, but dependence on participant characteristics is not established.; R1: premise not established (weakest posterior 0.50)
  - H4 inference not accepted: I_cd73904e62 (rejected): Nonsignificant BMI differences alongside variable weight reductions across fasting protocols and superiority of alternate day fasting over whole-day fasting indicate protocol-dependent effects. — The premises show alternate day fasting differs from whole-day fasting and that reductions vary, but they do not establish dependence on participant characteristics or outperformance of continuous restriction.
  - H3 inference not accepted: I_e3e54e5643 (rejected): Equivalent weight loss between intermittent fasting and continuous restriction contradicts the claim that continuous restriction consistently produces greater loss. — The premises show no significant difference and similar weight loss, not greater continuous restriction loss or the proposed mechanism.

## Critical claims: supporting and contradicting evidence
#### C_07b6564453: The systematic review and meta-analysis included 20 randomized controlled trials comparing isocaloric intermittent fasting with calorie restriction.
- Model-estimated posterior **39%** · evidence sufficiency **56%** · status `insufficient` · period: period unknown
- Raw sources: 3 · independent roots: **2** · history: 0.50 → 0.39
- AGAINST [1]: “99 randomised clinical trials involving 6582 adults of varying health conditions (720 healthy, 5862 existing health conditions) were identified” — source 0.77 · study 0.76 · replication ×1.00 · independence 0.20 · LR 0.8
- AGAINST [2]: “meta-analyses to assess weighted mean difference (WMD) with 95% confidence intervals (CIs) were performed for eight randomized controlled trials (total participants = 728)” — source 0.77 · study 0.72 · replication ×1.00 · independence 0.19 · LR 0.8

#### C_2634ce8fb8: Alternate day fasting reduced body weight by a mean difference of -1.05 kg (95% CI -1.90 to -0.19) compared with whole day fasting, with moderate certainty of evidence.
- Model-estimated posterior **82%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 2 · independent roots: **1** · history: 0.50 → 0.67 → 0.89 → 0.82
- SUPPORT [1]: “Additionally, alternate day fasting showed a trivial reduction in body weight compared with both time restricted eating and whole day fasting (mean difference −1.69 kg (−2.49 to −0.88) and −1.05 kg (−1.90 to −0.19), respectively, both with moderate certainty of evidence)” — source 0.76 · study 0.76 · replication ×1.00 · independence 0.20 · LR 4
- SUPPORT [3]: “Additionally, alternate day fasting showed a trivial reduction in body weight compared with both time restricted eating and whole day fasting (mean difference −1.69 kg (−2.49 to −0.88) and −1.05 kg (−1.90 to −0.19), respectively, both with moderate certainty of evidence)” — source 0.76 · study 0.76 · replication ×1.00 · independence 0.20 · LR 2
- MISSING: C_2634ce8fb8: supported by a single study (ST_498ae782ce) with no known replication

#### C_158746ec26: The systematic review and network meta-analysis assessed the effect of intermittent fasting diets (alternate day fasting, time restricted eating, and whole day fasting) compared with continuous energy restriction or unrestricted (ad-libitum) diets on intermediate cardiometabolic outcomes from randomised clinical trials.
- Model-estimated posterior **80%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.80
- SUPPORT [4]: “OBJECTIVE To assess the effect of intermittent fasting diets, with continuous energy restriction or unrestricted (ad-libitum) diets on intermediate cardiometabolic outcomes from randomised clinical trials.
DESIGN Systematic review and network meta-analysis” — source 0.77 · study 0.76 · replication ×1.00 · independence 0.00 · LR 4

#### C_2b765ed6fa: The three main forms of intermittent fasting (alternate day fasting, the 5:2 diet, and time-restricted eating) produced body weight reductions ranging from 1% to 13% over 2 to 52 weeks.
- Model-estimated posterior **67%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [5]: “The three main forms of intermittent fasting (alternate day fasting [ADF], the 5:2 diet, and time‐restricted eating) are effective weight‐loss interventions, producing body weight reductions ranging from 1% to 13% over 2 to 52 weeks” — source 0.76 · study 0.94 · replication ×1.00 · independence 1.00 · LR 2
- MISSING: C_2b765ed6fa: no independent confirmation of 'The three main forms of intermittent fasting (alternate day fasting, the 5:2 diet, and time-restricted eating) produced body weight reductions ranging from 1% to 13% over 2 to 52 weeks.'
- MISSING: C_2b765ed6fa: supported by a single study (ST_f67ce204d7) with no known replication

#### C_765a30b9a1: Intermittent fasting was not associated with a significantly greater reduction of body weight or BMI at any time point with respect to controls or in respect to continuous restricted diets, with low-to-moderate quality of evidence.
- Model-estimated posterior **67%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [6]: “IF was not associated with a significantly greater reduction of body weight or BMI at any time point with respect to controls or in respect to continuous restricted diets, with low-to moderate quality of evidence” — source 0.77 · study 0.89 · replication ×1.00 · independence 1.00 · LR 2
- MISSING: C_765a30b9a1: no independent confirmation of 'Intermittent fasting was not associated with a significantly greater reduction of body weight or BMI at any time point with respect to controls or in respect to continuous restricted diets, with low-to-moderate quality of evidence.'
- MISSING: C_765a30b9a1: supported by a single study (ST_94b171666e) with no known replication

#### C_38ae53a441: Compliance was generally high (>80%) in intermittent fasting trials shorter than 3 months.
- Model-estimated posterior **67%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [5]: “Compliance was generally high (>80%) in trials shorter than 3 months” — source 0.76 · study 0.94 · replication ×1.00 · independence 1.00 · LR 2
- MISSING: C_38ae53a441: no independent confirmation of 'Compliance was generally high (>80%) in intermittent fasting trials shorter than 3 months.'
- MISSING: C_38ae53a441: supported by a single study (ST_f67ce204d7) with no known replication

#### C_2b3d26bcc7: Eligibility criteria selected randomised clinical trials comparing intermittent fasting diets (alternate day fasting, time restricted eating, and whole day fasting) with continuous energy restriction or unrestricted diets.
- Model-estimated posterior **80%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.80
- SUPPORT [4]: “ELIGIBILITY CRITERIA FOR SELECTING STUDIES Randomised clinical trials comparing the association of intermittent fasting diets (alternate day fasting, time restricted eating, and whole d” — source 0.77 · study 0.76 · replication ×1.00 · independence 0.00 · LR 4

#### C_39da99e30f: Almost all (92%) of the identified randomised clinical trials were parallel in design, with a median follow-up time of 12 weeks (range 3–52 weeks); only five trials extended to 52 weeks or more.
- Model-estimated posterior **80%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.80
- SUPPORT [1]: “almost all (92%) were parallel in study design, with a median follow-up time of 12 weeks (range 3-52 weeks), a median sample size of 46 participants,32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 and most trials (81%) were designed for weight loss. A small subset of trials had a duration of three weeks, the minimum threshold, typically reporting modest weight reductions (eg, 0.5-2 kg), consistent with early phase feasibility studies. Conversely, only five trials extended to 52 weeks or more, limiting the feasibility of undertaking a robust analysis for very long term outcomes” — source 0.77 · study 0.76 · replication ×1.00 · independence 0.20 · LR 4

#### C_7347d40528: Alternate-day fasting lowers body weight, body fat, and total cholesterol in adults with overweight within 6 months compared to the control.
- Model-estimated posterior **67%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [2]: “body-weight), body fat, and total cholesterol in adults with overweight within 6 months compared to the control” — source 0.77 · study 0.72 · replication ×1.00 · independence 0.19 · LR 2
- MISSING: C_7347d40528: no independent confirmation of 'Alternate-day fasting lowers body weight, body fat, and total cholesterol in adults with overweight within 6 months compared to the control.'
- MISSING: C_7347d40528: supported by a single study (ST_08b177b76f) with no known replication

#### C_3611b079fc: There was no difference between ADF and continuous energy restriction, time-restricted feeding, or control with regard to lean body mass.
- Model-estimated posterior **67%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [2]: “However, there was no difference between ADF and continuous energy restriction, time-restricted feeding, or control with regard to [lean body mass” — source 0.77 · study 0.72 · replication ×1.00 · independence 0.19 · LR 2
- MISSING: C_3611b079fc: no independent confirmation of 'There was no difference between ADF and continuous energy restriction, time-restricted feeding, or control with regard to lean body mass.'
- MISSING: C_3611b079fc: supported by a single study (ST_08b177b76f) with no known replication

#### C_391de60e11: The network meta-analysis identified 99 randomised clinical trials.
- Model-estimated posterior **80%** · evidence sufficiency **50%** · status `likely` · period: period unknown
- Raw sources: 1 · independent roots: **1** · history: 0.50 → 0.80
- SUPPORT [3]: “99 randomised clinical trials involving 6582 adults of varying health conditions (720 healthy, 5862 existing health conditions) were identified” — source 0.77 · study 0.76 · replication ×1.00 · independence 0.20 · LR 4

#### C_5c2cff2244: In a 2022 meta-analysis by Zhang et al., the difference in BMI between intermittent fasting and continuous energy restriction failed to reach statistical significance.
- Model-estimated posterior **67%** · evidence sufficiency **34%** · status `likely` · period: period unknown
- Raw sources: 2 · independent roots: **1** · history: 0.50 → 0.67
- SUPPORT [7] (reported speech): “the difference in BMI between the two intervention failed to reach statistical significance” — source 0.76 · study 0.94 · replication ×1.00 · independence 1.00 · LR 2
- MISSING: C_5c2cff2244: supported by a single study (ST_62d1b04de4) with no known replication
- MISSING: C_5c2cff2244: 2 sources but only 1 independent root

## Source independence
**8 URLs with evidence → 6 publication families → 4 independent evidence roots.**
- Root S_533e8bcbae (Intermittent fasting strategies and their effects on body we): 3 sources S_533e8bcbae, S_5558e11fcd, S_769d81ca77
- Root S_7ec260fabb (Effectiveness of intermittent fasting for weight loss in ind): 3 sources S_7ec260fabb, S_84bd455455, S_b090e92842
- 14 source(s) screened out before extraction, e.g. S_a972e388b0 (duplicate source: same title on the same site as S_a05f0bd78); S_ecd46974e8 (Prezi presentation, not a primary source; commentary only); S_c8567287be (Search aggregator page listing multiple studies, not a prima)

## Scientific study quality
- **ST_62d1b04de4** Intermittent fasting and health outcomes: an umbrella review of systematic reviews and meta-analyses of randomised controlled trials: meta_analysis, n=2483, peer reviewed=None, preregistered=None, quality **0.94**; versions: systematic_review (S_6f57458b6a)
  - result [verified]: Fasting glucose in participants with obesity MD=-2.17 CI [-2.78, -1.55] n=None
  - result [verified]: Fasting glucose in participants without obesity MD=-0.96 CI [-3.04, 1.13] n=None
  - result [verified]: Fat mass MD=-1.26 CI [-1.57, -0.95] n=1610
  - methodological notes: design prior 0.85 (meta_analysis); large sample n=2483 (×1.05); Secondary synthesis of prior reviews/meta-analyses rather than a primary trial; Follow-up durations in included studies were short (4 to 12 weeks for the fat-mass comparison discussed); Sample sizes varied across included meta-analyses
- **ST_e6da544c2d** Is isocaloric intermittent fasting superior to calorie restriction? A systematic review and meta-analysis of RCTs: meta_analysis, n=7, peer reviewed=None, preregistered=None, quality **0.54**; versions: meta_analysis (S_84bd455455)
  - result [verified]: Hunger levels SMD=-0.37 CI [0.12, 0.62] n=None
  - result [verified]: Fatigue OR=1.79 CI [1.03, 3.09] n=None
  - result [verified]: Total events of side effects OR=1.51 CI [1.14, 2.0] n=None
  - methodological notes: design prior 0.85 (meta_analysis); very small sample n=7 (×0.6); Only seven RCTs were included; total participant count is not reported in the provided text.; Inclusion was restricted to English-language, peer-reviewed RCTs with durations of 3-12 months.; Studies were required to be isocaloric; trials with considerable differences in calorie restriction between groups were excluded.
- **ST_f67ce204d7** A meta‐analysis comparing the effectiveness of alternate day fasting, the 5:2 diet, and time‐restricted eating for weight loss: meta_analysis, n=1768, peer reviewed=None, preregistered=None, quality **0.94**; versions: meta_analysis (S_a05f0bd781)
  - result [verified]: Weight loss: intermittent fasting regimens vs caloric energy restriction mean difference (kg)=0.26 CI [-0.31, 0.84] n=1768
  - result [verified]: Compliance in intermittent fasting trials percent=None CI [None, None] n=None
  - result [verified]: Body weight reduction with intermittent fasting regimens percent of body weight=None CI [None, None] n=None
  - methodological notes: design prior 0.85 (meta_analysis); large sample n=1768 (×1.05); The majority of the studies reviewed had small sample sizes, potentially limiting their ability to detect significant differences between intervention groups.; The maximum length of the included studies is 12 months, which limits the applicability to longer-term health outcomes.; Meal timing, duration of fasting, and background diet differed from study to study and were not controlled for in the present analysis.
- **ST_94b171666e** Effectiveness of intermittent fasting for weight loss in individuals with obesity: A meta-analysis of randomized controlled trials: meta_analysis, n=540, peer reviewed=None, preregistered=None, quality **0.89**; versions: meta_analysis (S_7ec260fabb)
  - result [verified]: Body weight and BMI reduction Mean difference (IF vs controls)=None CI [None, None] n=540
  - result [verified]: Weight loss: IF vs non-intermittent fasting diets =None CI [None, None] n=540
  - result [unverified]: Alternate day fasting vs time restricted eating efficacy =None CI [None, None] n=540
  - methodological notes: design prior 0.85 (meta_analysis); Only 9 trials enrolling 540 patients were included.; Evidence quality was described as low-to-moderate.; Data on psychological parameters and overall well-being were insufficient for a formal meta-analysis.; LDL cholesterol reduction was observed only at 2-4 months, not in the longer term.
- **ST_498ae782ce** Intermittent fasting strategies and their effects on body weight and other cardiometabolic risk factors: systematic review and network meta-analysis of randomised clinical trials: meta_analysis, n=99, peer reviewed=True, preregistered=None, quality **0.76**; versions: meta_analysis (S_769d81ca77), systematic_review (S_533e8bcbae), meta_analysis (S_5558e11fcd)
  - result [verified]: Body weight (continuous energy restriction vs ad-libitum diet, <24 weeks) kg=-2.09 CI [-2.77, -1.41] n=76
  - result [verified]: Body weight (continuous energy restriction vs ad-libitum diet, ≥24 weeks) kg=-2.21 CI [-3.72, -0.7] n=17
  - result [verified]: Body weight (alternate day fasting vs continuous energy restriction) =None CI [None, None] n=None
  - methodological notes: design prior 0.85 (meta_analysis); sample size not reported (×0.85); The review assesses intermediate cardiometabolic outcomes rather than clinical endpoints.; Network meta-analysis was used because few randomised clinical trials directly compared intermittent fasting strategies, relying partly on indirect comparisons.; Only partial text is available in the provided excerpt; quantitative results are not included.
- **ST_08b177b76f** Effect of alternate-day fasting on obesity and cardiometabolic risk: A systematic review and meta-analysis: meta_analysis, n=n/a, peer reviewed=None, preregistered=None, quality **0.72**; versions: meta_analysis (S_b090e92842)
  - result [verified]: BMI WMD=-0.73 CI [-1.13, -0.34] n=None
  - result [verified]: Fat mass WMD=-1.27 CI [-2.09, -0.46] n=None
  - result [verified]: Total cholesterol WMD=-8.14 CI [-14.59, -1.69] n=None
  - methodological notes: design prior 0.85 (meta_analysis); sample size not reported (×0.85); Significant intervention effects were reported only for subgroups: comparison with control, overweight participants, and study duration under 6 months.; The available text is an article preview; full methods, sample size, heterogeneity, and risk-of-bias details are not shown.

## Research gaps
- **HIGH** [WEAK_INFERENCE] I_fd4eaedee5 → H2: needs evidence on 'Evidence that total calorie intake was matched between arms'
- **HIGH** [WEAK_INFERENCE] I_fd4eaedee5 → H2: needs evidence on 'A predefined equivalence margin'
- **HIGH** [NO_INDEPENDENT_SOURCE] C_59be92ab2f: no independent confirmation of 'The combination of intermittent fasting and calorie restriction reduced visceral fat mass by 1.51% from baseline to 10–12 months compared with continuous calorie restriction.'
- **HIGH** [NO_PRIMARY_SOURCE] C_59be92ab2f: no primary source for 'The combination of intermittent fasting and calorie restriction reduced visceral fat mass by 1.51% from baseline to 10–12 months compared with continuous calorie restriction.'
- **HIGH** [UNVERIFIED_EXTRACTION] C_0f88c5a407: 'Alternate-day fasting does not lower lean body mass compared to continuous energy restriction, time-restricted feeding, or control.' was extracted but its excerpt could not be located in the source
- **MEDIUM** [NO_INDEPENDENT_SOURCE] C_765a30b9a1: no independent confirmation of 'Intermittent fasting was not associated with a significantly greater reduction of body weight or BMI at any time point with respect to controls or in respect to continuous restricted diets, with low-to-moderate quality of evidence.'
- **MEDIUM** [NO_REPLICATION] C_2634ce8fb8: supported by a single study (ST_498ae782ce) with no known replication
- **MEDIUM** [NO_REPLICATION] C_5c2cff2244: supported by a single study (ST_62d1b04de4) with no known replication
- **MEDIUM** [NO_REPLICATION] C_765a30b9a1: supported by a single study (ST_94b171666e) with no known replication
- **MEDIUM** [NO_INDEPENDENT_SOURCE] C_3611b079fc: no independent confirmation of 'There was no difference between ADF and continuous energy restriction, time-restricted feeding, or control with regard to lean body mass.'

## What would change our mind
1. Large randomized trials of at least 12 months that directly compare intermittent fasting with continuous calorie restriction while verifying matched energy intake and measuring adherence and compensatory eating.
2. A high-quality systematic review or meta-analysis of isocaloric comparisons with predefined equivalence margins and low risk of bias.
3. Protocol- and population-stratified analyses for alternate-day fasting, 5:2, and time-restricted eating, including independent replication of any differential weight-loss or visceral-fat claim.
4. Primary-source verification and independent confirmation of the claim that an isocaloric review included 20 randomized controlled trials.
5. Evidence resolving: I_fd4eaedee5 → H2: needs evidence on 'Evidence that total calorie intake was matched between arms'
6. Evidence resolving: I_fd4eaedee5 → H2: needs evidence on 'A predefined equivalence margin'
7. Evidence resolving: C_59be92ab2f: no independent confirmation of 'The combination of intermittent fasting and calorie restriction reduced visceral fat mass by 1.51% from baseline to 10–12 months compared with continuous calorie restriction.'

## Why research stopped
- BUDGET_EXHAUSTED: model call budget exhausted
- Final agent bids: IndependenceResearcher 1.00, GapResearcher 0.77, AdversarialResearcher 0.72, PrimarySourceResearcher 0.66, ReplicationResearcher 0.65, GeneralResearcher 0.15, ContradictionResearcher 0.00, Synthesis 0.00

## Limitations and method
- Hypothesis-first research: competing hypotheses and evidence requirements were generated before searching.
- LLMs proposed claims, stances and inferences; code verified excerpts verbatim, counted sources and computed every score.
- Probabilities are model-estimated evidence beliefs from heuristic likelihood ratios, NOT calibrated probabilities.
- Evidence from one provenance cluster counts once; derivatives add 15% of their weight.
- Source credibility uses heuristic priors by source type, adjusted per claim category; no audited ratings.
- Scientific evidence is weighted by a deterministic study-quality score and replication factors; peer review alone is not decisive.
- Research agents were chosen each round by heuristic utility bids, not by a fixed pipeline.
- 14 source(s) were screened out before extraction; reasons are preserved (negative provenance).
- Stop reason: BUDGET_EXHAUSTED — model call budget exhausted

## Citations
[1] Intermittent fasting strategies and their effects on body weight and other cardiometabolic risk factors: systematic review and network meta-analysis of randomised clinical trials — https://pmc.ncbi.nlm.nih.gov/articles/PMC12175170 (nih.gov; published 2025-06-18; retrieved 2026-10-18; root S_533e8bcbae)
[2] Effect of alternate-day fasting on obesity and cardiometabolic risk: A systematic review and meta-analysis — https://www.sciencedirect.com/science/article/abs/pii/S0026049520302006 (sciencedirect.com; published unknown; retrieved 2026-10-18; root S_7ec260fabb)
[3] Intermittent fasting strategies and their effects on body weight and other cardiometabolic risk factors: systematic review and network meta-analysis of randomised clinical trials — https://www.bmj.com/content/389/bmj-2024-082007 (bmj.com; published unknown; retrieved 2026-10-18; root S_533e8bcbae)
[4] Intermittent fasting strategies and their effects on body weight and ... — https://www.bmj.com/content/bmj/389/bmj-2024-082007.full.pdf (bmj.com; published 2025-05-07; retrieved 2026-10-18; root S_533e8bcbae)
[5] A meta‐analysis comparing the effectiveness of alternate day fasting, the 5:2 diet, and time‐restricted eating for weight loss — https://pmc.ncbi.nlm.nih.gov/articles/PMC10098946 (nih.gov; published 2022-11-08; retrieved 2026-10-18; root S_a05f0bd781)
[6] Effectiveness of intermittent fasting for weight loss in individuals with obesity: A meta-analysis of randomized controlled trials — https://www.sciencedirect.com/science/article/pii/S0939475323001862 (sciencedirect.com; published unknown; retrieved 2026-10-18; root S_7ec260fabb)
[7] Intermittent fasting and health outcomes: an umbrella review of systematic reviews and meta-analyses of randomised controlled trials — https://pmc.ncbi.nlm.nih.gov/articles/PMC10945168 (nih.gov; published 2024-03-11; retrieved 2026-10-18; root S_6f57458b6a)

_Stats: {'iterations': 2, 'searches': 10, 'extractions': 10, 'model_calls': 37, 'hypothesis': 5, 'requirement': 14, 'source': 56, 'claim': 75, 'evidence': 87, 'document': 8, 'study': 6, 'result': 21, 'inference': 6, 'gap': 38, 'edges': 459, 'screened_out': 14, 'unverified_evidence': 10}_