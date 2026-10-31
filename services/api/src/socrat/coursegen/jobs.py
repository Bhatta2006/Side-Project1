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
"""

import asyncio
import json
import logging

from sqlalchemy import Engine, func, or_, select, update
from sqlalchemy.orm import Session

from socrat.assistant.gateway import ProviderError, make_provider
from socrat.catalog import generated, shape
from socrat.catalog.registry import Catalog, CatalogError
from socrat.config import Settings
from socrat.coursegen import execute, research, roles
from socrat.coursegen import package as pkg
from socrat.coursegen.outline import (
    ARCHITECT,
    CRITIC,
    Brief,
    architect_prompt,
    critic_prompt,
    from_course,
    to_course,
)
from socrat.models import GeneratedCourse, GenerationJob, now
from socrat.style import spec as styles

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


def active(db: Session, course_id: str, target: str | None = None) -> GenerationJob | None:
    """A queued or running job for the course (``target`` narrows it to one concept)."""
    query = select(GenerationJob).where(
        GenerationJob.course_id == course_id,
        GenerationJob.state.in_(["queued", "running"]),
    )
    if target is not None:
        query = query.where(GenerationJob.target == target)
    return db.scalars(query).first()


def enqueue(
    db: Session, kind: str, course_id: str, data: dict, user_id: str | None, target: str = ""
) -> GenerationJob:
    job = GenerationJob(
        kind=kind, course_id=course_id, target=target, input=data, log=[], created_by=user_id
    )
    db.add(job)
    db.flush()
    return job


def claim(engine: Engine) -> str | None:
    """Atomically take the oldest queued (or orphaned) job; safe with several API processes."""
    stamp = now()
    paused = select(GeneratedCourse.id).where(GeneratedCourse.paused != "")
    claimable = or_(
        GenerationJob.state == "queued",
        (GenerationJob.state == "running") & (GenerationJob.updated_at < stamp - STALE_SECONDS),
    ) & GenerationJob.course_id.not_in(paused)
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
    if brief.style is None and brief.style_request.strip():
        spec, source = await styles.interpret(engine, settings, brief.style_request, make)
        brief = brief.model_copy(update={"style": spec})
        _note(engine, job_id, {"role": "stylist", "style": spec.name, "source": source})
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


def _over_budget(engine: Engine, course_id: str, budget_usd: float) -> bool:
    with Session(engine) as db:
        return spent(db, course_id) >= budget_usd


def pause_for_budget(engine: Engine, course_id: str, job_id: str) -> None:
    """Course budget reached: pause the course and put this job back in the queue, so it
    restarts when the owner raises the budget and resumes."""
    with Session(engine) as db, db.begin():
        db.get(GeneratedCourse, course_id).paused = "budget"
    _note(engine, job_id, {"role": "system", "event": "budget_reached_paused"}, state="queued")
    log.error("course generation paused: %s reached its budget", course_id)


def _job_cost(engine: Engine, job_id: str) -> float:
    with Session(engine) as db:
        return db.get(GenerationJob, job_id).cost_usd


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
        job = db.get(GenerationJob, job_id)
        course_id, concept_id, data = job.course_id, job.target, job.input
        brief = Brief.model_validate(db.get(GeneratedCourse, course_id).brief)
        course = generated.course(db, course_id)
    concept = course.concept(concept_id)
    if concept.status != "planned":
        raise ValueError(f"{course_id}:{concept_id} is not planned")
    executor = executor or execute.Broker(engine, settings)
    # Code in quiz items and atoms only when every course language can be run to check it.
    runnable = executor.available(course.languages)
    editor = "editor" in shape.effective(course).tools
    workbench = "cas" in shape.effective(course).tools
    lab = "simulation" in shape.effective(course).tools
    code = list(course.languages) if editor and runnable == list(course.languages) else []
    style = brief.style
    ctx = pkg.context(base, course, brief.model_dump(), concept, style)
    reference = pkg.gold(base) if style is None or style.shows_reference() else None
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

    async def ask(role, system, prompt, tokens):
        reply = await roles.ask(engine, settings, role, system, prompt, tokens, make)
        models[role] = reply.model
        return reply

    if brief.research and not data.get("previous"):
        found = await ask("researcher", research.RESEARCHER, research.prompt(ctx), 2000)
        cited = await research.screen(found.data, http)
        _note(
            engine,
            job_id,
            {
                "role": "researcher",
                "sources": [{k: s[k] for k in ("n", "title", "url")} for s in cited],
            },
            found.cost_usd,
        )
        if cited:
            ctx = "\n\n".join([ctx, research.block(cited)])

    for attempt in range(1, ROUNDS + 1):
        if _over_budget(engine, course_id, brief.budget_usd):
            pause_for_budget(engine, course_id, job_id)
            return
        if _job_cost(engine, job_id) >= brief.concept_budget_usd:
            _note(engine, job_id, {"role": "system", "event": "concept_budget_reached"})
            break
        if "lesson" in redo:
            prompt = pkg.lesson_prompt(ctx, reference, lesson, notes["lesson"])
            reply = await ask("author", pkg.LESSON + note, prompt, 16000)
            if reply.data is None:
                notes["lesson"] = [reply.problem]
                entry = {"role": "author", "round": attempt, "issues": notes["lesson"]}
                _note(engine, job_id, entry, reply.cost_usd)
                continue
            lesson = reply.data
            problems = pkg.check_lesson(concept, course, lesson, style)
            problems += research.check(str(lesson.get("lesson", "")), cited)
            problems += [
                f"This resource link is unreachable or not public https; replace it: {url}"
                for url in await pkg.broken_links(lesson, http)
            ]
            entry = {
                "role": "author",
                "round": attempt,
                "characters": len(str(lesson.get("lesson", ""))),
                "issues": problems,
            }
            _note(engine, job_id, entry, reply.cost_usd, output={"lesson": lesson})
            if problems:
                notes["lesson"] = problems
                redo |= {"lesson"}
                continue
            notes["lesson"] = []
            lesson = research.attach(lesson, cited)
        pending = {}
        if "quiz" in redo or quiz is None:
            example = pkg.quiz_example(reference)
            if code:
                example += "\n\n" + pkg.QUIZ_CODE.format(languages=", ".join(code))
            if concept.outline and "explain" in concept.outline.assessment:
                example += "\n\n" + pkg.PROMPTS.format()
            if workbench:
                example += "\n\n" + pkg.EXERCISES.format()
            if lab:
                example += "\n\n" + pkg.EXPERIMENTS.format(models=pkg.models_text())
            prompt = pkg.part_prompt(ctx, lesson, quiz, notes["quiz"], example)
            pending["quiz"] = ask("quiz", pkg.QUIZ + note, prompt, 6000)
        if "atoms" in redo or atoms is None:
            extra = pkg.ATOMS_CODE.format(languages=", ".join(code)) if code else ""
            prompt = pkg.part_prompt(ctx, lesson, atoms, notes["atoms"], extra)
            pending["atoms"] = ask("atoms", pkg.ATOMS + note, prompt, 8000)
        replies = dict(zip(pending, await asyncio.gather(*pending.values()), strict=True))
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
        attribution = (
            f"Written by the {pkg.AI_AUTHOR}, then fact-checked and reviewed by AI models "
            "before release. Not reviewed by a person." + research.credit(cited)
        )
        live, problems = await asyncio.to_thread(
            pkg.build_concept, concept, lesson, quiz, version, attribution, code, workbench, lab
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
            continue
        shown = {k: lesson.get(k) for k in ("lesson", "key_points", "pitfalls")}
        # The checkers see the code's real output (adapters' expected), not the author's claim.
        bundle = json.dumps(
            {
                **shown,
                "quiz": [q.model_dump(mode="json", exclude_none=True) for q in live.quiz],
                "prompts": [x.model_dump(mode="json") for x in live.prompts],
                "exercises": [x.model_dump(mode="json") for x in live.exercises],
                "experiments": [x.model_dump(mode="json") for x in live.experiments],
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
        passed, notes, scores = pkg.verdict(facts.data, review.data, style is not None)
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
        if passed:
            pack = pkg.release_pack(pack, models["reviewer"], summary)
            wants = concept.outline is not None and "code" in concept.outline.assessment
            needed = sorted({"python", *course.languages})
            exercise = wants and executor.available(needed) == needed
            with Session(engine) as db, db.begin():
                generated.store_concept(db, base, course_id, live, pack)
                if exercise:
                    enqueue(db, "exercise", course_id, {"trigger": "release"}, None, concept_id)
                if project_due(db, course, concept_id):
                    enqueue(db, "project", course_id, {"trigger": "release"}, None, concept.module)
            event = {"role": "system", "event": "released"}
            if wants and not exercise:
                event["exercise"] = "waiting for the execution service"
            _note(engine, job_id, event, state="done")
            return
        redo = {k for k, v in notes.items() if v} or {"lesson"}
    _note(
        engine,
        job_id,
        {"role": "system", "event": "not_released"},
        state="failed",
        error="The package did not pass every gate; the concept stays planned. See the log.",
    )


def project_due(db: Session, course, released: str) -> bool:
    """Releasing ``released`` completes a module that asks for a project and has none yet."""
    module = next(m for m in course.modules if m.id == course.concept(released).module)
    concepts = [course.concept(c) for c in module.concepts]
    wants = any(c.outline and "project" in c.outline.assessment for c in concepts)
    ready = all(c.status == "live" or c.id == released for c in concepts)
    if not (wants and ready) or active(db, course.id, module.id) is not None:
        return False
    covers = {f"{course.id}:{c}" for c in module.concepts}
    stored = db.get(GeneratedCourse, course.id).projects or []
    return not any(set(p["concepts"]) == covers for p in stored)


async def run_once(
    engine: Engine, settings: Settings, base: Catalog, make=make_provider, http=None, executor=None
) -> bool:
    job_id = claim(engine)
    if job_id is None:
        return False
    try:
        with Session(engine) as db:
            kind = db.get(GenerationJob, job_id).kind
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
        _note(
            engine,
            job_id,
            {"role": "system", "event": "execution_unavailable"},
            state="failed",
            error=f"The execution service could not run the code: {exc}",
        )
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
