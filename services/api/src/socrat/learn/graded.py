"""Rubric-graded work as the learner sees it: prompts with their last grade, projects with
milestone progress. Read-only; ``graded_routes`` grades and records."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.catalog.registry import Catalog
from socrat.coursegen.package import AI_AUTHOR
from socrat.models import Enrollment, Evidence

PASS = 0.7  # a milestone counts as done at this score


def attempts_today(
    db: Session, enrollment: Enrollment, activity: str, concept: str, stamp: int
) -> int:
    """Graded attempts in the last day. Each attempt writes one row per concept, so the rows
    of one concept count attempts; a failed grading writes none and costs nothing."""
    return (
        db.scalar(
            select(func.count()).where(
                Evidence.enrollment_id == enrollment.id,
                Evidence.activity_id == activity,
                Evidence.concept == concept,
                Evidence.created_at > stamp - 86400,
            )
        )
        or 0
    )


def latest(db: Session, enrollment: Enrollment | None, activity: str) -> Evidence | None:
    if enrollment is None:
        return None
    return db.scalars(
        select(Evidence)
        .where(Evidence.enrollment_id == enrollment.id, Evidence.activity_id == activity)
        .order_by(Evidence.seq.desc())
    ).first()


def prompt_views(db: Session, enrollment: Enrollment | None, qualified: str, concept) -> list:
    """A concept's prompts for the learner: rubric criteria, and their last grade (with the
    model answer) once they have answered."""
    views = []
    for prompt in concept.prompts:
        last = latest(db, enrollment, f"answer:{qualified}:{prompt.id}")
        views.append(
            dict(
                id=prompt.id,
                prompt=prompt.prompt,
                max_words=prompt.max_words,
                rubric=[dict(criterion=c.criterion, points=c.points) for c in prompt.rubric],
                last=(
                    dict(
                        answer=last.details.get("answer", ""),
                        grade=last.details.get("grade", {}),
                        model_answer=prompt.model_answer,
                    )
                    if last
                    else None
                ),
            )
        )
    return views


def project_view(db: Session, cat: Catalog, enrollment: Enrollment, key: str) -> dict:
    project = cat.projects[key]
    milestones, open_next = [], True
    for m in project.milestones:
        last = latest(db, enrollment, f"project:{key}:{m.id}")
        best = (
            db.scalar(
                select(func.max(Evidence.score)).where(
                    Evidence.enrollment_id == enrollment.id,
                    Evidence.activity_id == f"project:{key}:{m.id}",
                )
            )
            or 0.0
        )
        done = best >= PASS
        milestones.append(
            dict(
                id=m.id,
                title=m.title,
                checklist=m.checklist,
                done=done,
                available=open_next,
                last=(
                    dict(
                        work=last.details.get("work", ""),
                        link=last.details.get("link", ""),
                        grade=last.details.get("grade", {}),
                    )
                    if last
                    else None
                ),
            )
        )
        open_next = open_next and done
    preparing = [c for c in project.concepts if cat.concept(c).status == "planned"]
    return dict(
        id=key,
        title=project.title,
        summary=project.summary,
        skills=project.skills,
        constraints=project.constraints,
        concepts=[dict(id=c, title=cat.concept(c).title) for c in project.concepts],
        rubric=[r.model_dump() for r in project.rubric],
        self_review=project.self_review,
        milestones=milestones,
        preparing=bool(preparing),
        ai_generated=project.provenance.author == AI_AUTHOR,
        attribution=project.provenance.attribution_md,
    )
