"""The course brain: subject roots, request specs, and serving an existing course to a second
compatible learner without generating again (docs/implementation/course-brain-plan.md)."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_generated_courses import ai_basics, concept
from test_learner_api import client, login  # noqa: F401

from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen.brain import roots
from socrat.coursegen.brain.route import compatible
from socrat.coursegen.brain.spec import derive, is_private, topic_of
from socrat.models import (
    CourseMatch,
    Enrollment,
    GeneratedCourse,
    GenerationJob,
    LearningRequest,
    SubjectAlias,
    SubjectRoot,
)

URL = "/api/v1/learning-requests"

ALGEBRA = dict(
    subject="Linear equations",
    domain="mathematics",
    goal="Solve linear equations in one unknown.",
    desired_level="beginner",
    starting_level="none",
    language="en",
    minutes_per_day=10,
)

DETECTIVE = "Teach me to solve linear equations through detective cases. I have ten minutes a day."
MYSTERY = "Help me solve first-degree equations as short mystery investigations. Ten minutes daily."
LONGER = "I want the same mystery-style algebra course, but I have 25 minutes a day."
DRILLS = "Teach me linear equations for an exam through timed drills."
PROBABILITY = "Teach me conditional probability through detective cases."


def spec(text, **intent):
    return derive(text, ALGEBRA | intent, "mathematics")


# --- the spec: wording never decides, hard requirements always do ---------------------------


def test_topic_ignores_style_time_and_synonyms():
    assert topic_of("Linear equations") == topic_of("first-degree equations") == "equation linear"
    assert topic_of("solve linear equations through detective cases") == "equation linear"
    assert topic_of("C") == "c"


def test_same_course_in_different_words_has_the_same_spec():
    one = spec(DETECTIVE)
    two = spec(MYSTERY, subject="First-degree equations")
    assert one.frame == two.frame == "investigation" and one.band == "bite"
    assert one.key() == two.key()


def test_a_different_experience_is_a_different_spec():
    base = spec(DETECTIVE)
    drills = spec(DRILLS, minutes_per_day=None)
    assert (drills.frame, drills.assessment) == ("none", "drill")
    failed = {k for k, (v, _) in compatible(base, drills).items() if v == "fail"}
    assert {"frame", "assessment"} <= failed
    plain = spec("Teach me linear equations")
    assert compatible(base, plain)["frame"][0] == "fail"  # no unasked-for theme
    proofs = spec("linear equations as detective cases with formal proofs of each step")
    assert proofs.rigor == "rigorous" and proofs.assessment == "proof"
    prob = spec(PROBABILITY, subject="Conditional probability")
    assert compatible(base, prob)["topic"][0] == "fail"


def test_time_and_starting_point_are_the_learners_not_the_courses():
    bite = spec(DETECTIVE)
    longer = spec(LONGER, minutes_per_day=25, starting_level="beginner")
    checks = compatible(bite, longer)
    assert all(v == "pass" for v, _ in checks.values()), checks
    # ...but a course of 25-minute lessons does not fit a ten-minute learner.
    assert compatible(longer, bite)["band"][0] == "fail"
    # A course that assumes more than the learner knows is not served.
    assert compatible(longer, bite)["entry"][0] == "fail"


def test_lesson0_frame_comes_from_the_learners_words_not_the_door():
    profile = {"learner_goal": {"learning_mode": "builder", "daily_time_budget_mins": 10}}
    door = "Introduce each new idea through this everyday scenario: a murder mystery podcast."
    got = derive("Teach me linear equations", ALGEBRA | {"style_request": door}, "m", profile)
    assert got.frame == "none" and got.mode == "builder" and got.band == "bite"


def test_personal_context_is_private():
    assert is_private("SQL for our startup's dashboard", None)
    assert is_private("SQL for my company dashboards", None)
    assert is_private("teach me SQL", "my notes")
    assert not is_private(DETECTIVE, None)


# --- roots: any subject, one root per subject ------------------------------------------------


def test_roots_are_created_on_demand_and_synonyms_meet(client):  # noqa: F811
    with Session(client.app.state.engine) as db, db.begin():
        a = roots.resolve(db, roots.name_for({"domain": "Maths", "subject": "x"}))
        b = roots.resolve(db, roots.name_for({"domain": "math", "subject": "y"}))
        c = roots.resolve(db, roots.name_for({"domain": "general", "subject": "Algebra 1"}))
        d = roots.resolve(
            db, roots.name_for({"domain": "", "subject": "Underwater basket weaving"})
        )
        e = roots.resolve(
            db, roots.name_for({"domain": "general", "subject": "Underwater basket weaving"})
        )
        assert a.id == b.id == c.id == "mathematics"
        assert d.id == e.id == "underwater-basket-weaving"
        assert db.scalar(select(SubjectRoot).where(SubjectRoot.id == d.id)) is not None
        assert db.get(SubjectAlias, "underwater basket weaving").root_id == d.id
        # A merged duplicate redirects.
        db.add(
            SubjectRoot(id="maths-dup", title="Maths", status="merged", merged_into="mathematics")
        )
        db.flush()
        db.add(SubjectAlias(alias="mathz", root_id="maths-dup", source="admin"))
        db.flush()
        assert roots.resolve(db, "mathz").id == "mathematics"


# --- end to end: a second learner is served the first learner's course -----------------------


@pytest.fixture
def brain(client):  # noqa: F811
    client.app.state.settings.learning_requests_enabled = True
    client.app.state.settings.course_brain = True
    return client


def ask(client, headers, text, **intent):  # noqa: F811
    made = client.post(URL, json={"text": text}, headers=headers)
    assert made.status_code in (200, 201), made.text
    body = made.json()
    done = client.post(
        f"{URL}/{body['id']}/confirm",
        json={"intent": body["intent"] | ALGEBRA | intent},
        headers=headers,
    )
    assert done.status_code == 200, done.text
    return done.json()


def build(client, course_id, owner, live=True):  # noqa: F811
    """Stand in for the outline job: store the course the first request asked for."""
    course = ai_basics(
        id=course_id,
        title="Linear equations",
        concepts=[
            concept("what-is-ml", "ideas", "live" if live else "planned"),
            concept("loss", "ideas", prerequisites=["what-is-ml"]),
        ],
    )
    with Session(client.app.state.engine) as db, db.begin():
        generated.save_course(db, default_catalog(), course, status="review")
        db.get(GeneratedCourse, course_id).owner_id = owner
        for job in db.scalars(select(GenerationJob).where(GenerationJob.course_id == course_id)):
            job.state = "done"  # as the worker leaves it once the outline is saved


def me(client):  # noqa: F811
    return client.get("/api/v1/me").json()["id"]


def adult(client, headers):  # noqa: F811
    client.patch("/api/v1/me", json={"birth_year": 2001, "timezone": "UTC"}, headers=headers)


def test_second_compatible_learner_gets_the_first_learners_course(brain):
    ada = login(brain, "ada", "Ada")
    adult(brain, ada)
    first = ask(brain, ada, DETECTIVE)
    assert first["status"] == "confirmed"
    build(brain, first["course_id"], me(brain))
    published = brain.post(f"{URL}/{first['id']}/publish", json={}, headers=ada).json()
    assert published["published"]
    with Session(brain.app.state.engine) as db:
        row = db.get(GeneratedCourse, first["course_id"])
        assert (row.root_id, row.serve) == ("mathematics", "shared")
        jobs_before = db.scalar(select(GenerationJob.id).where(GenerationJob.kind == "outline"))
        assert jobs_before is not None

    bob = login(brain, "bob", "Bob")
    adult(brain, bob)
    second = ask(brain, bob, MYSTERY, subject="First-degree equations")
    assert second["status"] == "matched" and second["course_id"] == first["course_id"]
    assert second["published"] and second["enroll"] and second["blueprint"]
    assert second["job"]["state"] == "done"  # no "generating" wait on the plan screen
    # Publishing again (the plan screen always does) is a no-op, and enrolment is allowed.
    again = brain.post(f"{URL}/{second['id']}/publish", json={}, headers=bob).json()
    assert again["course_id"] == first["course_id"]
    enrolled = brain.post("/api/v1/enrollments", json=again["enroll"], headers=bob)
    assert enrolled.status_code == 200, enrolled.text
    today = brain.get("/api/v1/today").json()
    assert today["next"]["concept"] == f"{first['course_id']}:what-is-ml", today["next"]

    with Session(brain.app.state.engine) as db:
        bob_id = db.scalar(
            select(LearningRequest.user_id).where(LearningRequest.id == second["id"])
        )
        # Nothing was generated for Bob.
        assert (
            db.scalars(
                select(GenerationJob).where(
                    GenerationJob.created_by == bob_id, GenerationJob.kind == "outline"
                )
            ).all()
            == []
        )
        match = db.scalar(select(CourseMatch).where(CourseMatch.request_id == second["id"]))
        assert match.outcome == "reuse" and "exact spec" in match.reason
        assert match.candidates[0]["passed"] is True
        enrollment = db.scalar(select(Enrollment).where(Enrollment.user_id == bob_id))
        assert enrollment.match_id == match.id
        assert enrollment.learner_plan["request"] == MYSTERY
        # Bob's words stay with Bob: nothing of them is on the shared course.
        shared = db.get(GeneratedCourse, first["course_id"])
        assert MYSTERY not in str(shared.payload) + str(shared.brief) + str(shared.spec)


def test_incompatible_or_unready_courses_are_not_served(brain):
    ada = login(brain, "ada", "Ada")
    adult(brain, ada)
    first = ask(brain, ada, DETECTIVE)
    build(brain, first["course_id"], me(brain), live=False)  # roadmap only, no lesson yet
    brain.post(f"{URL}/{first['id']}/publish", json={}, headers=ada)

    bob = login(brain, "bob", "Bob")
    adult(brain, bob)
    waiting = ask(brain, bob, MYSTERY, subject="First-degree equations")
    assert waiting["status"] == "confirmed" and waiting["course_id"] != first["course_id"]
    drills = ask(brain, bob, DRILLS, minutes_per_day=None, goal="Pass the algebra exam.")
    assert drills["status"] == "confirmed"
    with Session(brain.app.state.engine) as db:
        why = db.scalar(select(CourseMatch).where(CourseMatch.request_id == waiting["id"]))
        assert why.outcome == "extend_and_new"  # Ada's research for the topic is still open
        assert why.candidates[0]["why"] == "first lesson not ready"
        drill = db.scalar(select(CourseMatch).where(CourseMatch.request_id == drills["id"]))
        failed = set(drill.candidates[0]["failed"])
        assert {"frame", "assessment"} <= failed


def test_private_requests_build_privately_and_are_never_served(brain):
    ada = login(brain, "ada", "Ada")
    adult(brain, ada)
    first = ask(brain, ada, DETECTIVE + " Use my company spreadsheet as the examples.")
    build(brain, first["course_id"], me(brain))
    brain.post(f"{URL}/{first['id']}/publish", json={}, headers=ada)
    with Session(brain.app.state.engine) as db:
        assert db.get(GeneratedCourse, first["course_id"]).serve == "private"

    bob = login(brain, "bob", "Bob")
    adult(brain, bob)
    second = ask(brain, bob, DETECTIVE)
    assert second["status"] == "confirmed" and second["course_id"] != first["course_id"]


def test_shared_community_courses_are_candidates(brain):
    brain.app.state.settings.course_brain = False  # made before the brain existed
    ada = login(brain, "ada", "Ada")
    adult(brain, ada)
    first = ask(brain, ada, DETECTIVE)
    build(brain, first["course_id"], me(brain))
    brain.post(f"{URL}/{first['id']}/publish", json={}, headers=ada)
    with Session(brain.app.state.engine) as db, db.begin():
        row = db.get(GeneratedCourse, first["course_id"])
        assert row.root_id is None and row.serve is None
        row.visibility = "public"

    brain.app.state.settings.course_brain = True
    bob = login(brain, "bob", "Bob")
    adult(brain, bob)
    second = ask(brain, bob, MYSTERY, subject="First-degree equations")
    assert second["status"] == "matched" and second["course_id"] == first["course_id"]
    with Session(brain.app.state.engine) as db:
        assert db.get(GeneratedCourse, first["course_id"]).root_id == "mathematics"


def test_brain_off_changes_nothing(client):  # noqa: F811
    client.app.state.settings.learning_requests_enabled = True
    ada = login(client)
    adult(client, ada)
    done = ask(client, ada, DETECTIVE)
    assert done["status"] == "confirmed"
    with Session(client.app.state.engine) as db:
        assert db.scalars(select(CourseMatch)).all() == []
