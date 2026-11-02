"""Community courses: a learner may share their own course with everyone, and earns perks when
other learners really use it.

Sharing is opt-in and revocable. Perks count distinct *other* learners who enrolled and then
did something in the course (a learner with no activity is not a user). Awarding is a pure
sweep over the database, safe to run at any time: one row per (user, course, tier).
"""

from dataclasses import dataclass

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from socrat.models import ConceptState, CreatorPerk, Enrollment, GeneratedCourse

DAY = 86400


@dataclass(frozen=True)
class Tier:
    id: str
    learners: int  # distinct active learners other than the creator
    kind: str  # badge | plus
    days: int = 0  # Plus access granted, for kind == "plus"
    label: str = ""


TIERS = (
    Tier("creator", 10, "badge", label="Course creator"),
    Tier("plus-30", 50, "plus", 30, "30 days of Plus"),
    Tier("plus-90", 250, "plus", 90, "90 days of Plus"),
)


def active_learners(db: Session, course_id: str, owner_id: str) -> int:
    """Other learners who enrolled and have at least one concept with recorded progress."""
    return (
        db.scalar(
            select(func.count(distinct(Enrollment.user_id)))
            .select_from(Enrollment)
            .join(ConceptState, ConceptState.enrollment_id == Enrollment.id)
            .where(Enrollment.course_id == course_id, Enrollment.user_id != owner_id)
        )
        or 0
    )


def sweep(db: Session, stamp: int, course_id: str | None = None) -> list[CreatorPerk]:
    """Award every tier a shared course has reached. No commit; returns the new rows."""
    query = select(GeneratedCourse).where(
        GeneratedCourse.visibility == "public", GeneratedCourse.owner_id.is_not(None)
    )
    if course_id:
        query = query.where(GeneratedCourse.id == course_id)
    awarded = []
    for course in db.scalars(query):
        owner = course.owner_id
        assert owner is not None
        count = active_learners(db, course.id, owner)
        for tier in TIERS:
            if count < tier.learners or db.scalar(
                select(CreatorPerk).where(
                    CreatorPerk.user_id == owner,
                    CreatorPerk.course_id == course.id,
                    CreatorPerk.tier == tier.id,
                )
            ):
                continue
            perk = CreatorPerk(
                user_id=owner,
                course_id=course.id,
                tier=tier.id,
                kind=tier.kind,
                earned_at=stamp,
                expires_at=stamp + tier.days * DAY if tier.kind == "plus" else None,
            )
            db.add(perk)
            awarded.append(perk)
    db.flush()
    return awarded


def standing(db: Session, course: GeneratedCourse) -> dict:
    """What a creator sees: current count and the next tier."""
    assert course.owner_id is not None
    count = active_learners(db, course.id, course.owner_id)
    earned = {
        p.tier
        for p in db.scalars(
            select(CreatorPerk).where(
                CreatorPerk.user_id == course.owner_id, CreatorPerk.course_id == course.id
            )
        )
    }
    return dict(
        learners=count,
        tiers=[
            dict(id=t.id, learners=t.learners, label=t.label, earned=t.id in earned) for t in TIERS
        ],
    )
