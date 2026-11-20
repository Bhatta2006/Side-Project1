"""Item calibration (M7 tasks 29–31) on synthetic responses."""

from dataclasses import replace

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.calibration import job, report, stats
from socrat.catalog.registry import default_catalog
from socrat.database import make_engine
from socrat.models import Enrollment, ItemCalibration, LearnerAbility, QuizResponse, User
from socrat.quiz import modes, service
from socrat.quiz.config import DEFAULT as QUIZ

CAT = default_catalog()


def responses(n, correct, choice=None, time_s=30, ability=None):
    """n synthetic responses; ``correct``/``choice``/``ability`` are functions of the index."""
    return [
        stats.Response(
            correct=correct(i),
            choice=choice(i) if choice else (0 if correct(i) else 1),
            time_s=time_s,
            ability=ability(i) if ability else float(i),
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------- statistics (task 29)


def test_point_biserial_matches_the_formula():
    r = stats.point_biserial([False, False, True, True], [1, 2, 3, 4])
    assert r == pytest.approx((3.5 - 1.5) / 1.118034 * 0.5, rel=1e-4)
    assert stats.point_biserial([True, True], [1, 2]) is None  # nobody missed
    assert stats.point_biserial([True, False], [2, 2]) is None  # no spread in ability


def test_a_healthy_item_has_no_flags():
    result = stats.compute(responses(60, lambda i: i >= 25), answer=0, expected_seconds=60)
    assert result.n == 60 and 0.5 < result.pct_correct < 0.65
    assert result.discrimination > 0.8 and result.flags == ()
    assert result.distractor_counts == {"1": 25}


@pytest.mark.parametrize(
    ("kwargs", "flag"),
    [
        (dict(correct=lambda i: i == 0), "too-hard"),
        (dict(correct=lambda i: True), "too-easy"),
        (dict(correct=lambda i: i % 2 == 0), "low-discrimination"),
        (dict(correct=lambda i: i >= 30, time_s=400), "slow"),
    ],
)
def test_each_repair_rule(kwargs, flag):
    result = stats.compute(responses(60, **kwargs), answer=0, expected_seconds=60)
    assert flag in result.flags


def test_an_attractive_distractor_among_strong_learners():
    # The top third (abilities 40..59) mostly pick option 2; weaker learners get it right.
    result = stats.compute(
        responses(
            60,
            correct=lambda i: i < 40 or i % 5 == 0,
            choice=lambda i: 0 if (i < 40 or i % 5 == 0) else 2,
        ),
        answer=0,
        expected_seconds=60,
    )
    assert result.strong_top_distractor == pytest.approx(16 / 20)
    assert "attractive-distractor" in result.flags


def test_no_flags_before_thirty_responses():
    assert (
        stats.compute(responses(29, correct=lambda i: True), answer=0, expected_seconds=60).flags
        == ()
    )
    assert stats.compute([], answer=0, expected_seconds=60).n == 0


# ---------------------------------------------------------------- database: job, approvals, engine


@pytest.fixture
def db(tmp_path):
    url = f"sqlite:///{tmp_path / 'calibration.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = make_engine(url)
    with Session(engine) as session:
        yield session
    engine.dispose()


LEGACY = next(i for i in service.bank(CAT) if not i.family and i.pool == "practice")


def learners(db, n):
    found = []
    for i in range(n):
        user = User(issuer="test", subject=f"learner-{i}")
        db.add(user)
        db.flush()
        enrollment = Enrollment(
            user_id=user.id,
            course_id="algo",
            language="python",
            level_id="new",
            minutes_per_day=30,
            weekdays=[0],
        )
        db.add(enrollment)
        db.flush()
        found.append(enrollment)
    return found


def answer_all(db, item, enrollments, correct, choice=None):
    answer = job.answer_index(CAT, item)
    wrong = (answer + 1) % 4
    for i, enrollment in enumerate(enrollments):
        if db.get(LearnerAbility, (enrollment.id, item.pattern)) is None:
            db.add(
                LearnerAbility(
                    enrollment_id=enrollment.id, pattern=item.pattern, theta=800 + 10 * i, n=1
                )
            )
        ok = correct(i)
        db.add(
            QuizResponse(
                enrollment_id=enrollment.id,
                item_id=item.key,
                pattern=item.pattern,
                concept=item.concept,
                mode="concept_check",
                pool=item.pool,
                correct=ok,
                score=1.0 if ok else 0.0,
                time_s=30,
                choice=choice(i) if choice else (answer if ok else wrong),
                created_at=1,
            )
        )
    db.flush()


def test_stats_job_writes_health_but_never_status_or_approval(db):
    answer_all(db, LEGACY, learners(db, 40), lambda i: i >= 15)
    computed = job.run(db, CAT, now=100)
    record = db.get(ItemCalibration, LEGACY.key)
    assert computed[LEGACY.key].flags == () and record.flags == []
    assert record.n_responses == 40 and record.pct_correct == pytest.approx(25 / 40)
    assert record.discrimination > 0.8 and record.computed_at == 100
    assert record.status == "provisional" and record.approved_by is None


def test_status_changes_need_a_person_enough_responses_and_no_flags(db):
    enrollments = learners(db, 40)
    with pytest.raises(job.TransitionError, match="run the stats job"):
        job.transition(db, LEGACY.key, "calibrated", "Asha Rao")
    answer_all(db, LEGACY, enrollments[:20], lambda i: i >= 8)
    job.run(db, CAT)
    for nobody in ("", " ", "ci", "Claude"):
        with pytest.raises(job.TransitionError, match="name of the person"):
            job.transition(db, LEGACY.key, "calibrated", nobody)
    with pytest.raises(job.TransitionError, match="20 responses"):
        job.transition(db, LEGACY.key, "calibrated", "Asha Rao")

    flagged = next(i for i in service.bank(CAT) if not i.family and i.key != LEGACY.key)
    answer_all(db, flagged, enrollments, lambda i: True)
    job.run(db, CAT)
    with pytest.raises(job.TransitionError, match="too-easy"):
        job.transition(db, flagged.key, "calibrated", "Asha Rao")
    retired = job.transition(db, flagged.key, "retired", "Asha Rao", now=5)
    assert (retired.status, retired.approved_by, retired.approved_at) == ("retired", "Asha Rao", 5)
    with pytest.raises(job.TransitionError, match="not allowed"):
        job.transition(db, flagged.key, "calibrated", "Asha Rao")


def test_the_engine_honours_approved_statuses(db):
    item = LEGACY
    answer_all(db, item, learners(db, 40), lambda i: i >= 15)
    job.run(db, CAT)
    assert next(i for i in service.items_for(db, CAT) if i.key == item.key).status == "provisional"
    job.transition(db, item.key, "calibrated", "Asha Rao")
    assert next(i for i in service.items_for(db, CAT) if i.key == item.key).status == "calibrated"
    job.transition(db, item.key, "retired", "Asha Rao")
    assert next(i for i in service.items_for(db, CAT) if i.key == item.key).status == "retired"

    # Assessments open only when enough calibrated assessment items cover the concept (D3).
    concept = "algo:arrays"
    pool = [replace(i, pool="assessment") for i in service.bank(CAT) if i.concept == concept][:3]
    spec = QUIZ.modes["weekly"]
    assert not modes.available(spec, [concept], pool)
    statuses = {i.key: "calibrated" for i in pool}
    assert modes.available(spec, [concept], service.effective(pool, statuses))


# ---------------------------------------------------------------- report (task 31)


def test_report_has_every_section_and_no_learner_data(db):
    enrollments = learners(db, 40)
    answer_all(db, LEGACY, enrollments, lambda i: True)  # too easy: flagged
    job.run(db, CAT)
    text = report.build(db, CAT, "2026-10-16 12:00 UTC")
    for heading in (
        "## Item health",
        "## Coverage per band",
        "## Success-zone share",
        "## Atom gaps",
        "## Provenance completeness",
    ):
        assert heading in text
    assert f"`{LEGACY.key}`" in text and "too-easy" in text
    for enrollment in enrollments:
        assert enrollment.id not in text and enrollment.user_id not in text
    assert "learner-" not in text
    assert "`algo:trees`" in text  # a concept without an atom pack (gap)


def test_cli_runs_stats_status_and_report(db, tmp_path, capsys):
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[3] / "scripts" / "content" / "calibrate.py"
    spec = importlib.util.spec_from_file_location("calibrate_cli", path)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    url = str(db.get_bind().url)
    answer_all(db, LEGACY, learners(db, 35), lambda i: i >= 10)
    db.commit()

    assert cli.main(["--database-url", url, "stats"]) == 0
    assert (
        cli.main(
            [
                "--database-url",
                url,
                "set-status",
                LEGACY.key,
                "--to",
                "calibrated",
                "--approver",
                "bot",
            ]
        )
        == 1
    )
    assert "Refused" in capsys.readouterr().err
    assert (
        cli.main(
            [
                "--database-url",
                url,
                "set-status",
                LEGACY.key,
                "--to",
                "calibrated",
                "--approver",
                "Asha Rao",
            ]
        )
        == 0
    )
    out = tmp_path / "report.md"
    assert cli.main(["--database-url", url, "report", "--out", str(out)]) == 0
    assert "Human-approved status changes: 1." in out.read_text(encoding="utf-8")
    db.expire_all()
    assert (
        db.scalar(select(ItemCalibration.status).where(ItemCalibration.item_id == LEGACY.key))
        == "calibrated"
    )
