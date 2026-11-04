"""The scoring policy is versioned and the learner state can be rebuilt from evidence
(master prompt 9.1: model and scoring-policy version; raw evidence append-only, the derived
projection recalculable)."""

from dataclasses import dataclass

from socrat.mastery import model
from socrat.mastery.model import POLICY, ConceptState, apply, replay

T = 1_800_000_000


@dataclass
class Event:
    kind: str
    score: float
    assistance: int
    created_at: int


EVENTS = [
    Event("quiz", 1.0, 0, T),
    Event("code", 0.4, 2, T + 3600),
    Event("tutor", 0.9, 0, T + 3700),  # refused by apply: a tutor cannot raise mastery
    Event("review", 1.0, 0, T + 2 * model.DAY),
    Event("transfer", 1.0, 0, T + 5 * model.DAY),
]


def test_the_policy_version_is_a_digest_of_the_scoring_numbers():
    assert POLICY.startswith("beta-") and len(POLICY) == 17
    assert model.policy_digest(model.POLICY_PARTS) == POLICY
    tweaked = [{**model.WEIGHTS, "quiz": 0.61}, *model.POLICY_PARTS[1:]]
    assert model.policy_digest(tweaked) != POLICY


def test_every_update_records_the_policy_and_old_states_are_marked_stale():
    old = ConceptState.from_dict({"alpha": 2.0, "beta": 1.0, "evidence_count": 1})
    assert old.policy == "" and not old.current
    new = model.apply(old, "quiz", 1.0, T)
    assert new.policy == model.POLICY and new.current
    # A state saved by a later version with a field this code does not know still loads.
    assert ConceptState.from_dict({**new.to_dict(), "future_field": 1}).alpha == new.alpha


def test_replaying_the_evidence_gives_the_same_state_as_applying_it_live():
    live = ConceptState()
    for e in EVENTS:
        if e.kind == "tutor" and e.score > model.TUTOR_MAX_SCORE:
            continue
        live = apply(live, e.kind, e.score, e.created_at, e.assistance)
    assert replay(reversed(EVENTS)) == live  # order comes from the timestamps
    assert replay([]) == ConceptState()
    prior = model.placed(True, T - 10)
    assert replay(EVENTS[:1], start=prior).alpha > replay(EVENTS[:1]).alpha
