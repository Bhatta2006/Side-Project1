"""Learner API. Every write is CSRF-checked and runs in one transaction."""

import secrets
from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat import entitlements
from socrat.assistant import budget
from socrat.assistant import service as assistant
from socrat.assistant.gateway import make_provider
from socrat.assistant.tools import Toolbox
from socrat.auth import COOKIE, require_csrf, require_session
from socrat.catalog import generated, practice
from socrat.catalog.registry import Catalog, CatalogError, default_catalog
from socrat.database import record_event
from socrat.execution.protocol import ResultEnvelope
from socrat.judge import service as judge
from socrat.learn import placement, playground, quizzes, resources, views
from socrat.learn import service as learn
from socrat.mastery.model import ConceptState, band
from socrat.models import (
    AuditEvent,
    DailyActivity,
    DeliveredEvent,
    Draft,
    Enrollment,
    OutboxEvent,
    Submission,
    User,
    now,
)

router = APIRouter(prefix="/api/v1")
MIN_AGE = 13


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProfileUpdate(Strict):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    birthday_passed: bool = True
    timezone: str | None = Field(default=None, max_length=64)

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value):
        if value is None:
            return value
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError) as exc:
            raise ValueError("Choose an IANA timezone") from exc
        return value


class EnrollInput(Strict):
    course: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    language: Literal["python", "cpp", "java"]
    level: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    minutes_per_day: Literal[15, 20, 30, 45, 60, 90, 120]
    weekdays: list[int] = Field(min_length=1, max_length=7)
    target_date: date | None = None
    target_role: Literal["internship", "new-grad", "mid-level", "senior"] | None = None
    target_rating: int | None = Field(default=None, ge=0, le=4000)
    motivation: str | None = Field(default=None, max_length=280)

    @field_validator("weekdays")
    @classmethod
    def valid_days(cls, value):
        if any(d not in range(7) for d in value):
            raise ValueError("weekdays are 0 (Monday) to 6 (Sunday)")
        return value


class ScheduleUpdate(Strict):
    language: Literal["python", "cpp", "java"] | None = None
    minutes_per_day: Literal[15, 20, 30, 45, 60, 90, 120] | None = None
    weekdays: list[int] | None = Field(default=None, min_length=1, max_length=7)
    target_date: date | None = None
    clear_target_date: bool = False
    target_role: Literal["internship", "new-grad", "mid-level", "senior"] | None = None
    target_rating: int | None = Field(default=None, ge=0, le=4000)
    motivation: str | None = Field(default=None, max_length=280)

    @field_validator("weekdays")
    @classmethod
    def valid_days(cls, value):
        if value is not None and any(d not in range(7) for d in value):
            raise ValueError("weekdays are 0 (Monday) to 6 (Sunday)")
        return value


class PlacementAnswer(Strict):
    item: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    choice: int | None = Field(default=None, ge=0, le=9)


class QuizAnswer(Strict):
    item: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    choice: int = Field(ge=0, le=9)


class SourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: str = Field(max_length=64_000)
    language: Literal["python", "cpp", "java"] | None = None


class RunInput(SourceInput):
    custom_input: str | None = Field(default=None, max_length=20_000)


class ExplainInput(Strict):
    style: Literal["simpler", "example", "deeper"]


class MessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: str = Field(max_length=200)
    message: str = Field(default="", max_length=4000)
    intent: Literal["chat", "hint", "reveal", "reveal_confirmed"] = "chat"
    code: str = Field(default="", max_length=64_000)
    new_attempt: bool = False  # Compatibility hint; completed runs are verified by the server.


class WorkerInput(Strict):
    worker_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")


class Heartbeat(WorkerInput):
    images: list[str] = Field(min_length=1, max_length=3)


class Callback(BaseModel):
    model_config = ConfigDict(extra="forbid")
    worker_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    envelope: ResultEnvelope


def catalog() -> Catalog:
    try:
        return generated.merged(default_catalog())
    except CatalogError as exc:
        raise HTTPException(503, "content_unavailable") from exc


def engine(request: Request):
    return request.app.state.engine


def user_of(request: Request, db: Session, write: bool = False) -> User:
    session = require_session(request, db)
    if write:
        require_csrf(request, session)
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(401, "authentication_required")
    return user


def age_ok(birth_year: int | None, birthday_passed: bool, today: date) -> bool:
    if birth_year is None:
        return False
    age = today.year - birth_year - (0 if birthday_passed else 1)
    return age >= MIN_AGE


def is_admin(request: Request, user: User) -> bool:
    settings = request.app.state.settings
    allowed = settings.admin_subjects
    emails = {e.lower() for e in settings.admin_emails}
    return (
        f"{user.issuer}|{user.subject}" in allowed
        or user.subject in allowed
        or (user.admin_email is not None and user.admin_email in emails)
    )


def profile_view(db: Session, user: User, csrf: str, admin: bool = False) -> dict:
    enrollment = learn.active_enrollment(db, user.id)
    return dict(
        id=user.id,
        admin=admin,
        display_name=user.display_name,
        birth_year=user.birth_year,
        timezone=user.timezone,
        csrf_token=csrf,
        onboarded=enrollment is not None,
        tour_seen=user.tour_seen_at is not None,
        enrollment=None
        if enrollment is None
        else dict(
            id=enrollment.id,
            course=enrollment.course_id,
            language=enrollment.language,
            status=enrollment.status,
            minutes_per_day=enrollment.minutes_per_day,
            weekdays=enrollment.weekdays,
            goal=enrollment.goal,
            level=enrollment.level_id,
        ),
    )


# ---------------------------------------------------------------- account


@router.get("/auth/status")
def auth_status(request: Request):
    with Session(engine(request)) as db:
        try:
            session = require_session(request, db)
        except HTTPException:
            return {"profile": None}
        user = db.get(User, session.user_id)
        return {
            "profile": profile_view(db, user, session.csrf_token, is_admin(request, user))
            if user
            else None
        }


@router.get("/me")
def me(request: Request):
    with Session(engine(request)) as db:
        session = require_session(request, db)
        user = db.get(User, session.user_id)
        if user is None:
            raise HTTPException(401, "authentication_required")
        return profile_view(db, user, session.csrf_token, is_admin(request, user))


@router.get("/me/summary")
def me_summary(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = learn.active_enrollment(db, user.id)
        if enrollment is None or enrollment.status != "active":
            return {"streak": None, "minutes": None}
        stamp = now()
        day = db.get(DailyActivity, (user.id, learn.local_day(user, stamp).isoformat()))
        return {
            "streak": learn.streak(db, user, enrollment, stamp),
            "minutes": {"done": day.minutes if day else 0, "goal": enrollment.minutes_per_day},
        }


@router.patch("/me")
def update_me(body: ProfileUpdate, request: Request):
    with Session(engine(request)) as db, db.begin():
        session = require_session(request, db)
        require_csrf(request, session)
        user = db.get(User, session.user_id)
        if user is None:
            raise HTTPException(401, "authentication_required")
        if body.birth_year is not None:
            if not age_ok(body.birth_year, body.birthday_passed, date.today()):
                raise HTTPException(403, "minimum_age")
            user.birth_year = body.birth_year
        if body.display_name is not None:
            user.display_name = body.display_name
        if body.timezone is not None:
            user.timezone = body.timezone
        record_event(db, user.id, "profile.updated")
        return profile_view(db, user, session.csrf_token, is_admin(request, user))


@router.post("/me/tour", status_code=204)
def finish_tour(request: Request):
    """Records that the learner finished or skipped the first-run tour, so it shows once."""
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        if user.tour_seen_at is None:
            user.tour_seen_at = now()


@router.get("/me/export")
def export_me(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        return views.export(db, user)


@router.delete("/me", status_code=204)
def delete_me(request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        events = select(OutboxEvent.id).where(
            OutboxEvent.payload["actor_id"].as_string() == user.id
        )
        db.execute(delete(DeliveredEvent).where(DeliveredEvent.event_id.in_(events)))
        db.execute(
            delete(OutboxEvent).where(OutboxEvent.payload["actor_id"].as_string() == user.id)
        )
        db.execute(delete(AuditEvent).where(AuditEvent.actor_id == user.id))
        db.delete(user)  # Everything else cascades from the user row.
    response = Response(status_code=204)
    response.delete_cookie(COOKIE, path="/")
    return response


# ---------------------------------------------------------------- catalog & enrollment


@router.get("/attribution")
def attribution():
    """Public: the sources Socrat links to or adapts, and every adapted record."""
    from socrat.catalog import sources

    registry = sources.load_registry()
    use = {
        "adapt": "May be adapted with attribution",
        "share-alike-lane": "May be adapted in a labelled share-alike section",
        "link-only": "Linked only; not copied or adapted",
        "per-item": "License differs per item; linked unless an item is verified",
        "verify": "Not used until its license is verified",
    }
    return {
        "sources": [
            dict(
                id=entry.id,
                name=entry.name,
                url=str(entry.url),
                content=entry.content,
                license=entry.license,
                license_status=entry.license_status,
                use=use[entry.action],
            )
            for entry in registry.sources
        ],
        "adapted": [
            dict(
                record=where,
                attribution=provenance.attribution_md,
                sources=[
                    dict(
                        title=ref.title,
                        author=ref.author,
                        url=str(ref.url),
                        license=ref.license_spdx,
                    )
                    for ref in provenance.authors_adapted_from
                ],
            )
            for where, provenance in sources.provenances(catalog())
            if provenance.origin == "adapted"
        ],
    }


@router.get("/courses")
def courses():
    cat = catalog()
    return {
        "items": [
            views.course_card(cat, cid) for cid in ("zero", "dsa", "cp") if cid in cat.courses
        ]
        + [
            views.course_card(cat, cid)
            for cid in sorted(cat.courses)
            if cid not in {"zero", "dsa", "cp"}
        ]
    }


@router.post("/enrollments")
def enroll(body: EnrollInput, request: Request):
    cat = catalog()
    if body.course not in cat.courses:
        raise HTTPException(404, "unknown_course")
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        if user.birth_year is None:
            raise HTTPException(409, "profile_incomplete")
        # Course switching is off for now: one course per learner.
        if learn.active_enrollment(db, user.id) is not None:
            raise HTTPException(409, "already_enrolled")
        goal = {
            k: v
            for k, v in dict(
                target_date=body.target_date.isoformat() if body.target_date else None,
                target_role=body.target_role,
                target_rating=body.target_rating,
                motivation=body.motivation,
            ).items()
            if v is not None
        }
        enrollment = placement.enroll(
            db,
            cat,
            user,
            body.course,
            body.language,
            body.level,
            goal,
            body.minutes_per_day,
            body.weekdays,
            now(),
        )
        record_event(db, user.id, "enrollment.created", enrollment.id)
        return dict(id=enrollment.id, status=enrollment.status)


@router.patch("/enrollments/current")
def update_enrollment(body: ScheduleUpdate, request: Request):
    """Change study budget, language or goal; the plan re-flows and the revision says why."""
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = learn.require_enrollment(db, user.id)
        changes = []
        if body.language is not None and body.language != enrollment.language:
            if body.language not in cat.course(enrollment.course_id).languages:
                raise HTTPException(422, "language_not_offered")
            enrollment.language = body.language
            changes.append(f"language is now {views.LANGUAGES[body.language]}")
        if body.minutes_per_day is not None and body.minutes_per_day != enrollment.minutes_per_day:
            enrollment.minutes_per_day = body.minutes_per_day
            changes.append(f"{body.minutes_per_day} min per study day")
        if body.weekdays is not None and sorted(set(body.weekdays)) != enrollment.weekdays:
            enrollment.weekdays = sorted(set(body.weekdays))
            changes.append(f"{len(enrollment.weekdays)} study days a week")
        goal = dict(enrollment.goal)
        if body.clear_target_date and "target_date" in goal:
            goal.pop("target_date")
            changes.append("no target date")
        elif (
            body.target_date is not None and goal.get("target_date") != body.target_date.isoformat()
        ):
            goal["target_date"] = body.target_date.isoformat()
            changes.append(f"target date {body.target_date.isoformat()}")
        for key in ("target_role", "target_rating", "motivation"):
            value = getattr(body, key)
            if value is not None and goal.get(key) != value:
                goal[key] = value
        enrollment.goal = goal
        if changes and enrollment.status == "active":
            learn.revise(
                db, cat, user, enrollment, now(), f"You updated your plan: {', '.join(changes)}."
            )
        record_event(db, user.id, "enrollment.updated", enrollment.id)
        session = require_session(request, db)
        return profile_view(db, user, session.csrf_token, is_admin(request, user))


@router.get("/placement")
def placement_question(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        return placement.question_view(catalog(), learn.require_enrollment(db, user.id))


@router.post("/placement/answer")
def placement_answer(body: PlacementAnswer, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = learn.require_enrollment(db, user.id)
        return placement.answer(db, catalog(), enrollment, body.item, body.choice, now())


@router.get("/placement/summary")
def placement_summary(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        return placement.summary(catalog(), learn.require_enrollment(db, user.id))


# ---------------------------------------------------------------- plan & today


def active(db: Session, user: User) -> Enrollment:
    enrollment = learn.require_enrollment(db, user.id)
    if enrollment.status != "active":
        raise HTTPException(409, "placement_in_progress")
    return enrollment


@router.get("/today")
def today(request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        return views.today_view(db, catalog(), user, active(db, user), now())


@router.get("/plan")
def plan(request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        return views.plan_view(db, catalog(), user, active(db, user), now())


@router.get("/progress")
def progress(request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        return views.progress_view(db, catalog(), user, active(db, user), now())


# ---------------------------------------------------------------- lessons & quizzes


@router.get("/playground")
def playground_overview(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        guard_instruction(db, catalog(), user)
        return playground.overview(db, catalog(), user, enrollment, now())


@router.get("/concepts/{qualified}")
def concept(qualified: str, request: Request):
    cat = catalog()
    if qualified not in cat.concepts:
        raise HTTPException(404, "not_found")
    with Session(engine(request)) as db:
        user = user_of(request, db)
        guard_instruction(db, cat, user, qualified)
        return views.concept_view(
            db, cat, user, learn.active_enrollment(db, user.id), qualified, now()
        )


@router.post("/concepts/{qualified}/explain")
async def explain(qualified: str, body: ExplainInput, request: Request):
    cat = catalog()
    if qualified not in cat.concepts:
        raise HTTPException(404, "not_found")
    settings = request.app.state.settings
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        guard_instruction(db, cat, user, qualified)
        enrollment = learn.active_enrollment(db, user.id)
        language = enrollment.language if enrollment else "python"
        text, provider = await assistant.lesson_variant(
            db,
            budget.Metered(
                make_provider(settings),
                engine(request),
                settings,
                user_id=user.id,
                feature="lesson",
                db=db,
            ),
            cat,
            settings,
            qualified,
            language,
            body.style,
        )
        return {"content": text, "provider": provider}


ACTIVITY = (
    r"^(lesson|quiz|review|remedial|problem|checkpoint|probe|testout|moduletest"
    r"|example|explain|checkin|stretch):[a-z0-9:-]{1,160}$"
)
# Activities the learner finishes themselves (reading, talking it through, a stretch).
SELF_COMPLETE = {"lesson", "example", "explain", "checkin", "stretch"}


def guard_instruction(db: Session, cat: Catalog | None, user: User, qualified: str | None = None):
    """``cat`` may be None: it is loaded only to check a ``qualified`` concept. The catalog takes
    ~770 MB, so the Playground worker (512 MB) must not load it to save a finished visual."""
    from socrat.assessments import service as assessments
    from socrat.learn import sessions

    enrollment = learn.active_enrollment(db, user.id)
    if enrollment is None:
        raise HTTPException(404, "no_active_enrollment")

    def require_independent_work_finished():
        if sessions.instruction_blocked(db, enrollment, now()) or assessments.in_progress(
            db, enrollment, now()
        ):
            raise HTTPException(423, "independent_work_in_progress")

    if qualified is None:
        require_independent_work_finished()
        return
    full = cat or catalog()
    if qualified not in learn.curriculum(full, enrollment):
        raise HTTPException(404, "not_found")
    require_independent_work_finished()
    if enrollment.status == "active":
        learn.require_unlocked(db, full, enrollment, qualified, now())
    else:  # a paused or finished course still keeps to the plan
        entitlements.require_concept(db, full, user.id, qualified, now())


def activity_concept(cat: Catalog, activity_id: str) -> str | None:
    kind, _, target = activity_id.partition(":")
    if kind in {"checkpoint", "moduletest"}:
        return None  # gates check their own module
    if kind == "problem":
        course_id, problem = cat.problems[target]
        return f"{course_id}:{problem.concepts[0]}"
    return target


def guard(db: Session, cat: Catalog, enrollment: Enrollment, activity_id: str) -> None:
    """Concepts behind an unpassed gate can be previewed but not practised."""
    concept = activity_concept(cat, activity_id)
    if concept is not None:
        learn.require_unlocked(db, cat, enrollment, concept, now())
    elif activity_id.startswith(("checkpoint:", "moduletest:")):
        from socrat.planner import gates

        members = gates.module_concepts(cat, activity_id.partition(":")[2])
        if not any(c in learn.curriculum(cat, enrollment) for c in members):
            raise HTTPException(404, "not_found")
        if activity_id.startswith("moduletest:"):
            learn.require_unlocked(db, cat, enrollment, members[0], now())


def valid_activity(cat: Catalog, activity_id: str) -> str:
    import re

    if not re.match(ACTIVITY, activity_id):
        raise HTTPException(404, "not_found")
    kind, _, target = activity_id.partition(":")
    if kind == "problem" and target in cat.problems:
        return activity_id
    if kind in {"checkpoint", "moduletest"}:
        course_id, _, module_id = target.partition(":")
        if course_id in cat.courses and any(
            m.id == module_id for m in cat.course(course_id).modules
        ):
            return activity_id
        raise HTTPException(404, "not_found")
    if target in cat.concepts:
        return activity_id
    raise HTTPException(404, "not_found")


@router.post("/activities/{activity_id}/start")
def start_activity(activity_id: str, request: Request):
    cat = catalog()
    try:
        with Session(engine(request)) as db, db.begin():
            user = user_of(request, db, write=True)
            enrollment = active(db, user)
            activity = valid_activity(cat, activity_id)
            guard(db, cat, enrollment, activity)
            learn.start_activity(db, enrollment, activity, now())
    except IntegrityError:
        pass  # A concurrent request (e.g. a double-mounted page) started it first.
    return {"started": True}


@router.post("/activities/{activity_id}/complete")
def complete_lesson(activity_id: str, request: Request):
    cat = catalog()
    if activity_id.partition(":")[0] not in SELF_COMPLETE:
        raise HTTPException(409, "only_lessons_complete_directly")
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        activity = valid_activity(cat, activity_id)
        guard(db, cat, enrollment, activity)
        changed = learn.complete_activity(db, user, enrollment, activity, now())
        return {"completed": True, "first_time": changed}


@router.get("/quiz/{activity_id}")
def quiz(activity_id: str, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        guard_instruction(db, cat, user)
        enrollment = active(db, user)
        session = quizzes.open_session(db, cat, enrollment, valid_activity(cat, activity_id), now())
        return quizzes.session_view(cat, session, enrollment.language, db)


@router.post("/quiz/{activity_id}/answer")
def quiz_answer(activity_id: str, body: QuizAnswer, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        session = quizzes.open_session(db, cat, enrollment, valid_activity(cat, activity_id), now())
        quizzes.answer(db, cat, user, enrollment, session, body.item, body.choice, now())
        return quizzes.session_view(cat, session, enrollment.language, db)


# ---------------------------------------------------------------- company practice


@router.get("/companies")
def companies(request: Request, q: str = "", limit: int = 60):
    from socrat.library import service as library

    index = practice.default_index()
    with Session(engine(request)) as db:
        user = user_of(request, db)
        learner = library.learner_for(
            db, catalog(), user, learn.active_enrollment(db, user.id), now()
        )
        unlocked = entitlements.has(db, user.id, "companies")
    needle = q.strip().lower()
    items = [
        dict(
            slug=slug,
            name=c["name"],
            # Locked: the full bank size, as a preview of what Pro opens.
            problems=len(c["problems"])
            if not unlocked
            else sum(
                library_problem in index.problems
                and learner.can_practice(index.problems[library_problem])
                for library_problem, _, _ in c["problems"]
            ),
        )
        for slug, c in index.companies.items()
        if not needle or needle in c["name"].lower()
    ]
    items = [c for c in items if c["problems"]]
    items.sort(key=lambda c: (-c["problems"], c["name"]))
    return {
        "items": items[: max(1, min(limit, 700))],
        "total": len(items),
        "locked": not unlocked,  # names show as a preview; the questions need Pro
    }


@router.get("/companies/{slug}")
def company(
    slug: str,
    request: Request,
    window: Literal["thirty-days", "three-months", "six-months", "all"] = "all",
    difficulty: Literal["easy", "medium", "hard", "all"] = "all",
    offset: int = 0,
    limit: int = 50,
):
    from socrat.library import service as library

    index = practice.default_index()
    entry = index.companies.get(slug)
    if entry is None:
        raise HTTPException(404, "not_found")
    cat = catalog()
    with Session(engine(request)) as db:
        user = user_of(request, db)
        entitlements.require(db, user.id, "companies")
        enrollment = learn.active_enrollment(db, user.id)
        states = learn.states_for(db, enrollment) if enrollment else {}
        stamp = now()
        learner = library.learner_for(db, cat, user, enrollment, stamp)
    cutoff = practice.WINDOW_RANK[window]
    rows = []
    for problem_id, frequency, seen in entry["problems"]:
        problem = index.problems.get(problem_id)
        if (
            problem is None
            or not learner.can_practice(problem)
            or practice.WINDOW_RANK.get(seen, 4) > cutoff
        ):
            continue
        if difficulty != "all" and problem["difficulty"] != difficulty:
            continue
        primary = problem["concepts"][0] if problem["concepts"] else None
        rows.append(
            dict(
                practice.public(problem),
                frequency=frequency,
                window=seen,
                concept=None
                if primary is None or primary not in cat.concepts
                else dict(
                    id=primary,
                    title=cat.concept(primary).title,
                    band=band(states.get(primary, ConceptState()), stamp),
                ),
            )
        )
    offset = max(0, offset)
    return {
        "slug": slug,
        "name": entry["name"],
        "total": len(rows),
        "items": rows[offset : offset + max(1, min(limit, 100))],
    }


# ---------------------------------------------------------------- practice


def problem_or_404(cat: Catalog, problem_id: str):
    if problem_id not in cat.problems:
        raise HTTPException(404, "not_found")
    return cat.problem(problem_id)


def problem_in_scope(
    db: Session, cat: Catalog, user: User, enrollment: Enrollment | None, problem_id: str
) -> None:
    concept = f"{cat.problems[problem_id][0]}:{cat.problem(problem_id).concepts[0]}"
    if enrollment is None or concept not in learn.curriculum(cat, enrollment):
        raise HTTPException(404, "not_found")
    entitlements.require_concept(db, cat, user.id, concept, now())


@router.get("/runtimes")
def runtimes(request: Request):
    settings = request.app.state.settings
    with Session(engine(request)) as db:
        return {
            "backend": settings.execution_backend,
            "languages": judge.runtimes(db, settings, now()),
        }


@router.get("/problems/{problem_id}")
def problem(problem_id: str, request: Request, language: str | None = None):
    cat = catalog()
    problem_or_404(cat, problem_id)
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = learn.active_enrollment(db, user.id)
        problem_in_scope(db, cat, user, enrollment, problem_id)
        lang = (
            language
            if language in {"python", "cpp", "java"}
            else (enrollment.language if enrollment else "python")
        )
        return views.problem_view(db, cat, user, enrollment, problem_id, lang)


@router.put("/problems/{problem_id}/draft")
def save_draft(problem_id: str, body: SourceInput, request: Request):
    cat = catalog()
    problem_or_404(cat, problem_id)
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = learn.require_enrollment(db, user.id)
        problem_in_scope(db, cat, user, enrollment, problem_id)
        language = body.language or (enrollment.language if enrollment else "python")
        draft = db.get(Draft, (user.id, problem_id, language))
        if draft is None:
            db.add(
                Draft(
                    user_id=user.id,
                    problem_id=problem_id,
                    language=language,
                    source=body.source,
                    updated_at=now(),
                )
            )
        else:
            draft.source, draft.updated_at = body.source, now()
        return {"saved": True}


def queue(problem_id: str, body: RunInput, request: Request, mode: str):
    cat = catalog()
    problem_obj = problem_or_404(cat, problem_id)
    settings = request.app.state.settings
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = learn.require_enrollment(db, user.id)
        problem_in_scope(db, cat, user, enrollment, problem_id)
        language = body.language or (enrollment.language if enrollment else "python")
        if enrollment is not None and enrollment.status == "active":
            guard(db, cat, enrollment, f"problem:{problem_id}")
            from socrat.learn import sessions

            sessions.guard_problem_turn(db, user, enrollment, problem_id, now())
        if enrollment is not None and enrollment.status == "active" and mode == "submit":
            learn.start_activity(db, enrollment, f"problem:{problem_id}", now())
        job = judge.create(
            db,
            settings,
            user.id,
            enrollment.id if enrollment else None,
            problem_obj,
            language,
            body.source,
            mode,
            body.custom_input if mode == "run" else None,
            assistant.assistance_for(db, user.id, problem_id),
            now(),
        )
        draft = db.get(Draft, (user.id, problem_id, language))
        if draft is None:
            db.add(
                Draft(
                    user_id=user.id,
                    problem_id=problem_id,
                    language=language,
                    source=body.source,
                    updated_at=now(),
                )
            )
        else:
            draft.source, draft.updated_at = body.source, now()
        return judge.view(job)


@router.post("/problems/{problem_id}/run")
def run(problem_id: str, body: RunInput, request: Request):
    return queue(problem_id, body, request, "run")


@router.post("/problems/{problem_id}/submit")
def submit(problem_id: str, body: SourceInput, request: Request):
    return queue(
        problem_id, RunInput(source=body.source, language=body.language), request, "submit"
    )


@router.get("/submissions/{submission_id}")
def submission(submission_id: str, request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        job = db.get(Submission, submission_id)
        if job is None or job.user_id != user.id:
            raise HTTPException(404, "not_found")
        return judge.view(job)


class BrowserCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    index: int = Field(ge=0, le=99)
    status: Literal["executed", "compile_error", "runtime_error", "timeout", "output_limit"]
    digest: str = Field(default="", pattern=r"^([a-f0-9]{64})?$")
    wall_ms: int = Field(ge=0, le=120_000)
    stdout: str = Field(default="", max_length=16_000)
    stderr: str = Field(default="", max_length=16_000)


class BrowserResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(pattern=r"^[a-f0-9]{64}$")
    cases: list[BrowserCase] = Field(max_length=100)


@router.post("/submissions/{submission_id}/browser-result")
def browser_result(submission_id: str, body: BrowserResult, request: Request):
    """The learner's browser reports a local run; the server judges it from digests."""
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        job = db.get(Submission, submission_id, with_for_update=True)
        if job is None or job.user_id != user.id:
            raise HTTPException(404, "not_found")
        if judge.finalize_browser(job, body.token, [c.model_dump() for c in body.cases], now()):
            on_submission(db, cat, job, now())
        return judge.view(job)


def worker_auth(request: Request):
    settings = request.app.state.settings
    token = settings.execution_worker_secret.get_secret_value()
    if (
        not settings.worker_execution_enabled
        or not token
        or not secrets.compare_digest(request.headers.get("authorization", ""), "Bearer " + token)
    ):
        raise HTTPException(404, "not_found")


@router.post("/execution/worker/heartbeat")
def worker_heartbeat(body: Heartbeat, request: Request):
    worker_auth(request)
    with Session(engine(request)) as db, db.begin():
        judge.heartbeat(db, request.app.state.settings, body.worker_id, body.images, now())
    return {"ready": True, "server_now": now()}


@router.post("/execution/worker/claim")
def worker_claim(body: WorkerInput, request: Request):
    worker_auth(request)
    with Session(engine(request)) as db, db.begin():
        return {"job": judge.claim(db, body.worker_id, now())}


@router.post("/execution/worker/result")
def worker_result(body: Callback, request: Request):
    worker_auth(request)
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        job, fresh = judge.finalize(
            db, request.app.state.settings, body.worker_id, body.envelope, now()
        )
        if fresh:
            on_submission(db, cat, job, now())
        return judge.view(job)


def on_submission(db: Session, cat: Catalog, job: Submission, stamp: int):
    """Submit results become learning evidence; Runs never change mastery."""
    if job.mode != "submit" or job.status != "done" or job.enrollment_id is None:
        return
    enrollment = db.get(Enrollment, job.enrollment_id)
    user = db.get(User, job.user_id)
    if enrollment is None or user is None or job.problem_id not in cat.problems:
        return
    course_id, problem_obj = cat.problems[job.problem_id]
    concept = f"{course_id}:{problem_obj.concepts[0]}"
    activity = f"problem:{job.problem_id}"
    elapsed = learn.elapsed(db, enrollment, activity, stamp)
    expected = learn.expected_seconds(cat, activity, enrollment)
    if job.verdict == "accepted":
        already = activity in learn.completed_for(db, enrollment)
        if not already:
            learn.record_evidence(
                db,
                enrollment,
                concept,
                "code",
                1.0,
                activity,
                stamp,
                min(job.assistance, 5),
                elapsed,
                expected,
            )
            learn.complete_activity(
                db,
                user,
                enrollment,
                activity,
                stamp,
                outcome={"assistance": job.assistance},
                solved=True,
            )
        return
    if job.verdict in {"system_error", ""}:
        return
    today_start = stamp - 86400
    from socrat.models import Evidence

    earlier = db.scalar(
        select(Evidence.id).where(
            Evidence.enrollment_id == enrollment.id,
            Evidence.activity_id == activity,
            Evidence.created_at >= today_start,
        )
    )
    if earlier is None and activity not in learn.completed_for(db, enrollment):
        partial = 0.5 * job.passed / job.total if job.total else 0.0
        learn.record_evidence(
            db, enrollment, concept, "code", partial, activity, stamp, 0, elapsed, expected
        )


# ---------------------------------------------------------------- assistant


class RatingInput(Strict):
    rating: Literal[-1, 0, 1]


class ResourceAction(Strict):
    url: str = Field(min_length=8, max_length=512)
    action: Literal["open", "helpful", "unhelpful"]


@router.post("/assistant/messages/{message_id}/rating")
def rate_reply(message_id: str, body: RatingInput, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        return assistant.rate(db, user.id, message_id, body.rating)


@router.post("/concepts/{qualified}/resources")
def resource_event(qualified: str, body: ResourceAction, request: Request):
    cat = catalog()
    if qualified not in cat.concepts:
        raise HTTPException(404, "not_found")
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        return resources.record(
            db, user.id, qualified, cat.concept(qualified), body.url, body.action, now()
        )


@router.get("/assistant/thread")
def assistant_thread(scope: str, request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        guard_instruction(db, catalog(), user)
        return assistant.thread_view(db, user.id, scope)


class ChatScope(Strict):
    scope: str = Field(max_length=200)


@router.get("/assistant/chats")
def assistant_chats(scope: str, request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        return assistant.list_chats(db, user.id, scope)


@router.post("/assistant/chats")
def assistant_new_chat(body: ChatScope, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        return assistant.new_chat(db, user.id, body.scope, now())


@router.get("/assistant/chats/{thread_id}")
def assistant_chat(thread_id: str, request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        guard_instruction(db, catalog(), user)
        return assistant.chat_view(db, user.id, thread_id)


@router.post("/assistant/chats/{thread_id}/resume")
def assistant_resume_chat(thread_id: str, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        return assistant.resume_chat(db, user.id, thread_id, now())


@router.get("/assistant/context")
def assistant_context(scope: str, request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        return assistant.context_view(db, catalog(), user, scope, now())


@router.post("/assistant/messages")
async def assistant_message(body: MessageInput, request: Request):
    cat = catalog()
    settings = request.app.state.settings
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        user_id = user.id
        turn = assistant.prepare(
            db,
            cat,
            settings,
            user,
            body.scope,
            body.message,
            body.intent,
            body.code,
            body.new_attempt,
            now(),
        )
    bind = engine(request)
    provider = budget.Metered(
        make_provider(settings), bind, settings, user_id=user_id, feature="tutor"
    )
    toolbox = Toolbox(bind, cat, user_id)

    async def events():
        async for event, data in assistant.stream_reply(
            provider, turn, settings, toolbox.specs, toolbox.run
        ):
            if event == "done":
                with Session(bind) as db, db.begin():
                    message = assistant.persist_reply(
                        db, turn.thread_id, data["text"], data["level"], data["provider"], now()
                    )
                    data = {**data, "message_id": message.id if message else None}
            yield assistant.sse(event, data)

    return StreamingResponse(
        events(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"}
    )
