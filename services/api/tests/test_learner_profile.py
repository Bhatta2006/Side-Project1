"""The learner's preferences across courses (``socrat.learner_profile``), the preferences read from
behaviour, misconceptions of generated lessons, and the brief for work without an enrollment."""

# ruff: noqa: F811
import asyncio
import json

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401
from test_learner_memory import learner as signed_in

from socrat import learner, learner_profile
from socrat.adaptive.profile import SkillProfile
from socrat.assistant.tools import Toolbox
from socrat.database import make_engine
from socrat.learn.routes import catalog
from socrat.models import (
    ConceptUnitPin,
    Enrollment,
    Evidence,
    RootUnit,
    SubjectRoot,
    User,
    now,
)

LESSON0 = {
    "learner_goal": {"learning_mode": "sprint"},
    "personalization": {
        "primary_analogy_domain": "a music playlist",
        "preferred_tone": "direct",
        "max_explanation_length": "short_3_sentences",
    },
    "calibration": {"friction_limit_attempts": 2, "pace_level": "lightning"},  # not allowed
}


def test_writes_are_validated_ranked_logged_and_undoable():
    user = User(issuer="t", subject="s")
    with pytest.raises(ValueError):
        learner_profile.set_pref(user, "strictness", "strict", "learner", "")  # owned elsewhere
    with pytest.raises(ValueError):
        learner_profile.set_pref(user, "tone", "shouty", "learner", "")
    with pytest.raises(ValueError):
        learner_profile.set_pref(user, "analogy_domain", "</x>", "learner", "")
    with pytest.raises(ValueError):
        learner_profile.set_pref(user, "tone", "direct", "model", "")
    seeded = learner_profile.seed_from_lesson0(user, LESSON0, at=1)
    assert {e["key"] for e in seeded} == {
        "course_mode",
        "analogy_domain",
        "tone",
        "explanation_length",
        "friction_limit",
    }  # the out-of-range pace was skipped, not stored
    mine = learner_profile.set_pref(user, "tone", "curious_and_thorough", "learner", "mine", 2)
    assert learner_profile.set_pref(user, "tone", "direct", "onboarding", "again", 3) is None
    assert learner_profile.stored(user)["tone"]["source"] == "learner"
    assert learner_profile.undo(user, mine["id"])["undone"]
    assert learner_profile.stored(user)["tone"] == {
        "value": "direct",
        "source": "onboarding",
        "why": "From your first lesson.",
        "at": 1,
    }
    assert learner_profile.undo(user, mine["id"]) is None  # once only
    first = learner_profile.set_pref(user, "pace", "slow", "learner", "", 4)
    learner_profile.set_pref(user, "pace", "fast", "learner", "", 5)
    assert learner_profile.undo(user, first["id"]) is None  # a later write stands on it


def test_a_tutor_suggestion_changes_nothing_until_the_learner_accepts():
    user = User(issuer="t", subject="s")
    with pytest.raises(ValueError):
        learner_profile.suggest(user, "pace", "ludicrous", "why")
    item = learner_profile.suggest(user, "explanation_length", "short_3_sentences", "Asked twice")
    assert learner_profile.stored(user) == {}
    later = learner_profile.suggest(user, "explanation_length", "medium_one_page", "Changed mind")
    assert [p["id"] for p in learner_profile.profile(user)["pending"]] == [later["id"]]
    assert learner_profile.decide(user, item["id"], True) is None  # replaced already
    done = learner_profile.decide(user, later["id"], True)
    assert done["accepted"] and learner_profile.stored(user)["explanation_length"]["source"] == (
        "learner"
    )
    declined = learner_profile.suggest(user, "pace", "slow", "x")
    assert not learner_profile.decide(user, declined["id"], False)["accepted"]
    assert "pace" not in learner_profile.stored(user)


def test_routes_are_off_by_default_and_the_learner_owns_their_profile(client, monkeypatch):
    headers, _ = signed_in(client, monkeypatch)
    assert client.get("/api/v1/learner/profile", headers=headers).status_code == 404
    client.app.state.settings.learner_profile = True
    put = client.put("/api/v1/learner/profile/tone", json={"value": "direct"}, headers=headers)
    assert put.status_code == 200
    assert put.json()["prefs"]["tone"] == {"value": "direct", "source": "learner"}
    bad = client.put("/api/v1/learner/profile/tone", json={"value": "loud"}, headers=headers)
    assert bad.status_code == 422
    entry = put.json()["history"][0]["id"]
    undone = client.post(f"/api/v1/learner/profile/undo/{entry}", headers=headers)
    assert undone.status_code == 200 and "tone" not in undone.json()["prefs"]
    assert client.post(f"/api/v1/learner/profile/undo/{entry}", headers=headers).status_code == 409


def test_stored_and_observed_preferences_reach_the_snapshot(client, monkeypatch):
    signed_in(client, monkeypatch)
    with Session(client.app.state.engine) as db, db.begin():
        user = db.scalars(select(User)).one()
        enrollment = db.scalars(select(Enrollment)).one()
        enrollment.learner_plan = {"tone": "direct_and_encouraging", "door": "cricket"}
        learner_profile.set_pref(user, "tone", "curious_and_thorough", "learner", "mine")
        prefs = learner.snapshot(db, enrollment, now(), catalog=catalog()).prefs
    assert prefs["tone"] == learner.Pref("curious_and_thorough", "learner")  # beats the overlay
    assert prefs["analogy_domain"] == learner.Pref("cricket", "onboarding")


def test_behaviour_is_read_as_observed_preferences():
    def speed(value):
        return SkillProfile(concept="k:a", mastery=0.5, confidence=0.5, band="x", speed=value)

    taps = {"k:a": {"simpler": 3}, "k:b": {"simpler": 2}, "k:c": {"deeper": 2}}
    assert learner.observed(taps, {}) == {"explanation_length": "short_3_sentences"}
    assert learner.observed({"k:a": {"simpler": 3}}, {}) == {}  # one lesson is not a habit
    slow = {c: speed(2.0) for c in ("k:a", "k:b", "k:c")}
    assert learner.observed({}, slow) == {"pace": "slow"}
    assert learner.observed({}, dict(list(slow.items())[:2])) == {}  # too few concepts


def test_a_generated_lessons_misconceptions_resolve_through_its_unit_pins(client, monkeypatch):
    _, concept = signed_in(client, monkeypatch)
    course, local = concept.split(":", 1)
    with Session(client.app.state.engine) as db, db.begin():
        db.add(SubjectRoot(id="maths", title="Maths"))
        db.flush()
        unit = RootUnit(
            root_id="maths",
            unit_key="x.beginner",
            topic="x",
            depth="beginner",
            content={"misconceptions": [{"id": "or_binds_first", "belief": "OR before AND"}]},
        )
        db.add(unit)
        db.flush()
        db.add(ConceptUnitPin(course_id=course, concept_id=local, unit_id=unit.id))
    with Session(client.app.state.engine) as db:
        assert learner.misconceptions_for(db, concept) == {"or_binds_first": "OR before AND"}
    me = client.get("/api/v1/me").json()
    box = Toolbox(client.app.state.engine, catalog(), me["id"])
    for tag in ("or_binds_first", "made_up"):
        text, failed = asyncio.run(
            box.run(
                "record_observation",
                {"concept": concept, "understanding": "shaky", "note": "n", "misconception": tag},
            )
        )
        assert not failed, text
    with Session(client.app.state.engine) as db:
        tags = [e.details.get("misconception") for e in db.scalars(select(Evidence))]
        enrollment = db.scalars(select(Enrollment)).one()
        snap = learner.snapshot(db, enrollment, now(), catalog=catalog())
    assert tags == ["or_binds_first", None]  # an unknown id is never stored
    b = learner.brief(snap)
    assert {
        "concept": concept,
        "tag": "or_binds_first",
        "misses": 1,
        "belief": "OR before AND",
    } in (b["misconceptions"])


def test_the_tutor_tool_for_preferences_is_offered_only_behind_the_flag(client, monkeypatch):
    signed_in(client, monkeypatch)
    me = client.get("/api/v1/me").json()
    plain = Toolbox(client.app.state.engine, catalog(), me["id"])
    assert "suggest_preference" not in {s.name for s in plain.specs}
    box = Toolbox(client.app.state.engine, catalog(), me["id"], profile_tools=True)
    assert "suggest_preference" in {s.name for s in box.specs}
    text, failed = asyncio.run(
        box.run("suggest_preference", {"key": "pace", "value": "slow", "reason": "Takes time"})
    )
    assert not failed and json.loads(text)["status"] == "waiting for the learner"
    with Session(client.app.state.engine) as db:
        user = db.scalars(select(User)).one()
        assert learner_profile.stored(user) == {}  # nothing applied
        assert learner_profile.profile(user)["pending"][0]["value"] == "slow"


def test_a_user_brief_serves_work_without_an_enrollment(client, monkeypatch):
    signed_in(client, monkeypatch)
    with Session(client.app.state.engine) as db, db.begin():
        user = db.scalars(select(User)).one()
        learner_profile.set_pref(user, "analogy_domain", "a kitchen", "onboarding", "")
    with Session(client.app.state.engine) as db:
        user = db.scalars(select(User)).one()
        b = learner.user_brief(db, user.id, now())
        assert learner.user_brief(db, "nobody", now()) == {}
        with pytest.raises(ValueError):
            learner.user_brief(db, user.id, now(), purpose="essay")
    assert b["purpose"] == "outline" and b["other_courses"]
    assert b["delivery"]["analogy_domain"] == "a kitchen" and len(json.dumps(b)) <= 3500


def test_the_profile_column_migrates_up_and_down(tmp_path):
    url = f"sqlite:///{tmp_path / 'p.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    engine = make_engine(url)

    def columns():
        return {c["name"] for c in sa.inspect(engine).get_columns("users")}

    assert "learner_profile" in columns()
    command.downgrade(config, "0051_course_brain")
    engine.dispose()
    engine = make_engine(url)
    assert "learner_profile" not in columns()
    engine.dispose()
