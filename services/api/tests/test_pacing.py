"""Pacing: a course's budget grows with the lessons it releases, and a daily quota schedules
the next lesson instead of pausing the course."""

# ruff: noqa: F811
from sqlalchemy.orm import Session
from test_coursegen_batches import package_jobs, release
from test_coursegen_package import Scripted, published, run, web  # noqa: F401
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.config import Settings
from socrat.coursegen import jobs, pacing, prefetch
from socrat.models import GeneratedCourse, GenerationJob, now

DAY = pacing.DAY


def test_the_defaults_change_nothing():
    settings = Settings(_env_file=None)
    assert settings.gen_budget_per_lesson_usd == 0 and settings.gen_lessons_per_day == 0
    assert (settings.gen_initial_lessons, settings.gen_lessons_ahead) == (6, 3)
    assert (prefetch.INITIAL_CONCEPTS, prefetch.AHEAD, prefetch.LESSONS_PER_DAY) == (6, 3, 0)


def add(db, target, created, wait=0, state="done"):
    job = GenerationJob(
        kind="package", course_id="ai-basics", target=target, input={}, log=[], state=state
    )
    job.created_at, job.not_before = created, wait
    db.add(job)
    db.flush()
    return job


def test_the_quota_gives_each_lesson_a_time_in_a_rolling_day(client, published):
    t = now()
    with Session(client.app.state.engine) as db:
        assert pacing.slot(db, "ai-basics", 0, t) == 0  # no quota
        assert pacing.slot(db, "ai-basics", 2, t) == 0  # nothing written yet
        add(db, "a", t - 2 * DAY)  # older than a day: does not count
        add(db, "b", t - 3000)
        add(db, "x", t - 10, state="cancelled")  # cancelled: does not count
        assert pacing.slot(db, "ai-basics", 2, t) == 0  # one of two used
        add(db, "c", t - 1000)
        assert pacing.slot(db, "ai-basics", 2, t) == t - 3000 + DAY  # when "b" leaves the day
        add(db, "d", t, wait=t - 3000 + DAY, state="queued")  # a scheduled one counts then
        assert pacing.slot(db, "ai-basics", 2, t) == t - 1000 + DAY
        assert pacing.slot(db, "other-course", 2, t) == 0  # per course
        db.rollback()


def test_a_lesson_over_the_quota_is_scheduled_and_the_learner_is_told(
    client, published, monkeypatch
):
    learner = login(client, subject="ada", name="Ada")
    assert client.get("/api/v1/concepts/ai-basics:loss/writing").status_code == 404  # no quota
    monkeypatch.setattr(prefetch, "LESSONS_PER_DAY", 1)
    onboard(client, learner, course="ai-basics")  # placed at the start: prefetch runs
    first, second = package_jobs(client, "what-is-ml")[0], package_jobs(client, "loss")[0]
    assert first.not_before == 0
    assert abs(second.not_before - (first.created_at + DAY)) <= 2  # a day after the first
    assert second.state == "queued"

    told = client.get("/api/v1/concepts/ai-basics:loss/writing").json()
    assert told["state"] == "queued" and told["per_day"] == 1
    assert told["at"] == second.not_before and 0 < told["seconds"] <= DAY
    now_one = client.get("/api/v1/concepts/ai-basics:what-is-ml/writing").json()
    assert now_one["at"] is None and now_one["seconds"] == 0  # this one is being written now
    assert client.get("/api/v1/concepts/ai-basics:nope/writing").status_code == 404
    assert client.get("/api/v1/concepts/zero:programs-and-output/writing").status_code == 404

    # The runner takes the lesson that is due and leaves the scheduled one for its day.
    engine = client.app.state.engine
    assert jobs.claim(engine) == first.id
    assert jobs.claim(engine) is None
    with Session(engine) as db, db.begin():
        db.get(GenerationJob, second.id).not_before = now() - 1  # its day has come
    assert jobs.claim(engine) == second.id


def test_a_released_lesson_earns_its_course_more_budget(client, published, web):
    engine = client.app.state.engine
    release(client, "what-is-ml", web)
    with Session(engine) as db, db.begin():
        spent = jobs.spent(db, "ai-basics")
        row = db.get(GeneratedCourse, "ai-basics")
        row.brief = {**row.brief, "budget_usd": spent}  # the base budget is used up
        assert pacing.released(db, "ai-basics") == 1
        assert pacing.ceiling(db, "ai-basics", spent, 0) == spent
        assert pacing.ceiling(db, "ai-basics", spent, 0.5) == spent + 0.5
    assert jobs._over_budget(engine, "ai-basics", spent)  # as before: the course would stop
    assert not jobs._over_budget(engine, "ai-basics", spent, 0.5)

    # With no per-lesson budget the next lesson pauses the course; with one, it is written.
    with Session(engine) as db, db.begin():
        jobs.enqueue(db, "package", "ai-basics", {}, None, target="loss")
    run(client, Scripted().make, web())
    with Session(engine) as db, db.begin():
        row = db.get(GeneratedCourse, "ai-basics")
        assert row.paused == "budget"
        row.paused = ""
    client.app.state.settings.gen_budget_per_lesson_usd = 0.5
    from test_coursegen_package import ATOMS, FACTS_OK, PASS, QUIZ, lesson

    script = Scripted(
        author=[lesson()], quiz=[QUIZ], atoms=[ATOMS], facts=[FACTS_OK], reviewer=[PASS]
    )
    run(client, script.make, web())
    assert package_jobs(client, "loss")[0].state == "done"
    with Session(engine) as db:
        assert db.get(GeneratedCourse, "ai-basics").paused == ""


def test_how_many_lessons_are_written_up_front_and_ahead_are_settings(monkeypatch):
    from test_generation_recovery import _course

    big = _course([["a", "b", "c", "d"], ["e", "f", "g"], ["h"], ["i"]])
    monkeypatch.setattr(prefetch, "INITIAL_CONCEPTS", 2)
    assert prefetch.initial_slice(big) == ["a", "b"]  # two up front, the rest as they learn
    assert prefetch.initial_slice(big, start="e") == ["e", "f"]

    from socrat.main import create_app

    one = Settings(
        _env_file=None, gen_initial_lessons=1, gen_lessons_ahead=2, gen_lessons_per_day=4
    )
    create_app(one)
    assert (prefetch.INITIAL_CONCEPTS, prefetch.AHEAD, prefetch.LESSONS_PER_DAY) == (1, 2, 4)
    create_app(Settings(_env_file=None))
    assert (prefetch.INITIAL_CONCEPTS, prefetch.AHEAD, prefetch.LESSONS_PER_DAY) == (6, 3, 0)
