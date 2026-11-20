"""A small, generic course pack for tests that need a catalog served by the app.

Socrat ships no built-in courses (every course is generated for a learner and lives in the
database), so tests that go through ``default_catalog`` get these two synthetic packs instead:
``basics`` (a code course with a few modules) and ``algo`` (which builds on ``basics``). They
carry no real subject matter: a lesson is filler text, a question is "which option is right".
Nothing here may be shaped like a removed course; tests must not rely on concept names beyond
what this module defines.
"""

import json
import os
from pathlib import Path

import yaml

_SENTENCE = (
    "A focused explanation of the idea, with a worked example traced step by step and the "
    "reason it works. "
)
LESSON = "\n\n".join(
    f"## {heading}\n\n{_SENTENCE * 2}"
    for heading in ("The idea", "A worked example", "Why it works")
)


PROMPTS = [
    "What is the main purpose of {topic} when you first meet it in practice?",
    "Which of these examples correctly applies {topic} to a small input?",
    "A learner gets an unexpected result while using {topic}; what should they check first?",
    "Why does the usual approach to {topic} still give the right answer on edge cases?",
    "Which change would make a {topic} solution slower without changing its output?",
    "How would you explain {topic} to someone who has never seen it before?",
]


def quiz(prefix: str) -> list[dict]:
    """Six items from easy to hard, so every difficulty band has questions."""
    out = []
    for i, difficulty in enumerate([1, 2, 3, 4, 5, 4]):
        out.append(
            dict(
                id=f"{prefix}-q{i}",
                prompt=PROMPTS[i].format(topic=prefix),
                options=["the right one", "a wrong one", "another wrong one", "a last wrong one"],
                answer=0,
                explanation="Because the first option is the right one.",
                difficulty=difficulty,
                # The last question is about Python only, so language filtering has work to do.
                languages=["python"] if i == 5 else [],
            )
        )
    return out


def concept(cid: str, module: str, prerequisites=(), problems=(), minutes=30, difficulty=2) -> dict:
    return dict(
        id=cid,
        title=cid.replace("-", " ").title(),
        summary=f"Learn {cid} properly.",
        module=module,
        prerequisites=list(prerequisites),
        difficulty=difficulty,
        estimated_minutes=minutes,
        lesson=LESSON,
        key_points=["one", "two"],
        pitfalls=["a common slip"],
        resources=[
            dict(
                title="Official docs",
                url="https://docs.python.org/3/",
                kind="docs",
                source="Python",
                minutes=10,
            ),
            dict(
                title="A video",
                url="https://www.youtube.com/watch?v=abc",
                kind="video",
                source="YouTube",
                minutes=12,
            ),
        ],
        quiz=quiz(cid),
        problems=list(problems),
    )


def problem(pid: str, concept_id: str, difficulty: str) -> dict:
    return dict(
        id=pid,
        title=pid.replace("-", " ").title(),
        concepts=[concept_id],
        difficulty=difficulty,
        statement="Read a number and print twice its value, carefully.",
        input_format="One integer n.",
        output_format="The value 2n.",
        examples=[dict(input="2\n", output="4\n")],
        hints=["What operation doubles?", "Multiply by two."],
        approach="Multiply the input by two and print it.",
        reference="print(int(input()) * 2)\n",
    )


CASES = [
    dict(input="2\n", expected="4\n", public=True),
    dict(input="5\n", expected="10\n", public=False),
    dict(input="0\n", expected="0\n", public=False),
]

LEVELS = [
    dict(id="brand-new", label="Brand new", description="Never done this"),
    dict(id="some", label="Some", description="Done a little", start_concept="loops"),
]


def packs() -> dict[str, dict]:
    basics_concepts = [
        concept("values", "start", problems=["double-it", "double-twice"], difficulty=1),
        concept("text", "start", ["values"], problems=["double-text"], difficulty=1),
        concept("conditions", "start", ["text"], difficulty=2),
        concept("loops", "repeat", ["conditions"], problems=["sum-loop", "sum-again"]),
        concept("lists", "repeat", ["loops"], problems=["sum-list"]),
        concept("functions", "repeat", ["lists"], problems=["sum-fn", "sum-fn-two"], difficulty=3),
        concept("recursion", "bigger", ["functions"], difficulty=3),
        concept("files", "bigger", ["recursion"], difficulty=3),
    ]
    basics_problems = [
        problem("double-it", "values", "easy"),
        problem("double-twice", "values", "easy"),
        problem("double-text", "text", "easy"),
        problem("sum-loop", "loops", "medium"),
        problem("sum-again", "loops", "medium"),
        problem("sum-list", "lists", "medium"),
        problem("sum-fn", "functions", "medium"),
        problem("sum-fn-two", "functions", "hard"),
    ]
    algo_concepts = [
        concept("arrays", "core", ["basics:functions"], problems=["arr-easy", "arr-hard"]),
        concept("pairs", "core", ["arrays"], problems=["pair-easy"]),
        concept("lookup", "core", ["pairs"], problems=["lookup-easy"]),
        concept("trees", "shapes", ["lookup"]),
        concept("graphs", "deep", ["trees"], difficulty=4),
    ]
    algo_problems = [
        problem("arr-easy", "arrays", "easy"),
        problem("arr-hard", "arrays", "hard"),
        problem("pair-easy", "pairs", "easy"),
        problem("lookup-easy", "lookup", "easy"),
    ]
    return {
        "basics": dict(
            course=dict(
                id="basics",
                title="Basics",
                tagline="A small course used by tests.",
                description="A synthetic course used by tests to exercise the engine end to end.",
                version="1.0.0",
                languages=["python", "cpp", "java"],
                levels=LEVELS,
                modules=[
                    dict(
                        id="start",
                        title="Start",
                        summary="The first steps.",
                        concepts=["values", "text", "conditions"],
                    ),
                    dict(
                        id="repeat",
                        title="Repeat",
                        summary="Doing things again.",
                        concepts=["loops", "lists", "functions"],
                    ),
                    dict(
                        id="bigger",
                        title="Bigger",
                        summary="Larger programs.",
                        concepts=["recursion", "files"],
                    ),
                ],
            ),
            concepts=basics_concepts,
            problems=basics_problems,
        ),
        "algo": dict(
            course=dict(
                id="algo",
                title="Algo",
                tagline="A second small course used by tests.",
                description="A synthetic course that builds on the first one, used by tests.",
                version="1.0.0",
                languages=["python", "cpp", "java"],
                levels=[
                    dict(id="brand-new", label="Brand new", description="Never done this"),
                    dict(id="ok", label="Okay", description="Done some", start_concept="pairs"),
                ],
                modules=[
                    dict(
                        id="core",
                        title="Core",
                        summary="Core ideas.",
                        concepts=["arrays", "pairs", "lookup"],
                    ),
                    dict(
                        id="shapes",
                        title="Shapes",
                        summary="Structures.",
                        concepts=["trees"],
                    ),
                    dict(
                        id="deep",
                        title="Deep",
                        summary="Harder structures.",
                        concepts=["graphs"],
                    ),
                ],
            ),
            concepts=algo_concepts,
            problems=algo_problems,
        ),
    }


def write(root: Path, tests_root: Path) -> None:
    """Write the packs as the loader reads them (course.yaml, concepts/, problems/, tests)."""
    tests_root.mkdir(parents=True, exist_ok=True)
    for course_id, pack in packs().items():
        folder = root / course_id
        (folder / "concepts").mkdir(parents=True, exist_ok=True)
        (folder / "problems").mkdir(parents=True, exist_ok=True)
        (folder / "course.yaml").write_text(yaml.safe_dump(pack["course"]), encoding="utf-8")
        for item in pack["concepts"]:
            (folder / "concepts" / f"{item['id']}.yaml").write_text(
                yaml.safe_dump(item), encoding="utf-8"
            )
        for item in pack["problems"]:
            (folder / "problems" / f"{item['id']}.yaml").write_text(
                yaml.safe_dump(item), encoding="utf-8"
            )
            (tests_root / f"{item['id']}.json").write_text(json.dumps(CASES), encoding="utf-8")


def install() -> Path:
    """Point the app's catalog at the synthetic packs; call before the first catalog load."""
    # One folder per process, so parallel pytest runs never write over each other.
    default = Path(__file__).parents[3] / ".cache" / "test-content" / str(os.getpid())
    base = Path(os.environ.get("SOCRAT_TEST_CONTENT", default))
    root, tests_root = base / "courses", base / "tests"
    write(root, tests_root)  # small and deterministic: always rewritten, so it never goes stale
    os.environ["SOCRAT_CONTENT_ROOT"] = str(root)
    os.environ["SOCRAT_CONTENT_TESTS"] = str(tests_root)
    return root
