"""SYNTHETIC scientific scenario: "Does the MemoLoop app materially improve university exam scores?"

Fictional studies and authors on reserved ``.example`` domains. What the real pipeline must uncover:
  - an arXiv-style preprint, a conference paper and a journal article are ONE work (one research lineage),
    not three confirmations; the authors are co-founders of the product (conflict of interest);
  - a campus news story and a blog repost derive from the preprint;
  - a peer-reviewed pilot (n=12, no control group, high attrition) still scores low quality;
  - the replication gap makes the policy engine select a ReplicationResearcher, which finds a preregistered
    multi-site replication (smaller effect, REPLICATES) and a preregistered direct replication with no
    significant effect (FAILS_TO_REPLICATE); confidence in a material effect falls.
"""

from __future__ import annotations

from datetime import date

from ..models import (
    HypothesesOutput, HypothesisProposal, InferenceProposal, InferenceVerdict, QuestionAnalysis, RequirementProposal, ResultProposal,
    ScientificReviewOutput, StudyProposal, StudyRelationProposal, SynthesisOutput, SynthesisSentence,
)
from .base import Page, PageClaim, Scenario, find

TITLE = "MemoLoop: Adaptive Spaced Retrieval Improves University Exam Performance"
AUTHORS = ["Mara Lind", "Tobi Okafor", "Jana Haas"]
GENERAL = dict(subject="MemoLoop", predicate="effect on university exam scores", obj="improves",
               nl="MemoLoop improves university exam scores", category="technical", req_keywords=("randomized",), importance="high")
EFF31 = dict(subject="MemoLoop", predicate="exam score effect Lind et al. 2024 RCT", obj="0.31 SD",
             nl="MemoLoop raised final exam scores by 0.31 standard deviations in the Lind et al. randomized trial (n=412)",
             category="technical", req_keywords=("randomized", "effect size"), importance="high")

S1_RESULT = ("Students randomly assigned to use MemoLoop for one semester scored 0.31 standard deviations higher on the final exam "
             "than the control group (95% CI 0.12 to 0.50, p = 0.002).")
S2_RESULT = "students using MemoLoop scored 0.31 standard deviations higher on the final exam than controls (95% CI 0.12 to 0.50)."
S3_RESULT = "MemoLoop users scored 0.31 standard deviations higher on the final exam (95% CI 0.12 to 0.50, p = 0.002)."
S6_RESULT = "MemoLoop users scored 0.12 standard deviations higher on the final exam (95% CI 0.03 to 0.21)."
S7_RESULT = ("MemoLoop users scored 0.02 standard deviations higher on the final exam (95% CI -0.08 to 0.12, p = 0.71), "
             "which is not statistically significant.")
S8_RESULT = "Exam scores of the remaining students improved by 0.8 standard deviations compared with their previous term."
PRESS = ("According to a study posted at preprints-archive.example/abs/2403.01234, students who used the MemoLoop app did better on exams. "
         "\"MemoLoop boosts grades by a third of a letter grade,\" said co-founder Mara Lind. The study involved 412 students.")


def _orig(peer: bool, venue: str | None, excerpt: str, year: int, arxiv: str | None = "2403.01234", doi: str | None = None) -> ScientificReviewOutput:
    return ScientificReviewOutput(is_empirical_study=True, study=StudyProposal(
        title=TITLE, authors=AUTHORS, venue=venue, year=year, arxiv_id=arxiv, doi=doi, peer_reviewed=peer,
        study_design="randomized controlled trial", sample_size=412, control_group=True, randomized=True, blinded=False,
        preregistered=False, attrition="low", conflict_of_interest="material", code_available=False, data_available=False,
        methodological_warnings=["authors are co-founders of the product", "single-site trial"]),
        results=[ResultProposal(outcome="final exam score", effect_size=0.31, effect_measure="SD", ci_low=0.12, ci_high=0.50,
                                p_value=0.002, sample_size=412, exact_excerpt=excerpt)])


PAGES: list[Page] = [
    Page("https://preprints-archive.example/abs/2403.01234", TITLE, date(2024, 3, 12),
         f"arXiv:2403.01234v2 [cs.CY] 12 Mar 2024. {TITLE}. Mara Lind, Tobi Okafor, Jana Haas. Abstract. We report a randomized controlled "
         f"trial with 412 first-year university students. {S1_RESULT} The trial was not preregistered. Conflict of interest: M. Lind and "
         "T. Okafor are co-founders of MemoLoop. This is a preprint and has not been peer reviewed.",
         (("memoloop", "randomized"), ("memoloop", "study")), 0.90,
         [PageClaim(excerpt=S1_RESULT, **EFF31), PageClaim(excerpt=S1_RESULT, **GENERAL)],
         doc_type="preprint", review=_orig(False, None, S1_RESULT, 2024)),
    Page("https://las-proceedings.example/2024/paper-17", TITLE, date(2024, 6, 20),
         f"Proceedings of the 2024 Conference on Learning at Scale, pages 141-150. {TITLE}. Mara Lind, Tobi Okafor, Jana Haas. Also available "
         f"as arXiv:2403.01234. In a randomized controlled trial with 412 first-year students, {S2_RESULT}",
         (("memoloop", "study"), ("memoloop", "randomized")), 0.84,
         [PageClaim(excerpt=S2_RESULT, **EFF31), PageClaim(excerpt=S2_RESULT, **GENERAL)],
         doc_type="conference_paper", review=_orig(True, "Learning at Scale 2024", S2_RESULT, 2024)),
    Page("https://journal-of-learning-research.example/article/10.5555/jlr.2025.0042", TITLE, date(2025, 1, 15),
         f"Journal of Learning Research 18(2), 2025. DOI: 10.5555/jlr.2025.0042. Peer-reviewed article. {TITLE}. M. Lind, T. Okafor, J. Haas. "
         f"An earlier version appeared as arXiv:2403.01234 and at Learning at Scale 2024. In a randomized controlled trial with 412 "
         f"first-year students, {S3_RESULT} Funding: MemoLoop GmbH.",
         (("memoloop", "randomized"),), 0.82,
         [PageClaim(excerpt=S3_RESULT, **EFF31), PageClaim(excerpt=S3_RESULT, **GENERAL)],
         doc_type="peer_reviewed_article", review=_orig(True, "Journal of Learning Research", S3_RESULT, 2025, None, "10.5555/jlr.2025.0042")),
    Page("https://campus-news.example/2024/memoloop-boosts-grades", "MemoLoop boosts grades, campus study finds", date(2024, 3, 20),
         f"MemoLoop boosts grades, campus study finds. {PRESS}",
         (("memoloop", "grades"),), 0.80,
         [PageClaim(excerpt="According to a study posted at preprints-archive.example/abs/2403.01234, students who used the MemoLoop app did better on exams.",
                    attributed_to="Lind et al. study", **GENERAL)],
         doc_type="news_article"),
    Page("https://edtech-blog.example/memoloop-a-third-better", "EdTech roundup: MemoLoop", date(2024, 3, 22),
         f"EdTech roundup. MemoLoop boosts grades, campus study finds. {PRESS} We are impressed.",
         (("memoloop", "grades"),), 0.70,
         [PageClaim(excerpt="According to a study posted at preprints-archive.example/abs/2403.01234, students who used the MemoLoop app did better on exams.",
                    attributed_to="Lind et al. study", **GENERAL)],
         doc_type="blog"),
    Page("https://journal-of-classroom-studies.example/2023/memoloop-pilot", "A pilot evaluation of MemoLoop", date(2023, 11, 2),
         "Journal of Classroom Studies (peer reviewed), 2023. A pilot evaluation of MemoLoop. Twelve students used MemoLoop for six weeks; "
         f"there was no control group, and five of the twelve students dropped out before the final exam. {S8_RESULT}",
         (("memoloop", "study"),), 0.65,
         [PageClaim("Exam scores of MemoLoop pilot students improved by 0.8 standard deviations (n=12, no control group)", "MemoLoop",
                    "exam score change pilot 2023", "0.8 SD", S8_RESULT, "technical", None, ("effect size",), "medium"),
          PageClaim(excerpt=S8_RESULT, **GENERAL)],
         doc_type="peer_reviewed_article",
         review=ScientificReviewOutput(is_empirical_study=True, study=StudyProposal(
             title="A pilot evaluation of MemoLoop", authors=["R. Feld"], venue="Journal of Classroom Studies", year=2023, peer_reviewed=True,
             study_design="observational study", sample_size=12, control_group=False, randomized=False, attrition="high",
             methodological_warnings=["no control group", "5 of 12 participants dropped out"]),
             results=[ResultProposal(outcome="exam score change vs previous term", effect_size=0.8, effect_measure="SD", sample_size=7,
                                     exact_excerpt=S8_RESULT)])),
    Page("https://journal-of-open-replication.example/2025/memoloop-multisite", "A preregistered multi-site replication of Lind et al. (2024)",
         date(2025, 9, 10),
         "Journal of Open Replication 4, 2025. DOI: 10.5555/jor.2025.0107. Peer-reviewed registered report. A preregistered multi-site "
         f"replication of Lind et al. (2024), \"{TITLE}\". Six universities, 1,180 students, randomized at the course-section level. "
         f"{S6_RESULT} This replication confirms a positive effect of MemoLoop but finds a substantially smaller effect than the original "
         "study. Authors declare no conflicts of interest.",
         (("replication",), ("replicate",), ("independent", "preregistered")), 0.86,
         [PageClaim("MemoLoop raised final exam scores by 0.12 standard deviations in a preregistered multi-site replication (n=1,180)",
                    "MemoLoop", "exam score effect multi-site replication 2025", "0.12 SD", S6_RESULT, "technical", None,
                    ("replication", "effect size"), "high"),
          PageClaim(excerpt=S6_RESULT, **GENERAL)],
         [(("0.31",), "finds a substantially smaller effect than the original study")],
         doc_type="peer_reviewed_article",
         review=ScientificReviewOutput(is_empirical_study=True, study=StudyProposal(
             title="A preregistered multi-site replication of Lind et al. (2024)", authors=["S. Ortega", "K. Brandt"], venue="Journal of Open Replication",
             year=2025, doi="10.5555/jor.2025.0107", peer_reviewed=True, study_design="randomized controlled trial", sample_size=1180,
             control_group=True, randomized=True, preregistered=True, attrition="low", conflict_of_interest="none_declared", data_available=True),
             results=[ResultProposal(outcome="final exam score", effect_size=0.12, effect_measure="SD", ci_low=0.03, ci_high=0.21, sample_size=1180,
                                     exact_excerpt=S6_RESULT)],
             relations=[StudyRelationProposal(other_study_title=TITLE, relation="REPLICATES",
                                              exact_excerpt="This replication confirms a positive effect of MemoLoop but finds a substantially smaller effect than the original study.")])),
    Page("https://journal-of-replication-studies.example/2026/memoloop", "Preregistered direct replication of MemoLoop", date(2026, 2, 3),
         "Journal of Replication Studies, 2026. Preregistered direct replication, n = 640 students at two universities. We failed to replicate "
         f"the effect reported by Lind et al. (2024) in \"{TITLE}\". {S7_RESULT}",
         (("replication",), ("replicate",), ("no", "effect")), 0.84,
         [PageClaim("MemoLoop had no statistically significant effect on final exam scores in a preregistered direct replication (0.02 SD, n=640)",
                    "MemoLoop", "exam score effect direct replication 2026", "0.02 SD", S7_RESULT, "technical", None,
                    ("replication", "failed", "null"), "high")],
         [(("improves",), S7_RESULT), (("0.31",), "We failed to replicate the effect reported by Lind et al. (2024)")],
         doc_type="peer_reviewed_article",
         review=ScientificReviewOutput(is_empirical_study=True, study=StudyProposal(
             title="Preregistered direct replication of MemoLoop", authors=["A. Nwosu", "P. Kalnins"], venue="Journal of Replication Studies",
             year=2026, peer_reviewed=True, study_design="randomized controlled trial", sample_size=640, control_group=True, randomized=True,
             preregistered=True, attrition="low", conflict_of_interest="none_declared"),
             results=[ResultProposal(outcome="final exam score", effect_size=0.02, effect_measure="SD", ci_low=-0.08, ci_high=0.12, p_value=0.71,
                                     sample_size=640, exact_excerpt=S7_RESULT)],
             relations=[StudyRelationProposal(other_study_title=TITLE, relation="FAILS_TO_REPLICATE",
                                              exact_excerpt="We failed to replicate the effect reported by Lind et al. (2024)")])),
]

STANCES = [
    ("finds a substantially smaller effect than the original study", "0.31", "contradicts", "partial", "direct"),
    ("We failed to replicate the effect reported by Lind", "0.31", "contradicts", "explicit", "direct"),
    ("which is not statistically significant", "improves", "contradicts", "strong", "direct"),
]


class ScienceScenario(Scenario):
    name = "science"
    question = "Does the MemoLoop spaced-repetition app materially improve university exam scores?"
    pages = PAGES
    stances = STANCES
    high_impact = ("replication", "0.31", "effect", "randomized", "single study")
    necessary_keywords = ("multi-site",)
    default_queries = {
        "GeneralResearcher": ["MemoLoop exam scores randomized trial", "MemoLoop spaced repetition study", "MemoLoop university students grades"],
        "ReplicationResearcher": ["MemoLoop replication Lind et al. 2024", "MemoLoop failed to replicate"],
        "AdversarialResearcher": ["MemoLoop no effect exam scores", "MemoLoop criticism conflict of interest"],
        "IndependenceResearcher": ["MemoLoop independent preregistered study"],
        "GapResearcher": ["MemoLoop effect size replication studies"],
        "PrimarySourceResearcher": ["MemoLoop trial preregistration data"],
        "ContradictionResearcher": ["MemoLoop replication effect size"],
    }
    query_table = {"ReplicationResearcher": [("replication", "MemoLoop replication Lind et al. 2024"), ("single study", "MemoLoop failed to replicate")]}

    def analysis(self) -> QuestionAnalysis:
        return QuestionAnalysis(
            normalized_question=self.question, decision_context="whether a university should license MemoLoop for first-year courses",
            key_entities=["MemoLoop"], temporal_scope="2023 to 2026", geographic_scope=None,
            hidden_assumptions=["'materially' means an effect of at least 0.2 standard deviations"],
            dimensions=["randomized evidence", "effect size", "independent replication", "conflicts of interest"],
            ambiguity_notes=["outcome taken as final exam score, not long-term retention of knowledge"])

    def hypotheses(self) -> HypothesesOutput:
        R = RequirementProposal
        return HypothesesOutput(hypotheses=[
            HypothesisProposal(key="H1", text="MemoLoop materially improves university exam scores (effect of at least 0.2 SD)", plausibility="medium",
                               requirements=[R(description="randomized controlled evidence", importance="high"),
                                             R(description="independent replication", importance="high"),
                                             R(description="effect size magnitude", importance="high")]),
            HypothesisProposal(key="H2", text="MemoLoop has a small positive effect on exam scores (below 0.2 SD)", plausibility="medium",
                               requirements=[R(description="effect size estimates across independent studies", importance="high"),
                                             R(description="replication results", importance="high")]),
            HypothesisProposal(key="H3", text="MemoLoop has no meaningful effect on exam scores", plausibility="low",
                               requirements=[R(description="null or failed replication results", importance="high")]),
            HypothesisProposal(key="H4", text="MemoLoop's effect depends on context (only some students or settings benefit)", plausibility="low",
                               requirements=[R(description="subgroup analyses by student group", importance="medium"),
                                             R(description="heterogeneity of effects across sites", importance="medium")]),
            HypothesisProposal(key="H5", text="Public evidence is insufficient to judge MemoLoop's effect on exam scores",
                               is_null_hypothesis=True, plausibility="low"),
        ])

    def propose(self, cl: list[dict]) -> list[InferenceProposal]:
        e31, e12, e02, pilot = find(cl, "0.31 standard"), find(cl, "0.12 standard"), find(cl, "0.02 sd"), find(cl, "pilot")
        I = InferenceProposal
        props = []
        if e31:
            props.append(I(premise_ids=[e31], hypothesis_id="H1", direction="supports", inference_type="statistical",
                           statement="A randomized trial found a 0.31 SD effect, above the 0.2 SD threshold", proposed_strength="strong"))
        if pilot:
            props.append(I(premise_ids=[pilot], hypothesis_id="H1", direction="supports", inference_type="inductive",
                           statement="A pilot study found a 0.8 SD improvement", proposed_strength="moderate"))
        if e12:
            props += [I(premise_ids=[e12], hypothesis_id="H2", direction="supports", inference_type="statistical",
                        statement="A preregistered multi-site replication found 0.12 SD: a small positive effect", proposed_strength="strong"),
                      I(premise_ids=[e12], hypothesis_id="H1", direction="contradicts", inference_type="statistical",
                        statement="The large replication's effect of 0.12 SD is below the 0.2 SD threshold", proposed_strength="strong")]
        if e02:
            props += [I(premise_ids=[e02], hypothesis_id="H3", direction="supports", inference_type="statistical",
                        statement="A preregistered direct replication found no significant effect", proposed_strength="moderate"),
                      I(premise_ids=[e02], hypothesis_id="H1", direction="contradicts", inference_type="statistical",
                        statement="A preregistered replication found no significant effect, against a material effect", proposed_strength="strong")]
        if e12 and e02:
            props.append(I(premise_ids=[e12, e02], hypothesis_id="H2", direction="supports", inference_type="statistical",
                           statement="Two preregistered replications (0.12 SD and 0.02 SD) together indicate a small effect at most",
                           proposed_strength="strong"))
        return props

    def verify(self, inf: dict) -> InferenceVerdict:
        s, iid = inf["statement"].lower(), inf["inference_id"]
        if "0.31 sd effect" in s:
            return InferenceVerdict(inference_id=iid, verdict="plausible", missing_premises=["independent replication of the trial"],
                                    confounders=["authors' financial conflict of interest", "single-site sample"],
                                    reason="One randomized trial supports the effect, but it is unreplicated and conflicted.")
        if "pilot" in s:
            return InferenceVerdict(inference_id=iid, verdict="weak", reason="n=12, no control group and high attrition cannot establish an effect.")
        if "no significant effect" in s and inf["direction"] == "supports":
            return InferenceVerdict(inference_id=iid, verdict="plausible",
                                    reason="One null result does not establish no effect when another replication found a positive one.")
        return InferenceVerdict(inference_id=iid, verdict="valid", reason="Preregistered replication results bear directly on the effect size.")

    def synthesize(self, cl: list[dict]) -> SynthesisOutput:
        e31, e12, e02 = find(cl, "0.31 standard"), find(cl, "0.12 standard"), find(cl, "0.02 sd")
        S = SynthesisSentence
        out = []
        if e31:
            out.append(S(text="The original randomized trial with 412 students reported a 0.31 SD improvement; its preprint, conference and "
                              "journal versions are one study, not three confirmations.", claim_ids=[e31]))
        if e12:
            out.append(S(text="A preregistered multi-site replication with 1,180 students found a smaller effect of 0.12 SD.", claim_ids=[e12]))
        if e02:
            out.append(S(text="A preregistered direct replication with 640 students found no statistically significant effect (0.02 SD).",
                         claim_ids=[e02]))
        out.append(S(text="MemoLoop is used by over a million students worldwide.", claim_ids=[]))  # must be removed
        return SynthesisOutput(conclusion=out, what_would_change_our_mind=[
            "A third preregistered replication with an effect above 0.2 SD",
            "A meta-analysis pooling all randomized MemoLoop trials",
            "Evidence that the effect depends on how the app is used (dose or subgroup analyses)"])


SCENARIO = ScienceScenario()
