"""Adaptive quiz engine: rating math, pools, selection and modes (M3 tasks 10–13)."""

from dataclasses import replace

import pytest

from socrat.catalog.quizbank import GeneratorSpec
from socrat.catalog.registry import default_catalog
from socrat.quiz import modes, pools, rating, simulate
from socrat.quiz.config import DEFAULT
from socrat.quiz.selection import Context, Step, ladder, select

CHECK = DEFAULT.modes["concept_check"]


def step(band, outcome="correct", hints=0, pattern="sim:window", misconception=None, key=None):
    return Step(key or f"x{band}-{outcome}", pattern, band, "mcq", outcome, hints, misconception)


def ctx(**overrides):
    base = dict(
        track="interview",
        mode=CHECK,
        patterns=("sim:window",),
        language="python",
        thetas={"sim:window": 1000.0},
        seed="seed",
    )
    return Context(**{**base, **overrides})


# ---------------------------------------------------------------- rating


def test_probability_is_logistic_on_the_400_point_scale():
    assert rating.p_correct(1000, 1000) == 0.5
    assert rating.p_correct(1400, 1000) == pytest.approx(10 / 11)
    assert rating.p_correct(1000, 1400) == pytest.approx(1 / 11)


def test_k_schedules():
    assert [rating.k_user(n) for n in (0, 9, 10, 29, 30, 500)] == [40, 40, 24, 24, 16, 16]
    assert rating.k_item(0) == 36
    assert rating.k_item(20) == 21
    assert rating.k_item(10_000) == pytest.approx(6, abs=0.1)


def test_scores_reward_independence():
    assert [rating.answer_score(True, h) for h in (0, 1, 2, 3, 7)] == [1.0, 0.6, 0.3, 0.1, 0.1]
    assert rating.answer_score(False, 0) == 0.0


def test_update_moves_learner_and_item_in_opposite_directions():
    change = rating.update(1000, 1000, 1.0, 0, 0, False, (600, 2000))
    assert change.p == 0.5
    assert change.theta == 1020 and change.d == 982
    frozen = rating.update(1000, 1000, 0.0, 0, 0, True, (600, 2000))
    assert frozen.theta == 980 and frozen.d == 1000


def test_update_clamps_to_allowed_bands_and_rejects_bad_scores():
    low, high = rating.theta_bounds(4)
    assert high == 1250 + 150
    assert rating.update(1395, 1400, 1.0, 0, 0, False, (low, high)).theta == high
    with pytest.raises(ValueError):
        rating.update(1000, 1000, 1.5, 0, 0, False, (low, high))


def test_band_for_theta():
    assert rating.band_for(800) == 1
    assert rating.band_for(1000) == 2  # nearest prior 950
    assert rating.band_for(1025) == 2  # tie between 950 and 1100 goes down
    assert rating.band_for(5000) == 7


# ---------------------------------------------------------------- pools


def test_pool_partition_is_stable_and_near_seventy_percent():
    keys = [f"dsa:x:item-{n}" for n in range(4000)]
    first = [pools.pool_for_key(k) for k in keys]
    assert first == [pools.pool_for_key(k) for k in keys]
    share = first.count("practice") / len(first)
    assert 0.67 < share < 0.73


def test_legacy_bank_wraps_every_item_with_bands_and_pools():
    catalog = default_catalog()
    items = pools.keep_practice(pools.legacy_bank(catalog))
    total = sum(len(c.quiz) for c in catalog.concepts.values())
    assert len(items) == total >= 284
    assert len({i.key for i in items}) == total
    assert {i.band for i in items} <= {1, 2, 3, 5, 6}  # difficulty 4 and 5 map to bands 5 and 6
    assert all(i.d_prior == DEFAULT.prior(i.band) for i in items)
    assert all(i.status == "provisional" and i.reviewed for i in items)
    counts = pools.summary(items)
    assert all(c["practice"] >= 1 for c in counts.values())
    assert sum(c["assessment"] for c in counts.values()) > 30


def test_code_items_start_at_band_two():
    assert pools.band_for_difficulty(1, has_code=False) == 1
    assert pools.band_for_difficulty(1, has_code=True) == 2
    assert pools.band_for_difficulty(4, has_code=False) == 5
    assert pools.band_for_difficulty(5, has_code=True) == 6


def test_keep_practice_rescues_a_concept_with_only_assessment_items():
    items = [replace(i, concept="c:only", pool="assessment") for i in simulate.synthetic_bank()[:3]]
    fixed = pools.keep_practice(items)
    assert sum(i.pool == "practice" for i in fixed) == 1


def test_generator_seed_ranges_decide_the_pool():
    spec = GeneratorSpec(
        template="t",
        reference="x",
        seeds={"practice": {"start": 0, "stop": 700}, "assessment": {"start": 700, "stop": 1000}},
    )
    assert pools.pool_for_seed(spec, 0) == "practice"
    assert pools.pool_for_seed(spec, 699) == "practice"
    assert pools.pool_for_seed(spec, 700) == "assessment"
    assert pools.pool_for_seed(spec, 1000) is None


# ---------------------------------------------------------------- selection


def test_cold_start_serves_one_band_below_the_estimate():
    rule = ladder([], ctx(thetas={"sim:window": 1250.0}))
    assert rule.reason == "cold_start" and rule.preferred == (3, 3)
    contest = ladder([], ctx(mode=DEFAULT.modes["contest"], thetas={"sim:window": 1250.0}))
    assert contest.preferred == (4, 4)


def test_two_independent_corrects_raise_the_band():
    rule = ladder([step(3), step(3)], ctx())
    assert rule.reason == "ladder_up" and rule.preferred[0] == 4
    assisted = ladder([step(3), step(3, hints=1)], ctx())
    assert assisted.reason != "ladder_up"


def test_a_wrong_answer_never_raises_and_repairs_the_misconception():
    rule = ladder([step(3), step(4, "wrong", misconception="window-off-by-one")], ctx())
    assert rule.reason == "repair"
    assert rule.hard[1] == 4 and rule.preferred == (3, 4)
    assert rule.misconception == "window-off-by-one"


def test_three_wrongs_drop_a_band_with_a_micro_lesson():
    rule = ladder([step(4, "wrong"), step(4, "wrong"), step(4, "wrong")], ctx())
    assert rule.reason == "step_down" and rule.micro
    assert rule.preferred == (3, 3) and rule.hard[1] == 3


def test_skips_do_not_count_for_the_ladder():
    rule = ladder([step(3), step(3, "skipped"), step(3)], ctx())
    assert rule.reason == "ladder_up"


def test_select_prefers_the_missed_misconception_and_respects_the_pool():
    items = [i for i in simulate.synthetic_bank() if i.pool == "practice"]
    tag = next(i for i in items if i.band == 2 and i.misconceptions).misconceptions[1]
    choice = select(items, [step(2, "wrong", misconception=tag)], ctx())
    assert choice.reason == "repair" and choice.item is not None
    assert tag in choice.item.misconceptions and choice.item.band <= 2
    assessment = [i for i in simulate.synthetic_bank() if i.pool == "assessment"]
    assert select(assessment, [], ctx()).item is None


def test_select_is_deterministic_per_seed_and_skips_seen_items():
    items = simulate.synthetic_bank()
    first = select(items, [], ctx())
    assert first.item == select(items, [], ctx()).item
    again = select(items, [], ctx(seen=frozenset({first.item.key})))
    assert again.item is not None and again.item.key != first.item.key


def test_select_filters_languages_formats_and_exposure():
    items = [
        replace(i, languages=("cpp",)) if i.band == 1 else i for i in simulate.synthetic_bank()
    ]
    choice = select(items, [], ctx(thetas={"sim:window": 1000.0}))
    assert choice.item is not None and "cpp" not in choice.item.languages
    run = [Step(f"r{n}", "sim:window", 2, "mcq", "correct") for n in range(2)]
    assert select(simulate.synthetic_bank(), run, ctx()).item.format != "mcq"
    band3 = [i for i in simulate.synthetic_bank() if i.band == 2 and i.pool == "practice"]
    hot = {i.key: 0.5 for i in band3[:-1]}
    assert select(band3, [], ctx(exposure=hot, thetas={"sim:window": 1100.0})).item == band3[-1]


def test_interleave_alternates_patterns():
    items = simulate.synthetic_bank(patterns=("sim:a", "sim:b"))
    review = ctx(
        mode=DEFAULT.modes["review"],
        patterns=("sim:a", "sim:b"),
        thetas={"sim:a": 1000.0, "sim:b": 1000.0},
    )
    served = [Step("x", "sim:a", 2, "mcq", "correct")]
    assert select(items, served, review).item.pattern == "sim:b"


def test_contest_never_exceeds_the_rating_band():
    items = simulate.synthetic_bank()
    contest = ctx(mode=DEFAULT.modes["contest"], thetas={"sim:window": 1100.0})
    choice = select(items, [step(3), step(3)], contest)
    assert choice.item.band <= 3


def test_prerequisite_cap_limits_bands():
    items = simulate.synthetic_bank()
    choice = select(items, [step(4), step(4)], ctx(max_band=4))
    assert choice.item.band <= 4


# ---------------------------------------------------------------- modes


def test_assessment_modes_fail_closed_without_calibrated_items():
    items = pools.bank(default_catalog())
    concepts = ["dsa:sliding-window"]
    for mode in ("placement", "checkpoint", "weekly"):
        assert not modes.available(DEFAULT.modes[mode], concepts, items)
    assert modes.available(CHECK, concepts, items)
    calibrated = [
        replace(i, status="calibrated", pool="assessment", concept="c:x") for i in items[:3]
    ]
    assert modes.available(DEFAULT.modes["weekly"], ["c:x"], calibrated)
    assert not modes.available(DEFAULT.modes["weekly"], [], calibrated)


def test_initial_theta_uses_track_and_prior_mastery():
    assert modes.initial_theta("foundations", None) == 900
    assert modes.initial_theta("competitive", None) == 1100
    assert modes.initial_theta("interview", 0.5) == 1000
    assert modes.initial_theta("interview", 1.0) == 1200
    assert modes.initial_theta("interview", 0.0) == 800


def test_stop_rules():
    six = [step(2)] * 4 + [step(4), step(4)]
    assert modes.stop_reason(six, CHECK, ceiling_band=4) == "ceiling"
    assert modes.stop_reason(six[:5], CHECK, ceiling_band=4) is None
    flat = [
        replace(step(2, "wrong" if n % 2 else "correct"), theta_before=1000, theta_after=1004)
        for n in range(8)
    ]
    assert modes.stop_reason(flat, CHECK, ceiling_band=7) == "stable"
    assert modes.stop_reason([step(2, "wrong")] * 10, CHECK, ceiling_band=7) == "max_items"
    review = DEFAULT.modes["review"]
    assert modes.stop_reason([step(2)] * 5, review, 7) == "max_items"


def test_ceiling_is_capped_by_the_pool():
    legacy = pools.legacy_bank(default_catalog())
    assert modes.ceiling("interview", legacy, 7) == 5  # the authored pool now reaches band 5
    assert modes.ceiling("foundations", simulate.synthetic_bank(), 7) == 4
    assert modes.ceiling("interview", simulate.synthetic_bank(), 3) == 3


def test_concept_ability_rolls_up_and_caps_at_the_weakest_critical_pattern():
    thetas = {"a": 1200.0, "b": 1000.0}
    assert modes.concept_ability(thetas) == 1100
    assert modes.concept_ability(thetas, {"a": 3, "b": 1}) == 1150
    assert modes.concept_ability(thetas, {"a": 3, "b": 1}, frozenset({"b"})) == 1000
    assert modes.concept_ability({}) is None


def test_summary_is_evidence_not_a_score():
    steps = [step(2), step(3, hints=1), step(4), step(4), step(4, "wrong"), step(3, "skipped")]
    result = modes.summarise(steps)
    assert result.headline == "2 of 3 independent at band 4"
    assert (result.independent, result.assisted, result.wrong, result.skipped) == (3, 1, 1, 1)
    assert modes.summarise([]).headline == "No independent answers yet"


def test_family_items_render_with_hints_and_count_only_after_review():
    from types import SimpleNamespace

    from socrat.catalog.quizbank import QuizFamily
    from socrat.quiz import service

    family = QuizFamily.model_validate(
        dict(
            id="quiz:dsa:sliding-window:fixed-sum",
            family="fixed-sum",
            concept="dsa:sliding-window",
            format="mcq",
            tracks=["interview"],
            languages=["python"],
            hint_ladder=["Restate the question", "Look at the first window"],
            items=[
                dict(
                    id="one",
                    band=2,
                    prompt="Max sum of 2 consecutive numbers in [1, 3, 2]?",
                    options=["5", "4", "3"],
                    answer=0,
                    misconceptions=[None, "syntax-delimiters", None],
                    explanation="3 + 2 is the largest window.",
                    pool="practice",
                )
            ],
            provenance={},
        )
    )
    (item,) = pools.family_bank({family.id: family})
    assert item.key == "quiz:dsa:sliding-window:fixed-sum:one"
    assert item.pattern == "dsa:sliding-window" and item.pool == "practice"
    assert not item.reviewed and item.misconceptions[1] == "syntax-delimiters"
    shown = service.render(SimpleNamespace(quiz_families={family.id: family}), item, "s", "python")
    assert shown["options"][shown["answer"]] == "5"
    assert shown["hints"] == ["Restate the question", "Look at the first window"]
