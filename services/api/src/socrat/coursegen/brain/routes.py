"""Owner view of the course brain: why a request got its course, what root material exists, and
the correction path for a unit that turned out wrong."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.admin.routes import require_admin
from socrat.catalog.registry import default_catalog
from socrat.coursegen.brain import units as unitstore
from socrat.database import record_event
from socrat.learn.routes import engine
from socrat.models import CourseMatch, RootUnit, SubjectRoot

router = APIRouter(prefix="/api/v1/admin/brain")


class Correction(BaseModel):
    reason: str = Field(min_length=5, max_length=300)


def _unit(db: Session, unit: RootUnit) -> dict:
    return dict(
        id=unit.id,
        root=unit.root_id,
        key=unit.unit_key,
        revision=unit.revision,
        status=unit.status,
        topic=unit.topic,
        depth=unit.depth,
        concepts=[c.get("key") for c in unit.concepts or []],
        items={k: len((unit.content or {}).get(k, [])) for k in unitstore.CONTENT_KEYS},
        sources=unitstore.sources_of(db, unit),
        problems=(unit.quality or {}).get("problems", []),
        courses=sorted({c for c, _ in unitstore.pinned_courses(db, unit.id)}),
        created_at=unit.created_at,
    )


@router.get("/roots")
def roots(request: Request):
    with Session(engine(request)) as db:
        require_admin(request, db)
        rows = db.scalars(select(SubjectRoot).order_by(SubjectRoot.id)).all()
        return {
            "items": [
                dict(id=r.id, title=r.title, status=r.status, merged_into=r.merged_into)
                for r in rows
            ]
        }


@router.get("/units")
def units(request: Request, root: str | None = None):
    with Session(engine(request)) as db:
        require_admin(request, db)
        query = select(RootUnit).order_by(RootUnit.root_id, RootUnit.unit_key, RootUnit.revision)
        if root:
            query = query.where(RootUnit.root_id == root)
        return {"items": [_unit(db, u) for u in db.scalars(query)]}


@router.get("/matches/{request_id}")
def match(request_id: str, request: Request):
    """Why this request got the course it got: the decision, every candidate and each check."""
    with Session(engine(request)) as db:
        require_admin(request, db)
        row = db.scalar(select(CourseMatch).where(CourseMatch.request_id == request_id))
        if row is None:
            raise HTTPException(404, "not_found")
        return dict(
            request=row.request_id,
            outcome=row.outcome,
            course=row.course_id,
            reason=row.reason,
            root=row.root_id,
            spec=row.spec,
            candidates=row.candidates,
            adaptations=row.adaptations,
            units=row.units,
            # What belongs only to this learner is listed by name, never shown.
            private=sorted((row.private or {}).keys()),
            matcher=row.matcher_version,
        )


@router.post("/units/{unit_id}/correct")
def correct(unit_id: str, body: Correction, request: Request):
    """Withdraw a unit revision, research a corrected one, and rewrite its lessons."""
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        if db.get(RootUnit, unit_id) is None:
            raise HTTPException(404, "not_found")
        done = unitstore.correct(db, default_catalog(), unit_id, body.reason, user.id)
        record_event(db, user.id, "brain.unit_corrected", unit_id)
        return done
