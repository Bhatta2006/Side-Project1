"""Practice sets for any course: a model writes questions about one topic, the server grades.

Programming courses practise in the problem library. Every other course (a children's math
game, Kannada, finance) practises here: the learner picks a topic they have unlocked and gets a
short set of questions written for that course and that topic alone. Answers never leave the
server before the learner answers; each question is answered once and graded exactly
(a choice, a number or a short phrase), so no grading model is needed.

A set is stored as an ``ActivityRecord`` (``drill:<id>``) that is never completed, so plan
progress, streaks and achievements, which read completed records, never count it.
"""

import json
import re
import secrets
from datetime import UTC, datetime
from fractions import Fraction
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.assistant.gateway import Provider, ProviderError, Turn, complete
from socrat.catalog.registry import Catalog
from socrat.catalog.schema import Concept
from socrat.models import ActivityRecord, Enrollment, User

PREFIX = "drill:"
QUESTIONS = 5
SETS_PER_DAY = 12  # each set is one model call; practice, not a slot machine
KEEP = 20  # sets listed in the history


class Question(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    kind: Literal["choice", "number", "text"]
    prompt: str = Field(min_length=3, max_length=600)
    options: list[str] = Field(default_factory=list, max_length=5)
    answer: str = Field(min_length=1, max_length=120)
    accept: list[str] = Field(default_factory=list, max_length=6)
    hint: str = Field(default="", max_length=300)
    explanation: str = Field(min_length=3, max_length=800)

    @model_validator(mode="after")
    def gradable(self):
        if self.kind == "choice":
            if not 2 <= len(self.options) <= 5 or len(set(self.options)) != len(self.options):
                raise ValueError("a choice question needs 2-5 distinct options")
            if self.answer not in self.options:
                raise ValueError("the answer must be one of the options")
        elif self.options:
            self.options = []
        if self.kind == "number" and number(self.answer) is None:
            raise ValueError("a number question needs a numeric answer")
        return self


class Drafted(BaseModel):
    model_config = ConfigDict(extra="ignore")
    questions: list[Question] = Field(min_length=3, max_length=8)


SYSTEM = """You write practice questions for one topic of one course on Socrat, a learning app.
Write only about the course and topic you are given; never about programming, coding
interviews or another subject unless the course itself is about it. Match the learner's age
and level: for a children's course use short sentences, friendly stories and small numbers,
and make it feel like a game.

Reply with JSON only, no prose and no code fences, in exactly this shape:
{"questions": [
  {"kind": "choice", "prompt": "...", "options": ["...", "...", "..."], "answer": "<one option, copied exactly>",
   "hint": "a nudge that does not give the answer", "explanation": "why the answer is right"},
  {"kind": "number", "prompt": "...", "answer": "12", "hint": "...", "explanation": "..."},
  {"kind": "text", "prompt": "...", "answer": "a word or short phrase", "accept": ["other correct spellings"],
   "hint": "...", "explanation": "..."}
]}
Rules: write {count} questions, easiest first, mixing the kinds that suit the subject. A
"number" answer is a plain number or fraction (no units in the answer; say the unit in the
prompt). A "text" answer is at most three words with every acceptable variant in "accept".
Every question has exactly one correct answer. Check each answer before you reply."""


def number(text: str) -> Fraction | None:
    clean = text.strip().replace(",", "").replace(" ", "")
    try:
        return Fraction(clean)
    except (ValueError, ZeroDivisionError):
        return None


def normal(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", "", text.casefold())).strip()


def correct(question: dict, given: str) -> bool:
    kind = question["kind"]
    if kind == "choice":
        return given.strip() == question["answer"]
    if kind == "number":
        mine, theirs = number(given), number(question["answer"])
        return mine is not None and theirs is not None and abs(mine - theirs) <= Fraction(1, 10**6)
    return normal(given) in {normal(a) for a in [question["answer"], *question.get("accept", [])]}


def parse(reply: str) -> list[dict]:
    """The questions in a model reply; raises ValueError when there are none worth keeping."""
    start, end = reply.find("{"), reply.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in the reply")
    try:
        raw = json.loads(reply[start : end + 1])
    except ValueError as exc:
        raise ValueError("the reply is not JSON") from exc
    kept = []
    for item in raw.get("questions", []) if isinstance(raw, dict) else []:
        try:
            kept.append(Question.model_validate(item).model_dump())
        except ValidationError:
            continue  # drop one bad question, keep the rest
    try:
        Drafted.model_validate({"questions": kept})
    except ValidationError as exc:
        raise ValueError("too few gradable questions") from exc
    return kept[:QUESTIONS]


def from_concept_checks(concept: Concept, language: str) -> list[dict]:
    """Without a model, the topic's own concept checks become the set (choice questions)."""
    out = []
    for item in concept.quiz:
        if item.kind != "mcq" or item.code or not item.fits(language):
            continue
        if len(set(item.options)) != len(item.options) or item.answer >= len(item.options):
            continue
        out.append(
            dict(
                kind="choice",
                prompt=item.prompt,
                options=list(item.options),
                answer=item.options[item.answer],
                accept=[],
                hint="",
                explanation=item.explanation,
            )
        )
    return out[:QUESTIONS]


def brief(cat: Catalog, course_id: str, qualified: str, user: User, stamp: int) -> str:
    course = cat.course(course_id)
    concept = cat.concept(qualified)
    age = ""
    if user.birth_year:
        years = datetime.fromtimestamp(stamp, UTC).year - user.birth_year
        if 3 <= years <= 100:
            age = f"\nLearner's age: about {years}."
    points = "\n".join(f"- {p}" for p in concept.key_points) or "- (none listed)"
    pitfalls = "\n".join(f"- {p}" for p in concept.pitfalls) or "- (none listed)"
    return (
        f"Course: {course.title}\nAbout the course: {course.description}\n"
        f"Topic: {concept.title}\nSummary: {concept.summary}\n"
        f"Key points:\n{points}\nCommon mistakes:\n{pitfalls}{age}\n\n"
        f"Write {QUESTIONS} practice questions on this topic."
    )


def concepts(cat: Catalog, course_id: str, locked: dict) -> list[dict]:
    """The course's topics a learner can practise: written ones, unlocked first."""
    items = []
    for q in cat.course_concepts(course_id):
        concept = cat.concept(q)
        if concept.status != "live":
            continue
        items.append(dict(concept=q, title=concept.title, locked=q in locked))
    return items


def _records(db: Session, enrollment: Enrollment) -> list[ActivityRecord]:
    return list(
        db.scalars(
            select(ActivityRecord)
            .where(
                ActivityRecord.enrollment_id == enrollment.id,
                ActivityRecord.activity_id.like(f"{PREFIX}%"),
            )
            .order_by(ActivityRecord.started_at.desc())
        )
    )


def made_since(db: Session, enrollment: Enrollment, since: int) -> int:
    return sum(r.started_at >= since for r in _records(db, enrollment))


def summary(record: ActivityRecord) -> dict:
    outcome = record.outcome
    answered = outcome.get("answers", {})
    return dict(
        id=record.activity_id.removeprefix(PREFIX),
        concept=outcome["concept"],
        title=outcome["title"],
        created_at=record.started_at,
        questions=len(outcome["questions"]),
        answered=len(answered),
        correct=sum(a["correct"] for a in answered.values()),
    )


def history(db: Session, enrollment: Enrollment) -> list[dict]:
    return [summary(r) for r in _records(db, enrollment)[:KEEP]]


def view(record: ActivityRecord) -> dict:
    """The set as the learner sees it: answers and explanations only once answered."""
    outcome = record.outcome
    answers = outcome.get("answers", {})
    questions = []
    for index, q in enumerate(outcome["questions"]):
        item = dict(index=index, kind=q["kind"], prompt=q["prompt"], options=q["options"])
        item["hint"] = q.get("hint", "")
        if (given := answers.get(str(index))) is not None:
            item |= dict(
                given=given["given"],
                correct=given["correct"],
                expected=q["answer"],
                explanation=q["explanation"],
            )
        questions.append(item)
    return summary(record) | dict(items=questions, source=outcome.get("source", "model"))


def find(db: Session, enrollment: Enrollment, set_id: str) -> ActivityRecord | None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,32}", set_id):
        return None
    return db.get(ActivityRecord, (enrollment.id, f"{PREFIX}{set_id}"))


async def draft(
    provider: Provider, cat: Catalog, enrollment: Enrollment, user: User, qualified: str, stamp: int
) -> tuple[list[dict], str]:
    """Questions for the topic and where they came from ("model" or "checks")."""
    try:
        reply = await complete(
            provider,
            SYSTEM.replace("{count}", str(QUESTIONS)),
            [Turn("user", brief(cat, enrollment.course_id, qualified, user, stamp))],
            2500,
        )
        return parse(reply), "model"
    except (ProviderError, ValueError) as exc:
        fallback = from_concept_checks(cat.concept(qualified), enrollment.language)
        if len(fallback) >= 2:
            return fallback, "checks"
        if isinstance(exc, ProviderError):
            raise
        raise ProviderError("practice_unparsable") from exc


def store(
    db: Session,
    enrollment: Enrollment,
    cat: Catalog,
    qualified: str,
    questions: list[dict],
    source: str,
    stamp: int,
) -> ActivityRecord:
    record = ActivityRecord(
        enrollment_id=enrollment.id,
        activity_id=f"{PREFIX}{secrets.token_urlsafe(9)}",
        started_at=stamp,
        completed_at=None,  # never completed: a practice set is not a plan step
        outcome=dict(
            concept=qualified,
            title=cat.concept(qualified).title,
            questions=questions,
            answers={},
            source=source,
        ),
    )
    db.add(record)
    db.flush()
    return record


def answer(record: ActivityRecord, index: int, given: str, stamp: int) -> dict:
    """Grade one question once; a second answer to the same question is refused."""
    outcome = dict(record.outcome)
    questions = outcome["questions"]
    if not 0 <= index < len(questions):
        raise LookupError("no such question")
    answers = dict(outcome.get("answers", {}))
    if str(index) in answers:
        raise ValueError("already answered")
    question = questions[index]
    if question["kind"] == "choice" and given not in question["options"]:
        raise LookupError("not one of the options")
    right = correct(question, given)
    answers[str(index)] = dict(given=given, correct=right, at=stamp)
    outcome["answers"] = answers
    record.outcome = outcome  # reassign so the JSON column is written
    return dict(correct=right, expected=question["answer"], explanation=question["explanation"])
