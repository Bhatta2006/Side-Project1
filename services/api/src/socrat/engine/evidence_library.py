"""The Learning Evidence Library (master prompt 8): what each teaching technique is, what the
research says about it, and the rule Socrat applies. Versioned; the Pedagogical Strategist
(``engine.strategy``) may only choose techniques listed here.

Honesty about this file: the entries summarise widely cited reviews and studies as the author
knew them. The references were written from that knowledge and were **not re-checked against the
publications** when this version was written; ``REVIEWED_BY`` stays empty until a qualified
person has checked every entry. Findings and Socrat's product rules are kept apart: a ``rule`` is
a product hypothesis to measure, not a proven effect.
"""

from dataclasses import asdict, dataclass

VERSION = "2026-11-03.1"
REVIEW_DATE = "2026-11-03"
REVIEWED_BY: str | None = None  # a named, qualified reviewer, once every entry is checked


@dataclass(frozen=True)
class Technique:
    id: str
    name: str
    definition: str
    outcomes: str  # what it is meant to improve
    studied: str  # populations and domains in the evidence
    strength: str  # high | moderate | mixed | low, by the reviews cited
    limits: str
    useful_when: str
    unsuitable_when: str
    rule: str  # what Socrat does (a product hypothesis)
    measure: str  # how Socrat checks the rule helps
    references: tuple[str, ...]


LIBRARY: tuple[Technique, ...] = (
    Technique(
        "retrieval",
        "Retrieval practice",
        "Recalling or applying something from memory before the answer is shown.",
        "Long-term retention; later application.",
        "Students from school to university; word lists, prose, science and maths facts; lab and classroom.",
        "high",
        "Benefits are larger after a delay than on an immediate test; needs prior instruction and feedback when recall fails.",
        "After a concept has been taught; for facts, procedures and concepts.",
        "Before any instruction on the idea; when the learner is overloaded or the task is unsafe.",
        "Quiz and review items ask before showing; never before the lesson has been read.",
        "Delayed review accuracy versus re-reading, per concept.",
        (
            "Roediger, H. L., & Karpicke, J. D. (2006). Test-enhanced learning. Psychological Science, 17(3).",
            "Dunlosky, J., Rawson, K. A., Marsh, E. J., Nathan, M. J., & Willingham, D. T. (2013). Improving students' learning with effective learning techniques. Psychological Science in the Public Interest, 14(1).",
            "Adesope, O. O., Trevisan, D. A., & Sundararajan, N. (2017). Rethinking the use of tests: A meta-analysis of practice testing. Review of Educational Research, 87(3).",
        ),
    ),
    Technique(
        "spacing",
        "Spaced practice",
        "Spreading practice of the same material over time instead of massing it.",
        "Long-term retention.",
        "Many ages; mostly verbal material, with growing evidence in maths and skills.",
        "high",
        "The best gap depends on how long the knowledge must last; most studies use verbal recall.",
        "Anything that must be remembered beyond the next session.",
        "Material needed only once, immediately.",
        "Reviews follow expanding intervals after success and shorter ones after failure (mastery.model).",
        "Retention at the next review versus the interval used.",
        (
            "Cepeda, N. J., Pashler, H., Vul, E., Wixted, J. T., & Rohrer, D. (2006). Distributed practice in verbal recall tasks: A review and quantitative synthesis. Psychological Bulletin, 132(3).",
            "Dunlosky et al. (2013), as above.",
        ),
    ),
    Technique(
        "interleaving",
        "Interleaving",
        "Mixing problems of related types so the learner must choose the method.",
        "Discriminating between similar problem types; transfer of method choice.",
        "Mathematics, category learning, some motor skills.",
        "moderate",
        "Helps most when categories are similar and hard to tell apart; can hurt for very dissimilar material or early learning.",
        "After each type has been learned on its own and the objective includes choosing the method.",
        "While a single method is still new.",
        "Mixed practice only for concepts at 'developing' or above, drawing on related concepts.",
        "Accuracy on mixed sets and on method choice.",
        (
            "Rohrer, D., & Taylor, K. (2007). The shuffling of mathematics problems improves learning. Instructional Science, 35.",
            "Brunmair, M., & Richter, T. (2019). Similarity matters: A meta-analysis of interleaved learning and its moderators. Psychological Bulletin, 145(11).",
        ),
    ),
    Technique(
        "worked-examples",
        "Worked examples and fading",
        "Showing a complete solution, then removing steps as the learner gains competence.",
        "Initial skill acquisition with less cognitive load.",
        "Novices in maths, physics, programming and other well-structured domains.",
        "high",
        "The benefit reverses for learners who already know the method (expertise reversal); fading must follow performance.",
        "Novices on procedural or problem-solving content.",
        "Learners who already solve such problems unaided.",
        "Lessons lead with a worked example for new or emerging competencies; faded atoms later.",
        "Errors on the first unaided attempt after the example.",
        (
            "Sweller, J., & Cooper, G. A. (1985). The use of worked examples as a substitute for problem solving in learning algebra. Cognition and Instruction, 2(1).",
            "Renkl, A., & Atkinson, R. K. (2003). Structuring the transition from example study to problem solving in cognitive skill acquisition. Educational Psychologist, 38(1).",
            "Kalyuga, S., Ayres, P., Chandler, P., & Sweller, J. (2003). The expertise reversal effect. Educational Psychologist, 38(1).",
        ),
    ),
    Technique(
        "self-explanation",
        "Self-explanation",
        "Asking learners to explain why a step, result or method is valid.",
        "Understanding and transfer.",
        "School and university learners in science, maths and reading.",
        "moderate",
        "Quality of explanations varies; prompts must be specific; costs time.",
        "Conceptual material and worked examples.",
        "Pure memorisation targets.",
        "Free-text prompts ask why, not what; graded by rubric and never mastering alone.",
        "Transfer accuracy for concepts with and without explanation prompts.",
        (
            "Chi, M. T. H., de Leeuw, N., Chiu, M.-H., & LaVancher, C. (1994). Eliciting self-explanations improves understanding. Cognitive Science, 18(3).",
            "Bisra, K., Liu, Q., Nesbit, J. C., Salimi, F., & Winne, P. H. (2018). Inducing self-explanation: A meta-analysis. Educational Psychology Review, 30.",
        ),
    ),
    Technique(
        "elaboration",
        "Elaborative questioning",
        "Prompting why and how questions that connect new facts to what the learner knows.",
        "Retention of facts and their relations.",
        "Mostly fact learning with older students.",
        "moderate",
        "Weaker for learners with little prior knowledge of the topic.",
        "Fact-rich topics where the learner has some background.",
        "Complete beginners with nothing to connect to.",
        "Lessons end sections with a why or how question; the tutor asks them before telling.",
        "Recall of related facts at review.",
        ("Dunlosky et al. (2013), as above.",),
    ),
    Technique(
        "feedback",
        "Immediate and delayed feedback",
        "Specific information about the gap between the answer and the goal, at a useful time.",
        "Correcting errors; guiding the next attempt.",
        "Broad: classrooms, computer-based learning, many ages.",
        "high",
        "Effects vary widely; feedback about the person, or vague feedback, can hurt.",
        "Whenever an answer is checked.",
        "Never withheld when it is safety information.",
        "Every check explains each option or failed test; feedback is about the task, never the person.",
        "Accuracy on the next attempt after feedback.",
        (
            "Hattie, J., & Timperley, H. (2007). The power of feedback. Review of Educational Research, 77(1).",
            "Shute, V. J. (2008). Focus on formative feedback. Review of Educational Research, 78(1).",
        ),
    ),
    Technique(
        "scaffolding",
        "Scaffolding and fading",
        "Support matched to what the learner cannot yet do alone, removed as they improve.",
        "Independent performance on tasks just beyond current ability.",
        "Classroom and tutoring studies, many domains.",
        "moderate",
        "Hard to calibrate; support that never fades breeds dependence.",
        "New or difficult tasks.",
        "When the learner already performs independently.",
        "The hint ladder starts small and deepens on need; a full solution requires an unaided follow-up.",
        "Hint depth used over time per learner (should fall).",
        (
            "Wood, D., Bruner, J. S., & Ross, G. (1976). The role of tutoring in problem solving. Journal of Child Psychology and Psychiatry, 17(2).",
            "van de Pol, J., Volman, M., & Beishuizen, J. (2010). Scaffolding in teacher-student interaction: A decade of research. Educational Psychology Review, 22.",
        ),
    ),
    Technique(
        "dual-coding",
        "Dual coding and multimedia",
        "Coordinated words and relevant pictures, without decorative or redundant material.",
        "Understanding of systems and processes.",
        "Mostly university students with short science and technical lessons.",
        "moderate",
        "Decorative visuals and redundant narration can hurt; effects shrink for experts.",
        "Processes, structures and spatial ideas.",
        "When a picture would only decorate.",
        "Visuals must serve a stated purpose and have a text alternative; at most two per lesson.",
        "Check accuracy for lessons with and without the visual.",
        (
            "Mayer, R. E. (2009). Multimedia Learning (2nd ed.). Cambridge University Press.",
            "Clark, J. M., & Paivio, A. (1991). Dual coding theory and education. Educational Psychology Review, 3(3).",
        ),
    ),
    Technique(
        "concreteness-fading",
        "Concrete to abstract",
        "Moving from concrete or interactive representations to formal ones.",
        "Transfer of abstract ideas.",
        "Mathematics and science, mostly school age.",
        "moderate",
        "Few studies per domain; the right sequence is not settled.",
        "Abstract ideas new to the learner.",
        "Learners already fluent with the formalism.",
        "Lessons for emerging learners start from an example before the general rule.",
        "Transfer items at the formal level.",
        (
            "Fyfe, E. R., McNeil, N. M., Son, J. Y., & Goldstone, R. L. (2014). Concreteness fading in mathematics and science instruction: A systematic review. Educational Psychology Review, 26.",
        ),
    ),
    Technique(
        "desirable-difficulty",
        "Desirable difficulty",
        "Challenge that slows practice but improves durable learning.",
        "Long-term retention and transfer.",
        "Lab and classroom studies of memory and skills.",
        "moderate",
        "A difficulty is only desirable if the learner can respond to it; too hard is simply hard.",
        "Learners who succeed easily on current practice.",
        "Learners who are failing or frustrated.",
        "Difficulty rises after clean independent success and falls on repeated failure (stuck ladder).",
        "Retention after harder versus easier practice; drop-off after failures.",
        (
            "Bjork, R. A. (1994). Memory and metamemory considerations in the training of human beings. In Metcalfe & Shimamura (Eds.), Metacognition: Knowing about knowing. MIT Press.",
        ),
    ),
    Technique(
        "calibration",
        "Metacognitive calibration",
        "Asking learners how sure they are and comparing it with how they did.",
        "Accurate self-monitoring and study choices.",
        "University students, mostly in memory and text tasks.",
        "mixed",
        "Calibration training effects are inconsistent; feedback on accuracy is needed.",
        "Before checking answers, optionally.",
        "Never scored or used to judge the person.",
        "Optional confidence on quiz answers; a calibration report (gap and Brier score).",
        "Change in calibration gap over time.",
        (
            "Dunlosky, J., & Rawson, K. A. (2012). Overconfidence produces underachievement: Inaccurate self evaluations undermine students' learning and retention. Learning and Instruction, 22(4).",
        ),
    ),
    Technique(
        "deliberate-practice",
        "Deliberate practice",
        "Focused practice on a specific weakness with clear criteria and feedback.",
        "Performance on the targeted sub-skill.",
        "Music, games, sports, professions.",
        "mixed",
        "Explains less of the variation in performance than once claimed; quality of feedback matters.",
        "A known, specific weakness.",
        "Before the weakness is identified.",
        "Targeted practice on the weakest prerequisite or recurring misconception.",
        "Error rate on the targeted misconception.",
        (
            "Ericsson, K. A., Krampe, R. T., & Tesch-Römer, C. (1993). The role of deliberate practice in the acquisition of expert performance. Psychological Review, 100(3).",
            "Macnamara, B. N., Hambrick, D. Z., & Oswald, F. L. (2014). Deliberate practice and performance in music, games, sports, education, and professions: A meta-analysis. Psychological Science, 25(8).",
        ),
    ),
    Technique(
        "transfer",
        "Transfer practice",
        "Using the same underlying idea in an unfamiliar context.",
        "Flexible use of knowledge.",
        "Many domains; far transfer is rare.",
        "mixed",
        "Near transfer is common, far transfer is hard to get and to measure.",
        "Once a concept is applied correctly in familiar tasks.",
        "Before familiar application is secure.",
        "Transfer checks come after independent application; they count as transfer evidence.",
        "Accuracy on unseen problems that need the concept.",
        (
            "Barnett, S. M., & Ceci, S. J. (2002). When and where do we apply what we learn? A taxonomy for far transfer. Psychological Bulletin, 128(4).",
            "Gick, M. L., & Holyoak, K. J. (1983). Schema induction and analogical transfer. Cognitive Psychology, 15(1).",
        ),
    ),
    Technique(
        "cumulative-review",
        "Cumulative review",
        "Revisiting earlier prerequisites while learning new material.",
        "Retention of foundations.",
        "Derived from spacing research; few direct studies of cumulative schedules.",
        "low",
        "Evidence is mostly indirect (from spacing); the right mix is a product choice.",
        "Courses where later ideas rest on earlier ones.",
        "When reviews already exceed the learner's time.",
        "Due reviews of earlier concepts are mixed into the daily plan, capped per day.",
        "Retention of early concepts late in the course.",
        ("Cepeda et al. (2006), as above.", "Dunlosky et al. (2013), as above."),
    ),
)

# Claims Socrat must not make, with the evidence against them.
AVOID = (
    (
        "Matching teaching to a learner's 'learning style' (visual, auditory, kinaesthetic)",
        "Pashler, H., McDaniel, M., Rohrer, D., & Bjork, R. (2008). Learning styles: Concepts and evidence. Psychological Science in the Public Interest, 9(3).",
    ),
)

BY_ID = {t.id: t for t in LIBRARY}


def as_dict() -> dict:
    return dict(
        version=VERSION,
        review_date=REVIEW_DATE,
        reviewed_by=REVIEWED_BY,
        note="References were written from the author's knowledge and not re-checked against "
        "the publications; rules are product hypotheses to measure.",
        techniques=[asdict(t) for t in LIBRARY],
        avoid=[dict(claim=c, reference=r) for c, r in AVOID],
    )
