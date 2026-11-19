"""The streak upgrade (item 5 of docs/research/duolingo-teardown.md), behind
``streak_plus_enabled``: the streak with its protections, a streak goal the learner commits to,
and a month calendar. The rules live in ``learn/streaks.py``; nothing here is evidence.

The goal is a learner-owned setting (``Enrollment.adaptive["streak_goal"]``); setting or
clearing it changes no streak, freeze or schedule.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy.orm import Session

from socrat.learn import service as learn
from socrat.learn import streaks
from socrat.learn.routes import Strict, active, engine, user_of
from socrat.models import Enrollment, now

router = APIRouter(prefix="/api/v1/streak", tags=["learn"])
MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class Goal(Strict):
    days: Literal[7, 14, 30]


def _on(request: Request) -> None:
    if not request.app.state.settings.streak_plus_enabled:
        raise HTTPException(404, "not_found")


def _set_goal(enrollment: Enrollment, value: dict | None) -> None:
    data = dict(enrollment.adaptive or {})
    if value:
        data["streak_goal"] = value
    else:
        data.pop("streak_goal", None)
    enrollment.adaptive = data  # reassigned so the JSON change is saved


@router.get("")
def streak(request: Request) -> dict:
    """The streak with its protections and goal, plus the goals on offer."""
    _on(request)
    with Session(engine(request)) as db:
        user = user_of(request, db)
        out = learn.streak(db, user, active(db, user), now())
        return {**out, "goals": list(streaks.GOALS), "repair_minutes": streaks.REPAIR_MINUTES}


@router.put("/goal")
def set_goal(body: Goal, request: Request) -> dict:
    _on(request)
    stamp = now()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        _set_goal(enrollment, {"days": body.days, "set_at": stamp})
        db.flush()
        return {"goal": learn.streak(db, user, enrollment, stamp)["goal"]}


@router.delete("/goal")
def clear_goal(request: Request) -> dict:
    _on(request)
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        _set_goal(active(db, user), None)
        return {"goal": None}


@router.get("/calendar")
def calendar(
    request: Request,
    month: Annotated[str | None, Query(pattern=MONTH.pattern)] = None,
) -> dict:
    """One month of streak days (default: this month), from the course start to this month."""
    _on(request)
    stamp = now()
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        today = learn.local_day(user, stamp)
        start = learn.streak_start(enrollment)
        chosen = date.fromisoformat(f"{month}-01") if month else today.replace(day=1)
        earliest, latest = start.replace(day=1), today.replace(day=1)
        if not earliest <= chosen <= latest:
            raise HTTPException(404, "month_out_of_range")
        days = streaks.calendar(
            learn.minutes_by_day(db, user),
            today,
            set(enrollment.weekdays),
            start,
            enrollment.minutes_per_day,
            chosen,
        )
        return {
            "month": chosen.isoformat()[:7],
            "earliest": earliest.isoformat()[:7],
            "latest": latest.isoformat()[:7],
            "days": days,
        }
