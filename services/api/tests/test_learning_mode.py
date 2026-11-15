"""The learner chooses how strict Socrat is. Modes change friction, never what counts."""

from test_gates import answer_gate
from test_learner_api import client, login, onboard  # noqa: F401  (client is a fixture)
from test_transfer import CONCEPT, check, classify, learner, wrong_choice

from socrat import learning_mode
from socrat.assistant.socratic import Ladder, reveal_eligibility
from socrat.catalog.registry import default_catalog
from socrat.mastery import transfer
from socrat.mastery.model import DAY, ConceptState
from socrat.planner import gates

NOW = 1_800_000_000


def test_unknown_or_missing_mode_is_balanced():
    assert learning_mode.policy(None).mode == "balanced"
    assert learning_mode.policy("nonsense").mode == "balanced"
    assert learning_mode.normalize("strict") == "strict"


def test_strict_keeps_the_original_rules():
    strict = learning_mode.policy("strict")
    assert strict.locks_modules
    assert strict.checkpoint_cooldown == gates.COOLDOWN_SECONDS
    assert strict.transfer_cooldown == transfer.COOLDOWN
    assert strict.reveal_needs_hint_ladder and strict.reveal_min_failed_submits == 2


def test_gentler_modes_never_make_the_learner_wait():
    for mode in ("relaxed", "balanced"):
        policy = learning_mode.policy(mode)
        assert policy.checkpoint_cooldown == 0 and policy.transfer_cooldown == 0
    assert not learning_mode.policy("relaxed").locks_modules
    assert learning_mode.policy("balanced").locks_modules


def test_reveal_needs_one_real_attempt_in_gentler_modes():
    fresh = Ladder()
    assert not reveal_eligibility(fresh, 0, 1, False)[0]  # never before trying
    assert reveal_eligibility(fresh, 1, 1, False)[0]
    assert reveal_eligibility(fresh, 0, 1, False)[1] == "submit 1 attempt first"
    # Strict (the defaults) still wants the hint ladder too.
    assert not reveal_eligibility(fresh, 1)[0]


def test_transfer_wait_follows_the_learners_cooldown():
    miss = {"state": "failed", "at": NOW}
    strong = ConceptState(alpha=40, beta=2, evidence_count=12, last_evidence_at=NOW)
    assert strong.mastered(NOW)  # the check is only "due" for a mastered concept
    assert transfer.status(miss, False, strong, True, NOW + 60) == "wait"
    assert transfer.status(miss, False, strong, True, NOW + 60, cooldown=0) == "due"


def test_mode_is_saved_on_the_account(client):  # noqa: F811
    headers = login(client)
    me = client.get("/api/v1/me").json()
    assert me["learning_mode"] == "balanced"
    response = client.patch("/api/v1/me", json={"learning_mode": "relaxed"}, headers=headers)
    assert response.status_code == 200 and response.json()["learning_mode"] == "relaxed"
    assert client.get("/api/v1/me").json()["learning_mode"] == "relaxed"
    bad = client.patch("/api/v1/me", json={"learning_mode": "lenient"}, headers=headers)
    assert bad.status_code == 422
    assert client.get("/api/v1/me").json()["learning_mode"] == "relaxed"


def test_relaxed_keeps_every_module_open_but_still_plans_the_checkpoint(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    catalog = default_catalog()
    first, second = gates.module_keys(catalog, "zero")[:2]
    later = gates.module_concepts(catalog, second)[0]
    assert client.get(f"/api/v1/concepts/{later}").status_code == 423  # balanced: locked

    client.patch("/api/v1/me", json={"learning_mode": "relaxed"}, headers=headers)
    assert client.get(f"/api/v1/concepts/{later}").status_code == 200
    start = client.post(f"/api/v1/activities/lesson:{later}/start", headers=headers)
    assert start.status_code == 200
    plan = client.get("/api/v1/plan").json()
    module = next(m for m in plan["modules"] if m["id"] == second)
    assert not module.get("locked_by")
    assert all(c["status"] != "locked" for c in module["concepts"])
    # The checkpoint is still there to show what the learner can do alone.
    assert client.get(f"/api/v1/quiz/{gates.gate_id(first)}").status_code == 200


def test_balanced_lets_a_missed_checkpoint_be_retried_straight_away(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    catalog = default_catalog()
    first, second = gates.module_keys(catalog, "zero")[:2]
    gate = gates.gate_id(first)
    failed = answer_gate(client, headers, gate, right=False)
    assert failed["gate"]["passed"] is False and failed["gate"]["retry_at"] is None
    retry = client.get(f"/api/v1/quiz/{gate}").json()
    assert retry["id"] != failed["id"] and not retry["completed"]  # a fresh attempt now
    # Still balanced: the next module waits for a pass, the bar is unchanged.
    later = gates.module_concepts(catalog, second)[0]
    assert client.get(f"/api/v1/concepts/{later}").status_code == 423


def test_leaving_strict_ends_a_wait_already_running(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    gate = gates.gate_id(gates.module_keys(default_catalog(), "zero")[0])
    client.patch("/api/v1/me", json={"learning_mode": "strict"}, headers=headers)
    failed = answer_gate(client, headers, gate, right=False)
    assert failed["gate"]["retry_at"]
    assert client.get(f"/api/v1/quiz/{gate}").json()["id"] == failed["id"]  # waiting
    client.patch("/api/v1/me", json={"learning_mode": "balanced"}, headers=headers)
    assert client.get(f"/api/v1/quiz/{gate}").json()["id"] != failed["id"]


def test_day_constant_matches_the_strict_wait():
    assert learning_mode.policy("strict").checkpoint_cooldown == DAY


def test_balanced_offers_a_new_transfer_problem_after_a_miss(client):  # noqa: F811
    headers = learner(client)
    view = check(client)
    missed = classify(client, headers, view, wrong_choice(view)).json()
    assert missed["correct"] is False  # the miss still counts as evidence
    again = check(client)
    assert again["state"] == "classify" and again["problem"]["id"] != view["problem"]["id"]
    assert classify(client, headers, view, CONCEPT).status_code == 409  # no second guess
