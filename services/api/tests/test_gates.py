"""Module gates: locking order, the compounding staircase, and the API flow end to end."""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from test_learner_api import client, login, onboard  # noqa: F401  (client is a fixture)

from socrat.catalog.registry import default_catalog
from socrat.learn import routes
from socrat.mastery.model import DAY, ConceptState
from socrat.planner import gates

NOW = 1_800_000_000


def test_staircase_climbs_on_correct_and_drops_on_misses():
    levels = [1, 2, 3]
    assert gates.evaluate([], levels, 3).next_level == 2
    assert gates.evaluate([(2, True)], levels, 3).next_level == 3
    assert gates.evaluate([(2, True), (3, True)], levels, 3).next_level == 3
    assert gates.evaluate([(2, False)], levels, 3).next_level == 1


def test_three_strikes_end_the_gate_and_fail_it():
    result = gates.evaluate([(2, False), (1, False), (1, False)], [1, 2, 3], 3)
    assert result.done and not result.passed and result.strikes == 3


def test_an_easy_streak_cannot_pass_without_hard_answers():
    easy = [(1, True)] * gates.MAX_ITEMS
    result = gates.evaluate(easy, [1, 2, 3], hard_available=4)
    assert result.done and result.score == 1.0 and not result.passed
    climbed = [(2, True), (3, True), (3, True)] + [(3, True)] * 7
    assert gates.evaluate(climbed, [1, 2, 3], hard_available=4).passed


def test_hard_requirement_shrinks_when_a_module_has_few_hard_items():
    answers = [(2, True), (3, True)] + [(2, True)] * 8
    assert gates.evaluate(answers, [1, 2, 3], hard_available=1).passed


# Pure logic: a GC or scheduler pause during a busy full run must not fail it as "too slow".
@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(st.lists(st.tuples(st.integers(1, 3), st.booleans()), max_size=20))
def test_gate_rules_hold_for_any_answer_sequence(answers):
    result = gates.evaluate(answers, [1, 2, 3], hard_available=3)
    if result.passed:
        assert result.done and result.score >= gates.PASS_SCORE
        assert result.strikes < gates.MAX_STRIKES and result.hard_correct >= 2
    assert result.next_level in (1, 2, 3)


def test_checkpoint_pool_only_asks_about_the_learners_language():
    from socrat.learn.quizzes import gate_pool

    cat = default_catalog()
    everything = gate_pool(cat, "zero:first-steps", "python")
    assert any(not q.fits("cpp") for _, q in everything)  # the module does have Python-only items
    cpp = gate_pool(cat, "zero:first-steps", "cpp")
    assert cpp and all(q.fits("cpp") for _, q in cpp)


def test_quiz_item_ids_are_unique_within_a_module():
    # Checkpoints track items by id, so a duplicate shadows its twin and can starve the hard level.
    cat = default_catalog()
    for course_id in cat.courses:
        for key in gates.module_keys(cat, course_id):
            ids = [q.id for c in gates.module_concepts(cat, key) for q in cat.concept(c).quiz]
            assert len(ids) == len(set(ids)), key


def test_renamed_items_still_resolve_from_stored_sessions():
    from socrat.learn.quizzes import item

    cat = default_catalog()
    assert item(cat, "zero:lists", "neighbours").id == "list-neighbours"
    assert item(cat, "zero:grids", "neighbours").id == "neighbours"
    assert item(cat, "dsa:union-find", "components").id == "union-components"


def test_modules_unlock_in_order_and_known_modules_are_cleared():
    catalog = default_catalog()
    keys = gates.module_keys(catalog, "zero")
    locked = gates.locked_modules(catalog, "zero", {}, set(), NOW)
    assert keys[0] not in locked and set(locked) == set(keys[1:])
    assert all(gate == gates.gate_id(keys[0]) for gate in locked.values())

    passed_first = gates.locked_modules(catalog, "zero", {}, {gates.gate_id(keys[0])}, NOW)
    assert keys[1] not in passed_first and passed_first[keys[2]] == gates.gate_id(keys[1])

    known = {c: ConceptState(assumed=True) for c in gates.module_concepts(catalog, keys[0])}
    assert keys[1] not in gates.locked_modules(catalog, "zero", known, set(), NOW)


def answer_gate(client, headers, gate: str, right: bool) -> dict:  # noqa: F811
    catalog = default_catalog()
    view = client.get(f"/api/v1/quiz/{gate}").json()
    while not view["completed"]:
        question = next(q for q in view["questions"] if not q["answered"])
        q = next(x for x in catalog.concept(question["concept"]).quiz if x.id == question["id"])
        correct = q.shown(view["id"])["answer"]
        choice = correct if right else (correct + 1) % len(q.options)
        view = client.post(
            f"/api/v1/quiz/{gate}/answer",
            json={"item": question["id"], "choice": choice},
            headers=headers,
        ).json()
    return view


def test_gate_locks_the_next_module_until_passed(client, monkeypatch):  # noqa: F811
    headers = login(client)
    onboard(client, headers)  # Programming from Zero, brand new: active immediately
    catalog = default_catalog()
    first, second = gates.module_keys(catalog, "zero")[:2]
    locked_concept = gates.module_concepts(catalog, second)[0]
    gate = gates.gate_id(first)

    concept = client.get(f"/api/v1/concepts/{locked_concept}")
    assert concept.status_code == 423  # No new instruction behind a locked prerequisite.
    start = client.post(f"/api/v1/activities/lesson:{locked_concept}/start", headers=headers)
    assert start.status_code == 423 and start.json()["error"]["code"] == "concept_locked"
    assert client.get(f"/api/v1/quiz/quiz:{locked_concept}").status_code == 423
    plan = client.get("/api/v1/plan").json()
    second_module = next(m for m in plan["modules"] if m["id"] == second)
    assert second_module["locked_by"]["gate"] == gate
    assert all(c["status"] == "locked" for c in second_module["concepts"])
    assert any("checkpoint" in r for r in plan["reasons"])

    failed = answer_gate(client, headers, gate, right=False)
    assert failed["gate"]["passed"] is False and failed["gate"]["strikes"] == 3
    assert failed["gate"]["retry_at"] and len(failed["questions"]) == 3
    assert all("answer" in q for q in failed["questions"])  # revealed at the end
    again = client.get(f"/api/v1/quiz/{gate}").json()
    assert again["id"] == failed["id"]  # cooling down: the last attempt, not a new one
    queue = client.get("/api/v1/plan").json()["days"][0]["items"]
    assert not any(i["id"] == gate for i in queue)

    real_now = routes.now
    monkeypatch.setattr(routes, "now", lambda: real_now() + 2 * DAY)
    passed = answer_gate(client, headers, gate, right=True)
    assert passed["gate"]["passed"] is True and passed["id"] != failed["id"]
    assert passed["gate"]["hard_correct"] >= passed["gate"]["hard_needed"]
    levels = [q["difficulty"] for q in passed["questions"]]
    assert levels[1] >= levels[0]  # harder after a correct answer
    assert client.get(f"/api/v1/concepts/{locked_concept}").json()["locked"] is None
    assert (
        client.post(
            f"/api/v1/activities/lesson:{locked_concept}/start", headers=headers
        ).status_code
        == 200
    )
