"""Practice from the lesson's own checked material: ready at once, shaped by the subject,
and (when the owner allows it) seen by the coach. Both flags are off by default."""

# ruff: noqa: F811
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import Session
from test_drills import _first_open_concept
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.catalog.schema import Entry, Section
from socrat.drills import bank, service
from socrat.drills.routes import PRACTICE_EVIDENCE_PER_DAY
from socrat.models import Evidence

VOCAB = Section(
    id="vocabulary",
    title="Vocabulary",
    purpose="The words each lesson teaches, with their meaning.",
    style="cards",
    fields=["Word", "Meaning"],
)
TIMELINE = Section(
    id="timeline",
    title="Timeline",
    purpose="What happened when, in the order it happened.",
    style="timeline",
    fields=["Year", "Event"],
)


def lesson(id_, title, *entries):
    rows = [Entry(section=s, values=list(v)) for s, v in entries]
    return SimpleNamespace(id=id_, title=title, entries=rows)


def course(*sections):
    return SimpleNamespace(id="kannada", sections=list(sections))


def test_the_kinds_follow_the_subject_and_the_learner():
    plain = SimpleNamespace(sections=[])
    assert bank.plan(plain, "workbench")[0] == "number"
    assert bank.plan(plain, "code")[0] == "choice"
    # A course with a vocabulary practises it by matching first; a timeline by ordering.
    assert bank.plan(course(VOCAB), "reading")[0] == "match"
    assert bank.plan(course(TIMELINE, VOCAB), "reading")[:2] == ["order", "match"]
    # A young learner taps before they type.
    young = bank.plan(course(VOCAB), "workbench", "kid")
    assert young.index("choice") < young.index("number") and young[-2:] == ["text", "number"]
    assert len(set(young)) == len(young)


def test_a_vocabulary_becomes_matching_and_recall_filled_from_finished_lessons():
    here = lesson(
        "greetings",
        "Greetings",
        ("vocabulary", ["namaskara", "hello"]),
        ("vocabulary", ["hogi", "go"]),
    )
    before = lesson(
        "numbers",
        "Numbers",
        ("vocabulary", ["ondu", "one"]),
        ("vocabulary", ["eradu", "two"]),
        ("vocabulary", ["namaskara", "hello"]),  # a repeat is used once
    )
    items = bank.from_sections(course(VOCAB), here, [before])
    kinds = [q["kind"] for q in items]
    assert kinds == ["match", "truefalse", "text", "text"]
    judge = items[1]
    assert judge["prompt"] == "Vocabulary. True or false? namaskara: go"
    assert judge["truth"] is False and len(judge["options"]) == 2
    why = judge["options"].index("namaskara goes with: hello")
    assert service.correct(judge, f"false|{why}")
    assert not service.correct(judge, f"true|{why}")
    assert not service.correct(judge, f"false|{1 - why}")  # right verdict, wrong reason
    match = items[0]
    assert match["prompt"] == "Vocabulary: match each word to its meaning."
    assert match["lefts"] == ["namaskara", "hogi", "ondu", "eradu"]  # this lesson's rows first
    assert sorted(match["options"]) == ["go", "hello", "one", "two"]
    recall = items[2]
    assert recall["answer"] == "namaskara" and "hello" in recall["prompt"]
    assert service.correct(recall, "Namaskara") and not service.correct(recall, "hogi")
    assert len({q["ref"] for q in items}) == 4
    # Too few rows to match: judging and recall. Nothing of this lesson: nothing.
    alone = [q["kind"] for q in bank.from_sections(course(VOCAB), here, [])]
    assert alone == ["truefalse", "text", "text"]
    assert bank.from_sections(course(VOCAB), lesson("x", "X"), [before]) == []


def test_a_timeline_becomes_an_ordering_question_by_year():
    here = lesson(
        "empire",
        "The empire",
        ("timeline", ["1565", "Battle of Talikota"]),
        ("timeline", ["1336", "Vijayanagara is founded"]),
        ("timeline", ["1509", "Krishnadevaraya is crowned"]),
    )
    order = bank.from_sections(course(TIMELINE), here, [])[0]
    assert order["kind"] == "order"
    assert [order["options"][i] for i in order["key"]] == [
        "Vijayanagara is founded",
        "Krishnadevaraya is crowned",
        "Battle of Talikota",
    ]
    assert order["options"] != [order["options"][i] for i in order["key"]]  # shown shuffled


def step(prompt, options, answer=0, state=""):
    return SimpleNamespace(
        state=state, prompt=prompt, options=options, answer=answer, explanation="Because it is."
    )


def test_in_lesson_checks_come_back_as_recall_without_code_or_broken_ones():
    atoms = [
        SimpleNamespace(id="a", adapters={}, steps=[step("Which is a noun?", ["dog", "run"])]),
        SimpleNamespace(id="b", adapters={"python": 1}, steps=[step("What prints?", ["1", "2"])]),
        SimpleNamespace(
            id="c",
            adapters={},
            steps=[
                step("Pick one.", ["same", "same"]),  # options not distinct
                step("Too long?", ["a", "b"], state="x" * 700),
                step("What is 2 + 2?", ["3", "4"], 1, state="Add the numbers."),
            ],
        ),
    ]
    cat = SimpleNamespace(atom_packs={"k:l": SimpleNamespace(status="released", atoms=atoms)})
    items = bank.from_checks(cat, "k:l")
    assert [q["answer"] for q in items] == ["dog", "4"]
    assert items[1]["prompt"] == "Add the numbers.\n\nWhat is 2 + 2?"
    cat.atom_packs["k:l"].status = "quarantined"
    assert bank.from_checks(cat, "k:l") == [] and bank.from_checks(cat, "k:other") == []


def q(ref, kind="choice"):
    return {"ref": ref, "kind": kind}


def test_a_set_brings_back_misses_first_then_new_questions_and_mixes_kinds():
    items = [q("a"), q("b"), q("c", "match"), q("d"), q("e", "text"), q("f"), q("g")]
    chosen = bank.choose(items, ["match", "choice", "text"], right={"a", "b"}, missed={"g"})
    refs = [c["ref"] for c in chosen]
    assert refs[0] == "g" and len(refs) == service.QUESTIONS
    assert set(refs[1:]) == {"c", "d", "e", "f"}  # never answered, before those already right
    assert refs[1] == "c"  # the kind that suits the subject leads
    kinds = [c["kind"] for c in chosen[1:]]
    assert kinds[:3] == ["match", "choice", "text"]  # not two of a kind while another waits


def test_what_was_right_and_missed_is_read_from_stored_sets_newest_answer_winning():
    def record(*answers):
        return SimpleNamespace(
            outcome={
                "questions": [{"ref": r} for r, _ in answers],
                "answers": {str(i): {"correct": ok} for i, (_, ok) in enumerate(answers)},
            }
        )

    newest, oldest = record(("a", True), ("b", False)), record(("a", False), ("c", True))
    assert bank.history([newest, oldest]) == ({"a", "c"}, {"b"})
    assert bank.history(
        [SimpleNamespace(outcome={"questions": [{}], "answers": {"0": {"correct": True}}})]
    ) == (
        set(),
        set(),
    )


def test_the_coach_speaks_only_when_the_set_is_finished():
    def outcome(*marks):
        return {
            "concept": "k:l",
            "questions": [{}] * 4,
            "answers": {str(i): {"correct": m} for i, m in enumerate(marks)},
        }

    assert service.advice(outcome(True, True)) is None
    assert service.advice(outcome(True, True, True, True))["tone"] == "ahead"
    back = service.advice(outcome(True, False, False, False))
    assert back["tone"] == "review" and back["concept"] == "k:l" and "1 of 4" in back["message"]
    assert service.advice(outcome(True, True, True, False))["tone"] == "steady"


def stocked(monkeypatch, count=7):
    """A lesson with ``count`` checked questions in its bank."""
    items = [
        bank._question(
            f"ref-{i}",
            kind="choice",
            prompt=f"Question {i}?",
            options=["yes", "no"],
            answer="yes",
            explanation="Yes is right.",
        )
        for i in range(count)
    ]
    monkeypatch.setattr(bank, "pool", lambda *args: list(items))


def learner(client, monkeypatch, subject="mia"):
    monkeypatch.setattr("socrat.drills.routes.require_feature", lambda *a: None)
    headers = login(client, subject=subject, name=subject.title())
    onboard(client, headers)
    return headers, _first_open_concept(client, headers)[1]


def answer(client, headers, set_id, index, given):
    url = f"/api/v1/drills/{set_id}/answers"
    return client.post(url, json={"question": index, "answer": given}, headers=headers).json()


def test_a_bank_set_needs_no_model_is_free_and_brings_misses_back(client, monkeypatch):
    def no_model(settings):
        raise AssertionError("a bank set must not ask a model")

    monkeypatch.setattr("socrat.drills.routes.make_provider", no_model)
    monkeypatch.setattr(service, "SETS_PER_DAY", 0)  # the day's allowance is already used up
    stocked(monkeypatch)
    headers, concept = learner(client, monkeypatch)
    refused = client.post("/api/v1/drills", json={"concept": concept}, headers=headers)
    assert refused.status_code == 429  # off by default: the model path, and its allowance
    client.app.state.settings.practice_bank = True
    made = client.post("/api/v1/drills", json={"concept": concept}, headers=headers)
    assert made.status_code == 200, made.text
    first = made.json()
    assert first["source"] == "bank" and first["questions"] == service.QUESTIONS
    assert first["coach"] is None and "ref" not in first["items"][0]
    missed = first["items"][2]["prompt"]
    for index in range(service.QUESTIONS):
        result = answer(client, headers, first["id"], index, "no" if index == 2 else "yes")
        assert result["counted"] is False  # evidence is off
    # The miss earned one easier question on the same idea, added to the end of the set.
    extra = result["set"]["items"][-1]
    assert len(result["set"]["items"]) == service.QUESTIONS + 1
    assert extra["note"] == "An easier one on the same idea."
    assert answer(client, headers, first["id"], service.QUESTIONS, "yes")["set"]["coach"][
        "tone"
    ] == ("steady")
    second = client.post("/api/v1/drills", json={"concept": concept}, headers=headers).json()
    prompts = [item["prompt"] for item in second["items"]]
    assert prompts[0] == missed  # the miss comes back first
    assert "Question 6?" in prompts[1:3]  # then what was never asked


def test_too_little_in_the_bank_leaves_the_set_to_the_model(client, monkeypatch):
    stocked(monkeypatch, count=2)
    asked = []

    def model(settings):
        asked.append(1)
        raise AssertionError("stop here: the model was reached")

    monkeypatch.setattr("socrat.drills.routes.make_provider", model)
    headers, concept = learner(client, monkeypatch)
    client.app.state.settings.practice_bank = True
    try:
        client.post("/api/v1/drills", json={"concept": concept}, headers=headers)
    except AssertionError:
        pass
    assert asked


def test_bank_answers_count_as_recall_evidence_within_the_days_limits(client, monkeypatch):
    stocked(monkeypatch)
    headers, concept = learner(client, monkeypatch)
    settings = client.app.state.settings
    settings.practice_bank = settings.practice_evidence = True
    first = client.post("/api/v1/drills", json={"concept": concept}, headers=headers).json()
    counted = [
        answer(client, headers, first["id"], i, "no" if i == 0 else "yes")["counted"]
        for i in range(service.QUESTIONS)
    ]
    assert counted == [True] * PRACTICE_EVIDENCE_PER_DAY + [False] * 2  # a few a day, no more
    answer(client, headers, first["id"], service.QUESTIONS, "yes")  # the coach's extra question
    with Session(client.app.state.engine) as db:
        rows = db.scalars(select(Evidence).where(Evidence.activity_id.like("practice:%"))).all()
    assert [(r.kind, r.score, r.concept) for r in rows] == [
        ("retrieval", 0.0, concept),
        ("retrieval", 1.0, concept),
        ("retrieval", 1.0, concept),
    ]
    assert all(r.details["source"] == "practice" for r in rows)
    # The same question again today adds nothing, however often it is answered.
    second = client.post("/api/v1/drills", json={"concept": concept}, headers=headers).json()
    assert answer(client, headers, second["id"], 0, "yes")["counted"] is False


def test_a_model_written_set_never_counts(client, monkeypatch):
    import json

    from test_drills import SET, Scripted

    monkeypatch.setattr("socrat.drills.routes.make_provider", lambda s: Scripted(json.dumps(SET)))
    headers, concept = learner(client, monkeypatch)
    client.app.state.settings.practice_evidence = True
    made = client.post("/api/v1/drills", json={"concept": concept}, headers=headers).json()
    assert made["source"] == "model"
    assert answer(client, headers, made["id"], 0, "3")["counted"] is False
    with Session(client.app.state.engine) as db:
        assert (
            db.scalars(select(Evidence).where(Evidence.activity_id.like("practice:%"))).all() == []
        )


def test_true_or_false_is_judged_with_its_reason_and_refuses_malformed_answers():
    plain = service.Question.model_validate(
        {
            "kind": "truefalse",
            "prompt": "Ice is frozen water.",
            "answer": "True",
            "explanation": "It is.",
        }
    ).model_dump()
    assert plain["truth"] is True and plain["options"] == [] and plain["answer"] == "True"
    assert service.correct(plain, "true") and not service.correct(plain, "false")
    assert service.judged("true|0", plain) is None and service.judged("maybe", plain) is None
    reasoned = service.Question.model_validate(
        {
            "kind": "truefalse",
            "prompt": "Heavier things fall faster in a vacuum.",
            "answer": "false",
            "reasons": ["Gravity pulls harder on them", "Without air, all things fall alike"],
            "reason": "Without air, all things fall alike",
            "explanation": "Air resistance is what separates them.",
        }
    ).model_dump()
    key = reasoned["options"].index("Without air, all things fall alike")
    assert service.correct(reasoned, f"false|{key}") and not service.correct(reasoned, "false")
    assert service.judged("false", reasoned) is None  # a reason is required here
    assert "Without air" in reasoned["answer"]
    # A stored question validates again to the same question: the key is never lost.
    assert service.Question.model_validate(reasoned).model_dump() == reasoned
    for bad in (
        {"answer": "perhaps"},
        {"answer": "true", "reasons": ["only one"], "reason": "only one"},
        {"answer": "true", "reasons": ["a", "b"], "reason": "c"},
    ):
        try:
            service.Question.model_validate(
                {"kind": "truefalse", "prompt": "A statement.", "explanation": "Why."} | bad
            )
        except ValueError:
            continue
        raise AssertionError(bad)


def test_gaps_are_filled_from_a_shuffled_word_bank_and_graded_by_position():
    gaps = service.Question.model_validate(
        {
            "kind": "gaps",
            "prompt": "Water ___ at 100 degrees and ___ at 0.",
            "fills": ["boils", "freezes"],
            "extras": ["melts"],
            "explanation": "At sea level.",
        }
    ).model_dump()
    assert sorted(gaps["options"]) == ["boils", "freezes", "melts"]
    assert gaps["answer"] == "Water boils at 100 degrees and freezes at 0."
    right = ",".join(str(gaps["options"].index(w)) for w in ("boils", "freezes"))
    wrong = ",".join(str(gaps["options"].index(w)) for w in ("freezes", "boils"))
    assert service.correct(gaps, right) and not service.correct(gaps, wrong)
    assert service.picks("0", gaps) is None  # one pick per gap
    for bad in (
        {"prompt": "No gap here.", "fills": ["x"]},
        {"prompt": "One ___ only.", "fills": ["a", "b"]},
        {"prompt": "Same ___ and ___.", "fills": ["a", "a"]},
    ):
        try:
            service.Question.model_validate({"kind": "gaps", "explanation": "Why."} | bad)
        except ValueError:
            continue
        raise AssertionError(bad)
    kept = service.parse(
        '{"questions": ['
        + ",".join(
            [
                '{"kind": "gaps", "prompt": "A ___ b.", "fills": ["x"], "extras": ["y"], "explanation": "ok."}',
                '{"kind": "truefalse", "prompt": "Fire is cold.", "answer": "false", "explanation": "ok."}',
                '{"kind": "number", "prompt": "Two plus two?", "answer": "4", "explanation": "ok."}',
            ]
        )
        + "]}"
    )
    assert [q["kind"] for q in kept] == ["gaps", "truefalse", "number"]


def test_after_a_miss_the_coach_goes_easier_then_to_the_lesson_underneath(monkeypatch):
    def item(ref, kind="choice"):
        return {"ref": ref, "kind": kind}

    pools = {
        "k:loops": [item("l1", "text"), item("l2"), item("l3", "text")],
        "k:variables": [item("v1", "text"), item("v2", "match")],
    }
    monkeypatch.setattr(bank, "pool", lambda cat, course, concept, earlier: pools[concept])
    cat = SimpleNamespace(
        course=lambda course_id: None,
        prerequisites={"k:loops": ["k:missing", "k:variables"]},
        concepts={"k:variables": 1, "k:loops": 1},
        concept=lambda q: SimpleNamespace(status="live", title="Variables"),
    )
    outcome = {"source": "bank", "concept": "k:loops", "questions": [item("l1", "text")]}
    first = bank.follow_up(cat, outcome, 0, [])
    assert first["ref"] == "l2" and first["concept"] == "k:loops"  # recognising, same idea
    assert first["note"] == "An easier one on the same idea."
    outcome["questions"].append(first)
    second = bank.follow_up(cat, outcome, 1, [])  # the easier one was missed too
    assert second["ref"] == "v2" and second["concept"] == "k:variables"
    assert "Variables" in second["note"] and "builds on" in second["note"]
    outcome["questions"].append(second)
    assert bank.follow_up(cat, outcome, 2, []) is None  # two a set, no more
    assert (
        bank.follow_up(cat, {**outcome, "source": "model", "questions": [item("l1")]}, 0, [])
        is None
    )
