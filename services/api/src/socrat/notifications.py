"""Notes from an admin to a learner, shown once in the app.

An admin writes one from the admin page (to one learner, or to everyone). The learner's app asks
for the unseen ones when it opens and marks them seen when the learner closes them.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from socrat.learn.routes import engine, user_of
from socrat.models import UserNotification, now

router = APIRouter(prefix="/api/v1/me/notifications")

# A learner who has been away is not met with a wall of old notes.
SHOWN = 5


class Seen(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ids: list[str] = Field(min_length=1, max_length=50)


def view(row: UserNotification) -> dict:
    return dict(
        id=row.id, title=row.title, body=row.body, created_at=row.created_at, seen_at=row.seen_at
    )


@router.get("")
def unseen(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        rows = db.scalars(
            select(UserNotification)
            .where(UserNotification.user_id == user.id, UserNotification.seen_at.is_(None))
            .order_by(UserNotification.created_at.desc())
            .limit(SHOWN)
        ).all()
        return dict(items=[view(r) for r in rows])


@router.post("/seen")
def seen(body: Seen, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        db.execute(
            update(UserNotification)
            .where(
                UserNotification.user_id == user.id,
                UserNotification.id.in_(body.ids),
                UserNotification.seen_at.is_(None),
            )
            .values(seen_at=now())
        )
        return dict(ok=True)
