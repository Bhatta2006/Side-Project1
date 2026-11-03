"""Enrollment creation and the adaptive placement check."""

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.learn import service as learn
from socrat.mastery.model import placed
from socrat.models import Enrollment, User
from socrat.placement import engine as placement


def enroll(
    db: Session,
    catalog: Catalog,
    user: User,
    course_id: str,
    language: str,
    level_id: str,
    goal: dict,
    minutes_per_day: int,
    weekdays: list[int],
    now: int,
) -> Enrollment:
    course = catalog.course(course_id)
    if language not in course.languages:
        raise HTTPException(422, "language_not_offered")
    level = next((x for x in course.levels if x.id == level_id), None)
    if level is None:
        raise HTTPException(422, "unknown_level")
    db.execute(update(Enrollment).where(Enrollment.user_id == user.id).values(active=False))
    enrollment = Enrollment(
        user_id=user.id,
        course_id=course_id,
        language=language,
        level_id=level_id,
        goal=goal,
        minutes_per_day=minutes_per_day,
        weekdays=sorted(set(weekdays)),
        status="placement",
        active=True,
        created_at=now,
    )
    db.add(enrollment)
    db.flush()
    # Planned concepts have no questions to probe with yet.
    path = [
        c
        for c in catalog.closure(catalog.course_concepts(course_id))
        if catalog.concept(c).status != "planned"
    ]
    start = f"{course_id}:{level.start_concept}" if level.start_concept else None
    if start is not None and start not in path:
        # The level starts at a concept whose lesson is not written yet (a generated course).
        # Everything before it counts as already known, so the plan begins there, and there is
        # nothing to probe: placement ends at once.
        # "Before" means both: earlier in dependency order (prerequisites, also from other
        # courses) and earlier in the course's own module order, which is what checkpoints
        # gate on. Dependency order alone can put the start ahead of a deeper concept of an
        # earlier module; that module's checkpoint then locked the start (found in a live run).
        order = catalog.closure(catalog.course_concepts(course_id))
        own = catalog.course_concepts(course_id)
        earlier = set(order[: order.index(start)] if start in order else [])
        earlier |= set(own[: own.index(start)] if start in own else [])
        for concept in [c for c in order if c in earlier]:
            learn.set_state(db, enrollment, concept, placed(True, now), now)
        start = None
    state = placement.start(
        catalog, path, start, seed=int(enrollment.id.replace("-", "")[:8], 16), language=language
    )
    enrollment.placement = state.to_dict()
    if state.done:
        finish(db, catalog, enrollment, state, now)
    return enrollment


def current(catalog: Catalog, enrollment: Enrollment) -> placement.PlacementState:
    if enrollment.placement is None:
        raise HTTPException(409, "placement_not_started")
    return placement.PlacementState.from_dict(enrollment.placement)


def question_view(catalog: Catalog, enrollment: Enrollment) -> dict:
    state = current(catalog, enrollment)
    if state.done or enrollment.status != "placement":
        return {"done": True, "asked": len(state.asked)}
    q = placement.question(catalog, state)
    assert q is not None and state.pending is not None
    concept = catalog.concept(state.pending["concept"])
    return {
        "done": False,
        "asked": len(state.asked),
        "max_questions": placement.MAX_QUESTIONS,
        "question": {
            "id": q.id,
            "topic": concept.title,
            "prompt": q.prompt,
            "kind": q.kind,
            "code": q.snippet(enrollment.language),
            "options": q.shown(placement.seed_of(state))["options"],
        },
    }


def answer(
    db: Session,
    catalog: Catalog,
    enrollment: Enrollment,
    item_id: str,
    choice: int | None,
    now: int,
) -> dict:
    state = current(catalog, enrollment)
    if state.done or enrollment.status != "placement":
        raise HTTPException(409, "placement_complete")
    q = placement.question(catalog, state)
    if q is None or q.id != item_id:
        raise HTTPException(409, "stale_question")
    if choice is not None and not 0 <= choice < len(q.options):
        raise HTTPException(422, "invalid_choice")
    # "I don't know" is an honest, valid answer; it counts as not yet known.
    placement.answer(catalog, state, choice if choice is not None else -1)
    enrollment.placement = state.to_dict()
    if state.done:
        finish(db, catalog, enrollment, state, now)
    return question_view(catalog, enrollment)


def finish(
    db: Session, catalog: Catalog, enrollment: Enrollment, state: placement.PlacementState, now: int
):
    for concept, known in placement.result(state).items():
        learn.set_state(db, enrollment, concept, placed(known, now), now)
    enrollment.status = "active"
    enrollment.placement = state.to_dict()
    from socrat.coursegen import prefetch

    prefetch.request(db, enrollment, now, catalog)


def summary(catalog: Catalog, enrollment: Enrollment) -> dict:
    state = current(catalog, enrollment)
    known = placement.result(state)
    start = next((c for c in state.path if not known[c]), None)
    return {
        "asked": len(state.asked),
        "correct": sum(1 for x in state.asked if x["correct"]),
        "known_concepts": [catalog.concept(c).title for c, k in known.items() if k],
        "starting_concept": catalog.concept(start).title if start else None,
    }
