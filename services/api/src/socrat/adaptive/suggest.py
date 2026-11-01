"""Turn what the planner sees into roadmap changes Socrat wants to *propose*.

Pure: given the plan and the learner's signals, return drafts. ``proposals.sync`` stores
the new ones as pending; none of them changes anything until the learner accepts.
"""

import hashlib
import math
from dataclasses import dataclass, field
from datetime import date

from socrat.adaptive.stuck import Stuck, next_rung
from socrat.catalog.registry import Catalog
from socrat.planner import engine
from socrat.planner.engine import Plan

MINUTE_CHOICES = (15, 20, 30, 45, 60, 90, 120)
COMEBACK_DAYS = 7
REPLACE_SCORE = 0.9


@dataclass(frozen=True)
class Draft:
    kind: str
    key: str
    title: str
    reason: str
    payload: dict = field(default_factory=dict)
    group: str = ""


@dataclass(frozen=True)
class Signals:
    today: date
    minutes_per_day: int
    weekdays: tuple[int, ...]
    overrides: dict = field(default_factory=dict)
    stuck: dict[str, Stuck] = field(default_factory=dict)
    tried: dict[str, frozenset[str]] = field(default_factory=dict)
    days_away: int = 0
    recent_concepts: tuple[str, ...] = ()
    passed_checkpoint: tuple[str, float] | None = None  # (module key, score), recent
    weak_prereqs: dict[str, str] = field(default_factory=dict)  # concept -> weakest prereq


def drafts(catalog: Catalog, plan: Plan, s: Signals) -> list[Draft]:
    out: list[Draft] = []
    out += deadline(catalog, plan, s)
    out += doing_well(catalog, plan, s)
    out += stuck(catalog, plan, s)
    out += comeback(catalog, s)
    return out


def _title(catalog: Catalog, concept: str) -> str:
    return catalog.concept(concept).title


def deadline(catalog: Catalog, plan: Plan, s: Signals) -> list[Draft]:
    """B2: off track for the target date -> three alternatives; the learner picks one."""
    forecast = plan.forecast
    target = forecast.get("target_date")
    if not target or forecast.get("on_track") is not False:
        return []
    days_left = (date.fromisoformat(target) - s.today).days
    if days_left <= 0:
        return []
    adherence = float(forecast.get("adherence") or 1.0)
    capacity_weekly = s.minutes_per_day * len(s.weekdays) * adherence
    needed_weekly = plan.remaining_minutes / (days_left / 7) / adherence
    group = f"deadline:{target}"
    out: list[Draft] = []
    minutes = next((m for m in MINUTE_CHOICES if m * len(s.weekdays) >= needed_weekly), None)
    if minutes and minutes > s.minutes_per_day:
        out.append(
            Draft(
                "budget",
                f"deadline:minutes:{minutes}",
                f"Study {minutes} min per day to make {target}",
                f"At your current rhythm you'd finish {forecast['realistic_finish']}, after "
                f"your target of {target}.",
                {"minutes_per_day": minutes},
                group,
            )
        )
    if len(s.weekdays) < 7:
        days = math.ceil(needed_weekly / s.minutes_per_day)
        if len(s.weekdays) < days <= 7:
            extra = [d for d in (5, 6, 4, 2, 0, 1, 3) if d not in s.weekdays][
                : days - len(s.weekdays)
            ]
            out.append(
                Draft(
                    "budget",
                    f"deadline:days:{days}",
                    f"Study {days} days a week to make {target}",
                    f"Adding {len(extra)} study day(s) brings your finish in before {target}.",
                    {"weekdays": sorted(set(s.weekdays) | set(extra))},
                    group,
                )
            )
    capacity = capacity_weekly * days_left / 7
    candidates = sorted(
        (
            r
            for r in plan.roadmap
            if r["status"] in {"upcoming", "locked"} and r["relevance"] < 0.85
        ),
        key=lambda r: (r["relevance"], -r["minutes"], r["concept"]),
    )
    path = [r["concept"] for r in plan.roadmap]
    chosen: list[str] = []
    over = plan.remaining_minutes - capacity
    progress = True
    while over > 0 and progress:
        # A topic can go once nothing left on the path needs it; repeat as dependents go.
        progress = False
        for row in candidates:
            if over <= 0:
                break
            if row["concept"] in chosen:
                continue
            trial = engine.set_aside(catalog, path, {*chosen, row["concept"]})
            if row["concept"] in trial:
                chosen.append(row["concept"])
                over -= row["minutes"]
                progress = True
    if chosen and over <= 0:
        digest = hashlib.sha256(",".join(sorted(chosen)).encode()).hexdigest()[:10]
        names = ", ".join(_title(catalog, c) for c in chosen[:4])
        more = f" and {len(chosen) - 4} more" if len(chosen) > 4 else ""
        out.append(
            Draft(
                "skip",
                f"deadline:trim:{digest}",
                f"Drop {len(chosen)} lower-priority topic(s) to make {target}",
                f"Keeps what your goal needs most. Topics dropped: {names}{more}. "
                "You can add them back later.",
                {"concepts": chosen},
                group,
            )
        )
    if not out:
        # Nothing realistic closes the gap: say so, and offer a date the learner can make.
        later = date.fromisoformat(forecast["realistic_finish"])
        if later.isoformat() > target:
            out.append(
                Draft(
                    "goal",
                    f"deadline:date:{later.isoformat()}",
                    f"Move your target date to {later.isoformat()}",
                    f"Even a much bigger schedule would not cover the whole path by {target}. "
                    f"{later.isoformat()} is realistic at your current rhythm; you can also "
                    "keep the date and focus on what matters most.",
                    {"target_date": later.isoformat()},
                    group,
                )
            )
    return out


def doing_well(catalog: Catalog, plan: Plan, s: Signals) -> list[Draft]:
    """C1, C3, C4: offer to skip ahead when results say the learner is ready."""
    out: list[Draft] = []
    accelerating = plan.pace == "fast" or plan.style == "fast_track"
    if accelerating:
        nxt = next(
            (
                r
                for r in plan.roadmap
                if r["status"] == "upcoming" and r["mastery"] <= 0.5 and not r["deferred"]
            ),
            None,
        )
        if nxt is not None and nxt["concept"] not in s.overrides.get("testout", []):
            out.append(
                Draft(
                    "test_out",
                    f"testout:{nxt['concept']}",
                    f"Test out of {nxt['title']}",
                    "Your recent results are strong. Pass a short, hard check and you skip "
                    "straight past it; miss and nothing is lost.",
                    {"target": nxt["concept"]},
                )
            )
    if plan.pace == "fast" and not s.overrides.get("stretch"):
        out.append(
            Draft(
                "stretch",
                "stretch",
                "Add a weekly stretch problem",
                "You're solving at your level comfortably. One harder problem a week builds "
                "range faster.",
            )
        )
    if s.passed_checkpoint and s.passed_checkpoint[1] >= REPLACE_SCORE:
        module_key = s.passed_checkpoint[0]
        course_id = module_key.split(":", 1)[0]
        keys = [f"{course_id}:{m.id}" for m in catalog.course(course_id).modules]
        if module_key in keys and keys.index(module_key) + 1 < len(keys):
            following = keys[keys.index(module_key) + 1]
            started = any(
                r["module"] == following and r["status"] not in {"upcoming", "locked"}
                for r in plan.roadmap
            )
            if not started:
                out.append(
                    Draft(
                        "test_out",
                        f"testout:module:{following}",
                        f"Test out of {engine.module_title(catalog, following)}",
                        f"You aced the {engine.module_title(catalog, module_key)} checkpoint. "
                        "If the next module is familiar too, a placement check can skip it.",
                        {"target": f"module:{following}"},
                    )
                )
    return out


def stuck(catalog: Catalog, plan: Plan, s: Signals) -> list[Draft]:
    """D1-D3: the next roadmap-level rung of the intervention ladder, per stuck concept."""
    out: list[Draft] = []
    proposed: set[str] = set()
    for concept, signal in sorted(s.stuck.items()):
        weak = s.weak_prereqs.get(concept)
        rung = next_rung(
            signal,
            set(s.tried.get(concept, ())),
            weak is not None,
            bool(catalog.prerequisites.get(concept)),
        )
        if rung is None or not rung[1]:
            continue
        name = _title(catalog, concept)
        if rung[0] == "probe":
            out.append(
                Draft(
                    "probe",
                    f"probe:{concept}",
                    f"Quick check of the foundations under {name}",
                    f"{signal.summary} A 10-minute check of its prerequisites finds the real gap.",
                    {"concept": concept},
                )
            )
        elif rung[0] == "repair" and weak:
            proposed.add(concept)
            out.append(_repair(catalog, concept, weak, signal.summary))
        elif rung[0] == "defer":
            out.append(
                Draft(
                    "defer",
                    f"defer:{concept}",
                    f"Set {name} aside for now",
                    f"{signal.summary} Moving on and coming back later often makes it click.",
                    {"concept": concept},
                )
            )
    for concept, weak in sorted(plan.needs_repair.items()):
        if concept not in proposed and concept not in s.stuck:
            out.append(_repair(catalog, concept, weak, "Several attempts missed in a row."))
    return out


def _repair(catalog: Catalog, concept: str, weak: str, why: str) -> Draft:
    return Draft(
        "repair",
        f"repair:{weak}:{concept}",
        f"Refresh {_title(catalog, weak)} before more {_title(catalog, concept)}",
        f"{why} {_title(catalog, concept)} builds on {_title(catalog, weak)}, which looks shaky.",
        {"concept": weak, "for": concept},
    )


def comeback(catalog: Catalog, s: Signals) -> list[Draft]:
    """E5: after a long break, a short re-check and a gentler week."""
    if s.days_away < COMEBACK_DAYS or not s.recent_concepts:
        return []
    names = ", ".join(_title(catalog, c) for c in s.recent_concepts[:2])
    return [
        Draft(
            "comeback",
            f"comeback:{s.today.isoformat()}",
            "Ease back in with a quick re-check",
            f"Welcome back after {s.days_away} days. A short check on {names} shows what "
            "stuck, and this week runs at a gentler pace.",
            {"concepts": list(s.recent_concepts[:2])},
        )
    ]
