"""The starting-level check: valid questions only, key stays server-side, level from answers."""
# ruff: noqa: F811

import json

import pytest
from test_coursegen import OUTLINE, Scripted, run
from test_learner_api import client, login  # noqa: F401
from test_learning_requests import URL, model_returning, on  # noqa: F401

from socrat.catalog import generated
from socrat.coursegen import diagnostic
from socrat.models import Diagnostic


def item(concept, answer=1, **over):
    base = dict(
        concept=concept,
        stem=f"What is true about {concept}?",
        options=["A wrong idea one", "The correct idea.", "A wrong idea two", "A wrong idea 3"],
        answer=answer,
        why="Because of the definition.",
    )
    return base | over


def outline_course(on, ada):
    made = on.post(URL, json={"text": "Teach me machine learning"}, headers=ada).json()
    on.post(f"{URL}/{made['id']}/confirm", json={}, headers=ada)
    script = Scripted(
        architect=[json.dumps(OUTLINE)],
        critic=[json.dumps({"verdict": "pass", "summary": "ok", "issues": []})],
    )
    assert run(on, script)
    return made["id"]


def use_model(monkeypatch, payload):
    _, make = model_returning(payload)
    monkeypatch.setattr(diagnostic, "make", make)


def test_clean_drops_leaky_duplicate_and_unknown_items_and_remaps_the_key():
    leaky = item(
        "a", options=["No.", "This one is very much longer than the others by far", "No!", "No?"]
    )
    dup = item("b", options=["same", "same", "x y z", "q r s"])
    ok = item("c", answer=1)
    got = diagnostic.clean([leaky, dup, item("zzz"), ok, ok], ["a", "b", "c"], "seed")
    assert [g["concept"] for g in got] == ["c"]
    assert got[0]["options"][got[0]["answer"]] == "The correct idea."


def test_without_a_model_there_is_no_invented_check(on):
    ada = login(on)
    rid = outline_course(on, ada)
    assert on.post(f"{URL}/{rid}/diagnostic", headers=ada).status_code == 503


def test_check_end_to_end(on, monkeypatch):
    ada = login(on)
    rid = outline_course(on, ada)
    use_model(monkeypatch, {"items": [item("what-is-ml"), item("loss")]})
    # Two valid items is below the minimum of three.
    assert on.post(f"{URL}/{rid}/diagnostic", headers=ada).status_code == 502


def test_scoring_picks_the_level_and_the_key_never_reaches_the_learner(on, monkeypatch):
    from sqlalchemy.orm import Session

    ada = login(on)
    rid = outline_course(on, ada)
    course_id = on.get(f"{URL}/{rid}").json()["course_id"]
    with Session(on.app.state.engine) as db:
        course = generated.course(db, course_id)
    probes = diagnostic.probe_concepts(course)
    assert len(probes) == 2  # the outline has two concepts: fewer than the minimum

    assert diagnostic.MIN_ITEMS == 3 and course.levels[1].start_concept == "loss"

    items = [
        dict(concept="what-is-ml", stem="s" * 12, options=list("abcd"), answer=2, why="w"),
        dict(concept="loss", stem="t" * 12, options=list("abcd"), answer=0, why="w"),
    ]
    assert diagnostic.public(items)[0].keys() == {"concept", "stem", "options"}
    miss_first = diagnostic.score(course, items, [0, 0])
    assert miss_first["level"] == "brand-new" and miss_first["correct"] == 1
    got_first_missed_second = diagnostic.score(course, items, [2, 3])
    assert got_first_missed_second["level"] == "some"  # starts at "loss", the missed concept
    perfect = diagnostic.score(course, items, [2, 0])
    assert perfect["level"] == "some" and perfect["correct"] == 2
    with pytest.raises(ValueError):
        diagnostic.score(course, items, [2])


def test_api_flow_with_three_concepts(on, monkeypatch):
    """Use a three-concept outline so the minimum of three questions is reachable."""
    from sqlalchemy.orm import Session
    from test_coursegen import concept

    ada = login(on)
    made = on.post(URL, json={"text": "Teach me machine learning"}, headers=ada).json()
    on.post(f"{URL}/{made['id']}/confirm", json={}, headers=ada)
    outline = json.loads(json.dumps(OUTLINE))
    outline["modules"][0]["concepts"].append(concept("overfitting", ["loss"], "practitioner"))
    script = Scripted(
        architect=[json.dumps(outline)],
        critic=[json.dumps({"verdict": "pass", "summary": "ok", "issues": []})],
    )
    assert run(on, script)
    use_model(
        monkeypatch,
        {"items": [item("what-is-ml"), item("loss"), item("overfitting")]},
    )
    first = on.post(f"{URL}/{made['id']}/diagnostic", headers=ada).json()
    assert len(first["questions"]) == 3 and not first["done"]
    assert "answer" not in json.dumps(first) and "why" not in json.dumps(first)
    again = on.post(f"{URL}/{made['id']}/diagnostic", headers=ada).json()
    assert again["id"] == first["id"]  # one check per request

    with Session(on.app.state.engine) as db:
        stored = db.query(Diagnostic).one()
        key = [i["answer"] for i in stored.items]

    short = on.post(f"{URL}/{made['id']}/diagnostic/answer", json={"answers": [0]}, headers=ada)
    assert short.status_code == 422
    # Right on the first two, wrong on the third: starts at "loss" (level "some").
    wrong = (key[2] + 1) % 4
    done = on.post(
        f"{URL}/{made['id']}/diagnostic/answer",
        json={"answers": [key[0], key[1], wrong]},
        headers=ada,
    ).json()
    assert done["done"] and done["result"]["correct"] == 2 and done["result"]["level"] == "some"
    view = on.get(f"{URL}/{made['id']}").json()
    assert view["diagnostic"] == "done"
    # A second submission cannot change the stored result.
    stuck = on.post(
        f"{URL}/{made['id']}/diagnostic/answer", json={"answers": [wrong] * 3}, headers=ada
    ).json()
    assert stuck["result"]["correct"] == 2
    # Another learner cannot read it.
    login(on, subject="bob", name="Bob")
    assert on.get(f"{URL}/{made['id']}/diagnostic").status_code == 404
