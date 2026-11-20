"""Lesson 0 plan PR 6 (``session_one_adaptation``): after session one the next session follows
the evidence, deterministically: a missed probe or a second missed check puts a worked example
first, success with help adds a short retrieval, independent success adds one stretch item after
the next concept. Completed work and evidence are never touched."""

from types import SimpleNamespace

from test_adaptive_engine import NOW, plan
from test_learner_api import client  # noqa: F401

from socrat.learn import quizzes
from socrat.mastery.model import DAY
from socrat.planner.engine import SESSION_ONE_WINDOW, Adaptive, session_one

ARRAYS = "algo:arrays"
DONE = {f"lesson:{ARRAYS}", f"quiz:{ARRAYS}"}
ON = Adaptive(course_id="algo", goal={"adapt_first_session": True})


def check(score, assistance=0, at=NOW - DAY, concept=ARRAYS, kind="quiz", **details):
    return dict(
        kind=kind, score=score, assistance=assistance, concept=concept, at=at, details=details
    )


def ids(history, adaptive=ON, completed=DONE):
    return [a.id for a in plan(completed=completed, history=history, adaptive=adaptive).queue]


def test_session_one_reads_the_first_day_only():
    assert session_one([check(1.0)]) == {ARRAYS: "independent"}
    assert session_one([check(0.9, probe_missed=True)]) == {ARRAYS: "difficulty"}
    assert session_one([check(0.4), check(0.6)]) == {ARRAYS: "difficulty"}
    assert session_one([check(0.4)]) == {}  # one miss: the failed-check refresh handles it
    helped = [check(1.0, kind="code", assistance=2), check(0.9)]
    assert session_one(helped) == {ARRAYS: "helped"}
    later = [check(1.0), check(0.2, concept="algo:bfs", at=NOW), check(0.2, concept="algo:bfs")]
    assert session_one(later) == {ARRAYS: "independent"}  # day two is not session one
    assert session_one([check(1.0)] * SESSION_ONE_WINDOW) == {}  # the window no longer reaches it
    assert session_one([{"kind": "quiz", "score": 1.0, "concept": ARRAYS}]) == {}  # no dates


def test_a_missed_probe_puts_a_worked_example_first():
    queue = ids([check(0.9, probe_missed=True)])
    assert queue.index(f"example:{ARRAYS}") < queue.index("lesson:algo:two-pointers")
    assert f"example:{ARRAYS}" not in ids([check(0.9, probe_missed=True)], Adaptive("algo"))


def test_success_with_help_adds_a_short_retrieval_before_moving_on():
    queue = ids([check(1.0, kind="code", assistance=2), check(0.9)])
    assert f"review:{ARRAYS}" in queue
    assert queue.index(f"review:{ARRAYS}") < queue.index("lesson:algo:two-pointers")


def test_independent_success_adds_one_stretch_after_the_next_concept():
    queue = ids([check(1.0)])
    stretch = queue.index(f"stretch:{ARRAYS}")
    assert queue.index("quiz:algo:two-pointers") < stretch
    assert queue.count(f"stretch:{ARRAYS}") == 1
    assert f"stretch:{ARRAYS}" not in ids([check(1.0)], completed=DONE | {f"stretch:{ARRAYS}"})


def test_without_the_flag_the_plan_is_unchanged():
    history = [check(1.0)]
    assert ids(history, Adaptive("algo")) == ids(history, Adaptive("algo", goal={}))
    assert not any(i.startswith(("stretch:", "example:")) for i in ids(history, Adaptive("algo")))


def test_a_wrong_answer_on_the_probe_item_marks_the_evidence(monkeypatch):
    recorded = []
    monkeypatch.setattr(quizzes, "item", lambda cat, c, i: SimpleNamespace(probe=i == "p1"))
    monkeypatch.setattr(quizzes.learn, "elapsed", lambda *a: 60)
    monkeypatch.setattr(quizzes.learn, "expected_seconds", lambda *a: 60)
    monkeypatch.setattr(quizzes.learn, "record_evidence", lambda *a, **k: recorded.append(k))
    monkeypatch.setattr(quizzes, "settle_check", lambda *a: True)
    monkeypatch.setattr(quizzes, "score_of", lambda *a: 0.5)
    session = SimpleNamespace(
        activity_id=f"quiz:{ARRAYS}",
        items=[[ARRAYS, "p1"], [ARRAYS, "q2"]],
        answers={"p1": {"choice": 0, "correct": False}, "q2": {"choice": 1, "correct": True}},
        completed_at=None,
    )
    enrollment = SimpleNamespace(language="python")
    quizzes.finish(None, None, None, enrollment, session, NOW)
    assert recorded[0]["details"] == {"probe_missed": True}
    session.answers["p1"]["correct"] = True
    session.completed_at = None
    quizzes.finish(None, None, None, enrollment, session, NOW)
    assert recorded[1]["details"] is None


def test_enrolment_asks_for_it_only_for_a_lesson0_course_with_the_flag_on(client):  # noqa: F811
    from sqlalchemy.orm import Session
    from test_learner_api import login, onboard

    from socrat.models import Enrollment, User

    def goal(name):
        with Session(client.app.state.engine) as db:
            user = db.query(User).filter_by(display_name=name).one()
            return db.query(Enrollment).filter_by(user_id=user.id).one().goal

    client.app.state.settings.session_one_adaptation = True
    onboard(client, login(client, subject="ada", name="Ada"), course="basics", session_minutes=10)
    assert goal("Ada")["adapt_first_session"] is True
    onboard(client, login(client, subject="bob", name="Bob"), course="basics")  # no Lesson 0
    assert "adapt_first_session" not in goal("Bob")
    client.app.state.settings.session_one_adaptation = False
    onboard(client, login(client, subject="cy", name="Cy"), course="basics", session_minutes=10)
    assert "adapt_first_session" not in goal("Cy")


# ------------------------------------------------------------------ backlog 2.4


def test_tutor_turns_that_day_count_as_help():
    assert session_one([check(0.9)], {ARRAYS}) == {ARRAYS: "helped"}
    assert session_one([check(0.9)], {"algo:pairs"}) == {ARRAYS: "independent"}


def test_the_learner_layer_reads_tutor_turns_in_a_window(client):  # noqa: F811
    from sqlalchemy.orm import Session
    from test_learner_api import login

    from socrat import learner
    from socrat.models import AssistantMessage, AssistantThread, User

    login(client, subject="ada", name="Ada")
    with Session(client.app.state.engine) as db, db.begin():
        ada = db.query(User).one().id
        for scope, role, at in (
            (f"concept:{ARRAYS}", "user", 100),
            ("concept:algo:pairs", "assistant", 100),  # the tutor talking alone is not help
            ("concept:algo:lookup", "user", 900),  # outside the window
            ("problem:arr-easy", "user", 100),  # submissions record their own help
        ):
            thread = AssistantThread(user_id=ada, scope=scope, ladder={})
            db.add(thread)
            db.flush()
            db.add(AssistantMessage(thread_id=thread.id, role=role, content="?", created_at=at))
    with Session(client.app.state.engine) as db:
        assert learner.tutored_concepts(db, ada, 0, 500) == {ARRAYS}


def test_difficulty_offers_at_most_one_bridge():
    pairs = "algo:pairs"
    history = [check(0.9, probe_missed=True), check(0.9, concept=pairs, probe_missed=True)]
    done = DONE | {f"lesson:{pairs}", f"quiz:{pairs}"}
    found = plan(completed=done, history=history, adaptive=ON).needs_repair
    assert list(found) == [ARRAYS]  # one proposal, for the first concept that was hard
    assert plan(completed=done, history=history, adaptive=Adaptive("algo")).needs_repair == {}


def test_a_hard_concept_gets_a_smaller_easier_check():
    from test_adaptive_engine import catalog

    from socrat.models import Enrollment

    cat, enrollment = catalog(), Enrollment(id="e1", language="python")
    full = quizzes.choose_items(cat, enrollment, f"quiz:{ARRAYS}", 1)
    gentle = quizzes.choose_items(cat, enrollment, f"quiz:{ARRAYS}", 1, gentle=True)
    pool = quizzes.fitting(cat, ARRAYS, "python")
    levels = sorted({q.difficulty for q in pool})[:2]
    assert gentle and len(gentle) <= min(len(full), quizzes.GENTLE_ITEMS)
    assert all(quizzes.item(cat, c, i).difficulty in levels for c, i in gentle)
    hardest = max(quizzes.item(cat, c, i).difficulty for c, i in full)
    assert max(quizzes.item(cat, c, i).difficulty for c, i in gentle) < hardest


def test_the_tutor_ladder_starts_one_rung_along_after_difficulty(client, monkeypatch):  # noqa: F811
    from sqlalchemy.orm import Session
    from test_adaptive_engine import catalog
    from test_learner_api import login, onboard

    from socrat.assistant import service
    from socrat.models import AssistantThread, User

    ada = login(client, subject="ada", name="Ada")
    onboard(client, ada, course="algo")
    state = client.app.state

    def ceiling(verdict):
        monkeypatch.setattr(service.learn, "session_one_for", lambda db, e: {ARRAYS: verdict})
        with Session(state.engine) as db, db.begin():
            db.query(AssistantThread).delete()
            user = db.query(User).one()
            service.prepare(
                db, catalog(), state.settings, user, "problem:arr-easy", "ok", "", "", False, NOW
            )
            thread = db.query(AssistantThread).one()
            return thread.ladder["state"]["ceiling"]

    assert ceiling("difficulty") == 1
    assert ceiling("independent") == 0


# ------------------------------------------------------------------ backlog 3.3 (served courses)


def test_a_served_learners_lesson0_gap_gets_a_worked_example_before_the_check():
    from test_adaptive_engine import catalog

    from socrat import learner
    from socrat.models import Enrollment

    mine = {"calibration": {"detected_gaps": ["arrays", "medieval tax law"]}}
    gaps = learner.lesson0_gaps(catalog(), Enrollment(course_id="algo", learner_plan=mine))
    assert gaps == {ARRAYS}  # matched by code; the unmatched gap is left alone
    assert learner.lesson0_gaps(catalog(), Enrollment(course_id="algo", learner_plan={})) == set()
    from test_adaptive_engine import NOW, TODAY

    from socrat.planner.engine import build_plan

    cat = catalog()
    queue = [
        a.id
        for a in build_plan(
            cat, cat.course_concepts("algo"), {}, set(), [], TODAY, NOW, {0, 2, 4}, 45, gaps=gaps
        ).queue
    ]
    assert queue.index(f"lesson:{ARRAYS}") < queue.index(f"example:{ARRAYS}")
    assert queue.index(f"example:{ARRAYS}") < queue.index(f"quiz:{ARRAYS}")
