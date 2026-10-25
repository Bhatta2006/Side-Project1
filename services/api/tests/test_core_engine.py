"""Pure engine behaviour: catalog integrity, mastery, placement, planning, Socratic policy."""

import random
from datetime import date

import pytest
from catalog_support import algo, basics, catalog

from socrat.assistant.socratic import (
    Ladder,
    advance,
    genuine,
    leaks,
    parse_level,
    reveal_eligibility,
)
from socrat.catalog.registry import CatalogError, build
from socrat.catalog.schema import Course
from socrat.mastery.model import DAY, ConceptState, apply, band, placed
from socrat.placement import engine as placement
from socrat.planner.engine import Adaptive, build_plan, pace_of

NOW = 1_800_000_000
TODAY = date(2027, 1, 4)  # Monday


def test_catalog_orders_cross_course_prerequisites():
    cat = catalog()
    path = cat.closure(cat.course_concepts("algo"))
    assert path[:3] == ["basics:values", "basics:loops", "basics:functions"]
    assert path.index("algo:arrays") < path.index("algo:two-pointers") < path.index("algo:bfs")
    assert cat.module_of("algo:bfs") == "graphs"
    assert [t.input for t in cat.public_tests("double")] == ["2\n"]


def test_catalog_rejects_cycles_unknown_refs_and_orphans():
    payload = basics().model_dump(mode="json")
    payload["concepts"][0]["prerequisites"] = ["functions"]
    with pytest.raises(CatalogError, match="cycle"):
        build([Course.model_validate(payload)])
    payload = algo().model_dump(mode="json")
    with pytest.raises(CatalogError, match="unknown prerequisite"):
        build([Course.model_validate(payload)])
    payload = basics().model_dump(mode="json")
    payload["modules"][1]["concepts"] = []
    with pytest.raises(ValueError):
        build([Course.model_validate(payload)])
    payload = basics().model_dump(mode="json")
    payload["concepts"][0]["problems"] = ["missing"]
    with pytest.raises(CatalogError, match="unknown problem"):
        build([Course.model_validate(payload)])


def test_mastery_requires_independent_evidence_and_caps_steps():
    state = ConceptState()
    big = apply(state, "checkpoint", 1.0, NOW)
    assert big.mean - state.mean <= 0.15 + 1e-9
    assisted = state
    independent = state
    for i in range(8):
        assisted = apply(assisted, "code", 1.0, NOW + i, assistance=5)
        independent = apply(independent, "code", 1.0, NOW + i)
    assert independent.mastered(NOW + 10)
    assert assisted.mean < independent.mean
    assert assisted.independent_successes == 0 and assisted.assisted_successes == 8
    failing = apply(independent, "review", 0.0, NOW + 20)
    assert failing.review_step == 0 and failing.next_review_at == NOW + 20 + DAY


def test_placement_prior_is_not_verified_mastery():
    known = placed(True, NOW)
    assert known.assumed and not known.mastered(NOW)
    assert band(known, NOW) == "likely_known"
    confirmed = apply(known, "review", 1.0, NOW + DAY)
    assert not confirmed.assumed or confirmed.evidence_count == 1
    assert band(ConceptState(), NOW) == "not_started"


def test_overdue_reviews_decay_effective_mastery():
    state = ConceptState(alpha=9, beta=1, evidence_count=6, next_review_at=NOW)
    assert state.effective(NOW) == state.mean
    assert state.effective(NOW + 20 * DAY) < state.mean


@pytest.mark.parametrize("knows", range(0, 7))
def test_placement_finds_the_frontier(knows):
    cat = catalog()
    path = cat.closure(cat.course_concepts("algo"))
    state = placement.start(cat, path, "algo:arrays", seed=7)
    while not state.done:
        item = placement.question(cat, state)
        assert item is not None
        index = state.pending["index"]
        right = item.shown(placement.seed_of(state))["answer"]
        placement.answer(cat, state, right if index < knows else (right + 1) % len(item.options))
    known = placement.result(state)
    cap = int(
        len(path) * placement.SKIP_CAP
    )  # a perfect score still leaves the last stretch to learn
    assert [known[c] for c in path] == [i < min(knows, cap) for i in range(len(path))]
    assert not known[path[-1]]
    assert len(state.asked) <= placement.MAX_QUESTIONS


def test_absolute_beginner_skips_placement():
    cat = catalog()
    state = placement.start(cat, cat.closure(cat.course_concepts("algo")), None, seed=1)
    assert state.done and not any(placement.result(state).values())


def plan(states=None, completed=(), history=(), weekdays=frozenset({0, 2, 4}), minutes=45):
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
    )


def test_plan_respects_prerequisites_and_is_deterministic():
    first, second = plan(), plan()
    assert first.to_dict() == second.to_dict()
    order = [a.concept for a in first.queue if a.kind in {"lesson", "quiz", "problem"}]
    positions = {c: order.index(c) for c in dict.fromkeys(order)}
    cat = catalog()
    for concept, index in positions.items():
        for prerequisite in cat.prerequisites[concept]:
            assert positions[prerequisite] < index
    assert first.days[0]["date"] == TODAY.isoformat()
    assert all(day["items"] for day in first.days)


def test_known_concepts_are_skipped_and_reviewed():
    known = {c: placed(True, NOW) for c in ("basics:values", "basics:loops", "basics:functions")}
    result = plan(states=known)
    assert all(a.concept.startswith("algo:") for a in result.queue if a.kind != "checkpoint")
    assert any("Skipped 3" in r for r in result.reasons)
    reviews = [i for d in result.days for i in d["items"] if i["kind"] == "review"]
    assert {r["concept"] for r in reviews} == set(known)


def test_fast_learner_accelerates_and_struggling_learner_gets_support():
    fast = [
        dict(kind="code", score=1.0, assistance=0, elapsed_seconds=300, expected_seconds=600)
    ] * 3
    slow = [
        dict(kind="code", score=0.2),
        dict(kind="quiz", score=1.0),
        dict(kind="code", score=0.3),
    ]
    assert pace_of(fast)[0] == "fast" and pace_of(slow)[0] == "support"
    assert pace_of(fast[:2])[0] == "steady"
    steady, quick = plan(), plan(history=fast)
    assert quick.remaining_minutes < steady.remaining_minutes
    assert quick.projected_finish < steady.projected_finish
    assert "problem:arr-easy" not in {a.id for a in quick.queue}
    assert "problem:arr-easy" in {a.id for a in steady.queue}


def test_repeated_failure_suggests_a_refresher_and_inserts_it_only_once_approved():
    struggling = ConceptState(alpha=1, beta=4, evidence_count=3, failures=3)
    weak_prerequisite = ConceptState(alpha=1, beta=2, evidence_count=1)
    states = {"algo:two-pointers": struggling, "algo:arrays": weak_prerequisite}
    result = plan(states=states)
    # The planner never changes the roadmap on its own: it only flags the need.
    assert not [a for a in result.queue if a.kind == "remedial"]
    assert result.needs_repair == {"algo:two-pointers": "algo:arrays"}
    cat = catalog()
    approved = build_plan(
        cat,
        cat.course_concepts("algo"),
        states,
        set(),
        [],
        TODAY,
        NOW,
        {0, 2, 4},
        45,
        adaptive=Adaptive(overrides={"repair": [["algo:arrays", "algo:two-pointers"]]}),
    )
    remedial = [a for a in approved.queue if a.kind == "remedial"]
    assert [a.concept for a in remedial] == ["algo:arrays"]
    assert "approved" in remedial[0].reason


def test_missed_days_never_create_backlog():
    later = build_plan(
        catalog(),
        catalog().course_concepts("algo"),
        {},
        set(),
        [],
        date(2027, 2, 1),
        NOW + 28 * DAY,
        {0, 2, 4},
        45,
    )
    # Missed days are never stacked: each day stays within budget plus <40% of one activity.
    for day in later.days:
        largest = max(item["minutes"] for item in day["items"])
        assert day["minutes"] < 45 + 0.4 * largest or len(day["items"]) == 1
    assert later.days[0]["date"] == "2027-02-01"


def test_simulated_learners_never_violate_prerequisites():
    cat = catalog()
    rng = random.Random(3)
    for _ in range(200):
        states = {
            c: ConceptState(
                alpha=rng.uniform(1, 9), beta=rng.uniform(1, 9), evidence_count=rng.randint(0, 6)
            )
            for c in cat.order
            if rng.random() < 0.6
        }
        result = plan(states=states, weekdays={rng.randint(0, 6)}, minutes=rng.choice([20, 45, 90]))
        seen: set[str] = set()
        for activity in result.queue:
            if activity.kind in {"lesson", "quiz", "problem"}:
                for prerequisite in cat.prerequisites[activity.concept]:
                    assert prerequisite in seen or prerequisite not in {
                        a.concept for a in result.queue
                    }
                seen.add(activity.concept)


def test_socratic_ladder_needs_real_work_to_escalate():
    ladder = Ladder()
    for _ in range(5):
        ladder = advance(ladder, "help", new_attempt=False)
    assert ladder.ceiling == 0
    assert genuine("I tried a loop but it prints the wrong total for the second test", False)
    assert not genuine(
        "i dont get it. just give me the full code pls, i have interview tmrw", False
    )
    assert not genuine("I don't know where to start", False)
    for _ in range(10):
        ladder = advance(ladder, "", new_attempt=True)
    assert ladder.ceiling == 4 and ladder.turns_at_ceiling == 6


def test_full_answer_requires_struggle():
    assert not reveal_eligibility(Ladder(ceiling=1), failed_submits=0)[0]
    assert not reveal_eligibility(Ladder(ceiling=2), failed_submits=5)[0]
    assert reveal_eligibility(Ladder(ceiling=3), failed_submits=2)[0]
    assert reveal_eligibility(Ladder(ceiling=4, turns_at_ceiling=3), failed_submits=0)[0]


def test_leak_detection():
    reference = "n = int(input())\nprint(sum(x * x for x in range(1, n + 1)))\n"
    code = "```python\nn = int(input())\nprint(n)\n```"
    assert leaks(code, 3) and leaks(code, 4) and not leaks(code, 5)
    assert not leaks("What happens to the total after each step?", 1)
    pseudo = "```text\nfor each value\n  add its square\nprint the total\n```"
    assert leaks(pseudo, 3) and not leaks(pseudo, 4)
    copied = "Try this: print(sum(x * x for x in range(1, n + 1))) and n = int(input())"
    assert leaks(copied, 4, reference)
    assert parse_level("<level>2</level>\nThink about it.") == (2, "Think about it.")
    assert parse_level("No tag") == (None, "No tag")


def test_options_are_shuffled_so_position_never_gives_the_answer_away():
    cat = catalog()
    items = [q for c in cat.concepts.values() for q in c.quiz]
    positions = [q.shown("session-1")["answer"] for q in items]
    # Authors put the right option first; learners must not see it there every time.
    assert positions.count(0) < len(items) * 0.6
    for q in items[:20]:
        shown = q.shown("session-1")
        assert sorted(shown["options"]) == sorted(q.options)
        assert shown["options"][shown["answer"]] == q.options[q.answer]
        assert q.is_correct("session-1", shown["answer"])
        assert not q.is_correct("session-1", -1)
        assert q.shown("session-1") == shown  # stable for the same session


def test_placement_never_skips_unasked_course_topics():
    cat = catalog()
    own = set(cat.course_concepts("algo"))
    path = cat.closure(cat.course_concepts("algo"))
    state = placement.start(cat, path, path[-1], seed=3)
    while not state.done:  # A strong learner answers everything correctly.
        item = placement.question(cat, state)
        placement.answer(cat, state, item.shown(placement.seed_of(state))["answer"])
    known = placement.result(state, own)
    asked = {x["concept"] for x in state.asked}
    capped = set(path[: state.frontier])  # the last stretch always stays to learn
    assert all(known[c] == (c in asked and c in capped) for c in own)
    assert all(known[c] == (c in capped) for c in path if c not in own)


def test_quiz_items_about_other_languages_do_not_fit():
    from socrat.catalog.schema import QuizItem

    def item(id, prompt):
        return QuizItem(
            id=id, prompt=prompt, options=["a", "b"], answer=0, explanation="Because.", difficulty=2
        )

    cpp = item("cpp-ref", "In C++, what does the & mean?")
    assert cpp.fits("cpp") and not cpp.fits("python")
    both = item("decl", "In C++ or Java you declare a type. Why?")
    assert both.fits("java") and not both.fits("python")
    assert item("plain", "What does a hash map store?").fits("python")


def test_reveal_message_counts_attempts_in_plain_english():
    assert reveal_eligibility(Ladder(), failed_submits=1)[1].startswith("submit 1 more attempt or")
    assert "2 more attempts" in reveal_eligibility(Ladder(), failed_submits=0)[1]


def _course_dir(root, concepts: list[dict], modules: list[dict]):
    import yaml

    folder = root / "courses" / "mini"
    (folder / "concepts").mkdir(parents=True)
    (folder / "problems").mkdir()
    course = dict(
        id="mini",
        title="Mini course",
        tagline="A tiny course",
        description="A tiny course used to test draft concepts.",
        version="1.0.0",
        languages=["python"],
        levels=[
            dict(id="new", label="New", description="New"),
            dict(id="some", label="Some", description="Some", start_concept="basics"),
        ],
        modules=modules,
    )
    (folder / "course.yaml").write_text(yaml.safe_dump(course), encoding="utf-8")
    for concept in concepts:
        (folder / "concepts" / f"{concept['id']}.yaml").write_text(
            yaml.safe_dump(concept), encoding="utf-8"
        )
    return root / "courses"


def _concept(cid, module, prerequisites=(), status="live"):
    live = dict(
        lesson="x" * 200,
        key_points=["one", "two"],
        resources=[
            dict(
                title=f"Doc {i}",
                url=f"https://example.com/{i}",
                kind="docs",
                source="Ex",
                minutes=5,
            )
            for i in range(2)
        ],
        quiz=[
            dict(
                id=f"q{i}",
                prompt="Pick one.",
                options=["a", "b"],
                answer=0,
                explanation="Because.",
                difficulty=1,
            )
            for i in range(2)
        ],
    )
    return dict(
        id=cid,
        title=cid.title(),
        summary="A concept for testing.",
        module=module,
        prerequisites=list(prerequisites),
        difficulty=1,
        estimated_minutes=20,
        status=status,
        **(live if status == "live" else {"lesson": "## Recognition cues"}),
    )


def test_draft_concepts_are_validated_but_never_served(tmp_path):
    from socrat.catalog.registry import load

    root = _course_dir(
        tmp_path,
        [_concept("basics", "start"), _concept("later", "next", ["basics"], status="draft")],
        [
            dict(id="start", title="Start", summary="The first module.", concepts=["basics"]),
            dict(id="next", title="Next", summary="A module still in draft.", concepts=["later"]),
        ],
    )
    cat = load(root, tests_root=None)
    assert cat.course_concepts("mini") == ["mini:basics"]
    assert [m.id for m in cat.course("mini").modules] == ["start"]
    assert "mini:later" not in cat.concepts


def test_a_live_concept_cannot_depend_on_a_draft(tmp_path):
    from socrat.catalog.registry import load

    root = _course_dir(
        tmp_path,
        [_concept("basics", "start", ["later"]), _concept("later", "start", status="draft")],
        [
            dict(
                id="start", title="Start", summary="The first module.", concepts=["later", "basics"]
            )
        ],
    )
    with pytest.raises(CatalogError, match="unknown prerequisite"):
        load(root, tests_root=None)


def test_drafts_must_fit_the_graph_and_live_concepts_must_be_complete(tmp_path):
    from socrat.catalog.registry import load
    from socrat.catalog.schema import Concept

    root = _course_dir(
        tmp_path,
        [_concept("basics", "start"), _concept("later", "start", ["nowhere"], status="draft")],
        [
            dict(
                id="start", title="Start", summary="The first module.", concepts=["basics", "later"]
            )
        ],
    )
    with pytest.raises(CatalogError, match="unknown prerequisite"):
        load(root, tests_root=None)
    incomplete = _concept("basics", "start") | {"resources": []}
    with pytest.raises(ValueError, match="at least 2 resources"):
        Concept.model_validate(incomplete)
