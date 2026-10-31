"""Skill Passport: a public, shareable page of what a learner has *shown* they can do.

Everything on it is computed live from verified evidence: judged submissions (and whether
the tutor helped), concept checks, checkpoints, weekly assessments and spaced mastery.
Reading a lesson never appears. The passport is private until the learner turns it on, and
turning it off makes the link stop working at once. It shows the learner's display name and
nothing else about them.
"""

import re
import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.database import record_event
from socrat.learn import achievements
from socrat.learn import service as learn
from socrat.learn.routes import catalog, engine, user_of
from socrat.mastery.model import ConceptState, band
from socrat.models import Evidence, SkillPassport, User, WeeklyAssessment, now

router = APIRouter(prefix="/api/v1")
SLUG = re.compile(r"^[A-Za-z0-9_-]{8,24}$")
SKILL_LIMIT = 40


class PassportUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    public: bool


def month_of(stamp: int) -> str:
    return datetime.fromtimestamp(stamp, UTC).strftime("%B %Y")


def evidence(db: Session, catalog: Catalog, user: User, stamp: int) -> dict:
    """The public facts. Pure reads; nothing here is stored."""
    enrollment = learn.active_enrollment(db, user.id)
    base: dict[str, Any] = dict(
        name=(user.display_name or "Socrat learner").strip()[:80],
        member_since=month_of(user.created_at),
        course=None,
        language=None,
        mastered=[],
        practising=[],
        counts=dict(
            unaided_solves=0,
            judged_solves=0,
            assisted_solves=0,
            checks_passed=0,
            transfer_verified=0,
            checkpoints=0,
            weekly_assessments=0,
            longest_streak=0,
        ),
        badges=[],
        generated_at=stamp,
    )
    if enrollment is None or enrollment.status != "active":
        return base
    course = catalog.course(enrollment.course_id)
    states = learn.states_for(db, enrollment)
    plan = learn.plan_for(db, catalog, user, enrollment, stamp, record=False)
    mastered, practising = [], []
    for item in plan.roadmap:
        state = states.get(item["concept"], ConceptState())
        if not state.evidence_count:
            continue
        label = band(state, stamp)
        entry = dict(
            id=item["concept"],
            title=item["title"],
            evidence=state.evidence_count,
            # Solved a problem it had never seen, after naming the technique, with no help.
            transfer_verified=item.get("transfer") == "verified",
        )
        if label == "strong":
            mastered.append(entry)
        elif label in {"developing", "likely_known"}:
            practising.append(entry)
    streak = learn.streak(db, user, enrollment, stamp)
    facts = achievements.facts_for(db, catalog, user, enrollment, streak["longest"])
    solves = learn.evidence_counts(db, enrollment)
    checks = db.scalar(
        select(func.count())
        .select_from(Evidence)
        .where(
            Evidence.enrollment_id == enrollment.id,
            Evidence.kind.in_(("quiz", "testout", "checkpoint", "review", "moduletest")),
            Evidence.score >= 0.8,
            Evidence.assistance == 0,
        )
    )
    weekly = db.scalar(
        select(func.count())
        .select_from(WeeklyAssessment)
        .where(
            WeeklyAssessment.enrollment_id == enrollment.id,
            WeeklyAssessment.finished_at.is_not(None),
        )
    )
    own = len(facts.events.get("own", []))
    return dict(
        base,
        course=course.title,
        language=enrollment.language,
        mastered=mastered[:SKILL_LIMIT],
        practising=practising[:SKILL_LIMIT],
        counts=dict(
            unaided_solves=own,
            judged_solves=solves["independent_solves"] + solves["assisted_solves"],
            assisted_solves=solves["assisted_solves"],
            checks_passed=checks or 0,
            transfer_verified=sum(m["transfer_verified"] for m in mastered),
            checkpoints=len(facts.events.get("gates", [])),
            weekly_assessments=weekly or 0,
            longest_streak=streak["longest"],
        ),
        badges=[
            dict(
                id=b["id"], title=b["title"], description=b["description"], earned_at=b["earned_at"]
            )
            for b in achievements.evaluate(facts)
            if b["earned"]
        ],
    )


def owner_view(row: SkillPassport | None) -> dict:
    return dict(
        public=bool(row and row.public),
        slug=row.slug if row else None,
        path=f"/passport/{row.slug}" if row else None,
        updated_at=row.updated_at if row else None,
    )


@router.get("/me/passport")
def mine(request: Request):
    cat = catalog()
    with Session(engine(request)) as db:
        user = user_of(request, db)
        row = db.get(SkillPassport, user.id)
        return dict(owner_view(row), preview=evidence(db, cat, user, now()))


@router.put("/me/passport")
def update(body: PassportUpdate, request: Request):
    stamp = now()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        row = db.get(SkillPassport, user.id)
        if row is None:
            row = SkillPassport(user_id=user.id, slug=secrets.token_urlsafe(9), created_at=stamp)
            db.add(row)
        row.public = body.public
        row.updated_at = stamp
        record_event(db, user.id, "passport.published" if body.public else "passport.hidden")
        db.flush()
        return owner_view(row)


@router.get("/passport/{slug}")
def public(slug: str, request: Request):
    if not SLUG.match(slug):
        raise HTTPException(404, "not_found")
    cat = catalog()
    with Session(engine(request)) as db:
        row = db.scalar(select(SkillPassport).where(SkillPassport.slug == slug))
        user = db.get(User, row.user_id) if row is not None and row.public else None
        if user is None:
            raise HTTPException(404, "not_found")
        return evidence(db, cat, user, now())
