"""Roadmap changes Socrat proposes and the learner decides.

Socrat never changes the roadmap on its own. The planner, the weekly review and the tutor
can only *propose*; a pending proposal does nothing. Accepting applies it to the
enrollment's overrides (or schedule/goal), logs an explained plan revision, and retires
the alternatives in its group. Declining is remembered so the same idea is not re-asked
for a while. All writes happen in the caller's transaction.
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.adaptive.suggest import Draft
from socrat.catalog.registry import Catalog
from socrat.mastery.model import DAY
from socrat.models import Enrollment, PlanProposal, User
from socrat.planner import gates, goals

KINDS = {
    "repair",
    "bridge",
    "probe",
    "test_out",
    "defer",
    "skip",
    "prioritize",
    "budget",
    "stretch",
    "path_style",
    "comeback",
    "goal",
}
# Kinds whose effect lives in ``overrides`` and that a learner may undo from the roadmap.
UNDOABLE = {"defer", "skip", "prioritize", "stretch"}
DECLINE_COOLDOWN = 14 * DAY
MAX_PENDING = 6
MAX_PRIORITY = 3
MINUTES = {15, 20, 30, 45, 60, 90, 120}
ROLES = {"internship", "new-grad", "mid-level", "senior"}


def view(row: PlanProposal) -> dict:
    return dict(
        id=row.id,
        kind=row.kind,
        title=row.title,
        reason=row.reason,
        payload=row.payload,
        group=row.group,
        source=row.source,
        status=row.status,
        created_at=row.created_at,
        decided_at=row.decided_at,
    )


def pending(db: Session, enrollment: Enrollment) -> list[PlanProposal]:
    return list(
        db.scalars(
            select(PlanProposal)
            .where(PlanProposal.enrollment_id == enrollment.id, PlanProposal.status == "pending")
            .order_by(PlanProposal.created_at, PlanProposal.id)
        )
    )


def history(db: Session, enrollment: Enrollment, limit: int = 20) -> list[PlanProposal]:
    return list(
        db.scalars(
            select(PlanProposal)
            .where(PlanProposal.enrollment_id == enrollment.id, PlanProposal.status != "pending")
            .order_by(PlanProposal.decided_at.desc(), PlanProposal.id)
            .limit(limit)
        )
    )


def _blocked(db: Session, enrollment: Enrollment, draft: Draft, now: int) -> bool:
    rows = db.scalars(
        select(PlanProposal).where(
            PlanProposal.enrollment_id == enrollment.id,
            (PlanProposal.key == draft.key)
            | ((PlanProposal.group == draft.group) & (PlanProposal.group != "")),
        )
    )
    for row in rows:
        if row.key == draft.key and row.status in {"pending", "accepted"}:
            return True
        if row.status == "declined" and (row.decided_at or 0) > now - DECLINE_COOLDOWN:
            return True
        if row.group and row.group == draft.group and row.status == "accepted":
            return True
    return False


def add(
    db: Session, enrollment: Enrollment, draft: Draft, source: str, now: int
) -> PlanProposal | None:
    """Store a draft as pending unless it is already pending, done, or recently declined."""
    if draft.kind not in KINDS:
        raise ValueError(f"unknown proposal kind {draft.kind}")
    if _blocked(db, enrollment, draft, now):
        return None
    row = PlanProposal(
        enrollment_id=enrollment.id,
        kind=draft.kind,
        key=draft.key,
        group=draft.group,
        title=draft.title[:200],
        reason=draft.reason[:1000],
        payload=draft.payload,
        source=source,
        status="pending",
        created_at=now,
    )
    db.add(row)
    db.flush()
    return row


def sync(db: Session, enrollment: Enrollment, drafts: list[Draft], now: int) -> list[PlanProposal]:
    """Planner suggestions -> pending proposals. Stale planner proposals expire."""
    keys = {d.key for d in drafts}
    current = pending(db, enrollment)
    for row in current:
        if row.source == "planner" and row.key not in keys:
            row.status, row.decided_at = "expired", now
    open_count = sum(1 for r in current if r.status == "pending")
    created = []
    for draft in drafts:
        if open_count >= MAX_PENDING:
            break
        if draft.kind == "bridge":  # only the owner of a generated course may change it
            from socrat.models import GeneratedCourse

            meta = db.get(GeneratedCourse, enrollment.course_id)
            if meta is None or meta.owner_id != enrollment.user_id:
                continue
        new = add(db, enrollment, draft, "planner", now)
        if new is not None:
            created.append(new)
            open_count += 1
    return created


def validate(catalog: Catalog, enrollment: Enrollment, kind: str, payload: dict) -> dict:
    """Check a proposal's payload (the tutor's in particular) before it is stored."""
    scope = set(catalog.closure(catalog.course_concepts(enrollment.course_id)))

    def concept(key: str) -> str:
        value = str(payload.get(key, ""))
        if value not in scope:
            raise HTTPException(422, "invalid_proposal")
        return value

    if kind in {"probe", "defer", "prioritize"}:
        return {"concept": concept("concept")}
    if kind in {"repair", "bridge"}:
        weak, target = concept("concept"), concept("for")
        if weak not in catalog.closure([target]) or weak == target:
            raise HTTPException(422, "invalid_proposal")
        return {"concept": weak, "for": target}
    if kind == "test_out":
        target = str(payload.get("target", ""))
        if target.startswith("module:"):
            if target.removeprefix("module:") not in gates.module_keys(
                catalog, enrollment.course_id
            ):
                raise HTTPException(422, "invalid_proposal")
            return {"target": target}
        return {"target": concept("target")}
    if kind == "skip":
        values = [str(c) for c in payload.get("concepts", [])][:12]
        if not values or any(c not in scope for c in values):
            raise HTTPException(422, "invalid_proposal")
        return {"concepts": values}
    if kind == "budget":
        out: dict = {}
        if payload.get("minutes_per_day") is not None:
            if payload["minutes_per_day"] not in MINUTES:
                raise HTTPException(422, "invalid_proposal")
            out["minutes_per_day"] = int(payload["minutes_per_day"])
        if payload.get("weekdays") is not None:
            days = sorted({int(d) for d in payload["weekdays"]})
            if not days or any(d not in range(7) for d in days):
                raise HTTPException(422, "invalid_proposal")
            out["weekdays"] = days
        if not out:
            raise HTTPException(422, "invalid_proposal")
        return out
    if kind == "path_style":
        if payload.get("style") not in goals.STYLES:
            raise HTTPException(422, "invalid_proposal")
        return {"style": payload["style"]}
    if kind == "goal":
        out = {}
        if payload.get("target_role") in ROLES:
            out["target_role"] = payload["target_role"]
        if isinstance(payload.get("target_rating"), int) and 0 < payload["target_rating"] <= 4000:
            out["target_rating"] = payload["target_rating"]
        if isinstance(payload.get("target_date"), str) and len(payload["target_date"]) == 10:
            out["target_date"] = payload["target_date"]
        focus = [str(c) for c in payload.get("focus", []) if str(c) in scope][:MAX_PRIORITY]
        if focus:
            out["focus"] = focus
        if isinstance(payload.get("motivation"), str):
            out["motivation"] = payload["motivation"][:280]
        if not out:
            raise HTTPException(422, "invalid_proposal")
        return out
    if kind in {"stretch", "comeback"}:
        return {k: v for k, v in payload.items() if k == "concepts"}
    raise HTTPException(422, "invalid_proposal")


def apply(enrollment: Enrollment, row: PlanProposal, now: int) -> str:
    """Make an accepted proposal real. Returns the plan-revision reason."""
    adaptive = dict(enrollment.adaptive or {})
    overrides = dict(adaptive.get("overrides", {}))
    payload = row.payload

    def append(key: str, value) -> None:
        items = list(overrides.get(key, []))
        if value not in items:
            items.append(value)
        overrides[key] = items

    if row.kind == "repair":
        append("repair", [payload["concept"], payload["for"]])
    elif row.kind == "probe":
        append("probe", payload["concept"])
    elif row.kind == "test_out":
        append("testout", payload["target"])
    elif row.kind == "defer":
        append("defer", payload["concept"])
    elif row.kind == "skip":
        for concept in payload["concepts"]:
            append("skip", concept)
    elif row.kind == "prioritize":
        append("priority", payload["concept"])
        overrides["priority"] = overrides["priority"][-MAX_PRIORITY:]
    elif row.kind == "stretch":
        overrides["stretch"] = True
    elif row.kind == "comeback":
        overrides["comeback"] = {"until": now + 7 * DAY, "concepts": payload.get("concepts", [])}
    elif row.kind == "path_style":
        adaptive["style"] = payload["style"]
    elif row.kind == "budget":
        if "minutes_per_day" in payload:
            enrollment.minutes_per_day = payload["minutes_per_day"]
        if "weekdays" in payload:
            enrollment.weekdays = payload["weekdays"]
    elif row.kind == "goal":
        goal = dict(enrollment.goal or {})
        for key in ("target_role", "target_rating", "target_date", "motivation"):
            if key in payload:
                goal[key] = payload[key]
        enrollment.goal = goal
        for concept in payload.get("focus", []):
            append("priority", concept)
        if "priority" in overrides:
            overrides["priority"] = overrides["priority"][-MAX_PRIORITY:]
    adaptive["overrides"] = overrides
    enrollment.adaptive = adaptive
    return f"You approved: {row.title}."


def undo(enrollment: Enrollment, kind: str, concept: str) -> bool:
    """The learner takes back a roadmap override (add a topic back, unpin a focus...)."""
    adaptive = dict(enrollment.adaptive or {})
    overrides = dict(adaptive.get("overrides", {}))
    key = {"defer": "defer", "skip": "skip", "prioritize": "priority"}.get(kind)
    if kind == "stretch":
        changed = bool(overrides.pop("stretch", False))
    elif key is None or concept not in overrides.get(key, []):
        return False
    else:
        overrides[key] = [c for c in overrides[key] if c != concept]
        changed = True
    adaptive["overrides"] = overrides
    enrollment.adaptive = adaptive
    return changed


def decide(
    db: Session,
    catalog: Catalog,
    user: User,
    enrollment: Enrollment,
    proposal_id: str,
    accept: bool,
    now: int,
) -> PlanProposal:
    from socrat.learn import service as learn

    row = db.get(PlanProposal, proposal_id)
    if row is None or row.enrollment_id != enrollment.id:
        raise HTTPException(404, "not_found")
    if row.status != "pending":
        raise HTTPException(409, "proposal_already_decided")
    row.status, row.decided_at = ("accepted" if accept else "declined"), now
    if not accept:
        return row
    reason = apply(enrollment, row, now)
    if row.kind == "bridge":
        from socrat.catalog.registry import default_catalog
        from socrat.coursegen import evolve

        try:
            evolve.insert_bridge(
                db,
                default_catalog(),
                catalog,
                enrollment.course_id,
                row.payload["for"],
                row.payload["concept"],
                row.reason,
                user.id,
            )
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
    if row.group:
        for other in pending(db, enrollment):
            if other.group == row.group and other.id != row.id:
                other.status, other.decided_at = "superseded", now
    learn.revise(db, catalog, user, enrollment, now, reason)
    return row
