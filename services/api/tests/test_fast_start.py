"""A fast start: the plan's shape is shown while its details are written, a learner's first
lesson skips the researcher's model call, and its draft can be read while the checks run.

The two lesson changes are off by default (``gen_fast_first_lesson``,
``gen_first_lesson_preview``); the skeleton is only more information, sooner.
"""

# ruff: noqa: F811
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_applied_lessons import learner_outline, outline_script  # noqa: F401
from test_applied_lessons import run as run_outline
from test_coursegen_package import (  # noqa: F401
    ATOMS,
    FACTS_OK,
    GOOD,
    PASS,
    QUIZ,
    ROLES,
    Scripted,
    generate,
    lesson,
    published,
    run,
    web,
)
from test_learner_api import client, login  # noqa: F401
from test_learning_requests import URL, _published_course, on  # noqa: F401

from socrat.assistant.gateway import Event, usage_event
from socrat.coursegen import outline, research, search
from socrat.learn import preview
from socrat.models import GeneratedCourse, GenerationJob, User


def test_titles_are_the_plan_a_learner_can_read_and_survive_a_malformed_reply():
    plan = outline.titles(
        {
            "title": "  Machine   learning ",
            "tagline": "From zero",
            "modules": [
                {
                    "id": "ideas",
                    "title": "Ideas",
                    "concepts": [
                        {"id": "a", "title": "What a model is", "objectives": ["secret detail"]},
                        {"id": "b"},
                        "junk",
                    ],
                },
                {"title": 7},
                "junk",
            ],
        }
    )
    assert plan == {
        "title": "Machine learning",
        "tagline": "From zero",
        "modules": [{"title": "Ideas", "lessons": ["What a model is"]}],
    }
    assert outline.titles({"modules": None}) == {"title": "", "tagline": "", "modules": []}


def test_the_plans_shape_is_logged_before_its_details_and_review(learner_outline):
    assert run_outline(learner_outline, outline_script())
    with Session(learner_outline.app.state.engine) as db:
        job = db.scalars(select(GenerationJob).where(GenerationJob.kind == "outline")).one()
    events = [e.get("event") or e["role"] for e in job.log]
    assert events.index("skeleton") < events.index("critic")
    plan = next(e for e in job.log if e.get("event") == "skeleton")["plan"]
    assert len(plan["modules"]) == 3 and all(m["lessons"] for m in plan["modules"])


def test_a_waiting_learner_sees_the_skeleton_until_the_plan_is_saved(on):
    ada = login(on, subject="ada")
    made = on.post(URL, json={"text": "Teach me algebra", "choices": ["reg-adult"]}, headers=ada)
    request_id = made.json()["id"]
    on.post(f"{URL}/{request_id}/confirm", json={}, headers=ada)
    assert on.get(f"{URL}/{request_id}", headers=ada).json()["skeleton"] is None
    plan = {"title": "Algebra", "tagline": "", "modules": [{"title": "Start", "lessons": ["x"]}]}
    with Session(on.app.state.engine) as db, db.begin():
        job = db.scalars(select(GenerationJob).where(GenerationJob.kind == "outline")).one()
        job.state = "running"
        job.log = [*job.log, {"role": "architect", "event": "skeleton", "plan": plan}]
    seen = on.get(f"{URL}/{request_id}", headers=ada).json()
    assert seen["skeleton"] == plan and seen["blueprint"] is None
    # A failed job's draft is not a plan.
    with Session(on.app.state.engine) as db, db.begin():
        db.scalars(select(GenerationJob)).one().state = "failed"
    assert on.get(f"{URL}/{request_id}", headers=ada).json()["skeleton"] is None


def test_the_best_ranked_results_become_sources_text_before_video():
    def hit(title, kind, score):
        return search.Hit(
            title, f"https://example.org/{title}", f"about {title}", "p", kind, score=score
        )

    hits = [hit("video", "video", 9), hit("weak", "article", 1), hit("strong", "book", 5)]
    chosen = research.best(hits, most=2)["sources"]
    assert [s["title"] for s in chosen] == ["strong", "weak"]
    assert len(research.candidates(research.best(hits))) == 3  # the format screen() accepts


def first_job(client, admin, concept="what-is-ml", trigger="first"):
    """The concept's queued package job, marked as a learner's first lesson."""
    generate(client, admin, concept)
    with Session(client.app.state.engine) as db, db.begin():
        job = db.scalars(select(GenerationJob).where(GenerationJob.kind == "package")).one()
        job.input = {**job.input, "trigger": trigger}
        return job.id


class Researching(Scripted):
    """The scripted model with a researcher, counting how often each role is asked."""

    def __init__(self, **replies):
        super().__init__(**replies)
        self.asked: list[str] = []

    def make(self, settings):
        script = self
        known = ROLES | {research.RESEARCHER: "researcher"}

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                role = known[system]
                script.asked.append(role)
                yield Event("text", text=script.replies[role].pop(0))
                yield usage_event(1000, 3000)

        return Provider()


def searching(client, monkeypatch):
    """The course asks for research and the search finds the two good links."""
    settings = client.app.state.settings
    settings.research_providers, settings.research_read_pages = ["wikipedia"], False
    settings.youtube_transcripts = False
    settings.gen_fast_first_lesson = True
    found(monkeypatch)
    with Session(client.app.state.engine) as db, db.begin():
        meta = db.get(GeneratedCourse, "ai-basics")
        assert meta is not None
        meta.brief = {**(meta.brief or {}), "research": True}


def cited():
    """A lesson that cites the first source, as a researched lesson must."""
    draft = lesson()
    return draft | {"lesson": draft["lesson"] + "\n\nThis follows the first source [1]."}


PICKED = {
    "sources": [
        {"title": "Intro", "url": GOOD[0], "supports": "what a model is", "fit": 5},
        {"title": "Lecture", "url": GOOD[1], "supports": "learning from examples", "fit": 4},
    ]
}


def found(monkeypatch):
    async def gather(*args, **kwargs):
        return [
            search.Hit("Intro", GOOD[0], "what a model is", "wikipedia", "article", score=5),
            search.Hit("Lecture", GOOD[1], "learning from examples", "mit-ocw", "course", score=4),
        ]

    monkeypatch.setattr(search, "gather", gather)


def test_a_first_lesson_takes_ranked_sources_without_the_researcher(
    client, published, web, monkeypatch
):
    searching(client, monkeypatch)
    job_id = first_job(client, published)
    script = Researching(
        author=[cited()], quiz=[QUIZ], atoms=[ATOMS], facts=[FACTS_OK], reviewer=[PASS]
    )
    assert run(client, script.make, web())
    with Session(client.app.state.engine) as db:
        job = db.get(GenerationJob, job_id)
    assert job is not None and job.state == "done", job.log[-1]
    assert "researcher" not in script.asked
    entry = next(e for e in job.log if e.get("role") == "researcher")
    assert entry["chosen_by"] == "code" and [s["url"] for s in entry["sources"]] == GOOD


def test_any_other_lesson_still_asks_the_researcher(client, published, web, monkeypatch):
    searching(client, monkeypatch)
    job_id = first_job(client, published, trigger="prefetch")
    script = Researching(
        researcher=[PICKED],
        author=[cited()],
        quiz=[QUIZ],
        atoms=[ATOMS],
        facts=[FACTS_OK],
        reviewer=[PASS],
    )
    assert run(client, script.make, web())
    with Session(client.app.state.engine) as db:
        job = db.get(GenerationJob, job_id)
    assert job is not None and job.state == "done", job.log[-1]
    assert script.asked[0] == "researcher"
    entry = next(e for e in job.log if e.get("role") == "researcher")
    assert entry["chosen_by"] == "model"


def test_the_draft_is_marked_readable_once_it_passes_the_lesson_gates(client, published, web):
    client.app.state.settings.gen_first_lesson_preview = True
    job_id = first_job(client, published)
    script = Scripted(
        author=[lesson()], quiz=[QUIZ], atoms=[ATOMS], facts=[FACTS_OK], reviewer=[PASS]
    )
    assert run(client, script.make, web())
    with Session(client.app.state.engine) as db:
        job = db.get(GenerationJob, job_id)
    assert job is not None
    events = [e.get("event") for e in job.log]
    assert events.index("preview_ready") < events.index("validating")


def test_a_lesson_that_fails_its_gates_is_never_offered_as_a_draft(client, published, web):
    client.app.state.settings.gen_first_lesson_preview = True
    client.app.state.settings.gen_package_rounds = 1
    job_id = first_job(client, published)
    script = Scripted(author=[lesson(size=1)])  # too short: stopped by the lesson gates
    run(client, script.make, web())
    with Session(client.app.state.engine) as db:
        job = db.get(GenerationJob, job_id)
    assert job is not None and not any(e.get("event") == "preview_ready" for e in job.log)


def test_who_may_read_a_draft():
    assert preview.allowed_for({})
    assert preview.allowed_for({"learner": {"age": 30, "register": "general"}})
    assert not preview.allowed_for({"safety": ["Use a knife with an adult present."]})
    assert not preview.allowed_for({"learner": {"age": 9, "register": "teen"}})
    assert not preview.allowed_for({"learner": {"register": "little-kid"}})


def draft_job(on, course_id, concept="variables", **fields):
    with Session(on.app.state.engine) as db, db.begin():
        # The app may have queued this lesson already (one open job per lesson): use that one.
        job = db.scalars(
            select(GenerationJob).where(
                GenerationJob.course_id == course_id,
                GenerationJob.kind == "package",
                GenerationJob.target == concept,
                GenerationJob.state.in_(("queued", "running")),
            )
        ).first()
        if job is None:
            job = GenerationJob(kind="package", course_id=course_id, target=concept, input={})
            db.add(job)
        job.input = {"trigger": "first"}
        job.state = "running"
        job.log = [{"role": "system", "event": "preview_ready"}]
        job.output = {"lesson": {"lesson": "## Draft\n\nText.", "key_points": ["One", 2]}}
        for name, value in fields.items():
            setattr(job, name, value)
        db.flush()
        return job.id


def planned_concept(on, course_id) -> str:
    """A lesson of the course that is not written yet."""
    from socrat.catalog import generated

    with Session(on.app.state.engine) as db:
        course = generated.course(db, course_id)
    assert course is not None
    return next(c.id.split(":", 1)[-1] for c in course.concepts if c.status == "planned")


def test_only_the_owner_reads_their_first_lessons_draft(on):
    ada = login(on, subject="ada")
    request_id, course_id = _published_course(on, ada)
    view = on.get(f"{URL}/{request_id}", headers=ada).json()
    with Session(on.app.state.engine) as db, db.begin():
        db.scalars(select(User)).one().birth_year = 1990
    assert on.post("/api/v1/enrollments", json=view["enroll"], headers=ada).status_code < 300
    concept = planned_concept(on, course_id)
    url = f"/api/v1/concepts/{course_id}:{concept}/preview"
    job_id = draft_job(on, course_id, concept)
    with Session(on.app.state.engine) as db, db.begin():
        meta = db.get(GeneratedCourse, course_id)
        assert meta is not None
        noted = list((meta.brief or {}).get("safety") or [])  # the request's own safety notes
        meta.brief = {**(meta.brief or {}), "safety": []}
    assert on.get(url, headers=ada).status_code == 404  # off by default
    on.app.state.settings.gen_first_lesson_preview = True
    seen = on.get(url, headers=ada)
    assert seen.status_code == 200, seen.text
    body = seen.json()
    assert body["lesson"].startswith("## Draft") and body["checking"] is True
    assert body["key_points"] == ["One"]  # anything that is not text is left out

    def with_job(**fields):
        with Session(on.app.state.engine) as db, db.begin():
            job = db.get(GenerationJob, job_id)
            assert job is not None
            for name, value in fields.items():
                setattr(job, name, value)
        return on.get(url, headers=ada).status_code

    # Not past the gates, not a first lesson, or no longer running: no draft.
    assert with_job(log=[]) == 404
    assert with_job(log=[{"event": "preview_ready"}], input={"trigger": "prefetch"}) == 404
    assert with_job(input={"trigger": "first"}, state="failed") == 404
    assert with_job(state="running") == 200
    # A course that asks for care, or a young learner, waits for the checked lesson.
    with Session(on.app.state.engine) as db, db.begin():
        meta = db.get(GeneratedCourse, course_id)
        assert meta is not None
        meta.brief = {**(meta.brief or {}), "safety": noted or ["An adult must be present."]}
    assert on.get(url, headers=ada).status_code == 404
    with Session(on.app.state.engine) as db, db.begin():
        meta = db.get(GeneratedCourse, course_id)
        assert meta is not None
        meta.brief = {k: v for k, v in (meta.brief or {}).items() if k != "safety"}
    assert on.get(url, headers=ada).status_code == 200
    # Nobody else's course: another learner gets nothing, signed in or not.
    bob = login(on, subject="bob")
    assert on.get(url, headers=bob).status_code == 404
