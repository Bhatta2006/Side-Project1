"""Runtime tables for the adaptive quiz (Content Master Plan Appendix B): additive, reversible."""

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from socrat.database import make_engine
from socrat.models import (
    Enrollment,
    ItemCalibration,
    ItemRating,
    LearnerAbility,
    QuizResponse,
    User,
)
from socrat.schema_revision import SCHEMA_REVISION

TABLES = {
    "quiz_responses",
    "learner_abilities",
    "item_ratings",
    "item_calibrations",
    "quiz_engine_sessions",
}


def migrated(tmp_path, revision="head"):
    url = f"sqlite:///{tmp_path / 'quiz.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, revision)
    return config, make_engine(url)


def test_upgrade_creates_the_tables_and_downgrade_removes_only_them(tmp_path):
    config, engine = migrated(tmp_path)
    assert SCHEMA_REVISION == "0047_generation_job_priority"
    before = set(sa.inspect(engine).get_table_names())
    assert TABLES <= before
    command.downgrade(config, "0008_product_tour")
    after = set(sa.inspect(engine).get_table_names())
    assert after == before - TABLES - {
        "plan_proposals",
        "ai_usage",
        "error_reports",
        "skill_passports",
        "company_sprints",
        "subscriptions",
        "billing_plans",
        "playground_jobs",
        "email_codes",
        "referrals",
        "referral_rewards",
        "generated_courses",
        "generated_concepts",
        "generation_jobs",
        "shared_visuals",
        "learning_requests",
        "creator_perks",
        "course_reports",
        "diagnostics",
        "content_translations",
        "concept_versions",
        "resource_health",
        "validation_reports",
        "task_submissions",
        "course_revisions",
    }  # 0012-0029 roll back too
    command.upgrade(config, "head")
    assert TABLES <= set(sa.inspect(engine).get_table_names())
    engine.dispose()


def test_learner_rows_are_erased_with_the_account(tmp_path):
    _, engine = migrated(tmp_path)
    with Session(engine) as db:
        user = User(issuer="test", subject="erase-me")
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
        db.add(
            QuizResponse(
                enrollment_id=enrollment.id,
                item_id="dsa:sliding-window:fixed-update",
                concept="dsa:sliding-window",
                mode="concept_check",
                pool="practice",
                correct=True,
                score=1.0,
            )
        )
        db.add(
            LearnerAbility(
                enrollment_id=enrollment.id,
                pattern="dsa:sliding-window/variable-size",
                theta=1000.0,
            )
        )
        db.add(ItemRating(item_id="dsa:sliding-window:fixed-update", d_current=950.0))
        db.add(ItemCalibration(item_id="dsa:sliding-window:fixed-update", status="provisional"))
        db.commit()
        db.delete(db.get(User, user.id))
        db.commit()
        assert db.scalar(sa.select(sa.func.count()).select_from(QuizResponse)) == 0
        assert db.scalar(sa.select(sa.func.count()).select_from(LearnerAbility)) == 0
        # Item-level rows hold no learner data and stay.
        assert db.scalar(sa.select(sa.func.count()).select_from(ItemRating)) == 1
        calibration = db.get(ItemCalibration, "dsa:sliding-window:fixed-update")
        assert calibration is not None and calibration.approved_by is None
    engine.dispose()
