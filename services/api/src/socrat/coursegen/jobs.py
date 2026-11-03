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

from sqlalchemy import CursorResult, Engine, func, or_, select, update
from sqlalchemy.orm import Session

from socrat.assistant.gateway import ProviderError, make_provider
from socrat.catalog import generated, shape
from socrat.catalog.registry import Catalog, CatalogError
from socrat.catalog.schema import Citation
from socrat.config import Settings
from socrat.coursegen import execute, research, roles, search, validation
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
from socrat.models import GeneratedCourse, GenerationJob, need, now
from socrat.style import spec as styles

log = logging.getLogger(__name__)

ROUNDS = 3  # architect attempts per job; the critic sees every valid one
STALE_SECONDS = 3600  # a running job this old was orphaned by a crash or restart
POLL_SECONDS = 5
MAX_ATTEMPTS = 3  # transient failures before a job is dead
BACKOFF_SECONDS = (60, 300, 900)  # wait before the next try, by attempt
# Provider errors that a later try can fix. Anything else (offline, disabled, budget, a refusal,
# a 4xx) fails at once: retrying would only spend money or time on the same answer.
TRANSIENT = {"provider_unreachable", "provider_rate_limited", "ai_rate_limited"}
OPEN = ("queued", "running")
CLOSED = ("done", "failed", "dead", "cancelled")


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
        (GenerationJob.state == "queued") & (GenerationJob.not_before <= stamp),
        (GenerationJob.state == "running") & (GenerationJob.updated_at < stamp - STALE_SECONDS),
    ) & GenerationJob.course_id.not_in(paused)
    with Session(engine) as db, db.begin():
        candidates = db.scalars(
            select(GenerationJob.id).where(claimable).order_by(GenerationJob.created_at).limit(5)
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
    if reusable is not None and await _reuse(engine, base, job_id, brief, owner, *reusable):
        return
    if brief.style is None and brief.style_request.strip():
        spec, source = await styles.interpret(engine, settings, brief.style_request, make)
        brief = brief.model_copy(update={"style": spec})
        _note(engine, job_id, {"role": "stylist", "style": spec.name, "source": source})
    previous = from_course(stored) if stored is not None and job.input.get("revise") else None
    from socrat.coursegen.outline import graph_issues
    from socrat.engine import domains

    adapter = domains.ADAPTERS.get(brief.adapter)
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
        if owner is not None:
            need(db.get(GeneratedCourse, brief.id)).owner_id = owner
    _note(engine, job_id, {"role": "system", "event": "outline_saved"}, state="done")


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
) -> bool:
    """Save the earlier outline under this brief's id without a model call. False (and
    nothing saved) when it no longer validates against today's catalog."""

    with Session(engine) as db:
        source = generated.course(db, source_id)
    if source is None:
        return False
    try:
        course = to_course(brief, from_course(source))
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
    concept = course.concept(concept_id)
    if concept.status != "planned":
        raise ValueError(f"{course_id}:{concept_id} is not planned")
    from socrat.engine import design

    adapter = design.adapter_for(course, brief.adapter)
    bar = {d: (5 if d == "correctness" else 4) for d in pkg.DIMENSIONS}
    if brief.style is not None:
        bar[pkg.STYLE_DIMENSION] = 4
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
    style = brief.style
    ctx = pkg.context(base, course, brief.model_dump(), concept, style)
    from socrat.engine import strategy

    # The Pedagogical Strategist's plan, from the evidence library (deterministic).
    ctx = f"{ctx}\n\n{strategy.brief(strategy.plan(concept, 'unknown', adapter))}"
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
    calls: list[dict] = []  # every model call: role, model, prompt version, time, cost

    async def ask(role, system, prompt, tokens):
        reply = await roles.ask(engine, settings, role, system, prompt, tokens, make)
        models[role] = reply.model
        calls.append(
            {
                "role": role,
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
        prompt = research.prompt(ctx)
        allowed = None
        if settings.research_providers:
            hits = await search.gather(
                f"{concept.title} {course.title}", settings.research_providers, http
            )
            if hits:  # nothing found: fall back to named sources, still link-checked
                allowed = {h.url: h for h in hits}
                prompt = f"{prompt}\n\n{search.block(hits)}"
            _note(engine, job_id, {"role": "search", "hits": len(hits)})
        found = await ask("researcher", research.RESEARCHER, prompt, 2000)
        cited = await research.screen(found.data, http, allowed)
        _note(
            engine,
            job_id,
            {
                "role": "researcher",
                "grounded": allowed is not None,
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
            issues = pkg.check_lesson(concept, course, lesson, style)
            issues += research.check(str(lesson.get("lesson", "")), cited)
            issues += [
                f"This resource link is unreachable or not public https; replace it: {url}"
                for url in await pkg.broken_links(lesson, http)
            ]
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
            if pkg.wants_tasks(concept, adapter):
                example += "\n\n" + pkg.TASKS.format()
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
        passed, notes, scores = pkg.verdict(facts.data, review.data, style is not None)
        status, findings = validation.assess(
            [], facts.data, review.data, scores, bar, adapter, brief.safety
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
        if passed:
            pack = pkg.release_pack(pack, models["reviewer"], summary)
            wants = concept.outline is not None and "code" in concept.outline.assessment
            needed = sorted({"python", *course.languages})
            exercise = wants and executor.available(needed) == needed
            with Session(engine) as db, db.begin():
                generated.store_concept(db, base, course_id, live, pack, job_id=job_id)
                if exercise:
                    enqueue(db, "exercise", course_id, {"trigger": "release"}, None, concept_id)
                if project_due(db, course, concept_id):
                    enqueue(db, "project", course_id, {"trigger": "release"}, None, concept.module)
            event = {"role": "system", "event": "released", "calls": calls}
            if wants and not exercise:
                event["exercise"] = "waiting for the execution service"
            _note(engine, job_id, event, state="done")
            return
        redo = {k for k, v in notes.items() if v} or {"lesson"}
        entry = {"role": "system", "round": attempt, "event": "revising"}
        _note(engine, job_id, entry, stage="generating")
    report(ROUNDS, "rejected", findings)
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
