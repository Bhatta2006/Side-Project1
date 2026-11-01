"""Project Designer: one project per module, when the module's concepts are all released.

A project ties the module together in work the learner builds or writes: 2-5 milestones,
each with a checklist, and a rubric (weights total 100) that the grader applies to every
milestone. A reviewer checks scope and gradability before it is released.
"""

import json

from pydantic import ValidationError
from sqlalchemy.orm import Session

from socrat.catalog import generated
from socrat.catalog.projects import Project
from socrat.catalog.registry import Catalog
from socrat.catalog.schema import Course, Provenance
from socrat.coursegen import package as pkg
from socrat.coursegen import roles
from socrat.models import GeneratedCourse, GenerationJob, need

DIMENSIONS = ("alignment", "scope", "gradable", "clarity")

DESIGNER = """You are the Project Designer for Socrat. Design one project that makes the
learner integrate this module's concepts in realistic work: something they build, analyse
or write, not a quiz. It must be doable with what the module taught, in the stated time.

- 2-5 milestones in order; each has a title and a checklist of 2-6 concrete things the
  submission must contain (the learner ticks them; the grader checks them).
- A rubric of 3-6 criteria whose weights total 100; full_marks says exactly what a top
  submission shows, so a grader can apply it to any one milestone's work.
- Work is submitted as text (explanations, results, code pasted in) and optionally a public
  https link; nothing needs installing beyond the course languages.

Reply with one JSON object only:
{"id": "kebab-case", "title": "...", "summary": "what and why, 2-4 sentences",
 "skills": ["..."], "constraints": ["..."],
 "milestones": [{"id": "kebab-case", "title": "...", "checklist": ["..."]}],
 "rubric": [{"criterion": "...", "weight": 25, "full_marks": "..."}],
 "self_review": ["questions the learner asks themselves before submitting"]}"""

REVIEW = """You are the Reviewer for Socrat's projects. Judge the project against the
module it closes. Score 1-5 each: alignment (needs this module's concepts), scope (doable
in the time with what was taught), gradable (checklists and rubric are specific enough to
grade consistently), clarity.

Reply with one JSON object only:
{"scores": {"alignment": 1, "scope": 1, "gradable": 1, "clarity": 1},
 "summary": "2-3 sentences", "fixes": ["specific fixes"]}"""


def context(course: Course, module_id: str, brief: dict) -> str:
    module = next(m for m in course.modules if m.id == module_id)
    concepts = [c for c in course.concepts if c.id in module.concepts]
    return "\n\n".join(
        [
            f"Course: {course.title} — {course.description}",
            f"Learners: {brief['audience']}\nCourse languages: {', '.join(course.languages)}",
            f"Module: {module.title} — {module.summary}",
            "Concepts it taught:\n"
            + "\n".join(
                f"- {c.title}: {c.summary} Key points: {'; '.join(c.key_points)}" for c in concepts
            ),
            f"Time for the project: about {max(60, sum(c.estimated_minutes for c in concepts) // 2)} minutes.",
        ]
    )


def build(course: Course, module_id: str, raw: dict, version: int):
    """The project, or (None, problems)."""
    module = next(m for m in course.modules if m.id == module_id)
    try:
        project = Project.model_validate(
            {
                **{k: v for k, v in raw.items() if k not in {"course", "concepts", "status"}},
                "course": course.id,
                "concepts": [f"{course.id}:{c}" for c in module.concepts],
                "status": "provisional",
                "starter_repo": None,
                "provenance": Provenance(
                    author=pkg.AI_AUTHOR,
                    version=version,
                    attribution_md=f"Designed by the {pkg.AI_AUTHOR} and reviewed by an AI "
                    "model. Not reviewed by a person.",
                ).model_dump(mode="json"),
            }
        )
    except (ValidationError, TypeError) as exc:
        detail = pkg.errors_of(exc) if isinstance(exc, ValidationError) else [str(exc)]
        return None, detail
    problems = []
    if len(project.milestones) < 2:
        problems.append("Give at least 2 milestones.")
    if len(project.rubric) < 3:
        problems.append("Give at least 3 rubric criteria.")
    if any(len(m.checklist) < 2 for m in project.milestones):
        problems.append("Every milestone needs at least 2 checklist items.")
    return (None, problems) if problems else (project, [])


def passed(review: dict | None) -> tuple[bool, dict, list[str]]:
    scores = {}
    for dim in DIMENSIONS:
        try:
            scores[dim] = int((review or {}).get("scores", {}).get(dim, 0))
        except (TypeError, ValueError):
            scores[dim] = 0
    fixes = [str(f) for f in (review or {}).get("fixes", []) if f][:10]
    return all(scores[d] >= 4 for d in DIMENSIONS), scores, fixes


async def run_project(engine, settings, base: Catalog, job_id: str, make) -> None:
    from socrat.coursegen import jobs
    from socrat.coursegen.outline import Brief

    with Session(engine) as db:
        job = need(db.get(GenerationJob, job_id))
        course_id, module_id = job.course_id, job.target
        row = need(db.get(GeneratedCourse, course_id))
        brief = Brief.model_validate(row.brief)
        course = need(generated.course(db, course_id))
        stored = row.projects or []
    module = next(m for m in course.modules if m.id == module_id)
    if any(course.concept(c).status != "live" for c in module.concepts):
        raise ValueError(f"module {module_id} has concepts that are not live yet")
    ctx = context(course, module_id, brief.model_dump())
    covers = {f"{course_id}:{c}" for c in module.concepts}
    version = 1 + sum(set(p["concepts"]) == covers for p in stored)
    draft, notes = None, list[str]()
    for attempt in range(1, jobs.ROUNDS + 1):
        if jobs._over_budget(engine, course_id, brief.budget_usd):
            jobs.pause_for_budget(engine, course_id, job_id)
            return
        if jobs._job_cost(engine, job_id) >= brief.concept_budget_usd:
            jobs._note(engine, job_id, {"role": "system", "event": "concept_budget_reached"})
            break
        parts = [ctx]
        if draft is not None:
            parts.append("Your previous draft:\n" + json.dumps(draft, indent=1))
        if notes:
            parts.append("Fix all of these in a complete revised reply:\n- " + "\n- ".join(notes))
        reply = await roles.ask(
            engine, settings, "designer", DESIGNER, "\n\n".join(parts), 8000, make
        )
        if reply.data is None:
            notes = [reply.problem]
            entry = {"role": "designer", "round": attempt, "issues": notes}
            jobs._note(engine, job_id, entry, reply.cost_usd)
            continue
        draft = reply.data
        project, notes = build(course, module_id, draft, version)
        entry = {"role": "designer", "round": attempt, "issues": notes}
        jobs._note(engine, job_id, entry, reply.cost_usd, output={"project": draft})
        if project is None:
            continue
        shown = json.dumps(project.model_dump(mode="json", exclude={"provenance"}), indent=1)
        review = await roles.ask(
            engine, settings, "reviewer", REVIEW, f"{ctx}\n\nProject:\n{shown}", 4000, make
        )
        ok, scores, notes = passed(review.data)
        entry = {
            "role": "reviewer",
            "round": attempt,
            "verdict": "pass" if ok else "revise",
            "scores": scores,
            "summary": str((review.data or {}).get("summary", review.problem))[:1000],
            "issues": notes,
        }
        jobs._note(engine, job_id, entry, review.cost_usd)
        if not ok:
            notes = notes or ["The reviewer asked for a revision; tighten scope and rubric."]
            continue
        with Session(engine) as db, db.begin():
            generated.store_project(db, base, project)
        entry = {"role": "system", "event": "released", "project": project.id}
        jobs._note(engine, job_id, entry, state="done")
        return
    jobs._note(
        engine,
        job_id,
        {"role": "system", "event": "not_released"},
        state="failed",
        error="The project did not pass review; see the log.",
    )
