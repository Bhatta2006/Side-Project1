"""Review variants (backlog 4.2, flag ``gen_review_variants``): parallel quiz items per concept,
same skill in a new context, so a review or a session-one retrieval is not the check the learner
already answered. One ``variants`` job per released concept; one model call; code settles each
answer key (``keyed.settle``), validates the items and drops any that repeat an original prompt.
Stored on the concept as ``review_items``; reviews prefer them (``learn.quizzes.choose_items``)."""

import json

from pydantic import ValidationError
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from socrat.assistant.gateway import make_provider
from socrat.catalog import generated
from socrat.catalog.atoms import AtomPack
from socrat.catalog.registry import Catalog
from socrat.catalog.schema import QuizItem
from socrat.config import Settings
from socrat.coursegen import keyed, roles
from socrat.models import GeneratedConcept, GenerationJob

KIND = "variants"
PER_ITEM = 2  # at most this many variants of one original item
MOST = 12

VARIANTS = """You are the Quiz Builder for Socrat. For each quiz item given, write up to two new
items that check the SAME skill in a NEW context: a different scenario, numbers or example, never
the same question reworded. Use only facts the lesson teaches. Keep each item's difficulty.

- 3-5 distinct options; vary the correct position; never "all/none of the above".
- explanation says why the right answer is right and why the most tempting wrong one is wrong.
- "variant_of" is the id of the item you started from.

Reply with one JSON object only:
{"items": [{"id": "kebab-case", "variant_of": "<item id>", "prompt": "...", "options": ["..."],
            "answer": 0, "explanation": "...", "difficulty": 1}]}"""


def prompt(lesson: str, quiz: list[QuizItem]) -> str:
    items = [
        dict(id=q.id, prompt=q.prompt, options=q.options, answer=q.answer, difficulty=q.difficulty)
        for q in quiz
    ]
    return f"Lesson (excerpt):\n{lesson[:6000]}\n\nQuiz items:\n{json.dumps(items, indent=1)}"


def check(reply: dict | None, quiz: list[QuizItem]) -> tuple[list[QuizItem], list[str]]:
    """(kept items, problems). A bad item is dropped, never repaired; ids get a "v-" prefix so
    they never collide with the concept's own quiz ids."""
    originals = {q.id: q for q in quiz}
    seen_prompts = {" ".join(q.prompt.lower().split()) for q in quiz}
    kept: list[QuizItem] = []
    per: dict[str, int] = {}
    problems: list[str] = []
    for raw in (reply or {}).get("items") or []:
        if not isinstance(raw, dict) or raw.get("variant_of") not in originals:
            problems.append("an item names no known original")
            continue
        source = originals[raw["variant_of"]]
        try:
            data = keyed.settle(dict(raw))
            data.pop("variant_of", None)
            data["id"] = f"v-{str(data.get('id', ''))[:50]}"
            data["difficulty"] = source.difficulty
            data["languages"] = source.languages
            item = QuizItem.model_validate(data)
        except (TypeError, ValidationError) as exc:
            problems.append(f"{raw.get('id')}: {str(exc)[:120]}")
            continue
        text = " ".join(item.prompt.lower().split())
        if text in seen_prompts or per.get(source.id, 0) >= PER_ITEM:
            continue  # a reworded copy, or enough for this item
        if any(k.id == item.id for k in kept):
            continue
        seen_prompts.add(text)
        per[source.id] = per.get(source.id, 0) + 1
        kept.append(item)
        if len(kept) >= MOST:
            break
    return kept, problems


async def run_variants(
    engine: Engine, settings: Settings, base: Catalog, job_id: str, make=make_provider
) -> None:
    from socrat.coursegen.jobs import _note
    from socrat.models import need

    with Session(engine) as db:
        job = need(db.get(GenerationJob, job_id))
        course_id, concept_id = job.course_id, job.target
        course = generated.course(db, course_id)
    concept = next((c for c in course.concepts if c.id == concept_id), None) if course else None
    if concept is None or concept.status != "live" or len(concept.quiz) < 2:
        _note(engine, job_id, {"role": "system", "event": "nothing_to_vary"}, state="done")
        return
    reply = await roles.ask(
        engine, settings, "quiz", VARIANTS, prompt(concept.lesson, concept.quiz), 6000, make
    )
    items, problems = check(reply.data, concept.quiz)
    with Session(engine) as db, db.begin():
        row = db.get(GeneratedConcept, (course_id, concept_id))
        now_course = generated.course(db, course_id)
        current = next(
            (c for c in (now_course.concepts if now_course else []) if c.id == concept_id), None
        )
        same = current is not None and [q.id for q in current.quiz] == [q.id for q in concept.quiz]
        if items and current is not None and same and row is not None:
            atoms = AtomPack.model_validate(row.atoms) if row.atoms else None
            updated = current.model_copy(update={"review_items": items})
            generated.store_concept(db, base, course_id, updated, atoms, reason="variants")
    event = {"role": "quiz", "event": "variants", "kept": len(items), "problems": problems[:10]}
    if not same:
        event["event"] = "lesson_changed"  # rewritten meanwhile: these variants fit the old quiz
    _note(engine, job_id, event, reply.cost_usd, state="done")
