"""Found in a live run: every generated lesson failed its gates on slips code can repair
(a lesson a little over the style's length, a bash block, a citation [0], a three-sentence
hook, an extra field), so no course ever got a lesson."""

from socrat.catalog.atoms import Atom
from socrat.coursegen import package as pkg

SOURCES = [
    {"n": 1, "title": "A", "url": "https://a.example"},
    {"n": 2, "title": "B", "url": "https://b.example"},
]


def test_length_counts_the_lesson_not_its_answers_or_sources():
    body = "## Idea\n" + "x" * 1000
    text = (
        body
        + "\n<details><summary>Answers</summary>"
        + "y" * 900
        + "</details>\n## Sources\n"
        + "z" * 500
    )
    assert pkg.teaching_length(text) == len(body)


def test_shell_blocks_become_text_and_unknown_citations_go():
    draft = {
        "lesson": "Install it [1][0].\n```bash\npip install x\n```\n```python\nprint(1)\n```\nSee [3]."
    }
    out = pkg.tidy_lesson(draft, SOURCES)["lesson"]
    assert "```text\npip install x" in out and "```python" in out
    assert "[1]" in out and "[0]" not in out and "[3]" not in out
    assert pkg.tidy_lesson(draft, [])["lesson"].count("[0]") == 1  # nothing to check against


def test_an_almost_right_atom_is_repaired_without_inventing_checks():
    hook = pkg.tidy_atom(
        {
            "id": "h",
            "kind": "hook",
            "title": "Why",
            "objective": "Wonder why it works",
            "body": "One. Two? Three! Four.",
            "extra": 1,
        }
    )
    assert hook["body"] == "One. Two?" and "extra" not in hook and hook["seconds"] == 60
    Atom.model_validate(hook)
    bare = pkg.tidy_atom(
        {
            "id": "p",
            "kind": "predict",
            "title": "Guess",
            "objective": "Predict the output",
            "body": "What prints?",
            "seconds": 500,
            "steps": [{"prompt": "?", "options": ["a", "b"], "answer": 0}],
        }
    )
    assert bare["kind"] == "concept" and bare["steps"] == [] and bare["seconds"] == 120
    Atom.model_validate(bare)
    kept = pkg.tidy_atom(
        {
            "id": "t",
            "kind": "trace",
            "title": "Trace",
            "objective": "Trace the loop",
            "body": "Follow i.",
            "seconds": 40,
            "steps": [
                {
                    "state": "i=0",
                    "prompt": "What is i next?",
                    "options": ["0", "1"],
                    "answer": 1,
                    "explanation": "It adds one.",
                    "seconds": 5,
                }
            ],
        }
    )
    assert kept["kind"] == "trace" and "seconds" not in kept["steps"][0]
    Atom.model_validate(kept)


def test_sequence_entries_for_missing_activities_are_left_out():
    from socrat.catalog.registry import default_catalog

    concept = default_catalog().concept("zero:programs-and-output")
    lesson = {
        "lesson": concept.lesson,
        "key_points": concept.key_points,
        "resources": [r.model_dump(mode="json") for r in concept.resources],
    }
    quiz = {
        "quiz": [q.model_dump(mode="json") for q in concept.quiz][:6],
        "sequence": ["lesson", "visual:0", "task:never-written", "quiz"],
    }
    live, problems = pkg.build_concept(concept, lesson, quiz, 1, "test")  # a non-code course
    assert not any(problems.values()), problems
    assert live.sequence == ["lesson", "quiz"]


def test_a_long_atom_body_is_cut_at_a_sentence_within_the_limit():
    body = " ".join(f"Sentence {i} has exactly six words." for i in range(30))  # 180 words
    atom = pkg.tidy_atom(
        {
            "id": "r",
            "kind": "reflection",
            "title": "Think",
            "objective": "Reflect on it",
            "body": body,
        }
    )
    assert len(atom["body"].split()) <= 120 and atom["body"].endswith("words.")
    Atom.model_validate(atom)
