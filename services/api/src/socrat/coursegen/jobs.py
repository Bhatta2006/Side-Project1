"""Generation jobs: queued by the admin, claimed and run by a background loop.

An ``outline`` job runs the Course Architect, checks its outline against the schema and the
live catalog, asks the Curriculum Critic, and revises until the critic passes it or the
rounds run out. The best valid outline is stored for the owner's review, never published.
"""

import asyncio
import logging

from sqlalchemy import Engine, func, or_, select, update
from sqlalchemy.orm import Session

from socrat.assistant.gateway import ProviderError, make_provider
from socrat.catalog import generated
from socrat.catalog.registry import Catalog, CatalogError
from socrat.config import Settings
from socrat.coursegen import roles
from socrat.coursegen.outline import (
    ARCHITECT,
    CRITIC,
    Brief,
    architect_prompt,
    critic_prompt,
    from_course,
    to_course,
)
from socrat.models import GenerationJob, now

log = logging.getLogger(__name__)

ROUNDS = 3  # architect attempts per job; the critic sees every valid one
STALE_SECONDS = 3600  # a running job this old was orphaned by a crash or restart
POLL_SECONDS = 5


def spent(db: Session, course_id: str) -> float:
    return float(
        db.scalar(
            select(func.coalesce(func.sum(GenerationJob.cost_usd), 0.0)).where(
                GenerationJob.course_id == course_id
            )
        )
        or 0.0
    )


def active(db: Session, course_id: str) -> GenerationJob | None:
    return db.scalar(
        select(GenerationJob).where(
            GenerationJob.course_id == course_id,
            GenerationJob.state.in_(["queued", "running"]),
        )
    )


def enqueue(db: Session, kind: str, course_id: str, data: dict, user_id: str) -> GenerationJob:
    job = GenerationJob(kind=kind, course_id=course_id, input=data, log=[], created_by=user_id)
    db.add(job)
    db.flush()
    return job


def claim(engine: Engine) -> str | None:
    """Atomically take the oldest queued (or orphaned) job; safe with several API processes."""
    stamp = now()
    claimable = or_(
        GenerationJob.state == "queued",
        (GenerationJob.state == "running") & (GenerationJob.updated_at < stamp - STALE_SECONDS),
    )
    with Session(engine) as db, db.begin():
        candidates = db.scalars(
            select(GenerationJob.id).where(claimable).order_by(GenerationJob.created_at).limit(5)
        ).all()
        for job_id in candidates:
            # The state condition again: another process may have taken it meanwhile.
            taken = db.execute(
                update(GenerationJob)
                .where(GenerationJob.id == job_id, claimable)
                .values(state="running", updated_at=stamp)
            ).rowcount
            if taken:
                return job_id
    return None


def _note(engine: Engine, job_id: str, entry: dict, cost: float = 0.0, **fields) -> None:
    with Session(engine) as db, db.begin():
        job = db.get(GenerationJob, job_id)
        job.log = [*job.log, {**entry, "at": now()}]
        job.cost_usd += cost
        job.updated_at = now()
        for name, value in fields.items():
            setattr(job, name, value)


async def run_outline(
    engine: Engine, settings: Settings, base: Catalog, job_id: str, make=make_provider
) -> None:
    with Session(engine) as db:
        job = db.get(GenerationJob, job_id)
        brief = Brief.model_validate(job.input["brief"])
        stored = generated.course(db, brief.id)
    previous = from_course(stored) if stored is not None and job.input.get("revise") else None
    issues = [job.input["notes"]] if job.input.get("notes") else []
    best = None
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
            32000,
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
        previous = reply.data
        try:
            course = to_course(brief, reply.data)
            with Session(engine) as db:
                # The same check save_course runs, before spending a critic call on it.
                generated.extend(
                    base, [*(c for c in generated.courses(db) if c.id != brief.id), course]
                )
        except (ValueError, CatalogError) as exc:
            issues = [f"The outline failed validation: {exc}"]
            _note(
                engine,
                job_id,
                {"role": "architect", "round": attempt, "issues": issues},
                reply.cost_usd,
            )
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
            },
            reply.cost_usd,
        )
        review = await roles.ask(
            engine, settings, "critic", CRITIC, critic_prompt(brief, reply.data), 8000, make
        )
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
        if verdict == "pass":
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
    with Session(engine) as db, db.begin():
        generated.save_course(db, base, best, status="review", brief=brief.model_dump(mode="json"))
    _note(engine, job_id, {"role": "system", "event": "outline_saved"}, state="done")


async def run_once(engine: Engine, settings: Settings, base: Catalog, make=make_provider) -> bool:
    job_id = claim(engine)
    if job_id is None:
        return False
    try:
        with Session(engine) as db:
            kind = db.get(GenerationJob, job_id).kind
        if kind != "outline":
            raise ValueError(f"unknown job kind {kind}")
        await run_outline(engine, settings, base, job_id, make)
    except ProviderError as exc:
        _note(
            engine,
            job_id,
            {"role": "system", "event": "provider_error"},
            state="failed",
            error=f"AI provider refused: {exc}",
        )
    except Exception as exc:  # a failed job must never stop the loop
        log.exception("generation job %s failed", job_id)
        _note(
            engine,
            job_id,
            {"role": "system", "event": "crashed"},
            state="failed",
            error=f"{type(exc).__name__}: {exc}"[:500],
        )
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
