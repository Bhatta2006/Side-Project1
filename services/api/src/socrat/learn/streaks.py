"""Streaks with earned protection.

A streak counts consecutive scheduled study days with activity; rest days never break it.
Meeting a whole week's study goal banks a streak freeze (at most FREEZE_CAP). A missed
scheduled day spends a freeze instead of resetting the streak, so one bad day after a good
week costs nothing. Pure: the caller supplies minutes per local day.

With ``EXTRAS`` on (``streak_plus_enabled``, item 5 of docs/research/duolingo-teardown.md),
two more kinds of protection apply, both derived from the minutes alone, so nothing is stored
and the result can always be recomputed:

- **Saved**: a streak of at least ``SAVE_MIN_RUN`` days about to break, with no freeze banked,
  is covered once (at most once every ``SAVE_EVERY`` days). A learner about to lose a streak
  they built is the one at risk; a simple rule first, a return model later.
- **Earned back**: a missed study day that nothing covered is repaired when the learner's
  next study, within ``REPAIR_WINDOW`` days and with no other study day missed in between,
  lasts at least ``REPAIR_MINUTES`` (at most once every ``REPAIR_EVERY`` days). Until then the
  result offers it (``earn_back``).

Saved and repaired days keep the streak going; they never count as studied days.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

FREEZE_CAP = 2
EXTRAS = False  # set from settings.streak_plus_enabled at startup
SAVE_MIN_RUN = 3
SAVE_EVERY = 30
REPAIR_WINDOW = 2
REPAIR_MINUTES = 10
REPAIR_EVERY = 7
GOALS = (7, 14, 30)


def _week_goal_met(
    minutes: dict[date, int], monday: date, weekdays: set[int], start: date, daily_goal: int
) -> bool:
    days = [monday + timedelta(days=i) for i in range(7)]
    scheduled = [d for d in days if d >= start and d.weekday() in weekdays]
    if not scheduled or daily_goal <= 0:
        return False
    return sum(minutes.get(d, 0) for d in days) >= daily_goal * len(scheduled)


@dataclass
class Walk:
    run: int = 0
    longest: int = 0
    freezes: int = 0
    status: dict[date, str] = field(default_factory=dict)
    earn_back: dict | None = None
    repaired_today: bool = False  # today's study is what earned a missed day back


def _repair(
    minutes: dict[date, int], missed: date, today: date, weekdays: set[int], start: date
) -> str:
    """'repaired', 'pending' or 'no' for a missed study day nothing else covered."""
    last = missed + timedelta(days=REPAIR_WINDOW)
    cursor = missed + timedelta(days=1)
    while cursor <= min(last, today):
        if cursor in minutes:
            if minutes[cursor] >= REPAIR_MINUTES:
                return "repaired"
            return "pending" if cursor == today else "no"
        if cursor < today and cursor.weekday() in weekdays and cursor >= start:
            return "no"  # another study day missed in between
        cursor += timedelta(days=1)
    return "pending" if last >= today else "no"


def walk(
    minutes: dict[date, int],
    today: date,
    weekdays: set[int],
    start: date,
    daily_goal: int,
    extras: bool,
) -> Walk:
    studied = set(minutes)
    first = min([start, *studied]) if studied else start
    w = Walk()
    last_save: date | None = None
    last_repair: date | None = None
    cursor = first
    while cursor < today:
        if cursor in studied:
            w.run += 1
            w.longest = max(w.longest, w.run)
            w.status[cursor] = "studied"
        elif cursor.weekday() in weekdays and cursor >= start:
            if w.freezes:
                w.freezes -= 1
                w.status[cursor] = "frozen"
            elif (
                extras
                and w.run >= SAVE_MIN_RUN
                and (last_save is None or (cursor - last_save).days >= SAVE_EVERY)
            ):
                last_save = cursor
                w.status[cursor] = "saved"
            else:
                repair = (
                    _repair(minutes, cursor, today, weekdays, start)
                    if extras
                    and w.run > 0
                    and (last_repair is None or (cursor - last_repair).days >= REPAIR_EVERY)
                    else "no"
                )
                if repair == "repaired":
                    last_repair = cursor
                    w.status[cursor] = "repaired"
                    w.repaired_today = min(d for d in studied if d > cursor) == today
                else:
                    if repair == "pending":
                        w.earn_back = {
                            "missed": cursor.isoformat(),
                            "by": (cursor + timedelta(days=REPAIR_WINDOW)).isoformat(),
                            "keep": w.run,
                            "minutes": REPAIR_MINUTES,
                            "done_today": minutes.get(today, 0),
                        }
                    w.run = 0
                    w.status[cursor] = "missed"
        else:
            w.status[cursor] = "rest" if cursor >= start else "none"
        if cursor.weekday() == 6:  # Sunday closes the week
            monday = cursor - timedelta(days=6)
            if _week_goal_met(minutes, monday, weekdays, start, daily_goal):
                w.freezes = min(FREEZE_CAP, w.freezes + 1)
        cursor += timedelta(days=1)
    if w.earn_back and w.run:  # studied again since, below the bar: the offer has lapsed
        w.earn_back = None
    w.status[today] = "studied" if today in studied else "today"
    return w


def compute(
    minutes: dict[date, int],
    today: date,
    weekdays: set[int],
    start: date,
    daily_goal: int,
    extras: bool | None = None,
) -> dict:
    """`minutes`: local day -> minutes studied (a day with any activity counts as studied)."""
    extras = EXTRAS if extras is None else extras
    w = walk(minutes, today, weekdays, start, daily_goal, extras)
    current = w.run + (1 if today in minutes else 0)
    monday = today - timedelta(days=today.weekday())
    week_days = [monday + timedelta(days=i) for i in range(7)]
    week_goal = daily_goal * sum(1 for d in week_days if d >= start and d.weekday() in weekdays)
    recent = sorted(d for d in w.status if (today - d).days <= 14)
    out = {
        "current": current,
        "longest": max(w.longest, current),
        "studied_today": today in minutes,
        "freezes": w.freezes,
        "frozen": [d.isoformat() for d in recent if w.status[d] == "frozen"],
        "week_minutes": sum(minutes.get(d, 0) for d in week_days if d <= today),
        "week_goal": week_goal,
    }
    if extras:
        out["saved"] = [d.isoformat() for d in recent if w.status[d] == "saved"]
        out["repaired"] = [d.isoformat() for d in recent if w.status[d] == "repaired"]
        out["earn_back"] = w.earn_back
        out["repaired_today"] = w.repaired_today
    return out


def calendar(
    minutes: dict[date, int],
    today: date,
    weekdays: set[int],
    start: date,
    daily_goal: int,
    month: date,
) -> list[dict]:
    """Every day of ``month``'s calendar month with its streak status: studied, frozen,
    saved, repaired, missed, rest, today, planned, future or none (before the first study)."""
    w = walk(minutes, today, weekdays, start, daily_goal, EXTRAS)
    began = min(minutes) if minutes else today  # no streak can break before the first study
    first = month.replace(day=1)
    days = []
    cursor = first
    while cursor.month == first.month:
        status = w.status.get(cursor) or ("future" if cursor > today else "none")
        if status in {"missed", "rest"} and cursor < began:
            status = "none"
        if status == "future" and cursor.weekday() in weekdays:
            status = "planned"
        days.append(
            {"day": cursor.isoformat(), "status": status, "minutes": minutes.get(cursor, 0)}
        )
        cursor += timedelta(days=1)
    return days


def days_away(studied: set[date], today: date, weekdays: set[int], start: date) -> int:
    """Scheduled study days missed since the learner last studied (0 when active)."""
    if not studied:
        return 0
    last = max(d for d in studied if d <= today) if any(d <= today for d in studied) else None
    if last is None:
        return 0
    missed, cursor = 0, last + timedelta(days=1)
    while cursor < today:
        if cursor.weekday() in weekdays and cursor >= start:
            missed += 1
        cursor += timedelta(days=1)
    return missed
