import time
import uuid

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def need[T](value: T | None, what: str = "row") -> T:
    """``value``, which the caller knows exists (a row it just queued, a course it owns).
    Raises LookupError instead of failing later on ``None``."""
    if value is None:
        raise LookupError(f"{what} not found")
    return value


def identifier() -> str:
    return str(uuid.uuid4())


def now() -> int:
    return int(time.time())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("issuer", "subject"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    issuer: Mapped[str] = mapped_column(String(512))
    subject: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(80), default="")
    birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    # When the learner finished or skipped the first-run tour of the app; null until then.
    tour_seen_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Verified Google email, kept only for accounts on SOCRAT_ADMIN_EMAILS; null for learners.
    admin_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    # Lowercased, verified (an emailed code, or Google's email_verified); links sign-in methods.
    email: Mapped[str | None] = mapped_column(String(254), nullable=True, unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Share code for the referral link; made the first time the learner opens Invite friends.
    referral_code: Mapped[str | None] = mapped_column(String(12), nullable=True, unique=True)
    # Opt-in study reminder emails; ``reminders_unanswered`` counts those sent with no study since.
    reminders: Mapped[bool] = mapped_column(Boolean, default=False)
    locale: Mapped[str] = mapped_column(String(16), default="en")  # BCP-47, see socrat.localize
    reminder_sent_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reminders_unanswered: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf_token: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[int] = mapped_column(Integer, index=True)


class EmailCode(Base):
    """A one-time code emailed to confirm a sign-up or a password reset."""

    __tablename__ = "email_codes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    email: Mapped[str] = mapped_column(String(254), index=True)
    purpose: Mapped[str] = mapped_column(String(16))  # signup | reset
    code_hash: Mapped[str] = mapped_column(String(64))
    # Sign-up only: the chosen password and name, applied once the code is confirmed.
    password_hash: Mapped[str] = mapped_column(String(200), default="")
    display_name: Mapped[str] = mapped_column(String(80), default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class Enrollment(Base):
    """A learner's goal in one course. Exactly one enrollment per user is active."""

    __tablename__ = "enrollments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[str] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(16))
    level_id: Mapped[str] = mapped_column(String(64))
    goal: Mapped[dict] = mapped_column(JSON, default=dict)
    minutes_per_day: Mapped[int] = mapped_column(Integer)
    weekdays: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(16), default="placement")  # placement|active
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    placement: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    plan_signature: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    # Learner-approved roadmap overrides, path style and adaptive bookkeeping
    # (see socrat.adaptive.proposals). Only an accepted proposal or the learner writes here.
    adaptive: Mapped[dict] = mapped_column(JSON, default=dict)


class ConceptState(Base):
    __tablename__ = "concept_states"
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), primary_key=True
    )
    concept: Mapped[str] = mapped_column(String(160), primary_key=True)
    state: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class Evidence(Base):
    """Append-only scored learning evidence; the only input that changes mastery."""

    __tablename__ = "evidence"
    __table_args__ = (Index("ix_evidence_enrollment_created", "enrollment_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    enrollment_id: Mapped[str] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"))
    concept: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(16))
    score: Mapped[float] = mapped_column(Float)
    assistance: Mapped[int] = mapped_column(Integer, default=0)
    activity_id: Mapped[str] = mapped_column(String(200))
    elapsed_seconds: Mapped[int] = mapped_column(Integer, default=0)
    expected_seconds: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    seq: Mapped[int] = mapped_column(BigInteger, default=time.time_ns)


class LearningSession(Base):
    """A local-day session with pinned blocks, server-owned answers and a truthful summary."""

    __tablename__ = "learning_sessions"
    __table_args__ = (UniqueConstraint("enrollment_id", "day"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    day: Mapped[str] = mapped_column(String(10))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    finished_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": revision}


class ContentIssue(Base):
    __tablename__ = "content_issues"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    concept: Mapped[str] = mapped_column(String(160))
    atom_id: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(24))
    note: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class ActivityRecord(Base):
    """Start/completion of a plan activity (lesson, quiz, problem, checkpoint, review)."""

    __tablename__ = "activity_records"
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), primary_key=True
    )
    activity_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    started_at: Mapped[int] = mapped_column(Integer, default=now)
    completed_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[dict] = mapped_column(JSON, default=dict)


class QuizSession(Base):
    __tablename__ = "quiz_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    activity_id: Mapped[str] = mapped_column(String(200))
    items: Mapped[list] = mapped_column(JSON)  # [[qualified concept, item id], ...]
    answers: Mapped[dict] = mapped_column(JSON, default=dict)  # item id -> {choice, correct}
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    completed_at: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PlanRevision(Base):
    __tablename__ = "plan_revisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    pace: Mapped[str] = mapped_column(String(16))
    reasons: Mapped[list] = mapped_column(JSON)
    remaining_minutes: Mapped[int] = mapped_column(Integer)
    projected_finish: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    snapshot: Mapped[list] = mapped_column(JSON, default=list)  # queued activity ids
    changes: Mapped[dict] = mapped_column(JSON, default=dict)  # {added, removed} vs previous


class PlanProposal(Base):
    """A roadmap change Socrat wants to make. Nothing changes until the learner accepts it."""

    __tablename__ = "plan_proposals"
    __table_args__ = (Index("ix_plan_proposals_enrollment_status", "enrollment_id", "status"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    enrollment_id: Mapped[str] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(24))
    key: Mapped[str] = mapped_column(String(240))  # dedupe key, e.g. "repair:dsa:sorting"
    group: Mapped[str] = mapped_column(String(64), default="")  # alternatives share a group
    title: Mapped[str] = mapped_column(String(200))
    reason: Mapped[str] = mapped_column(String(1000))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(16))  # planner | tutor | review
    status: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    decided_at: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Draft(Base):
    __tablename__ = "drafts"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    problem_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    language: Mapped[str] = mapped_column(String(16), primary_key=True)
    source: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class Submission(Base):
    """A Run or Submit, doubling as the signed execution job for the worker."""

    __tablename__ = "submissions"
    __table_args__ = (Index("ix_submissions_status_created", "status", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    # None for verification jobs of the course generator (mode "verify"): no learner.
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    enrollment_id: Mapped[str | None] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=True
    )
    problem_id: Mapped[str] = mapped_column(String(64), index=True)
    language: Mapped[str] = mapped_column(String(16))
    mode: Mapped[str] = mapped_column(String(8))  # run|submit|verify
    source: Mapped[str] = mapped_column(Text)
    custom_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|running|done|failed
    verdict: Mapped[str] = mapped_column(String(24), default="")
    cases: Mapped[list] = mapped_column(JSON, default=list)
    passed: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    assistance: Mapped[int] = mapped_column(Integer, default=0)
    manifest: Mapped[dict] = mapped_column(JSON)
    signature: Mapped[str] = mapped_column(String(64))
    tests: Mapped[list] = mapped_column(JSON)
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_until: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    finished_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # A native re-run of a browser-judged submit: the id of the browser submission it confirms.
    recheck_of: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)


class JudgeWorker(Base):
    __tablename__ = "judge_workers"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    images: Mapped[list] = mapped_column(JSON)
    seen_at: Mapped[int] = mapped_column(Integer)


class AssistantThread(Base):
    __tablename__ = "assistant_threads"
    __table_args__ = (UniqueConstraint("user_id", "scope"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scope: Mapped[str] = mapped_column(String(200))  # general | problem:<id> | concept:<q>
    ladder: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class AssistantMessage(Base):
    __tablename__ = "assistant_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    thread_id: Mapped[str] = mapped_column(
        ForeignKey("assistant_threads.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))  # user|assistant
    content: Mapped[str] = mapped_column(Text)
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider: Mapped[str] = mapped_column(String(16), default="")
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)  # learner: +1 / -1
    created_at: Mapped[int] = mapped_column(Integer, default=now, index=True)
    # Strictly increasing order within a thread (several messages can share a second).
    seq: Mapped[int] = mapped_column(BigInteger, default=time.time_ns, index=True)


class PlaygroundJob(Base):
    """One visual generation, run by the worker so it outlives the request that asked for it."""

    __tablename__ = "playground_jobs"
    __table_args__ = (Index("ix_playground_jobs_status", "status", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # also the saved artifact's id
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    thread_id: Mapped[str] = mapped_column(ForeignKey("assistant_threads.id", ondelete="CASCADE"))
    prompt: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(16))
    language: Mapped[str] = mapped_column(String(32))
    mode: Mapped[str] = mapped_column(String(16), default="sketch")  # sketch | 3d
    status: Mapped[str] = mapped_column(String(16))  # queued|running|ready|failed|cancelled
    progress: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(String(64), default="")
    tries: Mapped[int] = mapped_column(Integer, default=0)
    heartbeat_at: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    # Fills the shared visual cache for everyone, so it is not charged to this learner's plan.
    shared: Mapped[bool] = mapped_column(Boolean, default=False)


class SharedVisual(Base):
    """One visual per concept, depth and language, generated once and shown to every learner.

    ``artifact_id`` is the saved artifact (an assistant message in the generating learner's
    playground thread); ``source_hash`` ties it to the lesson text it was made from, so an edited
    lesson is regenerated instead of served stale.
    """

    __tablename__ = "shared_visuals"
    concept: Mapped[str] = mapped_column(String(160), primary_key=True)
    level: Mapped[str] = mapped_column(String(16), primary_key=True)
    language: Mapped[str] = mapped_column(String(16), primary_key=True)
    status: Mapped[str] = mapped_column(String(16))  # generating|ready|failed|retired
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    artifact_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    source_hash: Mapped[str] = mapped_column(String(32), default="")
    reports: Mapped[list] = mapped_column(JSON, default=list)  # distinct learners who flagged it
    hits: Mapped[int] = mapped_column(Integer, default=0)  # times it was served without a new run
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class LessonVariant(Base):
    __tablename__ = "lesson_variants"
    concept: Mapped[str] = mapped_column(String(160), primary_key=True)
    language: Mapped[str] = mapped_column(String(16), primary_key=True)
    style: Mapped[str] = mapped_column(String(16), primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class DailyActivity(Base):
    __tablename__ = "daily_activity"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    day: Mapped[str] = mapped_column(String(10), primary_key=True)  # local YYYY-MM-DD
    activities: Mapped[int] = mapped_column(Integer, default=0)
    minutes: Mapped[int] = mapped_column(Integer, default=0)
    solved: Mapped[int] = mapped_column(Integer, default=0)
    # Last moment already credited as study time today; later credits start after it.
    counted_until: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    actor_id: Mapped[str] = mapped_column(String(36), index=True)
    kind: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    kind: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    delivered_at: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


class DeliveredEvent(Base):
    __tablename__ = "delivered_events"
    event_id: Mapped[str] = mapped_column(ForeignKey("outbox_events.id"), primary_key=True)
    delivered_at: Mapped[int] = mapped_column(Integer, default=now)


class PracticeMark(Base):
    """A learner's own status for an external (linked, not hosted) practice problem."""

    __tablename__ = "practice_marks"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    problem_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="todo")  # todo|attempted|solved
    bookmarked: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(16), default="self")  # self|codeforces
    opened_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    solved_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class LinkedAccount(Base):
    """A public competitive-programming profile the learner chose to link (handle only)."""

    __tablename__ = "linked_accounts"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    platform: Mapped[str] = mapped_column(String(16), primary_key=True)  # codeforces
    handle: Mapped[str] = mapped_column(String(64))
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank: Mapped[str] = mapped_column(String(40), default="")
    solved: Mapped[list] = mapped_column(JSON, default=list)  # problem ids, e.g. "cf:1873A"
    attempted: Mapped[list] = mapped_column(JSON, default=list)
    tag_stats: Mapped[dict] = mapped_column(JSON, default=dict)  # tag -> {solved, failed}
    synced_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sync_error: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class WeeklyAssessment(Base):
    """One personalised assessment per learner per ISO week, built from what they studied."""

    __tablename__ = "weekly_assessments"
    __table_args__ = (UniqueConstraint("enrollment_id", "iso_week"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    iso_week: Mapped[str] = mapped_column(String(10))  # e.g. 2026-W42, learner's local week
    concepts: Mapped[list] = mapped_column(JSON)  # [[qualified concept, reason]]
    items: Mapped[list] = mapped_column(JSON)  # [[qualified concept, item id]]
    coding: Mapped[list] = mapped_column(JSON, default=list)  # problem ids
    answers: Mapped[dict] = mapped_column(JSON, default=dict)  # item id -> {choice, correct}
    timed: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[int] = mapped_column(Integer, default=now)
    deadline: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finished_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    report: Mapped[dict] = mapped_column(JSON, default=dict)
    # Generated key -> {prompt, code, options, answer, explanation, edge}: hard questions
    # written for this exam and proven by running them (assessments/hard.py).
    generated: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class FocusSprint(Base):
    """A timed set of judged problems matched to the learner's level."""

    __tablename__ = "focus_sprints"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    problems: Mapped[list] = mapped_column(JSON)  # Socrat problem ids, easiest first
    started_at: Mapped[int] = mapped_column(Integer, default=now)
    deadline: Mapped[int] = mapped_column(Integer)
    finished_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    results: Mapped[dict] = mapped_column(JSON, default=dict)  # problem id -> seconds to solve


class ResourceEvent(Base):
    """A learner opening or rating a curated resource; ranks what each learner is shown."""

    __tablename__ = "resource_events"
    __table_args__ = (UniqueConstraint("user_id", "concept", "url"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    concept: Mapped[str] = mapped_column(String(160), index=True)
    url: Mapped[str] = mapped_column(String(512))
    opened_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    helpful: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class WebVital(Base):
    """One anonymous field measurement (no user, no session): powers performance budgets."""

    __tablename__ = "web_vitals"
    __table_args__ = (Index("ix_web_vitals_day_metric", "day", "metric"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    day: Mapped[str] = mapped_column(String(10))  # UTC date, enough for daily trends
    route: Mapped[str] = mapped_column(String(80))  # route pattern, never a concrete URL
    metric: Mapped[str] = mapped_column(String(8))  # LCP | INP | CLS | FCP | TTFB
    value: Mapped[float] = mapped_column(Float)
    device: Mapped[str] = mapped_column(String(8))  # mobile | desktop


class AIUsage(Base):
    """Tokens and estimated cost of one model call: powers the LLM budget and cost dashboard."""

    __tablename__ = "ai_usage"
    __table_args__ = (
        Index("ix_ai_usage_day", "day"),
        Index("ix_ai_usage_user_created", "user_id", "created_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    feature: Mapped[str] = mapped_column(String(24))  # tutor | lesson | playground
    provider: Mapped[str] = mapped_column(String(16))
    model: Mapped[str] = mapped_column(String(120))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    day: Mapped[str] = mapped_column(String(10))  # UTC date
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class ErrorReport(Base):
    """A grouped error (server exception, browser crash) or a learner's problem report."""

    __tablename__ = "error_reports"
    __table_args__ = (Index("ix_error_reports_status_last", "status", "last_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    source: Mapped[str] = mapped_column(String(16))  # server | browser | learner
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    message: Mapped[str] = mapped_column(Text)
    route: Mapped[str] = mapped_column(String(120), default="")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)  # stack, request id, release
    # Only learner reports name their author (so the owner can follow up).
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    count: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(12), default="open")  # open | resolved
    first_at: Mapped[int] = mapped_column(Integer, default=now)
    last_at: Mapped[int] = mapped_column(Integer, default=now)


# ---------------------------------------------------------------- adaptive quiz runtime
# Item definitions live in content files; only runtime state is stored here. Written by the
# adaptive quiz engine (behind adaptive_quiz_enabled) and the calibration job.


class QuizResponse(Base):
    """One answered quiz item; learner-scoped, erased with the account."""

    __tablename__ = "quiz_responses"
    __table_args__ = (Index("ix_quiz_responses_enrollment_created", "enrollment_id", "created_at"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    enrollment_id: Mapped[str] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"))
    item_id: Mapped[str] = mapped_column(String(200), index=True)
    family: Mapped[str] = mapped_column(String(200), default="")
    pattern: Mapped[str] = mapped_column(String(200), default="")
    concept: Mapped[str] = mapped_column(String(160))
    mode: Mapped[str] = mapped_column(String(24))  # placement | concept_check | review | ...
    pool: Mapped[str] = mapped_column(String(16))  # practice | assessment
    session_id: Mapped[str] = mapped_column(String(36), default="")
    correct: Mapped[bool] = mapped_column(Boolean)
    score: Mapped[float] = mapped_column(Float)  # 1.0 unassisted ... 0.0 wrong
    hint_level: Mapped[int] = mapped_column(Integer, default=0)
    time_s: Mapped[int] = mapped_column(Integer, default=0)
    seed: Mapped[str] = mapped_column(String(64), default="")
    choice: Mapped[int | None] = mapped_column(Integer, nullable=True)  # authored option index
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class LearnerAbility(Base):
    """Elo-style rating per learner and pattern; drives item selection, never mastery."""

    __tablename__ = "learner_abilities"
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), primary_key=True
    )
    pattern: Mapped[str] = mapped_column(String(200), primary_key=True)
    theta: Mapped[float] = mapped_column(Float)
    n: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class ItemRating(Base):
    """Current difficulty of a provisional item; frozen once the item is calibrated."""

    __tablename__ = "item_ratings"
    item_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    d_current: Mapped[float] = mapped_column(Float)
    n_responses: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class ItemCalibration(Base):
    """Item health from the calibration job. approved_by is set only by a named human."""

    __tablename__ = "item_calibrations"
    item_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    status: Mapped[str] = mapped_column(String(16))  # provisional | calibrated | retired
    n_responses: Mapped[int] = mapped_column(Integer, default=0)
    pct_correct: Mapped[float | None] = mapped_column(Float, nullable=True)
    discrimination: Mapped[float | None] = mapped_column(Float, nullable=True)
    distractor_counts: Mapped[dict] = mapped_column(JSON, default=dict)
    median_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    flags: Mapped[list] = mapped_column(JSON, default=list)
    computed_at: Mapped[int] = mapped_column(Integer, default=now)
    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    approved_at: Mapped[int | None] = mapped_column(Integer, nullable=True)


class QuizEngineSession(Base):
    """One adaptive quiz session: scope, served steps and the item awaiting an answer."""

    __tablename__ = "quiz_engine_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    mode: Mapped[str] = mapped_column(String(24))
    track: Mapped[str] = mapped_column(String(16))
    concepts: Mapped[list] = mapped_column(JSON)
    state: Mapped[dict] = mapped_column(JSON, default=dict)  # steps, pending, micro, stop
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    completed_at: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SkillPassport(Base):
    """A learner's shareable evidence page. Private until the learner turns it on."""

    __tablename__ = "skill_passports"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    slug: Mapped[str] = mapped_column(String(24), unique=True)
    public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class CompanySprint(Base):
    """A multi-week plan aimed at one company's interviews ("Amazon SDE-1 in 6 weeks").

    ``plan`` is frozen at the start (weekly skills and question ids) so the weeks stay
    stable; progress is computed live from mastery and solves.
    """

    __tablename__ = "company_sprints"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    company: Mapped[str] = mapped_column(String(80))
    company_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(16))
    weeks: Mapped[int] = mapped_column(Integer)
    started_on: Mapped[str] = mapped_column(String(10))
    ends_on: Mapped[str] = mapped_column(String(10))
    plan: Mapped[dict] = mapped_column(JSON)
    proposal_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    finished_at: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Subscription(Base):
    """A learner's paid plan. Paid access lasts until `current_end`; no row means Free."""

    __tablename__ = "subscriptions"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    plan: Mapped[str] = mapped_column(String(16))  # plus | pro
    interval: Mapped[str] = mapped_column(String(8))  # month | year
    currency: Mapped[str] = mapped_column(String(3))
    status: Mapped[str] = mapped_column(String(16), default="created")
    razorpay_subscription_id: Mapped[str] = mapped_column(String(64), unique=True)
    current_end: Mapped[int] = mapped_column(Integer, default=0)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    # An upgrade awaiting payment: "plan:interval:currency:razorpay_subscription_id".
    pending: Mapped[str | None] = mapped_column(String(96), nullable=True)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class Referral(Base):
    """Who invited whom. A learner can be referred once, by one referrer."""

    __tablename__ = "referrals"
    friend_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    referrer_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class ReferralReward(Base):
    """A ladder rung a learner reached. `granted_at` is null while it waits for a paid plan to end."""

    __tablename__ = "referral_rewards"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    rung: Mapped[str] = mapped_column(String(48), primary_key=True)
    earned_at: Mapped[int] = mapped_column(Integer, default=now)
    granted_at: Mapped[int | None] = mapped_column(Integer, nullable=True)


class BillingPlan(Base):
    """Razorpay plan ids, created on first use (key: plan:interval:currency)."""

    __tablename__ = "billing_plans"
    key: Mapped[str] = mapped_column(String(48), primary_key=True)
    razorpay_plan_id: Mapped[str] = mapped_column(String(64))


class GeneratedCourse(Base):
    """A course stored in the database rather than ``content/courses`` (the generation
    pipeline's output). ``payload`` is the ``Course`` schema without concepts or problems."""

    __tablename__ = "generated_courses"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    # review: outline awaiting the owner; published: served to learners.
    status: Mapped[str] = mapped_column(String(16), default="published")
    brief: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Why generation is paused ("budget" or "owner"); empty while it runs. Learners keep
    # everything already released either way.
    paused: Mapped[str] = mapped_column(String(24), default="")
    projects: Mapped[list | None] = mapped_column(JSON, nullable=True)  # ``Project``s
    # Set for a course a learner asked for: private to them. Empty for the owner's courses.
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    # private: only the owner. public: the owner agreed to share it with every learner.
    visibility: Mapped[str] = mapped_column(String(8), default="private")
    shared_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    credit_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # ok | held (hidden after reports, awaiting an admin) | removed (the owner may not re-share)
    moderation: Mapped[str] = mapped_column(String(8), default="ok")
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    # Bumped on every change to the course or its concepts; the catalog cache keys on it.
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class GeneratedConcept(Base):
    """One concept of a generated course; ``payload`` is the ``Concept`` schema."""

    __tablename__ = "generated_concepts"
    course_id: Mapped[str] = mapped_column(
        ForeignKey("generated_courses.id", ondelete="CASCADE"), primary_key=True
    )
    concept_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    atoms: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # an ``AtomPack``
    problems: Mapped[list | None] = mapped_column(JSON, nullable=True)  # ``Problem``s
    updated_at: Mapped[int] = mapped_column(Integer, default=now)
    # The job that released this version; its log holds models, prompt versions and sources.
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class GenerationJob(Base):
    """One run of the course-generation agents (e.g. brief → outline). The worker claims
    queued jobs; ``log`` keeps each agent round (verdicts, issues, cost) for the admin."""

    __tablename__ = "generation_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    kind: Mapped[str] = mapped_column(String(24))
    course_id: Mapped[str] = mapped_column(String(80), index=True)
    target: Mapped[str] = mapped_column(String(80), default="")  # concept id for a package
    input: Mapped[dict] = mapped_column(JSON)
    output: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # last draft, kept for audit
    state: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    log: Mapped[list] = mapped_column(JSON, default=list)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str] = mapped_column(String(500), default="")
    attempts: Mapped[int] = mapped_column(Integer, default=0)  # transient failures so far
    not_before: Mapped[int] = mapped_column(Integer, default=0)  # retry backoff
    stage: Mapped[str] = mapped_column(String(16), default="")  # generating | validating
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class LearningRequest(Base):
    """A learner's "teach me X": raw text, the parsed (and learner-editable) intent, and the
    course it became. Unique per learner and text, so a retry never creates a second one."""

    __tablename__ = "learning_requests"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_learning_request_user_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    key: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(String(2000))
    intent: Mapped[dict] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(16), default="model")  # model | rules
    # parsed | needs_clarification | blocked | confirmed
    status: Mapped[str] = mapped_column(String(24), default="parsed")
    course_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class CreatorPerk(Base):
    """A reward a course creator earned when enough other learners used their shared course.
    One row per user, course and tier, so the sweep that awards them can run any time."""

    __tablename__ = "creator_perks"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    course_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    tier: Mapped[str] = mapped_column(String(24), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))  # badge | plus
    earned_at: Mapped[int] = mapped_column(Integer, default=now)
    expires_at: Mapped[int | None] = mapped_column(Integer, nullable=True)  # plus access end


class CourseReport(Base):
    """A learner's report on a shared course; one per learner and course."""

    __tablename__ = "course_reports"
    course_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    reason: Mapped[str] = mapped_column(String(16))  # unsafe | wrong | offensive | copied | other
    note: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class Diagnostic(Base):
    """A short starting-level check for a learner-requested course. ``items`` holds the
    questions with their answer key; learners only ever receive the stems and options."""

    __tablename__ = "diagnostics"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    request_id: Mapped[str] = mapped_column(
        ForeignKey("learning_requests.id", ondelete="CASCADE"), unique=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    items: Mapped[list] = mapped_column(JSON)
    answers: Mapped[list | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class ContentTranslation(Base):
    """One concept translated into one locale. ``units`` are the translated text pieces (code,
    numbers and answer keys never pass through a model); ``source_hash`` ties it to the exact
    English it came from, so an edited lesson makes it stale instead of silently wrong."""

    __tablename__ = "content_translations"
    concept: Mapped[str] = mapped_column(String(160), primary_key=True)
    locale: Mapped[str] = mapped_column(String(16), primary_key=True)
    source_hash: Mapped[str] = mapped_column(String(64))
    units: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(12), default="machine")  # machine | reviewed
    model: Mapped[str] = mapped_column(String(64), default="")
    glossary_version: Mapped[str] = mapped_column(String(16), default="")
    reviewer: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, default=now)
    updated_at: Mapped[int] = mapped_column(Integer, default=now)


class ConceptVersion(Base):
    """A released version of a generated concept, kept before it is replaced (a rewrite after
    reports, a link repair, a rollback). Learner progress is keyed by concept id, so none is
    lost; ``digest`` stops identical snapshots piling up."""

    __tablename__ = "concept_versions"
    __table_args__ = (Index("ix_concept_versions_concept", "course_id", "concept_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=identifier)
    course_id: Mapped[str] = mapped_column(String(80), index=True)
    concept_id: Mapped[str] = mapped_column(String(80))
    version: Mapped[int] = mapped_column(Integer)
    digest: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    atoms: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    problems: Mapped[list | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str] = mapped_column(String(40), default="update")
    created_at: Mapped[int] = mapped_column(Integer, default=now)


class ResourceHealth(Base):
    """The latest link checks for one resource of one concept (``course:concept``)."""

    __tablename__ = "resource_health"
    concept: Mapped[str] = mapped_column(String(160), primary_key=True)
    url: Mapped[str] = mapped_column(String(512), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, default=0)  # consecutive failed checks
    first_failed_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_ok_at: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_checked_at: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(8), default="ok")  # ok | failing | dead
