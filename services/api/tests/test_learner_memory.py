"""How a lesson is read reaches the coach, the tutor and the learner (``lesson_signals``).

Counters only: a signal can make the stuck detector look, it can never move mastery.
"""

# ruff: noqa: F811
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_drills import _first_open_concept
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.adaptive import profile, stuck
from socrat.learn import memory
from socrat.mastery.model import ConceptState
from socrat.models import ActivityRecord, Enrollment, Evidence
from socrat.models import ConceptState as ConceptRow


def learner(client, monkeypatch, subject="mia"):
    monkeypatch.setattr("socrat.drills.routes.require_feature", lambda *a: None)
    headers = login(client, subject=subject, name=subject.title())
    onboard(client, headers)
    return headers, _first_open_concept(client, headers)[1]


def send(client, headers, concept, **body):
    return client.post(f"/api/v1/concepts/{concept}/signals", json=body, headers=headers)


def test_signals_are_off_by_default_and_refuse_what_is_not_this_learners(client, monkeypatch):
    headers, concept = learner(client, monkeypatch)
    assert send(client, headers, concept, kind="simpler").status_code == 404
    assert client.get("/api/v1/memory", headers=headers).status_code == 404
    client.app.state.settings.lesson_signals = True
    assert send(client, headers, concept, kind="simpler").status_code == 204
    assert send(client, headers, "dsa:complexity", kind="simpler").status_code == 404
    assert send(client, headers, concept, kind="cheer").status_code == 422
    assert send(client, headers, concept, kind="page", page=900).status_code == 422


def test_signals_are_counted_per_lesson_and_never_touch_mastery_or_progress(client, monkeypatch):
    headers, concept = learner(client, monkeypatch)
    client.app.state.settings.lesson_signals = True

    def mastery():
        with Session(client.app.state.engine) as db:
            return {(r.concept, str(r.state)) for r in db.scalars(select(ConceptRow))}

    before = mastery()
    for body in (
        {"kind": "page", "page": 3},
        {"kind": "page", "page": 2},  # going back does not lower the furthest page
        {"kind": "simpler"},
        {"kind": "simpler"},
        {"kind": "reread"},
        {"kind": "question"},
    ):
        assert send(client, headers, concept, **body).status_code == 204
    with Session(client.app.state.engine) as db:
        enrollment = db.scalars(select(Enrollment)).one()
        seen = memory.signals(db, enrollment)[concept]
        assert (seen["pages"], seen["simpler"], seen["reread"], seen["question"]) == (3, 2, 1, 1)
        record = db.get(ActivityRecord, (enrollment.id, f"signal:{concept}"))
        assert record is not None and record.completed_at is None  # never a finished step
        assert db.scalars(select(Evidence)).all() == []  # not evidence
    assert mastery() == before  # mastery untouched


def test_a_counter_stops_at_its_ceiling():
    class Db:
        def __init__(self):
            self.record = None

        def get(self, model, key):
            return self.record

        def add(self, record):
            self.record = record

    db = Db()
    enrollment = type("E", (), {"id": "e1"})()
    for _ in range(memory.MOST + 20):
        seen = memory.note(db, enrollment, "k:l", memory.Signal(kind="simpler"), 10)
    assert seen["simpler"] == memory.MOST


def test_reading_signs_join_the_stuck_signals_but_never_decide_alone():
    def built(**reading):
        return profile.build("k:l", ConceptState(), [], 0, reading=reading)

    quiet = built(simpler=1, reread=1)
    assert stuck.signals(quiet, 0) == []
    loud = built(simpler=2, reread=3)
    assert (loud.simpler_requests, loud.rereads) == (2, 3)
    assert stuck.signals(loud, 0) == ["asked_simpler", "rereading"]
    assert stuck.detect(loud, 0) is None  # nothing scored yet: reading alone is not stuck
    assert built().simpler_requests == 0
    for name in ("asked_simpler", "rereading"):
        assert name in stuck.SIGNAL_WORDS


def test_the_memory_is_short_plain_and_given_to_the_tutor(client, monkeypatch):
    from socrat.assistant import service as assistant
    from socrat.learn.routes import catalog
    from socrat.models import User, now

    headers, concept = learner(client, monkeypatch)
    cat = catalog()
    title = cat.concept(concept).title

    def sections():
        with Session(client.app.state.engine) as db:
            user = db.scalars(select(User)).one()
            enrollment = db.scalars(select(Enrollment)).one()
            return assistant.learner_sections(db, cat, user, enrollment, now())

    assert "what_socrat_has_noticed" not in sections()  # nothing recorded: nothing changes
    client.app.state.settings.lesson_signals = True
    assert client.get("/api/v1/memory", headers=headers).json() == {"items": []}
    for kind in ("simpler", "simpler", "simpler", "reread", "deeper"):
        send(client, headers, concept, kind=kind)
    items = client.get("/api/v1/memory", headers=headers).json()["items"]
    assert items == [
        {
            "kind": "simpler",
            "concept": concept,
            "text": f"Asked for a simpler explanation of {title} 3 times.",
        }
    ]  # one reread or one "deeper" tap is not worth remembering
    assert sections()["what_socrat_has_noticed"] == items[0]["text"]


def test_practice_results_are_remembered_latest_set_per_lesson():
    def record(at, concept, *marks, answered=None):
        return ActivityRecord(
            enrollment_id="e1",
            activity_id=f"drill:{at}",
            started_at=at,
            outcome={
                "concept": concept,
                "questions": [{}] * len(marks),
                "answers": {
                    str(i): {"correct": m}
                    for i, m in enumerate(marks[: answered if answered is not None else len(marks)])
                },
            },
        )

    class Db:
        def scalars(self, query):
            return [
                record(1, "k:a", True, True),
                record(2, "k:a", False, False, True, False),  # the later set wins
                record(3, "k:b", True, True, True),
                record(4, "k:c", True, False, answered=1),  # unfinished: not a result
            ]

    assert memory.practice(Db(), type("E", (), {"id": "e1"})()) == {
        "k:a": {"correct": 1, "questions": 4},
        "k:b": {"correct": 3, "questions": 3},
    }
