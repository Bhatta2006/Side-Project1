"""Read models for the adaptive roadmap: proposals, path options, profile, weekly review,
nudges and the daily check-in. Deterministic text from the learner's own data."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.adaptive import proposals
from socrat.adaptive import service as adaptive
from socrat.adaptive.profile import BAND_ORDER
from socrat.catalog.registry import Catalog
from socrat.database import record_event
from socrat.learn import service as learn
from socrat.mastery.model import DAY
from socrat.models import DailyActivity, Enrollment, Evidence, User
from socrat.planner import goals
from socrat.planner.engine import Plan

WEEK = 7


def concept_href(concept: str) -> str:
    return f"/learn/{concept.replace(':', '/')}"


def proposals_view(db: Session, enrollment: Enrollment) -> dict:
    return dict(
        pending=[proposals.view(p) for p in proposals.pending(db, enrollment)],
        recent=[proposals.view(p) for p in proposals.history(db, enrollment, limit=8)],
        overrides=(enrollment.adaptive or {}).get("overrides", {}),
        style=(enrollment.adaptive or {}).get("style", "balanced"),
    )


def plan_options(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment, now: int
) -> dict:
    """B4: the same learner, four ways to walk the course, so they can choose."""
    states = learn.states_for(db, enrollment)
    current = (enrollment.adaptive or {}).get("style", "balanced")
    options = []
    for style in goals.STYLES:
        plan, _ = learn.build_for(db, catalog, user, enrollment, now, states, style=style)
        label, blurb = goals.STYLE_WORDS[style]
        options.append(
            dict(
                style=style,
                label=label,
                description=blurb,
                current=style == current,
                remaining_minutes=plan.remaining_minutes,
                finish=plan.forecast["realistic_finish"],
                concepts=sum(1 for r in plan.roadmap if r["status"] not in {"optional", "skipped"}),
                optional=sum(1 for r in plan.roadmap if r["status"] == "optional"),
            )
        )
    return dict(
        current=current,
        focus=goals.focus_of(enrollment.course_id, enrollment.goal),
        options=options,
    )


def profile_view(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment, now: int
) -> dict:
    """A1: the full learner model the planner and tutor see."""
    from socrat.library import service as library

    states = learn.states_for(db, enrollment)
    skill = adaptive.build_profiles(db, catalog, enrollment, states, now)
    stuck = adaptive.stuck_map(skill, now)
    learner = library.learner_for(db, catalog, user, enrollment, now)
    return dict(
        level=adaptive.level_for(db, user.id, learner.rating, enrollment),
        review_scale=adaptive.review_scale_for(db, enrollment),
        adherence=adaptive.adherence_for(db, enrollment, learn.local_day(user, now)),
        concepts=[
            dict(
                p.to_dict(),
                title=catalog.concept(c).title,
                stuck=stuck[c].to_dict() if c in stuck else None,
            )
            for c, p in skill.items()
            if p.attempts or p.band != "not_started"
        ],
    )


def _minutes(db: Session, user: User, start: str, end: str) -> tuple[int, int]:
    rows = list(
        db.scalars(
            select(DailyActivity).where(
                DailyActivity.user_id == user.id,
                DailyActivity.day >= start,
                DailyActivity.day <= end,
            )
        )
    )
    return sum(r.minutes for r in rows), sum(1 for r in rows if r.minutes > 0)


def weekly_review(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment, now: int
) -> dict:
    """E1: what went well, what is slipping, and the plan changes waiting for a decision."""
    plan = learn.plan_for(db, catalog, user, enrollment, now)
    today = learn.local_day(user, now)
    start = today - timedelta(days=WEEK - 1)
    minutes, days = _minutes(db, user, start.isoformat(), today.isoformat())
    planned = enrollment.minutes_per_day * sum(
        1 for i in range(WEEK) if (start + timedelta(days=i)).weekday() in enrollment.weekdays
    )
    rows = list(
        db.scalars(
            select(Evidence)
            .where(Evidence.enrollment_id == enrollment.id, Evidence.created_at >= now - WEEK * DAY)
            .order_by(Evidence.created_at, Evidence.seq)
        )
    )
    first: dict[str, str] = {}
    last: dict[str, str] = {}
    for row in rows:
        first.setdefault(row.concept, (row.details or {}).get("before_band", "not_started"))
        last[row.concept] = (row.details or {}).get("after_band", "not_started")
    improved = [
        catalog.concept(c).title
        for c in last
        if c in catalog.concepts and BAND_ORDER.get(last[c], 0) > BAND_ORDER.get(first[c], 0)
    ]
    states = learn.states_for(db, enrollment)
    skill = adaptive.build_profiles(db, catalog, enrollment, states, now)
    stuck = adaptive.stuck_map(skill, now)
    slipping = [
        dict(concept=c, title=catalog.concept(c).title, href=concept_href(c))
        for c, s in sorted(states.items(), key=lambda kv: kv[1].next_review_at)
        if c in catalog.concepts and c not in stuck and s.due(now) and s.effective(now) < s.mean
    ][:5]
    wins = []
    if improved:
        wins.append(f"Moved up on {', '.join(improved[:3])}.")
    solved = sum(1 for r in rows if r.kind == "code" and r.score == 1 and r.assistance == 0)
    if solved:
        wins.append(f"Solved {solved} problem(s) on your own.")
    if planned and minutes >= planned:
        wins.append("Hit your study time for the week.")
    return dict(
        week_start=start.isoformat(),
        week_end=today.isoformat(),
        minutes=dict(done=minutes, planned=planned),
        study_days=days,
        evidence=len(rows),
        wins=wins or ["Every session counts — let's build on this week."],
        improved=improved,
        slipping=slipping,
        stuck=[
            dict(concept=c, title=catalog.concept(c).title, summary=s.summary, href=concept_href(c))
            for c, s in stuck.items()
        ],
        forecast=plan.forecast,
        next_milestone=plan.milestones[0] if plan.milestones else None,
        proposals=[proposals.view(p) for p in proposals.pending(db, enrollment)],
        seen=(enrollment.adaptive or {}).get("weekly_seen") == iso_week(today),
    )


def iso_week(day) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def mark_weekly_seen(user: User, enrollment: Enrollment, now: int) -> None:
    data = dict(enrollment.adaptive or {})
    data["weekly_seen"] = iso_week(learn.local_day(user, now))
    enrollment.adaptive = data


def weekly_ready(user: User, enrollment: Enrollment, now: int) -> bool:
    week = iso_week(learn.local_day(user, now))
    old_enough = now - enrollment.created_at >= 6 * DAY
    return old_enough and (enrollment.adaptive or {}).get("weekly_seen") != week


def nudges(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment,
    plan: Plan,
    now: int,
    record: bool = True,
) -> list[dict]:
    """E3: short, actionable prompts. Each kind is announced as an event at most once a
    day, so a mailer or push service can deliver them without spamming."""
    out: list[dict] = []
    states = learn.states_for(db, enrollment)
    skill = adaptive.build_profiles(db, catalog, enrollment, states, now)
    for concept, found in adaptive.stuck_map(skill, now).items():
        out.append(
            dict(
                kind="stuck",
                severity="high" if found.severity >= 2 else "medium",
                title=f"Stuck on {catalog.concept(concept).title}?",
                body=found.summary,
                href=concept_href(concept),
            )
        )
    due = [c for c, s in states.items() if s.due(now) and c in catalog.concepts]
    if len(due) >= 3:
        out.append(
            dict(
                kind="reviews",
                severity="medium",
                title=f"{len(due)} reviews are due",
                body="A few minutes now keeps them from fading.",
                href="/today",
            )
        )
    waiting = proposals.pending(db, enrollment)
    if plan.forecast.get("on_track") is False:
        options = any(p.group.startswith("deadline") for p in waiting)
        out.append(
            dict(
                kind="off_track",
                severity="high",
                title="You're behind for your target date",
                body=f"At your current rhythm you'd finish {plan.forecast['realistic_finish']}, "
                f"after {plan.forecast['target_date']}. "
                + (
                    "Socrat has options for you on your plan."
                    if options
                    else "More study time or a later date in Settings would close the gap."
                ),
                href="/plan#proposals" if options else "/settings",
            )
        )
    away = learn.days_away(db, user, enrollment, now)
    if away >= 2:
        out.append(
            dict(
                kind="away",
                severity="medium",
                title=f"It's been {away} study days",
                body="A short session today gets you rolling again.",
                href="/today",
            )
        )
    if waiting:
        out.append(
            dict(
                kind="proposals",
                severity="low",
                title=f"Socrat suggests {len(waiting)} change(s) to your plan",
                body="Nothing changes until you say yes.",
                href="/plan#proposals",
            )
        )
    ahead = [
        r for r in plan.roadmap if r["status"] not in {"mastered", "assumed", "skipped", "optional"}
    ][:3]
    writing = next((r for r in ahead if r["status"] == "preparing"), None)
    if writing is not None:
        # Generated courses: the hold state. Say what is coming and keep the day useful.
        out.append(
            dict(
                kind="preparing",
                severity="low",
                title=f"{writing['title']} is being written",
                body="It joins your plan as soon as it passes its checks. "
                "Meanwhile, your reviews and practice keep you moving.",
                href="/plan",
            )
        )
    if weekly_ready(user, enrollment, now):
        out.append(
            dict(
                kind="weekly_review",
                severity="low",
                title="Your weekly review is ready",
                body="See what went well, what's slipping, and what to change.",
                href="/plan#review",
            )
        )
    if record:
        day = learn.local_day(user, now).isoformat()
        data = dict(enrollment.adaptive or {})
        sent = dict(data.get("nudged", {}))
        for item in out:
            if sent.get(item["kind"]) != day:
                sent[item["kind"]] = day
                record_event(db, user.id, f"nudge.{item['kind']}", enrollment.id)
        if sent != data.get("nudged"):
            data["nudged"] = sent
            enrollment.adaptive = data
    return out


def checkin(
    db: Session, catalog: Catalog, user: User, enrollment: Enrollment, plan: Plan, now: int
) -> dict | None:
    """F4: Socrat opens the day by connecting yesterday's work to today's first step."""
    rows = list(
        db.scalars(
            select(Evidence)
            .where(Evidence.enrollment_id == enrollment.id, Evidence.created_at < now)
            .order_by(Evidence.created_at.desc())
            .limit(20)
        )
    )
    first = plan.days[0]["items"][0] if plan.days and plan.days[0]["items"] else None
    if not rows and first is None:
        return None
    today = learn.local_day(user, now)
    last_day = learn.local_day(user, rows[0].created_at) if rows else None
    session = [r for r in rows if learn.local_day(user, r.created_at) == last_day]
    lines = []
    if session and last_day != today:
        hard = [r for r in session if r.score < 0.5 and r.concept in catalog.concepts]
        good = [r for r in session if r.score >= 0.7 and r.concept in catalog.concepts]
        when = "Yesterday" if last_day == today - timedelta(days=1) else "Last time"
        if hard:
            lines.append(
                f"{when}, {catalog.concept(hard[0].concept).title} pushed back — that's normal "
                "at this stage."
            )
        elif good:
            lines.append(f"{when} went well on {catalog.concept(good[0].concept).title}.")
    if first is not None:
        why = first.get("reason") or "it's next on your path"
        lines.append(f"Today let's start with **{first['title']}**: {why[0].lower() + why[1:]}")
    if plan.forecast.get("on_track") is False:
        lines.append("You're a little behind for your date; your plan page shows what would help.")
    return dict(message=" ".join(lines), first=first) if lines else None
