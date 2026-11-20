"""Request -> course: serve a compatible existing course, or say why one has to be built.

Candidates are found by plain SQL (same root, published, in good standing, shareable). The
decision is code over two specs (``compatible``): every hard check must pass. No similarity
score can authorise serving a course. The decision, every candidate and each check's result are
written to ``course_matches`` (one row per request), so "why did this learner get this course"
is one query.
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.coursegen.brain import roots
from socrat.coursegen.brain.spec import (
    CHILD_REGISTERS,
    LEVELS,
    VERSION,
    CourseSpec,
    derive,
    is_private,
    overlay,
)
from socrat.models import CourseMatch, GeneratedCourse, LearningRequest, now

SERVED = ("reuse", "reuse_adapted")
BUILT = ("from_material", "extend_and_new", "new", "private_new")
BANDS = ("bite", "standard", "long")


@dataclass
class Decision:
    outcome: str  # SERVED or BUILT
    course_id: str | None
    reason: str
    spec: CourseSpec
    candidates: list[dict] = field(default_factory=list)
    adaptations: list[str] = field(default_factory=list)
    units: list[str] = field(default_factory=list)  # root unit refs a built course is made from

    @property
    def served(self) -> bool:
        return self.outcome in SERVED and self.course_id is not None


def _level(value: str) -> int:
    return LEVELS.index(value) if value in LEVELS else 0


def compatible(child: CourseSpec, wanted: CourseSpec) -> dict[str, tuple[str, str]]:
    """field -> ("pass" | "fail", why). Serving needs every field to pass."""
    out: dict[str, tuple[str, str]] = {}

    def same(name: str, a, b) -> None:
        out[name] = ("pass", "") if a == b else ("fail", f"asked {b!r}, course has {a!r}")

    same("root", child.root, wanted.root)
    same("topic", child.topic, wanted.topic)
    same("depth", child.depth, wanted.depth)
    # The course may assume less than the learner knows (placement skips ahead), never more.
    out["entry"] = (
        ("pass", "")
        if _level(child.entry) <= _level(wanted.entry)
        else ("fail", f"course assumes {child.entry}, learner is {wanted.entry}")
    )
    # A themed course never goes to someone who did not ask for that theme, and a request
    # for a theme is never met by a plain course.
    same("frame", child.frame, wanted.frame)
    same("assessment", child.assessment, wanted.assessment)
    same("rigor", child.rigor, wanted.rigor)
    out["mode"] = (
        ("fail", f"asked {wanted.mode!r}, course has {child.mode!r}")
        if child.mode and wanted.mode and child.mode != wanted.mode
        else ("pass", "")
    )
    # Short lessons pack into a longer session; a long lesson does not fit a short one.
    out["band"] = (
        ("pass", "")
        if BANDS.index(child.band) <= BANDS.index(wanted.band)
        else ("fail", f"lessons sized {child.band}, learner has {wanted.band} sessions")
    )
    same("language", child.language, wanted.language)
    reg_ok = child.audience == wanted.audience or not (
        {child.audience, wanted.audience} & CHILD_REGISTERS
    )
    out["audience"] = (
        ("pass", "") if reg_ok else ("fail", f"written for {child.audience}, not {wanted.audience}")
    )
    same("code_languages", child.code_languages, wanted.code_languages)
    return out


def adaptations(child: CourseSpec, wanted: CourseSpec) -> list[str]:
    """What the learner's own enrollment changes about a course that passed every check."""
    out = []
    if child.band != wanted.band:
        out.append(f"sessions: {wanted.band} (course lessons are {child.band})")
    if _level(wanted.entry) > _level(child.entry):
        out.append(f"start: placement from {wanted.entry}")
    if wanted.mode and not child.mode:
        out.append(f"mode: {wanted.mode} applied to pacing only")
    return out


def first_ready(course) -> bool:
    """The learner's first lesson is written and passed its gates."""
    order = [cid for m in course.modules for cid in m.concepts]
    start = course.levels[0].start_concept if course.levels else None
    first = start.split(":")[-1] if start else (order[0] if order else None)
    by_id = {c.id: c for c in course.concepts}
    return first is not None and first in by_id and by_id[first].status == "live"


def _creator_request(db: Session, row: GeneratedCourse) -> LearningRequest | None:
    return db.scalars(
        select(LearningRequest)
        .where(
            LearningRequest.course_id == row.id,
            LearningRequest.user_id == row.owner_id,
            LearningRequest.status == "confirmed",
        )
        .limit(1)
    ).first()


def spec_of(db: Session, row: GeneratedCourse) -> CourseSpec | None:
    """The stored spec, or one derived from the request that built it (courses shared before
    the brain existed). A derived spec is saved so the work is done once."""
    if row.spec:
        try:
            return CourseSpec.model_validate(row.spec)
        except ValueError:
            return None
    made = _creator_request(db, row)
    if made is None:
        return None
    from socrat import onboarding

    root = roots.resolve(db, roots.name_for(made.intent), made.id)
    spec = derive(made.text, made.intent, root.id, onboarding.profile_for(db, made.id))
    row.root_id, row.spec, row.spec_key = root.id, spec.model_dump(mode="json"), spec.key()
    return spec


def candidates(db: Session, root_id: str) -> list[GeneratedCourse]:
    """Courses the brain may serve: published, in good standing, learner-made, and either
    marked shareable by the brain or shared by their creator (community courses). Private
    courses are never candidates."""
    return list(
        db.scalars(
            select(GeneratedCourse).where(
                GeneratedCourse.status == "published",
                GeneratedCourse.moderation == "ok",
                GeneratedCourse.owner_id.is_not(None),
                ((GeneratedCourse.root_id == root_id) & (GeneratedCourse.serve == "shared"))
                | (
                    # community courses: their root is derived on first sight (spec_of)
                    (GeneratedCourse.visibility == "public")
                    & GeneratedCourse.serve.is_(None)
                    & (GeneratedCourse.root_id.is_(None) | (GeneratedCourse.root_id == root_id))
                ),
            )
        )
    )


def decide(db: Session, catalog, user_id: str, wanted: CourseSpec, private: bool) -> Decision:
    if private:
        return Decision(
            "private_new",
            None,
            "the request carries personal context: built for this learner only",
            wanted,
        )
    audit: list[dict] = []
    passing: list[tuple] = []
    rows = candidates(db, wanted.root)
    from socrat.coursegen.brain import units as unitstore

    withdrawn = unitstore.courses_on_quarantined_units(db, [r.id for r in rows])
    for row in rows:
        spec = spec_of(db, row)
        entry: dict = {"course": row.id}
        if spec is None:
            audit.append(entry | {"eligible": False, "why": "no spec could be derived"})
            continue
        if spec.root != wanted.root:
            continue  # a community course of another subject: not a candidate at all
        course = catalog.courses.get(row.id)
        checks = compatible(spec, wanted)
        entry["checks"] = {k: list(v) for k, v in checks.items()}
        failed = [k for k, (verdict, _) in checks.items() if verdict != "pass"]
        if course is None:
            entry |= {"eligible": False, "why": "not in the catalog (invalid or hidden)"}
        elif not first_ready(course):
            entry |= {"eligible": False, "why": "first lesson not ready"}
        elif row.id in withdrawn:
            entry |= {"eligible": False, "why": "written from a withdrawn (quarantined) unit"}
        else:
            entry["eligible"] = True
        entry["passed"] = not failed and entry["eligible"]
        if failed:
            entry["failed"] = failed
        audit.append(entry)
        if entry["passed"]:
            ready = sum(c.status == "live" for c in course.concepts)
            exact = spec.key() == wanted.key()
            passing.append(
                ((not exact, row.owner_id != user_id, -ready, row.created_at), row, spec)
            )
    if passing:
        passing.sort(key=lambda t: t[0])
        _, row, spec = passing[0]
        changes = adaptations(spec, wanted)
        outcome = "reuse_adapted" if changes else "reuse"
        why = f"every hard check passed against {row.id}" + (
            "; exact spec" if spec.key() == wanted.key() else ""
        )
        return Decision(outcome, row.id, why, wanted, audit, changes)
    reason = "no candidate under this subject" if not audit else "no candidate passed every check"
    return Decision("new", None, reason, wanted, audit)


def route(db: Session, catalog, user_id: str, row: LearningRequest, intent: dict) -> Decision:
    """Decide for one request and record it. Idempotent per request (``course_matches`` is
    unique on ``request_id``): routing again replaces the earlier, unsettled decision."""
    from socrat import onboarding

    profile = onboarding.profile_for(db, row.id)
    root = roots.resolve(db, roots.name_for(intent), row.id)
    wanted = derive(row.text, intent, root.id, profile)
    decision = decide(db, catalog, user_id, wanted, is_private(row.text, row.material))
    if not decision.served:
        # Root material: reuse the topic's validated unit, or research it once (canonical
        # topic only, never the learner's words). A private course reads shared units too.
        from socrat.coursegen.brain import units as unitstore

        key = unitstore.key_of(wanted.topic, wanted.depth)
        unit, job = unitstore.ensure(db, root.id, key, decision.spec.model_dump(), user_id)
        if unit is not None or job is not None:
            decision.units = [unitstore.ref(root.id, key)]
        if decision.outcome == "new":
            decision.outcome = (
                "from_material"
                if unit is not None and job is None
                else "extend_and_new"
                if job is not None
                else "new"
            )
    match = db.scalar(select(CourseMatch).where(CourseMatch.request_id == row.id))
    if match is None:
        match = CourseMatch(request_id=row.id, user_id=user_id)
        db.add(match)
    match.root_id = root.id
    match.spec = wanted.model_dump(mode="json")
    match.spec_key = wanted.key()
    match.outcome = decision.outcome
    match.course_id = decision.course_id
    match.reason = decision.reason[:500]
    match.candidates = decision.candidates
    match.adaptations = decision.adaptations
    match.units = decision.units
    match.private = overlay(row.text, intent, profile)
    match.matcher_version = VERSION
    match.created_at = now()
    db.flush()
    return decision


def built(db: Session, request_id: str, course_id: str) -> None:
    """A request that was not served now has its own course id (the outline is queued)."""
    match = db.scalar(select(CourseMatch).where(CourseMatch.request_id == request_id))
    if match is not None:
        match.course_id = course_id
        db.flush()


def attach(db: Session, course_id: str) -> None:
    """At publish: stamp the course with the root and spec of the request that built it, so
    the next compatible request can be served it. A private request's course stays private."""
    match = db.scalar(
        select(CourseMatch).where(
            CourseMatch.course_id == course_id, CourseMatch.outcome.in_(BUILT)
        )
    )
    row = db.get(GeneratedCourse, course_id)
    if match is None or row is None:
        return
    row.root_id, row.spec, row.spec_key = match.root_id, match.spec, match.spec_key
    row.serve = "private" if match.outcome == "private_new" else "shared"


def granted(db: Session, user_id: str, course_id: str) -> CourseMatch | None:
    """The decision that gave this learner this course, if the brain served or built it."""
    return db.scalars(
        select(CourseMatch)
        .where(CourseMatch.user_id == user_id, CourseMatch.course_id == course_id)
        .order_by(CourseMatch.created_at.desc())
    ).first()
