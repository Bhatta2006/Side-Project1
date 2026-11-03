"""Every bounded worker's reply becomes a typed result envelope (master prompt 7)."""

from socrat.coursegen.roles import Envelope, Reply, envelope


def reply(data, problem=""):
    return Reply(data, problem, 0.01, "m", "p", 5)


def test_a_reply_that_did_not_parse_is_not_ok_and_says_why():
    env = envelope("author", reply(None, "not valid JSON"))
    assert env == Envelope("author", False, "not valid JSON")
    assert env.as_log() == {"ok": False, "problem": "not valid JSON"}


def test_stated_confidence_assumptions_and_issues_are_kept_typed_and_capped():
    env = envelope(
        "architect",
        reply(
            {
                "modules": [],
                "confidence": 0.7,
                "assumptions": ["learner can read", 3, {"nested": "dropped"}],
                "unresolved": ["x" * 400] + [f"q{i}" for i in range(20)],
                "evidence": "not a list",
            }
        ),
    )
    assert env.ok and env.confidence == 0.7
    assert env.assumptions == ("learner can read", "3")
    assert len(env.unresolved) == 10 and len(env.unresolved[0]) == 300
    assert env.evidence == ()
    assert env.as_log()["confidence"] == 0.7 and "evidence" not in env.as_log()


def test_out_of_range_or_boolean_confidence_is_dropped_not_trusted():
    for bad in (1.5, -0.1, True, "high"):
        assert envelope("critic", reply({"confidence": bad})).confidence is None
