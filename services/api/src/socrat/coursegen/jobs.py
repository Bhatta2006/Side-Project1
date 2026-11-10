"""Generation jobs: queued by the admin, claimed and run by a background loop.

An ``outline`` job runs the Course Architect, checks its outline against the schema and the
live catalog, asks the Curriculum Critic, and revises until the critic passes it or the
rounds run out. The best valid outline is stored for the owner's review, never published.

A ``package`` job writes one planned concept's lesson, quiz and atoms (see ``package``) and
releases it only when every gate, the fact check and the reviewer pass. When the execution
plane runs every course language, quiz items and atoms may carry code, which is run.

An ``exercise`` job adds one judged problem to a live concept (see ``exercise``); a released
concept whose outline asks for code queues one.

A ``project`` job designs a module's project (see ``project``); releasing the last concept of
a module whose outline asks for a project queues one.

States (``GenerationJob.state``): ``queued`` -> ``running`` -> ``done``. A run that ends in a
transient failure (provider unreachable or rate limited, a crash, the execution service down) goes
back to ``queued`` with a backoff, up to ``MAX_ATTEMPTS``; after that it is ``dead`` (the
dead-letter state, kept for the owner). Content that does not pass its gates is ``failed``: retrying
the same thing would not help, it needs a revision. ``cancelled`` is a stop asked for by the owner.
``lifecycle`` maps a job and its concept to the stages the learner and owner see.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import replace
from typing import Any

from fastapi import HTTPException
from sqlalchemy import CursorResult, Engine, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from socrat.assistant.gateway import ProviderError, make_provider
from socrat.catalog import generated, shape
from socrat.catalog.registry import Catalog, CatalogError
from socrat.catalog.schema import Citation
from socrat.config import Settings
from socrat.coursegen import execute, fetch, research, roles, search, validation, youtube
from socrat.coursegen import package as pkg
from socrat.coursegen.outline import (
    ARCHITECT,
    CRITIC,
    DETAILER,
    Brief,
    architect_prompt,
    critic_prompt,
    detail_prompt,
    from_course,
    merge_details,
    needs_detail,
    skeleton_of,
    tidy,
    to_course,
)
from socrat.models import GeneratedCourse, GenerationJob, need, now
from socrat.style import spec as styles

log = logging.getLogger(__name__)

ROUNDS = 3  # architect attempts per job; the critic sees every valid one
DETAIL_CONCURRENCY = 12  # detail calls at the same time
DETAIL_CHUNK = 4  # concepts per detail call: small replies keep the slowest call short
STALE_SECONDS = 3600  # a running job this old was orphaned by a crash or restart
POLL_SECONDS = 2
MAX_ATTEMPTS = 3  # transient failures before a job is dead
BACKOFF_SECONDS = (60, 300, 900)  # wait before the next try, by attempt
# Provider errors that a later try can fix. Anything else (offline, disabled, budget, a refusal,
# a 4xx) fails at once: retrying would only spend money or time on the same answer.
TRANSIENT = {"provider_unreachable", "provider_rate_limited", "ai_rate_limited"}
OPEN = ("queued", "running")
CLOSED = ("done", "failed", "dead", "cancelled")


# Which job runs first (lower first), then oldest first. A learner looking at a spinner
# comes before lessons written ahead of time; before this, jobs ran oldest first across every
# course, so a new learner's plan waited behind other learners' background lessons.
BACKGROUND = 3
PRIORITY = {
    "outline": 0,  # someone is waiting for a plan
    "first": 1,  # the first lesson of a new course
    "owner": 1,  # the learner asked for this lesson again
    "bridge": 1,  # a bridge lesson the learner accepted
    "initial": 2,  # the rest of the first slice
    "prefetch": BACKGROUND,
    "release": 4,  # exercises and projects that follow a released lesson
}


def priority_of(kind: str, data: dict) -> int:
    if kind == "outline":
        return PRIORITY["outline"]
    if data.get("urgent"):  # the lesson the learner is standing in front of
        return PRIORITY["first"]
    return PRIORITY.get(str(data.get("trigger", "")), BACKGROUND)


def transient(error: ProviderError) -> bool:
    code = str(error)
    return code in TRANSIENT or code.startswith("provider_http_5")


def lifecycle(job: GenerationJob | None, concept_status: str | None = None) -> str:
    """The generation stage in the master prompt's terms, for one concept (or an outline):
    planned, queued, generating, validating, published, failed, blocked, cancelled, superseded."""
    if concept_status == "live":
        return "published"
    if job is None:
        return "planned"
    if job.state == "queued":
        return "queued"
    if job.state == "running":
        return "validating" if job.stage == "validating" else "generating"
    if job.state == "done":
        return "published" if concept_status is None else "superseded"
    if job.state == "dead":
        return "blocked"
    return job.state  # failed | cancelled


def spent(db: Session, course_id: str) -> float:
    return float(
        db.scalar(
            select(func.coalesce(func.sum(GenerationJob.cost_usd), 0.0)).where(
                GenerationJob.course_id == course_id
            )
        )
        or 0.0
    )


def active(db: Session, course_id: str, target: str | None = None) -> GenerationJob | None:
    """A queued or running job for the course (``target`` narrows it to one concept)."""
    query = select(GenerationJob).where(
        GenerationJob.course_id == course_id,
        GenerationJob.state.in_(OPEN),
    )
    if target is not None:
        query = query.where(GenerationJob.target == target)
    return db.scalars(query).first()


class AlreadyQueued(HTTPException):
    """The same course, kind and target already has a queued or running job."""

    def __init__(self) -> None:
        super().__init__(409, "generation_in_progress")


def enqueue(
    db: Session, kind: str, course_id: str, data: dict, user_id: str | None, target: str = ""
) -> GenerationJob:
    """Queue a job, or raise ``AlreadyQueued`` (a 409) when an open one exists. The database
    decides (migration 0045), so two requests that both passed an ``active()`` check cannot
    both queue it; the savepoint keeps the caller's transaction usable."""
    job = GenerationJob(
        kind=kind,
        course_id=course_id,
        target=target,
        input=data,
        log=[],
        created_by=user_id,
        priority=priority_of(kind, data),
    )
    try:
        with db.begin_nested():
            db.add(job)
            db.flush()
    except IntegrityError:
        raise AlreadyQueued() from None
    return job


def enqueue_once(
    db: Session, kind: str, course_id: str, data: dict, user_id: str | None, target: str = ""
) -> GenerationJob | None:
    """``enqueue`` for background callers: an open job already doing the work is enough."""
    try:
        return enqueue(db, kind, course_id, data, user_id, target)
    except AlreadyQueued:
        return None


def claim(engine: Engine) -> str | None:
    """Atomically take the oldest queued (or orphaned) job; safe with several API processes."""
    stamp = now()
    paused = select(GeneratedCourse.id).where(GeneratedCourse.paused != "")
    claimable = or_(
        (GenerationJob.state == "queued") & (GenerationJob.not_before <= stamp),
        (GenerationJob.state == "running") & (GenerationJob.updated_at < stamp - STALE_SECONDS),
    ) & GenerationJob.course_id.not_in(paused)
    with Session(engine) as db, db.begin():
        candidates = db.scalars(
            select(GenerationJob.id)
            .where(claimable)
            .order_by(GenerationJob.priority, GenerationJob.created_at)
            .limit(5)
        ).all()
        for job_id in candidates:
            # The state condition again: another process may have taken it meanwhile.
            result = db.execute(
                update(GenerationJob)
                .where(GenerationJob.id == job_id, claimable)
                .values(state="running", stage="generating", updated_at=stamp)
            )
            taken = result.rowcount if isinstance(result, CursorResult) else 0
            if taken:
                return job_id
    return None


def _note(engine: Engine, job_id: str, entry: dict, cost: float = 0.0, **fields) -> None:
    with Session(engine) as db, db.begin():
        job = need(db.get(GenerationJob, job_id))
        job.log = [*job.log, {**entry, "at": now()}]
        job.cost_usd += cost
        job.updated_at = now()
        for name, value in fields.items():
            setattr(job, name, value)


async def run_outline(
    engine: Engine, settings: Settings, base: Catalog, job_id: str, make=make_provider
) -> None:
    with Session(engine) as db:
        job = need(db.get(GenerationJob, job_id))
        brief = Brief.model_validate(job.input["brief"])
        owner = job.created_by if job.input.get("learning_request") else None
        stored = generated.course(db, brief.id)
        fresh = not job.input.get("revise") and not job.input.get("notes")
        reusable = reusable_outline(db, job_id, job.input["brief"]) if fresh else None
    if reusable is not None:
        source_id, architect = reusable
        if await _reuse(engine, base, job_id, brief, owner, source_id, architect, settings):
            return
    if brief.style is None and brief.style_request.strip():
        spec, source = await styles.interpret(engine, settings, brief.style_request, make)
        brief = brief.model_copy(update={"style": spec})
        _note(engine, job_id, {"role": "stylist", "style": spec.name, "source": source})
    if brief.session_minutes:
        brief = brief.model_copy(
            update={"style": styles.for_session(brief.style, brief.session_minutes)}
        )
    previous = (
        skeleton_of(from_course(stored)) if stored is not None and job.input.get("revise") else None
    )
    from socrat.coursegen.outline import graph_issues
    from socrat.engine import domains

    adapter = domains.ADAPTERS.get(brief.adapter)
    issues = [job.input["notes"]] if job.input.get("notes") else []
    best = None
    reviews = 0
    for attempt in range(1, ROUNDS + 1):
        with Session(engine) as db:
            if spent(db, brief.id) >= brief.budget_usd:
                _note(engine, job_id, {"role": "system", "event": "budget_reached"})
                break
        reply = await roles.ask(
            engine,
            settings,
            "architect",
            ARCHITECT,
            architect_prompt(brief, base, previous, issues),
            16000,
            make,
        )
        if reply.data is None:
            issues = [reply.problem]
            _note(
                engine,
                job_id,
                {"role": "architect", "round": attempt, "issues": issues},
                reply.cost_usd,
            )
            continue
        previous = skeleton_of(reply.data)
        outline = reply.data
        early: roles.Reply | None = (
            None  # the critic's review of the skeleton, run while the details are written
        )
        if needs_detail(outline):
            work: list[Any] = [_detail(engine, settings, brief, outline, issues, make)]
            if reviews < max(1, settings.gen_outline_reviews):
                reviews += 1
                work.append(
                    roles.ask(
                        engine,
                        settings,
                        "critic",
                        CRITIC,
                        critic_prompt(brief, previous),
                        8000,
                        make,
                    )
                )
            (missing, cost), *rest = await asyncio.gather(*work)
            early = rest[0] if rest else None
            reply.cost_usd += cost
            if missing:
                issues = [f"No details could be written for: {', '.join(missing[:20])}"]
                _note(
                    engine,
                    job_id,
                    {"role": "architect", "round": attempt, "issues": issues},
                    reply.cost_usd,
                )
                issues += _review(engine, job_id, attempt, early)[1] if early else []
                continue
        tidy(outline, base, brief.adapter)
        try:
            course = to_course(brief, outline)
            with Session(engine) as db:
                # The same check save_course runs, before spending a critic call on it.
                generated.extend(
                    base, [*(c for c in generated.courses(db) if c.id != brief.id), course]
                )
            if found_graph := graph_issues(course, adapter):
                raise ValueError("; ".join(found_graph))
        except (ValueError, CatalogError) as exc:
            issues = [f"The outline failed validation: {exc}"]
            _note(
                engine,
                job_id,
                {"role": "architect", "round": attempt, "issues": issues},
                reply.cost_usd,
            )
            issues += _review(engine, job_id, attempt, early)[1] if early else []
            continue
        best = course
        _note(
            engine,
            job_id,
            {
                "role": "architect",
                "round": attempt,
                "concepts": len(course.concepts),
                "modules": len(course.modules),
                # The prerequisite analysis the learner can inspect (master prompt 7.3).
                "assumptions": [str(a)[:300] for a in reply.data.get("assumptions", [])][:10],
                "unresolved": [str(u)[:300] for u in reply.data.get("unresolved", [])][:10],
            },
            reply.cost_usd,
        )
        if early is not None:
            review = early
        elif reviews >= max(1, settings.gen_outline_reviews):
            # The architect has answered every review it was given; keep this revision.
            _note(engine, job_id, {"role": "system", "event": "kept_after_review"})
            break
        else:
            reviews += 1
            review = await roles.ask(
                engine, settings, "critic", CRITIC, critic_prompt(brief, outline), 8000, make
            )
        verdict, found = _review(engine, job_id, attempt, review)
        if verdict == "pass":
            break
        if settings.gen_outline_reviews == 0:
            # Advisory review: the findings are in the log, the outline stands.
            _note(engine, job_id, {"role": "system", "event": "kept_after_review"})
            break
        issues = found or ["The critic asked for a revision without details; tighten the outline."]
    if best is None:
        _note(
            engine,
            job_id,
            {"role": "system", "event": "no_valid_outline"},
            state="failed",
            error="No valid outline after all rounds; see the log.",
        )
        return
    best = _with_applied(engine, settings, job_id, best, owner)
    with Session(engine) as db, db.begin():
        generated.save_course(db, base, best, status="review", brief=brief.model_dump(mode="json"))
        if owner is not None:
            need(db.get(GeneratedCourse, brief.id)).owner_id = owner
            early_first_lesson(db, settings, best)
    _note(engine, job_id, {"role": "system", "event": "outline_saved"}, state="done")


def early_first_lesson(db: Session, settings: Settings, course) -> None:
    """Start a learner's first lesson the moment their plan exists, so it is being written
    while they read the plan instead of after they press Start (``gen_early_first_lesson``).
    One lesson only: where they really begin is known after the placement check, and the
    rest of the first slice is queued at publish from there. No commit."""
    if not settings.gen_early_first_lesson:
        return
    first = next(
        (
            cid
            for m in course.modules
            for cid in m.concepts
            if course.concept(cid).status == "planned"
        ),
        None,
    )
    if first is not None:
        enqueue_once(db, "package", course.id, {"trigger": "first"}, None, first)


def _with_applied(engine: Engine, settings: Settings, job_id: str, course, owner: str | None):
    """A learner's course gains an "Apply" lesson closing each module (``gen_applied_lessons``).
    Added by code after the critic, so the critic judged the architect's plan alone."""
    if not settings.gen_applied_lessons or owner is None:
        return course
    from socrat.coursegen import applied

    widened = applied.add(course)
    added = [c.id for c in widened.concepts if c.id not in {x.id for x in course.concepts}]
    if added:
        _note(engine, job_id, {"role": "system", "event": "applied_lessons", "concepts": added})
    return widened


def _review(engine: Engine, job_id: str, attempt: int, review) -> tuple[str, list[str]]:
    """Records a critic reply in the job log; returns its verdict and issues as fix notes.
    The issues are empty for a pass."""
    verdict = (review.data or {}).get("verdict", "revise")
    found = [
        f"{i.get('where', '?')}: {i.get('problem', '')} Fix: {i.get('fix', '')}"
        for i in (review.data or {}).get("issues", [])
        if isinstance(i, dict)
    ][:30]
    _note(
        engine,
        job_id,
        {
            "role": "critic",
            "round": attempt,
            "verdict": verdict,
            "summary": str((review.data or {}).get("summary", review.problem))[:1000],
            "issues": found,
        },
        review.cost_usd,
    )
    return verdict, [] if verdict == "pass" else found


async def _detail(
    engine: Engine, settings: Settings, brief: Brief, outline: dict, issues: list[str], make
) -> tuple[list[str], float]:
    """Writes every concept's details into ``outline``, a few concepts per call and all calls in
    parallel, so the slowest call stays short; a chunk whose reply is unusable is asked once
    more. Returns the concept ids still without details and the cost of all calls."""
    gate = asyncio.Semaphore(DETAIL_CONCURRENCY)

    async def one(module_id: str, ids: list[str]) -> tuple[list[str], float]:
        cost, missing = 0.0, ids
        for _ in range(2):
            async with gate:
                reply = await roles.ask(
                    engine,
                    settings,
                    "architect",
                    DETAILER,
                    detail_prompt(brief, outline, module_id, missing, issues),
                    8000,
                    make,
                )
            cost += reply.cost_usd
            missing = merge_details(outline, missing, reply.data or {})
            if not missing:
                break
        return missing, cost

    # A malformed module is left alone here: to_course rejects it with a readable reason.
    chunks = [
        (m["id"], ids[i : i + DETAIL_CHUNK])
        for m in outline.get("modules", [])
        if isinstance(m, dict)
        and isinstance(m.get("id"), str)
        and isinstance(m.get("concepts"), list)
        and all(isinstance(c, dict) and isinstance(c.get("id"), str) for c in m["concepts"])
        for ids in [[c["id"] for c in m["concepts"]]]
        for i in range(0, len(ids), DETAIL_CHUNK)
    ]
    results = await asyncio.gather(*(one(module_id, ids) for module_id, ids in chunks))
    return [cid for missing, _ in results for cid in missing], sum(c for _, c in results)


# Fields of a brief that do not change what the architect is asked to design.
_NOT_DESIGN = {"id", "budget_usd", "concept_budget_usd"}
REUSE_SCAN = 200  # recent finished outline jobs searched for an identical brief


def design_key(brief: dict) -> str:
    """Identical briefs (ignoring id and budgets) ask for the same outline (master prompt 17:
    cache reusable non-personalised structures). The key covers every word the learner wrote,
    so reuse only ever happens between exactly equal requests and reveals nothing new."""
    kept = {k: v for k, v in brief.items() if k not in _NOT_DESIGN}
    return hashlib.sha256(json.dumps(kept, sort_keys=True).encode()).hexdigest()


def reusable_outline(db: Session, job_id: str, brief: dict):
    """(course id, architect log entry) of a recent outline for an identical brief that the
    critic passed and that is still in good standing; None when there is none."""
    key = design_key(brief)
    for job in db.scalars(
        select(GenerationJob)
        .where(
            GenerationJob.kind == "outline",
            GenerationJob.state == "done",
            GenerationJob.id != job_id,
        )
        .order_by(GenerationJob.created_at.desc())
        .limit(REUSE_SCAN)
    ):
        if design_key(job.input.get("brief") or {}) != key:
            continue
        log_ = job.log or []
        if not any(e.get("role") == "critic" and e.get("verdict") == "pass" for e in log_):
            continue
        row = db.get(GeneratedCourse, job.course_id)
        if row is None or row.moderation != "ok":
            continue
        architect: dict = next((e for e in reversed(log_) if e.get("role") == "architect"), {})
        return job.course_id, architect
    return None


async def _reuse(
    engine: Engine,
    base: Catalog,
    job_id: str,
    brief: Brief,
    owner: str | None,
    source_id: str,
    architect: dict,
    settings: Settings | None = None,
) -> bool:
    """Save the earlier outline under this brief's id without a model call. False (and
    nothing saved) when it no longer validates against today's catalog. Applied lessons are
    not part of the architect's plan: they are taken out of the source and added again only
    if this course gets them."""
    from socrat.coursegen import applied

    with Session(engine) as db:
        source = generated.course(db, source_id)
    if source is None:
        return False
    try:
        course = to_course(brief, from_course(applied.remove(source)))
        if settings is not None:
            course = _with_applied(engine, settings, job_id, course, owner)
        with Session(engine) as db, db.begin():
            generated.save_course(
                db, base, course, status="review", brief=brief.model_dump(mode="json")
            )
            if owner is not None:
                need(db.get(GeneratedCourse, brief.id)).owner_id = owner
    except (ValueError, CatalogError):
        return False
    entry = {
        "role": "architect",
        "round": 0,
        "reused_from": source_id,
        "concepts": len(course.concepts),
        "modules": len(course.modules),
        "assumptions": architect.get("assumptions", []),
        "unresolved": architect.get("unresolved", []),
    }
    _note(engine, job_id, entry)
    _note(engine, job_id, {"role": "system", "event": "outline_reused"}, state="done")
    return True


def _over_budget(engine: Engine, course_id: str, budget_usd: float) -> bool:
    with Session(engine) as db:
        return spent(db, course_id) >= budget_usd


def pause_for_budget(engine: Engine, course_id: str, job_id: str) -> None:
    """Course budget reached: pause the course and put this job back in the queue, so it
    restarts when the owner raises the budget and resumes."""
    with Session(engine) as db, db.begin():
        need(db.get(GeneratedCourse, course_id)).paused = "budget"
    _note(engine, job_id, {"role": "system", "event": "budget_reached_paused"}, state="queued")
    log.error("course generation paused: %s reached its budget", course_id)


def retry_or_bury(engine: Engine, job_id: str, event: str, error: str) -> str:
    """A transient failure: queue the job again after a backoff, or move it to ``dead`` once it
    has failed ``MAX_ATTEMPTS`` times. Returns the new state."""
    with Session(engine) as db, db.begin():
        job = need(db.get(GenerationJob, job_id))
        job.attempts += 1
        dead = job.attempts >= MAX_ATTEMPTS
        wait = BACKOFF_SECONDS[min(job.attempts, len(BACKOFF_SECONDS)) - 1]
        job.state = "dead" if dead else "queued"
        job.not_before = 0 if dead else now() + wait
        job.stage, job.error, job.updated_at = "", error[:500], now()
        entry = {"role": "system", "event": event, "attempt": job.attempts, "at": now()}
        job.log = [*job.log, entry if dead else {**entry, "retry_in": wait}]
        if dead:
            log.error(
                "generation job %s is dead after %s attempts: %s", job_id, job.attempts, error
            )
        return job.state


def _job_cost(engine: Engine, job_id: str) -> float:
    with Session(engine) as db:
        return need(db.get(GenerationJob, job_id)).cost_usd


async def run_package(
    engine: Engine,
    settings: Settings,
    base: Catalog,
    job_id: str,
    make=make_provider,
    http=None,
    executor=None,
) -> None:
    with Session(engine) as db:
        job = need(db.get(GenerationJob, job_id))
        course_id, concept_id, data = job.course_id, job.target, job.input
        brief = Brief.model_validate(need(db.get(GeneratedCourse, course_id)).brief)
        course = need(generated.course(db, course_id))
    concept = next((c for c in course.concepts if c.id == concept_id), None)
    if concept is None or concept.status != "planned":
        if data.get("trigger") == "first":
            # Queued before the learner had approved the plan; they changed it meanwhile.
            _note(engine, job_id, {"role": "system", "event": "plan_changed"}, state="cancelled")
            return
        raise ValueError(f"{course_id}:{concept_id} is not planned")
    from socrat.engine import design

    adapter = design.adapter_for(course, brief.adapter)
    bar = dict.fromkeys(pkg.DIMENSIONS, settings.gen_score_floor)
    if styles.for_session(brief.style, brief.session_minutes) is not None:
        bar[pkg.STYLE_DIMENSION] = settings.gen_score_floor
    findings: list[validation.Finding] = []

    def report(round_: int, status: str, found: list[validation.Finding]) -> None:
        with Session(engine) as db, db.begin():
            validation.record(db, course_id, concept_id, job_id, round_, status, found)

    executor = executor or execute.Broker(engine, settings)
    # Code in quiz items and atoms only when every course language can be run to check it.
    runnable = executor.available(course.languages)
    editor = "editor" in shape.effective(course).tools
    workbench = "cas" in shape.effective(course).tools
    lab = "simulation" in shape.effective(course).tools
    code = list(course.languages) if editor and runnable == list(course.languages) else []
    style = styles.for_session(brief.style, brief.session_minutes)
    ctx = pkg.context(base, course, brief.model_dump(), concept, style)
    from socrat.engine import strategy

    # The Pedagogical Strategist's plan, from the evidence library (deterministic).
    ctx = f"{ctx}\n\n{strategy.brief(strategy.plan(concept, 'unknown', adapter))}"
    # Lesson pages sized for this learner (style/pages.py), decided by code from the request.
    paging = None
    if settings.gen_lesson_pages:
        from socrat.style import pages

        paging = pages.profile(brief.learner or pages.learner_of(None, style), style)
        ctx = f"{ctx}\n\n{pages.block(paging)}"
    reference = pkg.gold(base, course) if style is None or style.shows_reference() else None
    note = pkg.STYLE_NOTE if style else ""
    cited: list[dict] = []
    version = concept.provenance.version + 1 if concept.provenance else 1
    lesson = quiz = atoms = None
    notes: dict[str, list[str]] = {"lesson": [], "quiz": [], "atoms": []}
    if data.get("previous"):
        # A quarantined concept: revise the reported version with the learners' reports.
        old = data["previous"]["concept"]
        lesson = {k: old.get(k) for k in ("lesson", "key_points", "pitfalls", "resources")}
        reported = [f"Learners reported: {r}" for r in data.get("reports", [])]
        why = f"This version was withdrawn ({data.get('reason', 'reported')})."
        notes["lesson"] = [why, *reported]
        notes["quiz"] = list(reported)
    redo = {"lesson", "quiz", "atoms"}
    models: dict[str, str] = {}
    calls: list[dict] = []  # every model call: role, model, prompt version, time, cost

    async def ask(role, system, prompt, tokens, escalate=False):
        reply = await roles.ask(
            engine, settings, role, system, prompt, tokens, make, escalate=escalate
        )
        models[role] = reply.model
        calls.append(
            {
                "role": role,
                "tier": roles.tier_of(role, escalate) or "default",
                "model": reply.model,
                "prompt": reply.prompt_version,
                "ms": reply.ms,
                "cost_usd": round(reply.cost_usd, 6),
                # The typed result envelope: parsed or not, confidence, assumptions, issues.
                "result": roles.envelope(role, reply).as_log(),
            }
        )
        return reply

    if brief.research and not data.get("previous"):
        prompt = research.prompt(ctx, brief.adapter)
        allowed = None
        if settings.research_providers:
            hits = await search.gather(
                f"{concept.title} {course.title}",
                settings.research_providers,
                http,
                broad=course.title,
                youtube_key=settings.youtube_api_key.get_secret_value(),
                keys={
                    "web": settings.web_search_api_key.get_secret_value(),
                    "openalex": settings.openalex_api_key.get_secret_value(),
                },
            )
            if hits:  # nothing found: fall back to named sources, still link-checked
                allowed = {h.url: h for h in hits}
                prompt = f"{prompt}\n\n{search.block(hits)}"
            _note(engine, job_id, {"role": "search", "hits": len(hits)})
        found = await ask("researcher", research.RESEARCHER, prompt, 2000)
        cited = await research.screen(found.data, http, allowed)
        if settings.youtube_transcripts:
            cited = research.add_videos(cited, list(allowed.values()) if allowed else [])
            cited = await youtube.with_transcripts(cited)
        if settings.research_read_pages and allowed is not None:
            cited = await fetch.with_pages(cited, http)
        _note(
            engine,
            job_id,
            {
                "role": "researcher",
                "grounded": allowed is not None,
                "sources": [
                    {k: s[k] for k in ("n", "title", "url")}
                    | ({"transcript_chars": len(s["passage"])} if s.get("transcript") else {})
                    | ({"page_chars": len(s["passage"])} if s.get("page") else {})
                    for s in cited
                ],
            },
            found.cost_usd,
        )
        if cited:
            ctx = "\n\n".join([ctx, research.block(cited)])
        if len(cited) >= 2:
            # Enough verified sources: they are the resources, and the author names no URL
            # of its own (its guesses mostly 404ed in live runs and cost whole rounds).
            ctx += "\n\nResources: list only the verified sources above, or leave it empty."

    def release(live_, pack_, summary_) -> None:
        pack_ = pkg.release_pack(pack_, models["reviewer"], summary_)
        # A code exercise only for a code course, whatever an older outline planned.
        wants = (
            concept.outline is not None
            and "code" in concept.outline.assessment
            and shape.effective(course).studio == "code"
        )
        needed = sorted({"python", *course.languages})
        exercise = wants and executor.available(needed) == needed
        with Session(engine) as db, db.begin():
            generated.store_concept(db, base, course_id, live_, pack_, job_id=job_id)
            if exercise:
                enqueue_once(db, "exercise", course_id, {"trigger": "release"}, None, concept_id)
            if project_due(db, course, concept_id):
                enqueue_once(db, "project", course_id, {"trigger": "release"}, None, concept.module)
        event = {"role": "system", "event": "released", "calls": calls}
        if wants and not exercise:
            event["exercise"] = "waiting for the execution service"
        _note(engine, job_id, event, state="done")

    polished = False  # one extra round for imprecise facts, at most
    rounds = settings.gen_package_rounds
    fallback = None  # the first package that passed, kept while that round runs
    for attempt in range(1, rounds + 1):
        if _over_budget(engine, course_id, brief.budget_usd):
            pause_for_budget(engine, course_id, job_id)
            return
        if _job_cost(engine, job_id) >= brief.concept_budget_usd:
            _note(engine, job_id, {"role": "system", "event": "concept_budget_reached"})
            break
        last = attempt == rounds and rounds > 1
        if "lesson" in redo:
            prompt = pkg.lesson_prompt(ctx, reference, lesson, notes["lesson"])
            # The first draft is the cheap model's; a lesson sent back is rewritten by the
            # reviser (a stronger model when one is set), so only failing lessons cost more.
            writer = "author" if lesson is None else "reviser"
            reply = await ask(writer, pkg.LESSON + note, prompt, 16000)
            if reply.data is None:
                notes["lesson"] = [reply.problem]
                entry = {"role": "author", "round": attempt, "issues": notes["lesson"]}
                _note(engine, job_id, entry, reply.cost_usd)
                continue
            lesson = pkg.tidy_lesson(reply.data, cited)
            if len(cited) >= 2:
                verified = {s["url"] for s in cited}
                lesson["resources"] = [
                    r
                    for r in lesson.get("resources", [])
                    if isinstance(r, dict) and r.get("url") in verified
                ]
            issues = pkg.check_lesson(concept, course, lesson, style, paging)
            issues += research.check(str(lesson.get("lesson", "")), cited)
            # A dead link is dropped, not a reason for a new round, while the live ones and the
            # researcher's sources still make the two a lesson needs.
            dead = set(await pkg.broken_links(lesson, http))
            lesson["resources"] = [
                r
                for r in lesson.get("resources", [])
                if not (isinstance(r, dict) and r.get("url") in dead)
            ]
            # Too few live links is not a defect of the lesson: the dead ones are gone, the
            # lesson keeps what was verified. (It used to cost a whole rewrite round, and the
            # author's replacement guesses mostly failed the same check.)
            entry = {
                "role": "author",
                "round": attempt,
                "characters": len(str(lesson.get("lesson", ""))),
                "issues": issues,
            }
            _note(engine, job_id, entry, reply.cost_usd, output={"lesson": lesson})
            if issues:
                status, findings = validation.assess(issues, None, None, {}, bar, adapter, [])
                report(attempt, status, findings)
                notes["lesson"] = issues
                redo |= {"lesson"}
                continue
            notes["lesson"] = []
            lesson = research.attach(lesson, cited)
        assert lesson is not None  # written above, or kept from the previous round
        pending = {}
        asked: dict[str, tuple[str, str, int]] = {}  # part -> (system, prompt, tokens)
        if "quiz" in redo or quiz is None:
            example = pkg.quiz_example(reference, settings.gen_marked_answers)
            if code:
                example += "\n\n" + pkg.QUIZ_CODE.format(languages=", ".join(code))
            if concept.outline and "explain" in concept.outline.assessment:
                example += "\n\n" + pkg.PROMPTS.format()
            if workbench:
                example += "\n\n" + pkg.EXERCISES.format()
            if lab:
                example += "\n\n" + pkg.EXPERIMENTS.format(models=pkg.models_text())
            if pkg.wants_tasks(concept, adapter):
                example += "\n\n" + pkg.TASKS.format()
            if course.sections:
                example += "\n\n" + pkg.entries_block(course)
            prompt = pkg.part_prompt(ctx, lesson, quiz, notes["quiz"], example)
            quiz_rules = pkg.QUIZ_MARKED if settings.gen_marked_answers else pkg.QUIZ
            asked["quiz"] = (quiz_rules + note, prompt, 6000)
            # A part sent back twice goes to the strong model for its last try.
            pending["quiz"] = ask("quiz", *asked["quiz"], escalate=last and quiz is not None)
        if "atoms" in redo or atoms is None:
            extra = pkg.ATOMS_CODE.format(languages=", ".join(code)) if code else ""
            prompt = pkg.part_prompt(ctx, lesson, atoms, notes["atoms"], extra)
            atom_rules = pkg.ATOMS_MARKED if settings.gen_marked_answers else pkg.ATOMS
            asked["atoms"] = (atom_rules + note, prompt, 8000)
            pending["atoms"] = ask("atoms", *asked["atoms"], escalate=last and atoms is not None)
        replies = dict(zip(pending, await asyncio.gather(*pending.values()), strict=True))
        # A quiz or atoms reply that is not readable JSON is re-asked once, at once and alone,
        # with the parse error. Before, it cost a whole round (3 by default), and the next round
        # could also rewrite the lesson; the first live run lost lessons this way.
        unreadable = [name for name, reply in replies.items() if reply.data is None]
        if unreadable:
            retried = await asyncio.gather(
                *(
                    ask(
                        name,
                        asked[name][0],
                        f"{asked[name][1]}\n\n{pkg.UNREADABLE.format(problem=replies[name].problem)}",
                        asked[name][2],
                        escalate=True,  # the usual model could not; ask the strong one once
                    )
                    for name in unreadable
                )
            )
            spent = sum(replies[name].cost_usd for name in unreadable)
            _note(
                engine,
                job_id,
                {"role": "system", "round": attempt, "event": "reasked", "parts": unreadable},
                spent,
            )
            replies.update(dict(zip(unreadable, retried, strict=True)))
        for name, reply in replies.items():
            if reply.data is None:
                notes[name] = [reply.problem]
            elif name == "quiz":
                quiz = reply.data
            else:
                atoms = reply.data
        cost = sum(r.cost_usd for r in replies.values())
        if any(r.data is None for r in replies.values()):
            redo = {n for n, r in replies.items() if r.data is None}
            issues = notes["quiz"] + notes["atoms"]
            entry = {"role": "system", "round": attempt, "event": "unparsable", "issues": issues}
            _note(engine, job_id, entry, cost)
            continue
        assert quiz is not None and atoms is not None  # both parsed by now
        entry = {"role": "system", "round": attempt, "event": "validating"}
        _note(engine, job_id, entry, stage="validating")
        from socrat.engine import safety as rules

        caution = rules.disclaimer(brief.safety)
        attribution = (
            f"Written by the {pkg.AI_AUTHOR}, then fact-checked and reviewed by AI models "
            "before release. Not reviewed by a person."
            + research.credit(cited)
            + (f" {caution}" if caution else "")
        )
        live, problems = await asyncio.to_thread(
            pkg.build_concept,
            concept,
            lesson,
            quiz,
            version,
            attribution,
            code,
            workbench,
            lab,
            course.sections,
        )
        pack, problems["atoms"] = pkg.build_atoms(course, concept, atoms, version, code)
        output = {"lesson": lesson, "quiz": quiz, "atoms": atoms}
        if live is not None and pack is not None and code:
            pack, ran = await pkg.run_code(executor, live, pack)
            problems = {**problems, **ran}
            if any(ran.values()):
                live = None
        if live is None or pack is None:
            notes = {k: problems.get(k, []) for k in notes}
            redo = {k for k, v in notes.items() if v}
            issues = [f"{k}: {x}" for k, v in notes.items() for x in v]
            entry = {"role": "system", "round": attempt, "event": "gates_failed", "issues": issues}
            _note(engine, job_id, entry, cost, output=output)
            status, findings = validation.assess(issues, None, None, {}, bar, adapter, [])
            report(attempt, status, findings)
            continue
        if settings.gen_visuals:
            live = await add_visuals(
                ask,
                live,
                course,
                str(lesson.get("lesson", "")),
                engine,
                job_id,
                attempt,
                brief.adapter,
            )
        shown = {k: lesson.get(k) for k in ("lesson", "key_points", "pitfalls")}
        # The checkers see the code's real output (adapters' expected), not the author's claim.
        bundle = json.dumps(
            {
                **shown,
                "quiz": [q.model_dump(mode="json", exclude_none=True) for q in live.quiz],
                "prompts": [x.model_dump(mode="json") for x in live.prompts],
                "exercises": [x.model_dump(mode="json") for x in live.exercises],
                "experiments": [x.model_dump(mode="json") for x in live.experiments],
                "visuals": [x.model_dump(mode="json") for x in live.visuals],
                "atoms": [a.model_dump(mode="json", exclude_none=True) for a in pack.atoms],
            },
            indent=1,
        )
        review_prompt = pkg.lesson_prompt(ctx, reference, None, [])
        facts, review = await asyncio.gather(
            ask("facts", pkg.FACTS, f"{ctx}\n\nPackage:\n{bundle}", 8000),
            ask(
                "reviewer",
                pkg.REVIEW + (pkg.STYLE_REVIEW if style else ""),
                f"{review_prompt}\n\nPackage to review:\n{bundle}",
                6000,
            ),
        )
        # One disputed quiz item or atom is dropped, not a reason to rewrite the part.
        live, pack, checked, dropped = pkg.drop_disputed(live, pack, facts.data)
        if dropped:
            entry = {"role": "system", "round": attempt, "event": "dropped", "items": dropped}
            _note(engine, job_id, entry)
            # Gone from the drafts too, so a later round cannot bring the item back.
            gone = {d.split(":", 1)[1] for d in dropped}
            for draft, key, kind in ((quiz, "quiz", "quiz"), (atoms, "atoms", "atom")):
                if any(d.startswith(f"{kind}:") for d in dropped):
                    draft[key] = [
                        x
                        for x in draft.get(key, [])
                        if not (isinstance(x, dict) and x.get("id") in gone)
                    ]
        passed, notes, scores = pkg.verdict(
            checked, review.data, style is not None, settings.gen_score_floor
        )
        status, findings = validation.assess(
            [], checked, review.data, scores, bar, adapter, brief.safety
        )
        if passed != (status in validation.RELEASED):  # the two must agree; the gate wins
            status = "needs_revision" if not passed else status
        # Which source backs which claim, by code, kept on the concept (master prompt 11.4).
        cites = research.ground(live.lesson, cited)
        if status in validation.RELEASED:
            status, findings = validation.with_grounding(status, findings, cites)
        live = live.model_copy(update={"citations": [Citation.model_validate(c) for c in cites]})
        report(attempt, status, findings)
        summary = str((review.data or {}).get("summary", review.problem))[:1000]
        entry = {
            "role": "reviewer",
            "round": attempt,
            "verdict": "pass" if passed else "revise",
            "scores": scores,
            "summary": summary,
            "issues": [f"{k}: {x}" for k, v in notes.items() for x in v][:30],
        }
        spend = cost + facts.cost_usd + review.cost_usd
        _note(engine, job_id, entry, spend, output={**output, "scores": scores})
        if passed and attempt < rounds and not polished:
            polish = pkg.imprecise_notes(facts.data)
            # Only with room to spare: a polish round must not run into the lesson's budget.
            if any(polish.values()) and _job_cost(engine, job_id) < brief.concept_budget_usd / 2:
                polished, fallback = True, (live, pack, summary, status, findings)
                notes, redo = polish, {k for k, v in polish.items() if v}
                issues = [f"{k}: {x}" for k, v in polish.items() for x in v][:30]
                entry = {"role": "system", "round": attempt, "event": "polishing", "issues": issues}
                _note(engine, job_id, entry, stage="generating")
                continue
        if passed:
            release(live, pack, summary)
            return
        # Every deterministic gate passed and the fact checker found nothing incorrect: the
        # only objection is the reviewer's rubric. Keep it, and release it if no later round
        # does better, with the reviewer's findings on its report. A lesson with a wrong fact
        # or a failed gate is never kept this way.
        sound = checked is not None and not any(
            isinstance(c, dict) and c.get("verdict") == "incorrect"
            for c in checked.get("claims", [])
        )
        # Correctness must be at the floor; the other dimensions may be weak (2), never
        # unusable (1). An unread review counts as no objection: the facts were checked.
        right = scores.get("correctness", settings.gen_score_floor) >= settings.gen_score_floor
        if sound and fallback is None and right and all(s >= 2 for s in scores.values()):
            held = [
                replace(f, severity="warning") if f.severity == "blocking" else f for f in findings
            ]
            person = validation.needs_person(adapter, brief.safety)
            kept_as = "human_review_required" if person else "pass_with_warnings"
            fallback = (live, pack, summary, kept_as, held + person)
        redo = {k for k, v in notes.items() if v} or {"lesson"}
        entry = {"role": "system", "round": attempt, "event": "revising"}
        _note(engine, job_id, entry, stage="generating")
    if fallback is not None:
        # The polish round did not pass, but the package before it did: release that one, with
        # its own report on top so the learner's label is not "being revised".
        live, pack, summary, status, findings = fallback
        report(rounds, status, findings)
        release(live, pack, summary)
        return
    report(rounds, "rejected", findings)
    _note(
        engine,
        job_id,
        {"role": "system", "event": "not_released", "calls": calls},
        state="failed",
        error="The package did not pass every gate; the concept stays planned. See the log.",
    )


async def add_visuals(
    ask, live, course, lesson_text: str, engine, job_id: str, attempt: int, chosen: str = ""
):
    """The Experience Designer step. Visuals only enrich a lesson, so a refusal, a bad reply or
    specs that fail the registry leave the lesson as written (and say so in the log)."""
    from socrat.engine import design

    if not design.allowed(course, chosen):
        return live
    try:
        reply = await ask(
            "experience", design.SYSTEM, design.prompt(course, live, lesson_text, chosen), 3000
        )
    except ProviderError:
        _note(engine, job_id, {"role": "experience", "round": attempt, "event": "unavailable"})
        return live
    kept, dropped = design.check((reply.data or {}).get("visuals", []), course, chosen)
    entry = {"role": "experience", "round": attempt, "visuals": len(kept), "dropped": dropped[:5]}
    _note(engine, job_id, entry, reply.cost_usd)
    return live.model_copy(update={"visuals": kept}) if kept else live


def project_due(db: Session, course, released: str) -> bool:
    """Releasing ``released`` completes a module that asks for a project and has none yet."""
    module = next(m for m in course.modules if m.id == course.concept(released).module)
    concepts = [course.concept(c) for c in module.concepts]
    wants = any(c.outline and "project" in c.outline.assessment for c in concepts)
    ready = all(c.status == "live" or c.id == released for c in concepts)
    if not (wants and ready) or active(db, course.id, module.id) is not None:
        return False
    covers = {f"{course.id}:{c}" for c in module.concepts}
    stored = need(db.get(GeneratedCourse, course.id)).projects or []
    return not any(set(p["concepts"]) == covers for p in stored)


async def run_once(
    engine: Engine, settings: Settings, base: Catalog, make=make_provider, http=None, executor=None
) -> bool:
    job_id = claim(engine)
    if job_id is None:
        return False
    try:
        with Session(engine) as db:
            kind = need(db.get(GenerationJob, job_id)).kind
        if kind == "package":
            await run_package(engine, settings, base, job_id, make, http, executor)
        elif kind == "exercise":
            from socrat.coursegen.exercise import run_exercise

            executor = executor or execute.Broker(engine, settings)
            await run_exercise(engine, settings, base, job_id, make, executor)
        elif kind == "project":
            from socrat.coursegen.project import run_project

            await run_project(engine, settings, base, job_id, make)
        elif kind == "outline":
            await run_outline(engine, settings, base, job_id, make)
        else:
            raise ValueError(f"unknown job kind {kind}")
    except execute.Unavailable as exc:
        retry_or_bury(
            engine,
            job_id,
            "execution_unavailable",
            f"The execution service could not run the code: {exc}",
        )
    except ProviderError as exc:
        if transient(exc):
            retry_or_bury(engine, job_id, "provider_error", f"AI provider failed: {exc}")
        else:
            _note(
                engine,
                job_id,
                {"role": "system", "event": "provider_error"},
                state="failed",
                stage="",
                error=f"AI provider refused: {exc}",
            )
    except Exception as exc:  # a failed job must never stop the loop
        log.exception("generation job %s failed", job_id)
        retry_or_bury(engine, job_id, "crashed", f"{type(exc).__name__}: {exc}")
    return True


async def run_forever(engine: Engine, settings: Settings, catalog) -> None:
    """``catalog`` is a callable returning the current file catalog."""
    while True:
        try:
            if not await run_once(engine, settings, catalog()):
                await asyncio.sleep(POLL_SECONDS)
        except Exception:
            log.exception("generation runner error")
            await asyncio.sleep(POLL_SECONDS)
