"""Admin API for generated courses: write a brief, follow the agents, review, edit, publish."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.admin.routes import require_admin
from socrat.catalog import generated
from socrat.catalog.registry import CatalogError, default_catalog
from socrat.catalog.schema import Course, Slug
from socrat.coursegen import jobs, quality
from socrat.coursegen.outline import Brief
from socrat.database import record_event
from socrat.learn.routes import catalog, engine
from socrat.models import GeneratedConcept, GeneratedCourse, GenerationJob

router = APIRouter(prefix="/api/v1/admin/courses")


class Notes(BaseModel):
    notes: str = Field(min_length=3, max_length=4000)


class OutlineEdit(BaseModel):
    course: dict


class Budget(BaseModel):
    budget_usd: float = Field(gt=0, le=1000)
    concept_budget_usd: float = Field(gt=0, le=100)


class Generate(BaseModel):
    concepts: list[Slug] = Field(min_length=1, max_length=20)


def job_view(job: GenerationJob) -> dict:
    return dict(
        id=job.id,
        kind=job.kind,
        state=job.state,
        log=job.log,
        cost_usd=round(job.cost_usd, 4),
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("")
def list_courses(request: Request):
    with Session(engine(request)) as db:
        require_admin(request, db)
        rows = {r.id: r for r in db.scalars(select(GeneratedCourse))}
        live: dict[str, int] = {}
        for concept in db.scalars(select(GeneratedConcept)):
            live[concept.course_id] = live.get(concept.course_id, 0) + (
                concept.payload.get("status") == "live"
            )
        latest: dict[str, GenerationJob] = {}
        for job in db.scalars(select(GenerationJob).order_by(GenerationJob.created_at)):
            latest[job.course_id] = job
        items = []
        for course_id in sorted(set(rows) | set(latest)):
            row, job = rows.get(course_id), latest.get(course_id)
            brief = (row.brief if row else None) or job.input["brief"]
            items.append(
                dict(
                    id=course_id,
                    title=brief["title"],
                    status=row.status if row else "drafting",
                    paused=row.paused if row else "",
                    concepts=None
                    if row is None
                    else sum(len(m["concepts"]) for m in row.payload["modules"]),
                    live=live.get(course_id, 0),
                    job=job_view(job) if job else None,
                    spent_usd=round(jobs.spent(db, course_id), 4),
                    budget_usd=brief["budget_usd"],
                )
            )
        return {"items": items}


@router.post("/briefs")
def create_brief(brief: Brief, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        if brief.id in cat.courses or db.get(GeneratedCourse, brief.id) is not None:
            raise HTTPException(409, "course_exists")
        if jobs.active(db, brief.id) is not None:
            raise HTTPException(409, "generation_in_progress")
        unknown = [r for r in brief.reuse if r not in cat.concepts]
        if unknown:
            raise HTTPException(422, "unknown_reuse_concept")
        job = jobs.enqueue(
            db, "outline", brief.id, {"brief": brief.model_dump(mode="json")}, user.id
        )
        record_event(db, user.id, "coursegen.brief_created", brief.id)
        return job_view(job)


def _course_row(db: Session, course_id: str) -> GeneratedCourse:
    row = db.get(GeneratedCourse, course_id)
    if row is None:
        raise HTTPException(404, "not_found")
    return row


@router.get("/{course_id}")
def course_detail(course_id: str, request: Request):
    with Session(engine(request)) as db:
        require_admin(request, db)
        row = db.get(GeneratedCourse, course_id)
        history = list(
            db.scalars(
                select(GenerationJob)
                .where(GenerationJob.course_id == course_id)
                .order_by(GenerationJob.created_at.desc())
            )
        )
        if row is None and not history:
            raise HTTPException(404, "not_found")
        stored = generated.course(db, course_id) if row else None
        packages: dict[str, dict] = {}
        exercises: dict[str, dict] = {}
        for job in reversed(history):  # oldest first, so the newest per concept wins
            if job.kind == "package":
                packages[job.target] = job_view(job)
            elif job.kind == "exercise":
                exercises[job.target] = job_view(job)
        return dict(
            packages=packages,
            exercises=exercises,
            id=course_id,
            status=row.status if row else "drafting",
            paused=row.paused if row else "",
            brief=(row.brief if row else None) or history[0].input["brief"],
            course=stored.model_dump(mode="json") if stored else None,
            jobs=[job_view(j) for j in history],
            spent_usd=round(jobs.spent(db, course_id), 4),
        )


@router.put("/{course_id}/outline")
def edit_outline(course_id: str, body: OutlineEdit, request: Request):
    """Replace the outline under review. Returns the validation errors instead of saving."""
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        row = _course_row(db, course_id)
        if row.status != "review":
            raise HTTPException(409, "outline_published")
        try:
            course = Course.model_validate({**body.course, "id": course_id})
            if any(c.status != "planned" for c in course.concepts):
                raise ValueError("an outline holds planned concepts only")
            generated.save_course(db, default_catalog(), course, status="review")
        except ValidationError as exc:
            errors = [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()[:20]]
            return {"saved": False, "errors": errors}
        except (ValueError, CatalogError) as exc:
            return {"saved": False, "errors": [str(exc)]}
        record_event(db, user.id, "coursegen.outline_edited", course_id)
        return {"saved": True, "errors": []}


@router.post("/{course_id}/revise")
def revise_outline(course_id: str, body: Notes, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        row = _course_row(db, course_id)
        if row.status != "review":
            raise HTTPException(409, "outline_published")
        if jobs.active(db, course_id) is not None:
            raise HTTPException(409, "generation_in_progress")
        data = {"brief": row.brief, "revise": True, "notes": f"Owner's notes: {body.notes}"}
        job = jobs.enqueue(db, "outline", course_id, data, user.id)
        record_event(db, user.id, "coursegen.revision_requested", course_id)
        return job_view(job)


@router.post("/{course_id}/publish")
def publish(course_id: str, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        row = _course_row(db, course_id)
        if row.status != "review":
            raise HTTPException(409, "outline_published")
        if jobs.active(db, course_id) is not None:
            raise HTTPException(409, "generation_in_progress")
        try:
            generated.publish(db, default_catalog(), course_id)
        except (ValueError, CatalogError) as exc:
            raise HTTPException(422, "outline_invalid") from exc
        record_event(db, user.id, "coursegen.published", course_id)
        return {"published": True}


@router.post("/{course_id}/concepts/generate")
def generate_packages(course_id: str, body: Generate, request: Request):
    """Queue lesson, quiz and atoms for planned concepts of a published course."""
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        row = _course_row(db, course_id)
        if row.status != "published":
            raise HTTPException(409, "publish_outline_first")
        stored = generated.course(db, course_id)
        status = {c.id: c.status for c in stored.concepts}
        if any(status.get(cid) != "planned" for cid in body.concepts):
            raise HTTPException(422, "concept_not_planned")
        queued = []
        for cid in dict.fromkeys(body.concepts):
            if jobs.active(db, course_id, cid) is None:
                job = jobs.enqueue(db, "package", course_id, {}, user.id, target=cid)
                queued.append(job_view(job))
        record_event(db, user.id, "coursegen.packages_requested", course_id)
        return {"queued": queued}


@router.post("/{course_id}/concepts/{concept_id}/exercise")
def generate_exercise(course_id: str, concept_id: str, request: Request):
    """Queue one more judged problem for a live concept; its code runs in the execution plane."""
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        row = db.get(GeneratedConcept, (course_id, concept_id))
        if row is None or row.payload.get("status") != "live":
            raise HTTPException(409, "concept_not_live")
        if jobs.active(db, course_id, concept_id) is not None:
            raise HTTPException(409, "generation_in_progress")
        job = jobs.enqueue(db, "exercise", course_id, {"trigger": "owner"}, user.id, concept_id)
        record_event(db, user.id, "coursegen.exercise_requested", course_id)
        return job_view(job)


@router.get("/{course_id}/concepts/{concept_id}")
def package_detail(course_id: str, concept_id: str, request: Request):
    """One concept as stored, with every package run and its last draft (for audit)."""
    with Session(engine(request)) as db:
        require_admin(request, db)
        row = db.get(GeneratedConcept, (course_id, concept_id))
        if row is None:
            raise HTTPException(404, "not_found")
        runs = db.scalars(
            select(GenerationJob)
            .where(GenerationJob.course_id == course_id, GenerationJob.target == concept_id)
            .order_by(GenerationJob.created_at.desc())
        )
        return dict(
            concept=row.payload,
            atoms=row.atoms,
            problems=row.problems or [],
            jobs=[{**job_view(j), "output": j.output} for j in runs],
        )


@router.post("/{course_id}/pause")
def pause(course_id: str, request: Request):
    """Stop starting new agent work; queued jobs wait. Learners keep released content."""
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        _course_row(db, course_id).paused = "owner"
        record_event(db, user.id, "coursegen.paused", course_id)
        return {"paused": "owner"}


@router.post("/{course_id}/resume")
def resume(course_id: str, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        row = _course_row(db, course_id)
        if jobs.spent(db, course_id) >= row.brief["budget_usd"]:
            raise HTTPException(409, "budget_reached")
        row.paused = ""
        record_event(db, user.id, "coursegen.resumed", course_id)
        return {"paused": ""}


@router.put("/{course_id}/budget")
def set_budget(course_id: str, body: Budget, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        row = _course_row(db, course_id)
        row.brief = {**row.brief, **body.model_dump()}  # a new dict, so the JSON is saved
        record_event(db, user.id, "coursegen.budget_changed", course_id)
        return body.model_dump()


@router.post("/{course_id}/concepts/{concept_id}/quarantine")
def quarantine(course_id: str, concept_id: str, body: Notes, request: Request):
    """Withdraw a released concept now and have it rewritten with the owner's notes."""
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        row = db.get(GeneratedConcept, (course_id, concept_id))
        if row is None or row.payload.get("status") != "live":
            raise HTTPException(409, "concept_not_live")
        if jobs.active(db, course_id, concept_id) is not None:
            raise HTTPException(409, "generation_in_progress")
        quality.quarantine(db, default_catalog(), course_id, concept_id, "owner", [body.notes])
        record_event(db, user.id, "coursegen.quarantined", course_id)
    quality.announce(course_id, concept_id, "owner")
    return {"quarantined": True}
