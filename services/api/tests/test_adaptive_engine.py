"""Adaptive roadmap logic: learner profile, stuck detection, ordering, suggestions."""

import math
from dataclasses import replace
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from catalog_support import catalog

from socrat.adaptive import profile, stuck, suggest
from socrat.adaptive.profile import EvidenceRow
from socrat.mastery.model import DAY, MAX_STEP, ConceptState, apply
from socrat.planner import goals
from socrat.planner.engine import Adaptive, build_plan, ordered, set_aside

NOW = 1_800_000_000
TODAY = date(2027, 1, 4)  # Monday


def plan(states=None, completed=(), history=(), adaptive=None, minutes=45, weekdays=(0, 2, 4)):
    cat = catalog()
    return build_plan(
        cat,
        cat.course_concepts("algo"),
        states or {},
        set(completed),
        list(history),
        TODAY,
        NOW,
        set(weekdays),
        minutes,
        adaptive=adaptive,
    )


def row(score, days_ago=1, kind="quiz", assistance=0, **extra):
    return EvidenceRow(
        "algo:arrays", kind, score, assistance, created_at=NOW - days_ago * DAY, **extra
    )


# ---------------------------------------------------------------- mastery


def test_testout_pass_proves_a_concept_in_one_step():
    state = apply(ConceptState(alpha=1, beta=2), "testout", 1.0, NOW)
    assert state.mastered(NOW)


def test_tutor_observations_can_only_flag_gaps():
    with pytest.raises(ValueError):
        apply(ConceptState(), "tutor", 1.0, NOW)
    lowered = apply(ConceptState(alpha=3, beta=1), "tutor", 0.0, NOW)
    assert lowered.mean < 0.75


def test_clean_record_moves_faster_and_review_spacing_follows_forgetting():
    clean = ConceptState(alpha=1, beta=1, independent_successes=2)
    messy = replace(clean, failures=1)
    assert apply(clean, "checkpoint", 1.0, NOW).mean - clean.mean > MAX_STEP
    assert apply(messy, "checkpoint", 1.0, NOW).mean - messy.mean <= MAX_STEP + 1e-9
    slow = apply(ConceptState(), "quiz", 1.0, NOW, interval_scale=1.5).next_review_at
    fast = apply(ConceptState(), "quiz", 1.0, NOW, interval_scale=0.6).next_review_at
    assert slow - NOW == int(1.5 * DAY) and fast - NOW == int(0.6 * DAY)


# ---------------------------------------------------------------- profile


def test_profile_reads_speed_hints_trend_and_unresolved_mistakes():
    rows = [
        row(0.2, 12, misconception="off-by-one"),
        row(0.3, 10, misconception="off-by-one"),
        row(1.0, 5, assistance=3, elapsed_seconds=900, expected_seconds=300),
        row(1.0, 2, assistance=0, elapsed_seconds=600, expected_seconds=300),
    ]
    p = profile.build("algo:arrays", ConceptState(alpha=2, beta=2), rows, NOW, 1350.0, ["timeout"])
    assert p.hint_dependence == 0.5
    assert p.speed == 2.5
    assert p.misconceptions == {"off-by-one": 2}
    assert p.trend is not None and p.trend > 0
    assert p.failure_modes == {"performance": 1}
    assert p.rating == 1350.0
    resolved = rows + [row(1.0, 1, misconception="off-by-one")]
    assert profile.build("algo:arrays", ConceptState(), resolved, NOW).misconceptions == {}


def test_forgetting_rate_adherence_and_unified_level():
    assert profile.review_scale([1.0, 1.0]) == 1.0  # too few reviews to judge
    assert profile.review_scale([1.0] * 6) > 1.0
    assert profile.review_scale([0.0, 0.3, 1.0, 0.2]) == 0.6
    assert profile.adherence(100, 400, 30) == 0.25
    assert profile.adherence(100, 400, 3) == 1.0  # too early to judge
    level = profile.level(1200, [1400.0], 1500)
    assert level["rating"] == 1360 and level["codeforces"] == 1500


# ---------------------------------------------------------------- stuck


def stuck_profile(**changes):
    base = profile.SkillProfile(
        concept="algo:arrays",
        mastery=0.45,
        confidence=0.6,
        band="needs_practice",
        attempts=7,
        recent_failures=3,
        first_seen_at=NOW - 8 * DAY,
        active_days=4,
        misconceptions={"off-by-one": 2},
    )
    return replace(base, **changes)


def test_stuck_needs_several_signals_and_names_the_cause():
    found = stuck.detect(stuck_profile(), NOW)
    assert found is not None and found.severity == 3
    assert {"long_time", "many_attempts", "repeat_mistake", "failing"} <= set(found.signals)
    assert found.failure_mode == "concept_gap"
    one_bad_day = stuck_profile(
        attempts=2, recent_failures=1, first_seen_at=NOW - DAY, misconceptions={}
    )
    assert stuck.detect(one_bad_day, NOW) is None
    assert stuck.detect(stuck_profile(band="strong"), NOW) is None
    slow_code = stuck_profile(recent_failures=1, failure_modes={"performance": 3})
    assert stuck.failure_mode(slow_code) == "performance"


def test_intervention_ladder_escalates_one_rung_at_a_time():
    signal = stuck.detect(stuck_profile(), NOW)
    assert stuck.next_rung(signal, set(), True) == ("example", False)
    assert stuck.next_rung(signal, {"example", "explain"}, True) == ("probe", True)
    assert stuck.next_rung(signal, {"example", "explain", "probe"}, False) == ("checkin", False)
    assert stuck.next_rung(signal, {"example", "explain", "probe", "checkin"}, False) == (
        "defer",
        True,
    )
    mild = replace(signal, severity=1)
    assert stuck.next_rung(mild, set(), True) == ("example", False)
    # Rungs that did not help escalate: a mild case still reaches the tutor, then moving on,
    # instead of retaking the same check forever.
    assert stuck.next_rung(mild, {"example", "explain", "probe", "repair"}, True) == (
        "checkin",
        False,
    )
    tried = {"example", "explain", "probe", "repair", "checkin"}
    assert stuck.next_rung(mild, tried, True) == ("defer", True)
    # Nothing underneath to probe: straight past the probe rung.
    assert stuck.next_rung(mild, {"example", "explain"}, False, has_prereqs=False) == (
        "checkin",
        False,
    )


# ---------------------------------------------------------------- planner


def test_stuck_concept_gets_in_concept_support_but_no_roadmap_change():
    signal = stuck.detect(stuck_profile(), NOW)
    states = {"algo:arrays": ConceptState(alpha=1, beta=3, evidence_count=6, failures=4)}
    result = plan(states, adaptive=Adaptive(stuck={"algo:arrays": signal}))
    ids = [a.id for a in result.queue]
    assert "example:algo:arrays" in ids
    assert ids.index("example:algo:arrays") < ids.index("problem:arr-easy")
    assert not any(a.kind in {"remedial", "probe"} for a in result.queue)
    after = plan(
        states,
        completed={"example:algo:arrays"},
        adaptive=Adaptive(stuck={"algo:arrays": signal}),
    )
    assert "explain:algo:arrays" in [a.id for a in after.queue]


def test_ordering_keeps_prerequisites_first_and_moves_only_free_concepts():
    fake = SimpleNamespace(prerequisites={"a": [], "b": ["a"], "c": [], "d": ["c"], "e": []})
    path = ["a", "b", "c", "d", "e"]
    assert ordered(fake, path, {}) == path  # equal scores keep the authored order
    moved = ordered(fake, path, {"d": 3, "e": 2})
    assert moved == ["c", "d", "e", "a", "b"]  # d pulls its prerequisite c forward
    assert set_aside(fake, path, {"a", "e"}) == {"e"}  # b still needs a


def test_approved_overrides_shape_the_queue():
    adaptive = Adaptive(
        overrides={
            "testout": ["algo:two-pointers"],
            "probe": ["algo:arrays"],
            "skip": ["algo:bfs"],
            "stretch": True,
        }
    )
    result = plan(adaptive=adaptive)
    ids = [a.id for a in result.queue]
    assert ids[:2] == ["testout:algo:two-pointers", "probe:algo:arrays"]
    assert not any(a.concept == "algo:bfs" for a in result.queue)
    assert next(r for r in result.roadmap if r["concept"] == "algo:bfs")["status"] == "skipped"
    assert "stretch:algo:arrays" in ids
    done = plan(completed={"testout:algo:two-pointers"}, adaptive=adaptive)
    assert "testout:algo:two-pointers" not in [a.id for a in done.queue]


def test_learner_feel_sets_per_concept_pace():
    easy = plan(adaptive=Adaptive(overrides={"feel": {"algo:arrays": "easy"}}))
    assert "problem:arr-easy" not in [a.id for a in easy.queue]
    arrays = next(r for r in easy.roadmap if r["concept"] == "algo:arrays")
    assert "easy" in arrays["why"]


def test_forecast_uses_real_adherence_and_milestones_cover_the_path():
    planned = plan(adaptive=Adaptive(goal={"target_date": "2027-02-01"}))
    behind = plan(adaptive=Adaptive(goal={"target_date": "2027-02-01"}, adherence=0.4))
    assert behind.forecast["realistic_finish"] > planned.forecast["realistic_finish"]
    assert behind.forecast["planned_finish"] == planned.forecast["planned_finish"]
    weeks = [m["week"] for m in planned.milestones]
    assert weeks == sorted(weeks) and planned.milestones[0]["outcome"].startswith("You'll")
    covered = {c["concept"] for m in planned.milestones for c in m["concepts"]}
    assert "algo:bfs" in covered


def test_goal_relevance_for_interviews_and_contests():
    assert goals.focus_of("dsa", {}) == "interview"
    assert goals.focus_of("zero", {"target_rating": 1400}) == "contest"
    assert goals.relevance("dsa:arrays-hashing", "dsa", {}) == 1.0
    junior = goals.relevance("dsa:union-find", "dsa", {"target_role": "internship"})
    assert junior < goals.relevance("dsa:union-find", "dsa", {"target_role": "senior"})
    assert goals.relevance("cp:segment-tree", "cp", {"target_rating": 1200}) < 0.35
    assert goals.relevance("zero:loops", "dsa", {}) == goals.DEFAULT_RELEVANCE  # bridge


# ---------------------------------------------------------------- suggestions


def signals(**changes):
    return replace(suggest.Signals(today=TODAY, minutes_per_day=45, weekdays=(0, 2, 4)), **changes)


def test_off_track_deadline_offers_alternatives_in_one_group():
    remaining = plan().remaining_minutes
    # Reachable at about 250 min/week: more than today's 135, within the 3 x 120 maximum.
    target = TODAY + timedelta(days=math.ceil(remaining / 250 * 7))
    result = plan(adaptive=Adaptive(goal={"target_date": target.isoformat()}))
    assert result.forecast["on_track"] is False
    drafts = suggest.deadline(catalog(), result, signals())
    kinds = {d.kind for d in drafts}
    assert "budget" in kinds
    assert len({d.group for d in drafts}) == 1
    days = next((d for d in drafts if d.key.startswith("deadline:days")), None)
    if days:
        assert {0, 2, 4} < set(days.payload["weekdays"])
    on_time = plan(adaptive=Adaptive(goal={"target_date": "2030-01-01"}))
    assert suggest.deadline(catalog(), on_time, signals()) == []


def test_strong_results_offer_a_testout_and_a_stretch():
    fast = [
        dict(kind="code", score=1.0, assistance=0, elapsed_seconds=300, expected_seconds=600)
    ] * 3
    result = plan(history=fast)
    drafts = suggest.doing_well(catalog(), result, signals())
    kinds = {d.kind: d for d in drafts}
    assert kinds["test_out"].payload["target"].startswith("basics:")
    assert "stretch" in kinds
    steady = suggest.doing_well(catalog(), plan(), signals())
    assert steady == []


def test_stuck_proposals_follow_the_ladder_and_long_breaks_offer_a_comeback():
    signal = stuck.detect(stuck_profile(), NOW)
    s = signals(
        stuck={"algo:arrays": signal},
        tried={"algo:arrays": frozenset({"example", "explain"})},
        weak_prereqs={"algo:arrays": "basics:functions"},
    )
    drafts = suggest.stuck(catalog(), plan(), s)
    assert [d.kind for d in drafts] == ["probe"]
    s = replace(s, tried={"algo:arrays": frozenset({"example", "explain", "probe"})})
    repair = suggest.stuck(catalog(), plan(), s)
    assert repair[0].payload == {"concept": "basics:functions", "for": "algo:arrays"}
    back = suggest.comeback(catalog(), signals(days_away=9, recent_concepts=("algo:arrays",)))
    assert back[0].kind == "comeback" and back[0].payload["concepts"] == ["algo:arrays"]
    assert suggest.comeback(catalog(), signals(days_away=2, recent_concepts=("x",))) == []


def test_an_unreachable_deadline_offers_an_honest_new_date():
    result = plan(adaptive=Adaptive(goal={"target_date": "2027-01-05"}))
    drafts = suggest.deadline(catalog(), result, signals())
    assert [d.kind for d in drafts] == ["goal"]
    assert drafts[0].payload["target_date"] == result.forecast["realistic_finish"]
