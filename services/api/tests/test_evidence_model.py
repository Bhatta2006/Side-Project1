"""Evidence types and stages (master prompt 9.2, 9.3, 9.5) and confidence calibration (8.1)."""

# ruff: noqa: F811
from types import SimpleNamespace

from test_learner_api import client, login  # noqa: F401

from socrat.mastery import evidence
from socrat.mastery.model import DAY, ConceptState

MASTERED = ConceptState(alpha=20, beta=1, evidence_count=6)
LOW = ConceptState(alpha=2, beta=4, evidence_count=3)
MID = ConceptState(alpha=4, beta=3, evidence_count=4)
NOW = 100 * DAY


def ev(kind, score=1.0, assistance=0, day=0.0):
    return SimpleNamespace(kind=kind, score=score, assistance=assistance, created_at=int(day * DAY))


def test_no_evidence_is_unknown_and_recognition_alone_is_emerging():
    assert evidence.summarise([], ConceptState(), NOW).stage == "unknown"
    got = evidence.summarise([ev("quiz"), ev("quiz")], LOW, NOW)
    assert got.stage == "emerging" and got.by_type == {"recognition": 2}
    assert "recall or apply" in got.reasons[0]


def test_applied_evidence_below_the_bar_is_developing():
    got = evidence.summarise([ev("code"), ev("quiz", 0.2)], MID, NOW)
    assert got.stage == "developing" and got.by_type == {"application": 1}


def test_mastery_estimate_alone_is_proficient_until_shown_alone_and_lasting():
    # At the bar on quizzes only: proficient, never demonstrated.
    assert evidence.summarise([ev("quiz"), ev("quiz", day=2)], MASTERED, NOW).stage == "proficient"
    # Applied alone, but nothing held after a delay or in a new context yet.
    same_day = evidence.summarise([ev("code"), ev("code", day=0.2)], MASTERED, NOW)
    assert same_day.stage == "proficient" and "last" in same_day.reasons[0]
    # Applied alone and it held a day later: demonstrated.
    held = evidence.summarise([ev("code"), ev("review", day=3)], MASTERED, NOW)
    assert held.stage == "demonstrated" and held.delayed == 1
    # Or applied alone and transferred to something new.
    moved = evidence.summarise([ev("code"), ev("transfer", day=0.5)], MASTERED, NOW)
    assert moved.stage == "demonstrated"


def test_a_full_solution_needs_an_unaided_follow_up():
    shown = [ev("code"), ev("review", day=3), ev("code", assistance=evidence.FULL_SOLUTION, day=4)]
    got = evidence.summarise(shown, MASTERED, NOW)
    assert got.stage == "proficient" and got.needs_follow_up and got.assisted == 1
    followed = [*shown, ev("code", day=5)]
    again = evidence.summarise(followed, MASTERED, NOW)
    assert again.stage == "demonstrated" and not again.needs_follow_up
    # An assisted retry is not a follow-up.
    helped = evidence.summarise([*shown, ev("code", assistance=2, day=5)], MASTERED, NOW)
    assert helped.needs_follow_up


def test_tutor_observations_never_count_as_success():
    got = evidence.summarise([ev("tutor", 0.5), ev("tutor", 1.0)], LOW, NOW)
    assert got.by_type == {} and got.stage == "emerging"


def test_calibration_compares_stated_confidence_with_accuracy():
    assert evidence.calibration([]) is None
    over = evidence.calibration([(1.0, False), (1.0, True), (1.0, False), (1.0, True)])
    assert over == dict(rated=4, confidence=1.0, accuracy=0.5, gap=0.5, brier=0.5)
    honest = evidence.calibration([(1.0, True), (0.0, False)])
    assert honest["gap"] == 0.0 and honest["brier"] == 0.0


def test_rated_quiz_answers_feed_calibration_and_the_evidence_view(client):
    from test_learner_api import onboard

    from socrat.catalog.registry import default_catalog

    headers = login(client)
    onboard(client, headers)
    assert client.get("/api/v1/progress/calibration").json() == {"calibration": None}
    url = "/api/v1/quiz/quiz:zero:programs-and-output"
    quiz = client.get(url).json()
    answers = {
        q.id: q.shown(quiz["id"])["answer"]
        for q in default_catalog().concept("zero:programs-and-output").quiz
    }
    for n, question in enumerate(quiz["questions"]):
        body = {"item": question["id"], "choice": answers[question["id"]]}
        if n == 0:
            body["confidence"] = 4  # certain, and right
        client.post(f"{url}/answer", json=body, headers=headers)
    got = client.get("/api/v1/progress/calibration").json()["calibration"]
    assert got["rated"] == 1 and got["confidence"] == 1.0 and got["accuracy"] == 1.0
    bad = client.post(
        f"{url}/answer", json={"item": "x", "choice": 0, "confidence": 9}, headers=headers
    )
    assert bad.status_code == 422
    view = client.get("/api/v1/concepts/zero:programs-and-output").json()["evidence"]
    assert view["by_type"] == {"recognition": 1} and view["stage"] in {"emerging", "proficient"}
