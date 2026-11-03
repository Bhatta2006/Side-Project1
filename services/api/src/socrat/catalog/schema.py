"""Authoring schema for course packs.

A course is a folder of YAML documents. Concepts form a prerequisite DAG that may
reference concepts in other courses with a ``course:concept`` identifier, so a new
skill can reuse an existing foundation without duplicating it.
"""

import random
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from socrat.catalog import dialect
from socrat.catalog.shape import CourseShape

Slug = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")]
Ref = Annotated[str, Field(pattern=r"^([a-z][a-z0-9-]{0,63}:)?[a-z][a-z0-9-]{0,63}$")]
# Evidence a competency asks for, in the master prompt's terms (9.2), beyond mere exposure.
EvidenceType = Literal[
    "recognition", "recall", "application", "transfer", "explanation", "performance"
]
PracticeType = Literal[
    "retrieval",
    "worked-example",
    "problem-set",
    "lab",
    "project",
    "performance",
    "reflection",
    "discussion",
]
Language = Literal["python", "cpp", "java"]
LANGUAGES: tuple[Language, ...] = ("python", "cpp", "java")


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Resource(Model):
    title: str = Field(min_length=3, max_length=160)
    url: HttpUrl
    kind: Literal["article", "video", "docs", "course", "book", "interactive", "visualizer"]
    source: str = Field(min_length=2, max_length=80)
    minutes: int = Field(ge=1, le=600)
    level: Literal["intro", "core", "deep"] = "core"
    languages: list[Language] = Field(default_factory=list)  # empty = language-neutral
    # Provenance for researched sources (master prompt 11.2); empty for hand-picked ones.
    author: str = Field(default="", max_length=200)
    published: str = Field(default="", max_length=40)
    license: str = Field(default="", max_length=120)
    why: str = Field(default="", max_length=300)  # why it was chosen, in plain words


class Citation(Model):
    """Which source backs which claim, and where (master prompt 11.4). Built by code from the
    lesson's inline [n] markers (``coursegen.research.ground``); never written by a model."""

    n: int = Field(ge=1, le=20)
    url: HttpUrl
    offset: int = Field(ge=0)  # character position of the [n] marker in the lesson text
    claim: str = Field(max_length=400)  # the sentence that carries the marker
    passage: str = Field(default="", max_length=400)  # the source text the claim rests on
    # retrieved: text the search provider returned; summary: the researcher's paraphrase only
    basis: Literal["retrieved", "summary"] = "summary"
    overlap: float = Field(ge=0, le=1)  # share of the claim's content words found in it
    supported: bool


class Review(Model):
    """Human sign-off recorded when a drafted problem is approved (item 5 of the backlog)."""

    by: str = Field(min_length=2, max_length=120)
    at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    notes: str = Field(default="", max_length=2000)


class SourceRef(Model):
    """One source an adapted record was derived from (Content Master Plan §2.5)."""

    source_id: Slug  # must exist in content/sources/registry.yaml (checked by the license gate)
    title: str = Field(min_length=2, max_length=200)
    author: str = Field(min_length=2, max_length=200)
    url: HttpUrl
    license_spdx: str = Field(min_length=2, max_length=64)
    license_url: HttpUrl
    retrieved_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    changes: str = Field(default="", max_length=1000)


class Provenance(Model):
    """Who made a record, from what, under which rights. Optional: absent means legacy.

    ``review`` is only ever written by a human; tooling never fills it in.
    """

    origin: Literal["original", "adapted", "linked", "partnered"] = "original"
    author: str = Field(default="Socrat Learning", min_length=2, max_length=200)
    authors_adapted_from: list[SourceRef] = Field(default_factory=list)
    review: Review | None = None
    version: int = Field(default=1, ge=1)
    rights: str = Field(
        default="Socrat original, all rights reserved", min_length=2, max_length=300
    )
    attribution_md: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def sources_match_origin(self):
        if self.origin == "adapted" and not self.authors_adapted_from:
            raise ValueError("adapted content must cite at least one source")
        if self.origin != "adapted" and self.authors_adapted_from:
            raise ValueError("only adapted content lists authors_adapted_from")
        return self


class QuizItem(Model):
    id: Slug
    kind: Literal["mcq", "output", "bug"] = "mcq"
    prompt: str = Field(min_length=5, max_length=4000)
    code: dict[Language, str] = Field(default_factory=dict)
    options: list[str] = Field(min_length=2, max_length=6)
    answer: int = Field(ge=0)
    explanation: str = Field(min_length=5, max_length=2000)
    difficulty: int = Field(ge=1, le=5)
    provenance: Provenance | None = None
    # Ids this item had before a rename, so stored sessions and placements still resolve.
    former_ids: list[Slug] = Field(default_factory=list)
    # Languages this item is valid for; empty means all (use for language-specific syntax).
    languages: list[Language] = Field(default_factory=list)

    def matches(self, item_id: str) -> bool:
        return item_id == self.id or item_id in self.former_ids

    def snippet(self, language: str) -> str | None:
        """The code shown with this question in the learner's language, if any."""
        for key, value in self.code.items():
            if key == language:
                return value
        return next(iter(self.code.values()), None)

    def fits(self, language: str) -> bool:
        """False for items written about another language ("In C++, ...", id ``cpp-...``)."""
        if self.languages and language not in self.languages:
            return False
        names = {"c++": "cpp", "cpp": "cpp", "java": "java", "python": "python", "py": "python"}
        lead = re.match(
            r"\s*In ((?:C\+\+|Java|Python)(?:\s*(?:,|or|and)\s*(?:C\+\+|Java|Python))*)",
            self.prompt,
        )
        named = (
            {names[x.lower()] for x in re.findall(r"C\+\+|Java|Python", lead.group(1))}
            if lead
            else set()
        )
        prefix = self.id.split("-", 1)[0]
        if not named and prefix in names and "-" in self.id:
            named = {names[prefix]}
        if self.code and language not in self.code:
            return False  # its code exists only in other languages
        if named:
            return language in named
        # No explicit tag: the prose itself must not be written in another language's syntax.
        return not dialect.foreign(language, self.prompt, *self.options, self.explanation)

    def order(self, seed: str) -> list[int]:
        """Display position -> authored option index, fixed per (seed, item).

        Authors write the correct option first; the order learners see must not leak it.
        """
        order = list(range(len(self.options)))
        random.Random(f"{seed}:{self.id}").shuffle(order)
        return order

    def shown(self, seed: str) -> dict:
        order = self.order(seed)
        return dict(options=[self.options[i] for i in order], answer=order.index(self.answer))

    def is_correct(self, seed: str, choice: int) -> bool:
        return 0 <= choice < len(self.options) and self.order(seed)[choice] == self.answer

    @model_validator(mode="after")
    def answer_in_range(self):
        if self.answer >= len(self.options):
            raise ValueError(f"quiz {self.id}: answer index out of range")
        if len(set(self.options)) != len(self.options):
            raise ValueError(f"quiz {self.id}: duplicate options")
        return self


class Criterion(Model):
    criterion: str = Field(min_length=2, max_length=120)
    points: int = Field(ge=1, le=4)
    look_for: str = Field(min_length=5, max_length=400)  # what earns the points


class Prompt(Model):
    """A free-text question answered in the learner's own words and graded against its
    rubric (AI-graded evidence: ``explain``). The model answer is shown only after grading."""

    id: Slug
    prompt: str = Field(min_length=10, max_length=1000)
    rubric: list[Criterion] = Field(min_length=2, max_length=6)
    model_answer: str = Field(min_length=20, max_length=3000)
    max_words: int = Field(default=250, ge=30, le=600)


class Task(Model):
    """Work a quiz cannot judge (master prompt 4): a reflection, case study, oral explanation,
    performance, portfolio piece or practical. Each has a rubric and says who judges it. Work
    shown by doing (oral, performance, portfolio, practical) is judged by a person; reflections
    and case studies are checked by the learner against the rubric and never count as evidence."""

    id: Slug
    kind: Literal["reflection", "case-study", "oral", "performance", "portfolio", "practical"]
    prompt: str = Field(min_length=10, max_length=1500)
    rubric: list[Criterion] = Field(min_length=2, max_length=6)
    safety: str = Field(default="", max_length=300)  # what to do (or not) when practising it

    @property
    def evaluator(self) -> str:
        return "self" if self.kind in ("reflection", "case-study") else "person"


class PracticeLink(Model):
    title: str = Field(min_length=2, max_length=160)
    url: HttpUrl
    platform: str = Field(min_length=2, max_length=40)
    difficulty: Literal["easy", "medium", "hard"]


class Outline(Model):
    """What a generated concept must teach, set when the course outline is planned. The
    authoring agents write the lesson from it; hand-authored concepts leave it empty."""

    depth: Literal["overview", "practitioner", "mastery"] = "practitioner"
    objectives: list[str] = Field(min_length=1, max_length=6)  # observable, start with a verb
    misconceptions: list[str] = Field(default_factory=list, max_length=6)
    assessment: list[Literal["quiz", "code", "explain", "project"]] = Field(
        min_length=1, max_length=4
    )
    # The competency graph (master prompt 3.3). All optional so older outlines stay valid.
    # knowledge: facts and ideas; skill: something done; both: an idea you must also apply.
    category: Literal["knowledge", "skill", "both"] = "knowledge"
    # Concepts that connect without being required first (contrasts, same idea elsewhere).
    related: list[Ref] = Field(default_factory=list, max_length=6)
    # What a learner must show before this counts as demonstrated (prompt 9.2).
    evidence: list[EvidenceType] = Field(default_factory=list, max_length=5)
    expected: str = Field(default="", max_length=300)  # the performance that shows it, observable
    practice: list[PracticeType] = Field(default_factory=list, max_length=5)


class Exercise(Model):
    """A worked-out problem a studio grades with the harness (never by a model)."""

    id: Slug
    prompt: str = Field(min_length=5, max_length=2000)
    check: Literal["equivalent", "equation", "numeric", "steps"]
    expected: str = Field(min_length=1, max_length=200)  # the reference answer, as text
    unit: str = Field(default="", max_length=40)
    hints: list[str] = Field(default_factory=list, max_length=3)
    plot: list[str] = Field(default_factory=list, max_length=3)  # expressions in x to draw
    points: list[tuple[float, float]] = Field(default_factory=list, max_length=12)  # data to fit
    difficulty: int = Field(ge=1, le=5)
    explanation: str = Field(min_length=5, max_length=2000)  # the worked solution, shown after

    @model_validator(mode="after")
    def hints_are_short(self):
        if any(len(h) > 300 for h in self.hints) or any(len(p) > 120 for p in self.plot):
            raise ValueError("hints are at most 300 characters and plots 120")
        return self


class Experiment(Model):
    """A lab experiment: predict one result, run the vetted simulation, compare, explain.

    The true answer is never stored: the harness computes it from ``model`` and ``params`` when
    the learner commits a prediction, so it cannot be wrong or leak through the listing.
    """

    id: Slug
    prompt: str = Field(min_length=5, max_length=1500)  # the scenario; asks for the prediction
    model: str = Field(min_length=2, max_length=40)  # a model in harness.physics.MODELS
    params: dict[str, float] = Field(max_length=8)
    predict: str = Field(min_length=2, max_length=40)  # the reported quantity to predict
    tolerance: float = Field(default=0.05, ge=0.005, le=0.25)  # relative; 0.05 is 5%
    vary: str = ""  # a parameter the learner may change afterwards to see the effect
    hints: list[str] = Field(default_factory=list, max_length=3)
    difficulty: int = Field(ge=1, le=5)
    explanation: str = Field(min_length=5, max_length=2000)  # why, in the model's terms
    rubric: list[Criterion] = Field(default_factory=list, max_length=4)  # grades the written why

    @model_validator(mode="after")
    def hints_are_short(self):
        if any(len(h) > 300 for h in self.hints):
            raise ValueError("hints are at most 300 characters")
        return self


class Visual(Model):
    """A typed, interactive element of a lesson: a registered renderer plus validated params.
    Never code. Checked against ``socrat.engine.renderers`` when the concept loads."""

    renderer: str
    version: str = "1.0"
    params: dict = Field(default_factory=dict)
    purpose: str = Field(min_length=5, max_length=300)
    fallback_text: str = Field(min_length=10, max_length=4000)
    alt_text: str = Field(min_length=5, max_length=600)

    @model_validator(mode="after")
    def registered(self):
        from socrat.engine import renderers

        problems = renderers.validate_spec(self.model_dump())
        if problems:
            raise ValueError("; ".join(problems))
        return self


class Concept(Model):
    id: Slug
    title: str = Field(min_length=2, max_length=100)
    summary: str = Field(min_length=10, max_length=300)
    module: Slug
    prerequisites: list[Ref] = Field(default_factory=list)
    difficulty: int = Field(ge=1, le=5)
    estimated_minutes: int = Field(ge=3, le=600)
    lesson: str = ""  # empty only while planned
    key_points: list[str] = Field(default_factory=list, max_length=8)
    pitfalls: list[str] = Field(default_factory=list, max_length=8)
    resources: list[Resource] = Field(default_factory=list, max_length=8)
    quiz: list[QuizItem] = Field(default_factory=list, max_length=10)
    prompts: list[Prompt] = Field(default_factory=list, max_length=4)
    exercises: list[Exercise] = Field(default_factory=list, max_length=10)
    visuals: list[Visual] = Field(default_factory=list, max_length=4)
    experiments: list[Experiment] = Field(default_factory=list, max_length=6)
    problems: list[Slug] = Field(default_factory=list)
    practice_links: list[PracticeLink] = Field(default_factory=list, max_length=10)
    tasks: list[Task] = Field(default_factory=list, max_length=4)
    # The order a learner meets this concept's activities (empty: the page's default order):
    # "lesson", "quiz", "visual:N", or "prompt:", "exercise:", "experiment:", "problem:",
    # "task:" followed by an id. Every entry must name something this concept has.
    sequence: list[str] = Field(default_factory=list, max_length=24)
    # Quiz items a rewrite dropped: never offered again, but still resolvable so open
    # sessions, placements and stored attempts keep working (catalog/revisions.carry).
    retired_quiz: list[QuizItem] = Field(default_factory=list, max_length=40)
    citations: list[Citation] = Field(default_factory=list, max_length=40)
    provenance: Provenance | None = None
    outline: Outline | None = None
    # A draft is being authored: validated and kept in the graph, but never served.
    # A planned concept is an outline entry whose content is not generated yet: it is in
    # the graph and on the roadmap, but its lesson and activities are held.
    status: Literal["draft", "live", "planned"] = "live"

    @model_validator(mode="after")
    def live_is_complete(self):
        if self.status != "planned" and not self.lesson:
            raise ValueError(f"concept {self.id} needs a lesson")
        if self.status == "live":
            missing = [
                name
                for name, ok in (
                    ("a lesson of at least 200 characters", len(self.lesson) >= 200),
                    ("at least 2 key points", len(self.key_points) >= 2),
                    ("at least 2 resources", len(self.resources) >= 2),
                    ("at least 2 quiz items", len(self.quiz) >= 2),
                )
                if not ok
            ]
            if missing:
                raise ValueError(f"live concept {self.id} needs {', '.join(missing)}")
        known = {"lesson", "quiz"} | {f"visual:{i}" for i in range(len(self.visuals))}
        known |= {f"prompt:{x.id}" for x in self.prompts} | {f"task:{x.id}" for x in self.tasks}
        known |= {f"exercise:{x.id}" for x in self.exercises}
        known |= {f"experiment:{x.id}" for x in self.experiments}
        known |= {f"problem:{x}" for x in self.problems}
        if unknown := [s for s in self.sequence if s not in known]:
            raise ValueError(f"concept {self.id} sequence names unknown activities: {unknown}")
        if len(set(self.sequence)) != len(self.sequence):
            raise ValueError(f"concept {self.id} sequence repeats an activity")
        if len({t.id for t in self.tasks}) != len(self.tasks):
            raise ValueError(f"concept {self.id} task ids must be unique")
        live_ids = {i for q in self.quiz for i in (q.id, *q.former_ids)}
        if clash := sorted({q.id for q in self.retired_quiz} & live_ids):
            raise ValueError(f"concept {self.id} retired quiz ids are still live: {clash}")
        return self

    def quiz_item(self, item_id: str) -> QuizItem:
        """The quiz item stored under ``item_id`` (current, renamed or retired)."""
        for q in (*self.quiz, *self.retired_quiz):
            if q.matches(item_id):
                return q
        raise KeyError(f"concept {self.id} has no quiz item {item_id}")


class Example(Model):
    input: str
    output: str
    explanation: str = ""


class TestCase(Model):
    input: str = Field(max_length=2_000_000)
    expected: str = Field(max_length=2_000_000)
    public: bool = False


class Problem(Model):
    id: Slug
    title: str = Field(min_length=2, max_length=100)
    concepts: list[Slug] = Field(min_length=1)
    difficulty: Literal["easy", "medium", "hard"]
    statement: str = Field(min_length=20)
    input_format: str = Field(min_length=3)
    output_format: str = Field(min_length=3)
    constraints: list[str] = Field(default_factory=list)
    examples: list[Example] = Field(min_length=1, max_length=5)
    hints: list[str] = Field(min_length=2, max_length=5)
    approach: str = Field(min_length=20)  # Revealed only at the final Socratic level.
    reference: str = Field(min_length=10)  # Python reference; generates expected output.
    generator: str = ""  # Python: def cases(rng): yield input strings.
    starter: dict[Language, str] = Field(default_factory=dict)
    # Quality gates (scripts/content/validate_problems.py): a slow but obviously correct
    # solution, small inputs it can handle, and references in the other judge languages.
    brute: str = ""  # Python brute force; must agree with `reference` on small inputs.
    small_generator: str = ""  # Python: def cases(rng): yield small input strings.
    references: dict[Language, str] = Field(default_factory=dict)  # cpp / java
    review: Review | None = None
    time_limit_ms: int = Field(default=2000, ge=500, le=10000)
    tests: list[TestCase] = Field(default_factory=list)
    provenance: Provenance | None = None


class Module(Model):
    id: Slug
    title: str = Field(min_length=2, max_length=100)
    summary: str = Field(min_length=10, max_length=300)
    concepts: list[Slug] = Field(min_length=1)


class LevelStart(Model):
    """Self-reported level → concept at which adaptive placement starts probing."""

    id: Slug
    label: str
    description: str
    start_concept: Slug | None = None  # None = absolute beginner, skip placement.


class Course(Model):
    id: Slug
    title: str = Field(min_length=2, max_length=80)
    tagline: str = Field(min_length=5, max_length=140)
    description: str = Field(min_length=20, max_length=1200)
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    languages: list[Language] = Field(min_length=1)
    levels: list[LevelStart] = Field(min_length=2)
    modules: list[Module] = Field(min_length=1)
    concepts: list[Concept] = Field(default_factory=list)
    problems: list[Problem] = Field(default_factory=list)
    # How this course is practised and evidenced; none means a programming course.
    shape: CourseShape | None = None

    def concept(self, concept_id: str) -> Concept:
        return next(item for item in self.concepts if item.id == concept_id)

    def problem(self, problem_id: str) -> Problem:
        return next(item for item in self.problems if item.id == problem_id)
