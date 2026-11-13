"""The tutor pause while a check is open ends as soon as the learner finishes a check."""

from sqlalchemy.orm import Session

from socrat.database import make_engine
from socrat.learn import quizzes
from socrat.models import Base, Enrollment, QuizEngineSession, QuizSession, User

NOW = 1_800_000_000


def learner(db: Session) -> Enrollment:
    user = User(issuer="test", subject="open-test")
    db.add(user)
    db.flush()
    enrollment = Enrollment(
        user_id=user.id,
        course_id="dsa",
        language="python",
        level_id="new",
        minutes_per_day=30,
        weekdays=[0, 1, 2],
    )
    db.add(enrollment)
    db.flush()
    return enrollment


def engine_session(enrollment: Enrollment, created: int, completed: int | None = None):
    return QuizEngineSession(
        enrollment_id=enrollment.id,
        mode="concept_check",
        track="python",
        concepts=["dsa:arrays"],
        state={"steps": [], "pending": {"served_at": created} if completed is None else None},
        created_at=created,
        completed_at=completed,
    )


def test_open_check_pauses_then_a_finished_check_releases(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'open.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        enrollment = learner(db)
        assert not quizzes.open_test(db, enrollment, NOW)

        # A check being taken pauses the tutor.
        db.add(engine_session(enrollment, NOW - 300))
        db.flush()
        assert quizzes.open_test(db, enrollment, NOW)

        # The same check started twice: the learner finishes one copy. The leftover copy
        # must not keep the tutor paused.
        db.add(engine_session(enrollment, NOW - 290, completed=NOW - 60))
        db.flush()
        assert not quizzes.open_test(db, enrollment, NOW)

        # A fixed quiz left unfinished before that finish does not count either.
        db.add(
            QuizSession(
                enrollment_id=enrollment.id,
                activity_id="quiz:dsa:arrays",
                items=[],
                answers={},
                created_at=NOW - 600,
            )
        )
        db.flush()
        assert not quizzes.open_test(db, enrollment, NOW)

        # A new check started after the finish pauses the tutor again.
        db.add(engine_session(enrollment, NOW - 10))
        db.flush()
        assert quizzes.open_test(db, enrollment, NOW)
    engine.dispose()
