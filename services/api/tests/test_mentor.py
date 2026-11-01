"""The mentor: bounded automatic moves, a visible reason for each, undo, and learner-first."""

from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401
from test_style_engine import admin_headers

from socrat.adaptive.profile import SkillProfile
from socrat.adaptive.service import overrides_with_mentor
from socrat.adaptive.stuck import Stuck
from socrat.catalog.registry import default_catalog
from socrat.mastery.model import DAY
from socrat.mentor import policy, service
from socrat.mentor import state as saved
from socrat.models import Enrollment, User

NOW = 1_800_000_000
TITLES = {"c:a": "Forces", "c:b": "Energy", "c:c": "Momentum"}


def profile(concept="c:a", **kw) -> SkillProfile:
    base = dict(concept=concept, mastery=0.5, confidence=0.5, band="developing", attempts=5)
    return SkillProfile(**(base | kw))


def stuck(concept="c:a", severity=2) -> Stuck:
    return Stuck(concept, severity, ("plateau", "failing"), "concept_gap", "Stuck signs: plateau.")


def decide(skill, stuck_map=None, state=None, feel=None):
    return policy.decide(skill, stuck_map or {}, state or {}, TITLES, NOW, feel)


def test_a_struggling_learner_gets_smaller_steps_with_a_reason():
    moves = decide({"c:a": profile(recent_failures=3)})
    assert [m.kind for m in moves] == ["pace_down"]
    assert "smaller steps" in moves[0].why.lower() and "Forces" in moves[0].why


def test_a_fast_accurate_learner_moves_faster():
    fast = profile(band="strong", hint_dependence=0.0, speed=0.6, trend=0.1)
    assert [m.kind for m in decide({"c:a": fast})] == ["pace_up"]
    hinted = profile(band="strong", hint_dependence=0.3, speed=0.6)
    assert decide({"c:a": hinted}) == []  # needing any help means it is not "easy"


def test_what_the_learner_said_wins_and_too_little_evidence_means_no_move():
    assert decide({"c:a": profile(recent_failures=4)}, feel={"c:a": "easy"}) == []
    assert decide({"c:a": profile(recent_failures=4, attempts=2)}) == []


def test_a_stuck_concept_is_explained_another_way_and_cycles_through_the_styles():
    first = decide({"c:a": profile()}, {"c:a": stuck()})
    assert [m.kind for m in first] == ["explain"] and first[0].value == 0
    state: dict = {"explain": {"c:a": 0}}
    assert decide({"c:a": profile()}, {"c:a": stuck()}, state)[0].value == 1
    assert decide({"c:a": profile()}, {"c:a": stuck(severity=1)}) == []  # mild: leave it alone


def test_faded_knowledge_earns_a_recall_warmup_and_the_run_is_capped():
    old = NOW - 12 * DAY
    faded = {
        c: profile(c, band="strong", mastery=0.4, last_seen_at=old, attempts=0) for c in TITLES
    }
    moves = decide(faded)
    assert [m.kind for m in moves] == ["recall"] * 3
    many = {f"c:{i}": profile(f"c:{i}", recent_failures=3) for i in range(8)}
    assert len(decide(many)) == policy.MAX_MOVES


def test_a_move_is_logged_applied_and_undone_and_the_mentor_does_not_redo_it():
    state: dict = {}
    move = decide({"c:a": profile(recent_failures=3)})[0]
    entry = saved.apply(state, move, NOW)
    assert state["feel"] == {"c:a": "hard"} and entry["why"] == move.why
    # Cooldown: the same move is not repeated right away.
    assert decide({"c:a": profile(recent_failures=3)}, state=state) == []
    undone = saved.undo(state, entry["id"], NOW + 10)
    assert undone is not None and state["feel"] == {}
    assert state["log"][0]["undone"] is True
    assert saved.undo(state, entry["id"], NOW + 20) is None  # only once
    later = NOW + 5 * DAY  # past the normal cooldown, inside the longer undo lock
    assert decide({"c:a": profile(recent_failures=3)}, state=state) == []
    assert policy.decide({"c:a": profile(recent_failures=3)}, {}, state, TITLES, later) == []


def test_the_planner_sees_mentor_pace_but_the_learners_word_wins():
    data = {
        "mentor": {"feel": {"c:a": "hard", "c:b": "easy"}},
        "overrides": {"feel": {"c:a": "easy"}},
    }
    assert overrides_with_mentor(data)["feel"] == {"c:a": "easy", "c:b": "easy"}
    assert "feel" not in overrides_with_mentor({})


def test_the_tutor_is_told_how_to_teach_this_learner():
    state = {"feel": {"c:a": "hard"}, "explain": {"c:a": 1}, "recall": ["c:b"]}
    text = saved.note(state, "c:a", TITLES)
    assert "smaller steps" in text and "Explain it this way" in text and "Energy" in text
    assert saved.note(state, "c:z", TITLES) == "Open with one short recall question on: Energy."
    assert saved.note({}, "c:a", TITLES) == ""


def test_the_mentor_api_is_admin_only_and_records_nothing_without_evidence(client):  # noqa: F811
    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner)
    assert client.get("/api/v1/mentor", headers=learner).status_code == 404
    assert client.post("/api/v1/mentor/refresh", headers=learner).status_code == 404
    admin = admin_headers(client)
    onboard(client, admin)
    assert client.get("/api/v1/mentor", headers=admin).json() == {"log": [], "recall": []}
    assert client.post("/api/v1/mentor/refresh", headers=admin).json()["log"] == []
    assert client.post("/api/v1/mentor/undo", json={"id": "nope"}, headers=admin).status_code == 404


def test_refresh_applies_a_move_revises_the_plan_and_undo_restores_it(client, monkeypatch):  # noqa: F811
    admin = admin_headers(client)
    onboard(client, admin)
    move = policy.Move(
        "pace_down", "zero:loops", "Smaller steps on Loops", "Misses lately.", "hard"
    )
    monkeypatch.setattr(policy, "decide", lambda *a, **k: [move])
    shown = client.post("/api/v1/mentor/refresh", headers=admin).json()
    assert shown["log"][0]["title"] == "Smaller steps on Loops" and not shown["log"][0]["undone"]
    with Session(client.app.state.engine) as db:
        enrollment = db.query(Enrollment).join(User).filter(User.subject == "boss").one()
        assert enrollment.adaptive["mentor"]["feel"] == {"zero:loops": "hard"}
        note = service.tutor_note(enrollment, default_catalog(), "concept:zero:loops")
        assert "smaller steps" in note
    monkeypatch.undo()
    back = client.post("/api/v1/mentor/undo", json={"id": shown["log"][0]["id"]}, headers=admin)
    assert back.json()["log"][0]["undone"] is True
