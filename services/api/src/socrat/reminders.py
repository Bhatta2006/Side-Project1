"""Study reminders: one honest email on a planned study day if nothing has been done yet.

Opt-in (``users.reminders``), and built not to nag: at most one per local day, only on the
learner's own study weekdays and only in the early evening, and after three in a row with no
study in between it goes quiet until the learner comes back. Every email says how to turn it off.
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from socrat import email_auth
from socrat.config import Settings
from socrat.learn import service as learn
from socrat.models import DailyActivity, User, now

log = logging.getLogger("socrat.reminders")

WINDOW = range(18, 21)  # local hours (18:00 to 20:59) in which a reminder may go out
MIN_GAP = 20 * 3600
MAX_UNANSWERED = 3


def local_time(user: User, stamp: int) -> datetime:
    try:
        zone = ZoneInfo(user.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo("UTC")
    return datetime.fromtimestamp(stamp, zone)


def studied_since(db: Session, user: User, stamp: int) -> bool:
    """Any study on the local day of ``stamp`` or later."""
    first_day = local_time(user, stamp).date().isoformat()
    return (
        db.scalar(
            select(DailyActivity.day).where(
                DailyActivity.user_id == user.id,
                DailyActivity.day >= first_day,
                DailyActivity.activities > 0,
            )
        )
        is not None
    )


def should_send(db: Session, user: User, stamp: int) -> bool:
    if not user.reminders or not user.email:
        return False
    enrollment = learn.active_enrollment(db, user.id)
    if enrollment is None or enrollment.status != "active":
        return False
    here = local_time(user, stamp)
    if here.weekday() not in enrollment.weekdays or here.hour not in WINDOW:
        return False
    if user.reminder_sent_at is not None and stamp - user.reminder_sent_at < MIN_GAP:
        return False
    if user.reminders_unanswered >= MAX_UNANSWERED:
        return False
    return not studied_since(db, user, stamp)  # nothing yet today


def message(settings: Settings, user: User, minutes: int) -> tuple[str, str]:
    name = (user.display_name or "").split(" ")[0] or "there"
    return (
        "Your Socrat session is ready",
        f"Hi {name}, today is one of your study days and nothing has been done yet.\n\n"
        f"A short session is about {minutes} minutes. If today is not the day, skipping it is fine.\n\n"
        f"Open it: {settings.public_origin}/today\n\n"
        f"Turn these reminders off any time in Settings: {settings.public_origin}/settings",
    )


def sweep(
    engine: Engine, settings: Settings, stamp: int | None = None, send=email_auth.send
) -> int:
    """Send the reminders that are due. Returns how many went out."""
    stamp = now() if stamp is None else stamp
    sent = 0
    with Session(engine) as db, db.begin():
        users = db.scalars(select(User).where(User.reminders.is_(True), User.email.is_not(None)))
        for user in users:
            # Studying since the last reminder answers it, and wakes the reminders again.
            if user.reminder_sent_at is not None and studied_since(db, user, user.reminder_sent_at):
                user.reminders_unanswered = 0
            if not should_send(db, user, stamp):
                continue
            enrollment = learn.active_enrollment(db, user.id)
            assert enrollment is not None and user.email is not None
            try:
                send(settings, user.email, *message(settings, user, enrollment.minutes_per_day))
            except HTTPException:
                continue  # already logged; the next sweep tries again within the window
            user.reminder_sent_at = stamp
            user.reminders_unanswered += 1
            sent += 1
    if sent:
        log.info("reminders sent: %d", sent)
    return sent
