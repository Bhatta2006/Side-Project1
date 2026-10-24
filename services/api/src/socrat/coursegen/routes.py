"""Admin API for generated courses: write a brief, follow the agents, review, edit, publish."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.admin.routes import require_admin
from socrat.catalog import generated
from socrat.catalog.registry import CatalogError, default_catalog
from socrat.catalog.schema import Course
from socrat.coursegen import jobs
from socrat.coursegen.outline import Brief
from socrat.database import record_event
from socrat.learn.routes import catalog, engine
from socrat.models import GeneratedCourse, GenerationJob

router = APIRouter(prefix="/api/v1/admin/courses")


class Notes(BaseModel):
    notes: str = Field(min_length=3, max_length=4000)


class OutlineEdit(BaseModel):
    course: dict


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
                    concepts=None
                    if row is None
                    else sum(len(m["concepts"]) for m in row.payload["modules"]),
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
        return dict(
            id=course_id,
            status=row.status if row else "drafting",
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
