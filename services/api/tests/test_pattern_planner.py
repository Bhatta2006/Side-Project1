"""Pattern planner (M6 tasks 25–28): scoring, triggers, templates, constraints, golden plans."""

from dataclasses import replace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog import atoms
from socrat.catalog.registry import CONTENT_ROOT, default_catalog
from socrat.learn import pattern_sessions
from socrat.mastery.model import placed
from socrat.models import ConceptState, Enrollment, Evidence, LearningSession, now
from socrat.planner import patterns as P

CAT = default_catalog()


def view(**overrides):
    base = dict(
        pattern="dsa:sliding-window/variable-size",
        concept="dsa:sliding-window",
        gate=True,
        mastery=0.4,
        seen=True,
    )
    return P.PatternView(**{**base, **overrides})


# ---------------------------------------------------------------- scoring (task 25)


def test_priority_follows_the_weighted_formula():
    score = P.priority(view(mastery=0.4, due=True, overdue_days=6, relevance=0.5, unlock=1.0), None)
    assert score.parts == {
        "weakness": pytest.approx(0.35 * 0.6),
        "review_due": pytest.approx(0.25 * 1.0),
        "track_relevance": pytest.approx(0.20 * 0.5),
        "diversity": pytest.approx(0.10),
        "unlock": pytest.approx(0.10),
    }
    assert score.total == pytest.approx(0.21 + 0.25 + 0.10 + 0.10 + 0.10)


def test_gate_diversity_and_retention():
    assert P.priority(view(gate=False), None).total == 0
    assert P.priority(view(), "dsa:sliding-window/variable-size").parts["diversity"] == 0
    idle = P.priority(view(mastery=0.9, idle_days=8), None)
    assert idle.parts["review_due"] == pytest.approx(0.25)
    fresh = P.priority(view(mastery=0.9, idle_days=2), None)
    assert fresh.parts["review_due"] == 0


def test_rank_drops_gated_patterns_and_is_deterministic():
    views = [
        view(pattern="a:x/p", mastery=0.2),
        view(pattern="a:x/q", mastery=0.2),
        view(pattern="a:x/r", gate=False, mastery=0.0),
        view(pattern="a:x/s", mastery=0.9),
    ]
    ranked = P.rank(views, None)
    assert [s.pattern for s in ranked] == ["a:x/p", "a:x/q", "a:x/s"]


def test_relevance_is_scaled_per_track():
    for track in ("foundations", "interview", "competitive"):
        scale = pattern_sessions.relevance(CAT, track)
        assert set(scale) == set(CAT.patterns)
        assert max(scale.values()) == 1 and min(scale.values()) >= 0
    interview = pattern_sessions.relevance(CAT, "interview")
    assert interview["dsa:sliding-window/variable-size"] > interview["zero:for-loops/accumulator"]


# ---------------------------------------------------------------- triggers (task 26)


def test_triggers_follow_section_9_4():
    assert P.triggers(view(seen=False)) == ["intro"]
    assert P.triggers(view(solved=("v1",))) == ["advance"]
    assert P.triggers(view(solved=("v1", "v2", "v3"))) == ["classifier", "advance"]
    assert "classify_first" in P.triggers(
        view(solved=("v1", "v2"), classify_misses=3, classify_hits=1)
    )
    assert "contrast" in P.triggers(view(confusions=("pattern-window-vs-prefix-sums",)))
    assert "retain" in P.triggers(view(mastery=0.85, idle_days=9))
    assert P.triggers(view(pitfall_misses=("window-with-negatives",)))[0] == "repair"


def test_session_type_choice():
    assert P.session_type(view(seen=False), 5, ["intro"]) == "intro"
    assert P.session_type(view(), 3, []) == "mixed_review"
    assert P.session_type(view(), 0, ["retain"]) == "mixed_review"
    assert P.session_type(view(), 1, ["advance"]) == "drill"


def test_contrast_cards_cover_every_pattern_confusion_tag():
    taxonomy = atoms.load_taxonomy(CONTENT_ROOT.parent / "atoms")
    table = pattern_sessions.contrasts(str(CONTENT_ROOT.parent / "patterns" / "contrasts.yaml"))
    tags = {t for t in taxonomy if t.startswith("pattern-")}
    assert set(table) == tags
    assert all(len(card["body"].split()) <= 80 for card in table.values())


# ---------------------------------------------------------------- templates and constraints (task 27)


def content(pattern="dsa:sliding-window/variable-size", **overrides):
    concept = CAT.patterns[pattern].concept
    problems = sorted(CAT.concept(concept).problems)
    made = pattern_sessions.content(CAT, pattern, problems, set(CAT.problems), [], (), True)
    return replace(made, **overrides)


def test_constraint_checker_catches_each_rule():
    good = P.build("intro", view(seen=False), content(), ["intro"], 30, True, False)
    assert P.violations(good, set(), set(), 30, False, False, True) == []
    assert any(
        "locked concept" in v
        for v in P.violations(good, {"dsa:sliding-window"}, set(), 30, False, False, True)
    )
    assert any("draft atom" in v for v in P.violations(good, set(), set(), 30, False, False, False))
    assert any("retrieval" in v for v in P.violations(good, set(), set(), 30, False, True, True))
    assert any("time budget" in v for v in P.violations(good, set(), set(), 5, False, False, True))
    two_new = good + [{**good[0], "pattern": "dsa:heaps/top-k"}]
    assert any(
        "one new idea" in v for v in P.violations(two_new, set(), set(), 60, False, False, True)
    )
    independent = [b for b in good if b.get("mode") == "independent"][0]
    assert any(
        "back to back" in v
        for v in P.violations(
            good + [independent, independent], set(), set(), 99, False, False, True
        )
    )
    no_practice = [b for b in good if b["kind"] != "problem"]
    assert any(
        "independent" in v for v in P.violations(no_practice, set(), set(), 30, False, False, True)
    )
    assert P.violations(no_practice, set(), set(), 30, True, False, True) == []  # recovery


views_st = st.builds(
    view,
    pattern=st.sampled_from(sorted(CAT.patterns)),
    mastery=st.floats(0, 1),
    seen=st.booleans(),
    due=st.booleans(),
    overdue_days=st.floats(0, 30),
    idle_days=st.one_of(st.none(), st.floats(0, 30)),
    solved=st.lists(st.sampled_from(["v1", "v2", "v3", "v4"]), unique=True, max_size=4).map(tuple),
    classify_hits=st.integers(0, 4),
    classify_misses=st.integers(0, 4),
    confusions=st.sampled_from([(), ("pattern-window-vs-prefix-sums",)]),
    pitfall_misses=st.sampled_from([(), ("window-with-negatives",)]),
)


@settings(max_examples=150, deadline=None)
@given(
    views_st,
    st.sampled_from([20, 30, 45, 60, 90]),
    st.booleans(),
    st.booleans(),
    st.integers(0, 3),
    st.integers(0, 4),
    st.booleans(),
)
def test_built_sessions_never_break_a_hard_constraint(
    v, minutes, beginner, recovery, reviews, n_problems, with_atoms
):
    pattern = CAT.patterns[v.pattern]
    v = replace(v, concept=pattern.concept)
    problems = sorted(CAT.problems)[:n_problems]
    stuff = content(
        v.pattern,
        concept_problems=problems,
        unsolved=set(problems),
        reviews=["dsa:arrays-hashing", "dsa:two-pointers", "dsa:stacks"][:reviews],
    )
    if not with_atoms:
        stuff = replace(stuff, atoms={})
    fired = P.triggers(v)
    kind = P.session_type(v, reviews, fired)
    blocks = P.build(kind, v, stuff, fired, minutes, beginner, recovery)
    found = P.violations(
        blocks, set(), {v.pattern} if v.seen else set(), minutes, recovery, reviews > 0, True
    )
    # The only failure build may produce is "no independent attempt" when nothing is left
    # to practise; plan() then refuses the session and the composer runs instead.
    assert set(found) <= {"no independent attempt"}
    if found:
        assert not stuff.unsolved and not problems
    assert blocks[-1]["kind"] == "reflection"
    assert all(b.get("pattern") == v.pattern for b in blocks if b["kind"] in {"atom", "problem"})


# ---------------------------------------------------------------- golden plans (task 28)


def outline(blocks):
    return [
        (
            b["kind"],
            b.get("atom", {}).get("kind") or b.get("mode") or "",
            b["concept"],
            b.get("problem", ""),
            b["seconds"],
        )
        for b in blocks
    ]


def plan_for(v, minutes, unsolved, reviews=(), beginner=False):
    pattern = CAT.patterns[v.pattern]
    problems = sorted(p for p in CAT.concept(pattern.concept).problems if p in unsolved)
    stuff = pattern_sessions.content(
        CAT, v.pattern, problems, set(unsolved), list(reviews), v.confusions, True
    )
    fired = P.triggers(v)
    kind = P.session_type(v, len(reviews), fired)
    blocks = P.build(kind, v, stuff, fired, minutes, beginner, False)
    assert (
        P.violations(
            blocks, set(), {v.pattern} if v.seen else set(), minutes, False, bool(reviews), True
        )
        == []
    )
    return kind, fired, outline(blocks)


def test_golden_new_foundations_learner_gets_a_pattern_intro():
    v = P.PatternView(
        "zero:for-loops/accumulator", "zero:for-loops", True, 0.0, False, relevance=1.0
    )
    # The pattern's own variant first (guided), then a concept problem on its own.
    kind, fired, blocks = plan_for(v, 30, {"sum-of-multiples", "fizzbuzz"}, beginner=True)
    assert (kind, fired) == ("intro", ["intro"])
    assert blocks == [
        ("atom", "pattern", "zero:for-loops", "", 120),
        ("atom", "worked", "zero:for-loops", "", 120),
        ("atom", "visualizer", "zero:for-loops", "", 120),
        ("problem", "guided", "zero:for-loops", "sum-of-multiples", 540),
        ("problem", "independent", "zero:for-loops", "fizzbuzz", 720),
        ("reflection", "", "zero:for-loops", "", 30),
    ]


def test_golden_interview_learner_after_a_first_variant_gets_a_drill():
    v = P.PatternView(
        "dsa:sliding-window/variable-size",
        "dsa:sliding-window",
        True,
        0.55,
        True,
        solved=("longest-unique-substring",),
        relevance=0.8,
    )
    kind, fired, blocks = plan_for(v, 45, {"max-window-sum"}, reviews=["dsa:arrays-hashing"])
    assert (kind, fired) == ("drill", ["advance"])
    assert blocks == [
        ("review", "", "dsa:arrays-hashing", "", 180),
        ("atom", "pattern", "dsa:sliding-window", "", 90),
        ("problem", "independent", "dsa:sliding-window", "max-window-sum", 420),
        ("reflection", "", "dsa:sliding-window", "", 30),
    ]


def test_golden_returning_learner_with_due_patterns_gets_mixed_review_and_a_contrast():
    v = P.PatternView(
        "dsa:binary-search/answer-monotonic-predicate",
        "dsa:binary-search",
        True,
        0.85,
        True,
        due=True,
        overdue_days=3,
        idle_days=10,
        solved=("koko-speed",),
        confusions=("pattern-search-needs-sorted-input",),
    )
    due = ["dsa:binary-search", "dsa:sliding-window", "dsa:arrays-hashing"]
    kind, fired, blocks = plan_for(v, 30, {"lower-bound-queries"}, reviews=due)
    assert (kind, fired) == ("mixed_review", ["contrast", "retain", "advance"])
    assert blocks == [
        ("review", "", "dsa:binary-search", "", 180),
        ("review", "", "dsa:sliding-window", "", 180),
        ("review", "", "dsa:arrays-hashing", "", 180),
        ("atom", "pattern", "dsa:binary-search", "", 90),
        ("atom", "classify", "dsa:binary-search", "", 240),
        ("problem", "independent", "dsa:binary-search", "lower-bound-queries", 600),
        ("reflection", "", "dsa:binary-search", "", 30),
    ]


# ---------------------------------------------------------------- end to end, flag on and off


def make_client(tmp_path, enabled):
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient
    from runner_support import SIGNING, WORKER, profiles

    from socrat.config import Settings
    from socrat.main import create_app

    url = f"sqlite:///{tmp_path / 'planner.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    settings = Settings(
        database_url=url,
        environment="test",
        dev_login_enabled=True,
        execution_profiles=profiles(),
        browser_runtimes=[],
        execution_signing_secret=SIGNING,
        execution_worker_secret=WORKER,
        pattern_planner_enabled=enabled,
    )
    app = create_app(settings)
    return app, TestClient(app, base_url="http://localhost:3000")


@pytest.mark.parametrize("enabled", [True, False])
def test_session_start_uses_the_pattern_planner_only_with_the_flag(tmp_path, monkeypatch, enabled):
    from test_learner_api import login, onboard

    from socrat.learn import service as learn

    monkeypatch.setattr(learn, "locked_concepts", lambda *args: {})  # open every concept
    app, client = make_client(tmp_path, enabled)
    with client:
        headers = login(client)
        onboard(client, headers, course="zero")
        # Patterns wait for their course prerequisites: place the learner past every concept
        # that has no pattern, so the patterns built on them are ready to teach.
        catalog = default_catalog()
        taught = {p.concept for p in catalog.patterns.values()}
        with Session(app.state.engine) as db, db.begin():
            enrollment = db.scalar(select(Enrollment).where(Enrollment.active.is_(True)))
            for concept in catalog.course_concepts("zero"):
                if concept not in taught:
                    db.merge(
                        ConceptState(
                            enrollment_id=enrollment.id,
                            concept=concept,
                            state=placed(True, now()).to_dict(),
                        )
                    )
        assert client.get("/api/v1/features").json()["pattern_planner"] is enabled
        view = client.post(
            "/api/v1/learning-sessions", json={"minutes": 30}, headers=headers
        ).json()
        with Session(app.state.engine) as db:
            row = db.get(LearningSession, view["id"])
            plan = row.payload.get("pattern_plan")
            if not enabled:
                assert plan is None
                assert not any("pattern" in b for b in row.payload["blocks"])
                return
            assert plan["type"] == "intro" and plan["pattern"].startswith("zero:")
            assert len(plan["scores"]) >= 1 and set(plan["scores"][0]["parts"]) >= {
                "weakness",
                "diversity",
            }
            blocks = row.payload["blocks"]
            assert all(
                b.get("pattern") == plan["pattern"]
                for b in blocks
                if b["kind"] in {"atom", "problem"}
            )
            assert any(b.get("mode") == "independent" for b in blocks)
        # Working through the draft pattern atoms writes no mastery evidence.
        from test_learning_sessions import complete_current

        while view["current"]["kind"] == "atom":
            view = complete_current(client, headers, view)
        with Session(app.state.engine) as db:
            assert not list(db.scalars(select(Evidence).where(Evidence.activity_id.like("atom:%"))))
    app.state.engine.dispose()
