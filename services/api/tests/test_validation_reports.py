"""Validation reports (master prompt 12): five states decided by code from the gates and the
checkers' structured replies, stored per round, shown to learners as a plain label, and cleared
only by a named person when automated checks cannot vouch for a subject."""

# ruff: noqa: F811
from sqlalchemy.orm import Session
from test_learner_api import client, login  # noqa: F401

from socrat.coursegen import validation
from socrat.engine import domains

MATH = domains.ADAPTERS["math-science"]
MUSIC = domains.ADAPTERS["music"]
BAR = {"correctness": 5, "clarity": 4}
GOOD = {"correctness": 5, "clarity": 4}


def test_gate_problems_mean_revision_without_asking_the_checkers():
    status, found = validation.assess(
        ["quiz q1: answer out of range"], None, None, {}, BAR, MATH, []
    )
    assert status == "needs_revision"
    assert found[0].source == "gates" and found[0].severity == "blocking"


def test_wrong_fact_or_low_score_blocks_and_imprecise_only_warns():
    wrong = {
        "claims": [{"where": "lesson", "claim": "2+2=5", "verdict": "incorrect", "correction": "4"}]
    }
    assert validation.assess([], wrong, {}, GOOD, BAR, MATH, [])[0] == "needs_revision"
    assert (
        validation.assess([], {"claims": []}, {}, {"correctness": 4, "clarity": 5}, BAR, MATH, [])[
            0
        ]
        == "needs_revision"
    )
    assert validation.assess([], None, {}, GOOD, BAR, MATH, [])[0] == "needs_revision"  # no reply
    vague = {"claims": [{"where": "quiz q2", "claim": "about 3", "verdict": "imprecise"}]}
    status, found = validation.assess([], vague, {}, GOOD, BAR, MATH, [])
    assert status == "pass_with_warnings" and found[0].where == "quiz q2"
    assert validation.assess([], {"claims": []}, {}, GOOD, BAR, MATH, [])[0] == "pass"


def test_unverifiable_subjects_and_safety_notes_need_a_person_even_when_everything_passed():
    status, found = validation.assess([], {"claims": []}, {}, GOOD, BAR, MUSIC, [])
    assert status == "human_review_required"
    assert {f.source for f in found} == {"domain"}
    status, found = validation.assess([], {"claims": []}, {}, GOOD, BAR, MATH, ["Mains voltage"])
    assert status == "human_review_required" and found[-1].source == "safety"


def test_newest_report_counts_and_a_named_person_clears_review(client):
    client.app.state.settings.admin_subjects = ["boss"]
    admin = login(client, subject="boss", name="Boss")
    with Session(client.app.state.engine) as db, db.begin():
        validation.record(db, "c", "k", None, 1, "needs_revision", [])
        finding = validation.Finding("domain", "info", "music", "Limited verification.")
        validation.record(db, "c", "k", None, 2, "human_review_required", [finding])
        validation.record(db, "c", "other", None, 1, "pass", [])
    queue = client.get("/api/v1/admin/maintenance/validation", headers=admin).json()["items"]
    assert [(i["course_id"], i["concept_id"], i["status"]) for i in queue] == [
        ("c", "k", "human_review_required")
    ]
    url = "/api/v1/admin/maintenance/validation/c/k/confirm"
    assert client.post(url, json={"reviewer": "Boss"}, headers=admin).status_code == 422
    done = client.post(url, json={"reviewer": "Asha Rao", "note": "Checked ragas"}, headers=admin)
    assert done.json()["status"] == "pass" and done.json()["reviewer"] == "Asha Rao"
    assert client.get("/api/v1/admin/maintenance/validation", headers=admin).json()["items"] == []
    assert client.post(url, json={"reviewer": "Asha Rao"}, headers=admin).status_code == 409
    with Session(client.app.state.engine) as db:
        assert validation.latest(db, "c", "k").reviewer == "Asha Rao"
    learner = login(client, subject="learner")
    assert client.get("/api/v1/admin/maintenance/validation", headers=learner).status_code in (
        401,
        403,
    )


def test_unknown_status_is_refused(client):
    with Session(client.app.state.engine) as db:
        try:
            validation.record(db, "c", "k", None, 1, "looks fine", [])
        except ValueError:
            return
    raise AssertionError("an unknown status was stored")
