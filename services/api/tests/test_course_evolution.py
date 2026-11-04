"""Adaptive course evolution (master prompt 10.4): a bridge lesson when a prerequisite is shaky,
proposed to the course's owner, inserted by code, logged as a visible revision; existing
objectives and assessment standards never change silently."""

# ruff: noqa: F811
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_generation_recovery import _published, on  # noqa: F401
from test_learner_api import client, login  # noqa: F401
from test_learning_requests import URL

from socrat.adaptive import proposals, suggest
from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen import evolve
from socrat.models import Enrollment, GenerationJob, User


def _user_id(on, subject):
    with Session(on.app.state.engine) as db:
        return db.scalar(select(User.id).where(User.subject == subject))


def _insert(on, course_id, user_id):
    with Session(on.app.state.engine) as db, db.begin():
        base = default_catalog()
        return evolve.insert_bridge(
            db,
            base,
            generated.merged(base),
            course_id,
            f"{course_id}:loss",
            f"{course_id}:what-is-ml",
            "Missed loss three times.",
            user_id,
        )


def test_a_bridge_goes_before_the_struggling_concept_and_is_logged(on):
    ada = login(on, subject="ada")
    request_id, course_id = _published(on, ada)
    with Session(on.app.state.engine) as db:
        before = generated.course(db, course_id).concept("loss").outline.model_dump()
    local = _insert(on, course_id, _user_id(on, "ada"))
    with Session(on.app.state.engine) as db:
        course = generated.course(db, course_id)
        order = course.modules[0].concepts
        assert order.index(local) == order.index("loss") - 1
        assert local in course.concept("loss").prerequisites
        assert course.concept("loss").outline.model_dump() == before  # objectives untouched
        bridge = course.concept(local)
        assert bridge.status == "planned" and bridge.outline.evidence == ["application"]
        job = db.scalars(select(GenerationJob).where(GenerationJob.target == local)).one()
        assert job.input["trigger"] == "bridge"
    items = on.get(f"{URL}/{request_id}/revisions").json()["items"]
    assert items[0]["version"] == 1 and "bridge lesson" in items[0]["change"]
    assert items[0]["reason"] == "Missed loss three times."


def test_only_the_owner_and_only_once(on):
    ada = login(on, subject="ada")
    _, course_id = _published(on, ada)
    login(on, subject="bob", name="Bob")
    with pytest.raises(ValueError, match="not_your_course"):
        _insert(on, course_id, _user_id(on, "bob"))
    _insert(on, course_id, _user_id(on, "ada"))
    with pytest.raises(ValueError, match="bridge_exists"):
        _insert(on, course_id, _user_id(on, "ada"))


def test_generated_concepts_get_a_bridge_option_in_the_same_group():
    import copy

    from socrat.catalog.schema import Provenance
    from socrat.coursegen.package import AI_AUTHOR

    cat = default_catalog()
    hand = next(k for k, p in cat.prerequisites.items() if p and k.startswith("zero:"))
    weak = cat.prerequisites[hand][0]
    assert [d.kind for d in suggest._gap(cat, hand, weak, "Stuck.")] == ["repair"]
    made = copy.copy(cat)
    made.concepts = dict(cat.concepts)
    made.concepts[hand] = cat.concepts[hand].model_copy(
        update={"provenance": Provenance(author=AI_AUTHOR)}
    )
    drafts = suggest._gap(made, hand, weak, "Stuck.")
    assert [d.kind for d in drafts] == ["repair", "bridge"]
    assert drafts[0].group == drafts[1].group == f"gap:{hand}"


def test_the_owner_accepts_a_bridge_proposal_end_to_end(on):
    ada = login(on, subject="ada")
    request_id, course_id = _published(on, ada)
    body = on.get(f"{URL}/{request_id}").json()["enroll"]
    with Session(on.app.state.engine) as db, db.begin():
        db.scalars(select(User).where(User.subject == "ada")).one().birth_year = 1995
    assert on.post("/api/v1/enrollments", json=body, headers=ada).status_code == 200
    draft = suggest.Draft(
        "bridge",
        f"bridge:{course_id}:what-is-ml:{course_id}:loss",
        "Add a bridge lesson",
        "Stuck on loss.",
        {"concept": f"{course_id}:what-is-ml", "for": f"{course_id}:loss"},
        f"gap:{course_id}:loss",
    )
    base = default_catalog()
    with Session(on.app.state.engine) as db, db.begin():
        enrollment = db.scalars(select(Enrollment).where(Enrollment.course_id == course_id)).one()
        [row] = proposals.sync(db, enrollment, [draft], 1)
        user = db.get(User, enrollment.user_id)
        proposals.decide(db, generated.merged(base), user, enrollment, row.id, True, 2)
    items = on.get(f"{URL}/{request_id}/revisions").json()["items"]
    assert len(items) == 1 and items[0]["reason"] == "Stuck on loss."


def test_a_bridge_is_never_offered_on_someone_elses_course(client):
    from test_learner_api import onboard

    headers = login(client)
    onboard(client, headers)  # a hand-written course: the learner owns no generated course
    draft = suggest.Draft(
        "bridge",
        "bridge:x",
        "Bridge",
        "Why.",
        {"concept": "zero:programs-and-output", "for": "zero:loops"},
    )
    with Session(client.app.state.engine) as db, db.begin():
        enrollment = db.scalars(select(Enrollment)).one()
        assert proposals.sync(db, enrollment, [draft], 1) == []
