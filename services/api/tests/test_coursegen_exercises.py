"""Generated code: exercises, code quiz items and atom adapters, verified by execution."""

import asyncio
import json
import subprocess
import sys
import threading

from runner_support import SIGNING, WORKER, profiles
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_coursegen_package import (  # noqa: F401  (fixtures)
    ATOMS,
    FACTS_OK,
    PASS,
    QUIZ,
    lesson,
    published,
    web,
)
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant.gateway import Event, usage_event
from socrat.catalog import generated
from socrat.catalog.registry import default_catalog
from socrat.coursegen import execute, exercise, jobs
from socrat.coursegen import package as pkg
from socrat.execution.protocol import CaseResult, ExecutionResult, JobEnvelope, same_output, sign
from socrat.models import GeneratedConcept, GenerationJob, Submission

ROLES = {
    pkg.LESSON: "author",
    pkg.QUIZ: "quiz",
    pkg.ATOMS: "atoms",
    pkg.FACTS: "facts",
    pkg.REVIEW: "reviewer",
    exercise.ENGINEER: "engineer",
    exercise.REVIEW: "checker",
}


class Scripted:
    def __init__(self, **replies):
        self.replies = {role: [json.dumps(r) for r in rs] for role, rs in replies.items()}
        self.prompts: dict[str, list[str]] = {role: [] for role in ROLES.values()}

    def make(self, settings):
        script = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                role = ROLES[system]
                script.prompts[role].append(turns[0].content)
                yield Event("text", text=script.replies[role].pop(0))
                yield usage_event(1000, 3000)

        return Provider()


def python(source: str, stdin: str) -> dict:
    """Test stand-in for a Python worker; the code here is the tests' own fixtures."""
    done = subprocess.run(
        [sys.executable, "-I", "-c", source], input=stdin, capture_output=True, text=True
    )
    status = "executed" if done.returncode == 0 else "runtime_error"
    return dict(status=status, stdout=done.stdout, stderr=done.stderr)


class Local:
    def __init__(self, languages=("python",)):
        self.languages, self.runs = set(languages), []

    def available(self, languages):
        return [lang for lang in languages if lang in self.languages]

    async def run(self, language, source, inputs):
        self.runs.append(language)
        return [python(source, stdin) for stdin in inputs]


def run(client, make, executor, http=None):  # noqa: F811
    state = client.app.state
    return asyncio.run(
        jobs.run_once(state.engine, state.settings, default_catalog(), make, http, executor)
    )


REFERENCE = (
    "n = int(input())\np = list(map(int, input().split()))\nt = list(map(int, input().split()))\n"
    "print(sum((a - b) ** 2 for a, b in zip(p, t)))\n"
)
BRUTE = (
    "n = int(input())\np = input().split()\nt = input().split()\ntotal = 0\n"
    "for i in range(n):\n    d = int(p[i]) - int(t[i])\n    total += d * d\nprint(total)\n"
)
WRONG = REFERENCE.replace("(a - b) ** 2", "abs(a - b)")


def gen(low, high, count=14):
    return (
        "def cases(rng):\n"
        f"    for _ in range({count}):\n"
        "        n = rng.randint(1, 6)\n"
        f"        p = [rng.randint({low}, {high}) for _ in range(n)]\n"
        f"        t = [rng.randint({low}, {high}) for _ in range(n)]\n"
        "        yield f\"{n}\\n{' '.join(map(str, p))}\\n{' '.join(map(str, t))}\"\n"
    )


def engineered(low=-5, high=5, example=("2\n1 2\n2 4", "5")):
    return {
        "problem": {
            "id": "squared-error",
            "title": "Squared error",
            "difficulty": "easy",
            "statement": "Given predictions and targets, print the sum of squared errors.",
            "input_format": "n, then n predictions, then n targets.",
            "output_format": "One integer.",
            "constraints": ["1 <= n <= 100"],
            "examples": [{"input": example[0], "output": example[1]}],
            "hints": ["Square each difference.", "Add them up."],
            "approach": "Sum (prediction - target) squared over all pairs; squaring "
            "punishes large errors more than small ones.",
            "reference": REFERENCE,
            "brute": BRUTE,
            "generator": gen(low, high),
            "small_generator": gen(low, high, 6),
            "starter": {"python": "n = int(input())\n# read the two lines and print the sum\n"},
        },
        "wrong": WRONG,
    }


CHECKED = {
    "scores": {d: 5 for d in exercise.DIMENSIONS},
    "summary": "Exercises the loss directly.",
    "fixes": [],
}


def release(client, web, script, executor, concept="what-is-ml"):  # noqa: F811
    with Session(client.app.state.engine) as db, db.begin():
        jobs.enqueue(db, "package", "ai-basics", {}, None, target=concept)
    run(client, script.make, executor, web())


def wants_code(client, concept="what-is-ml"):  # noqa: F811
    with Session(client.app.state.engine) as db, db.begin():
        row = db.get(GeneratedConcept, ("ai-basics", concept))
        outline = {**row.payload["outline"], "assessment": ["quiz", "code"]}
        row.payload = {**row.payload, "outline": outline}


def latest(client, kind):  # noqa: F811
    with Session(client.app.state.engine) as db:
        query = select(GenerationJob).where(GenerationJob.kind == kind)
        return db.scalars(query.order_by(GenerationJob.created_at.desc())).first()


WORKER_HEADERS = {"Authorization": "Bearer " + WORKER}


def heartbeat(client):  # noqa: F811
    images = [p["image"] for p in profiles()]
    client.post(
        "/api/v1/execution/worker/heartbeat",
        json={"worker_id": "w1", "images": images},
        headers=WORKER_HEADERS,
    )


def work(client) -> tuple[str, dict]:  # noqa: F811
    """Act as a Python worker for the next job: claim, run each case, report signed facts."""
    envelope = None
    while envelope is None:
        envelope = client.post(
            "/api/v1/execution/worker/claim", json={"worker_id": "w1"}, headers=WORKER_HEADERS
        ).json()["job"]
    job = JobEnvelope.model_validate(envelope)
    cases = []
    for i, test in enumerate(job.tests):
        ran = python(job.source, test.input)
        if test.expected is None:
            status = ran["status"]
        else:
            status = "passed" if same_output(ran["stdout"], test.expected) else "wrong_answer"
        shown = ran["stdout"] if test.visibility == "public" else ""
        cases.append(CaseResult(index=i, status=status, wall_ms=3, stdout=shown))
    result = ExecutionResult(
        job_id=job.manifest.job_id,
        nonce=job.manifest.nonce,
        code_hash=job.manifest.code_hash,
        test_digest=job.manifest.test_digest,
        image=job.manifest.image,
        operational_status="healthy",
        cases=cases,
        reason_code="execution_finalized",
    ).model_dump()
    signed = {"result": result, "signature": sign(result, SIGNING)}
    response = client.post(
        "/api/v1/execution/worker/result",
        json={"worker_id": "w1", "envelope": signed},
        headers=WORKER_HEADERS,
    )
    return job.manifest.job_id, response.json()


def test_verification_jobs_run_through_the_execution_broker(client):  # noqa: F811
    state = client.app.state
    heartbeat(client)
    broker = execute.Broker(state.engine, state.settings, timeout=20, poll=0.05)
    assert broker.available(["python", "cpp"]) == ["python", "cpp"]
    out: dict = {}

    def verify():
        out["cases"] = asyncio.run(broker.run("python", "print(input() * 2)", ["ab\n"]))

    thread = threading.Thread(target=verify)
    thread.start()
    job_id, _ = work(client)
    thread.join(10)
    assert out["cases"][0]["status"] == "executed" and out["cases"][0]["stdout"] == "abab"
    with Session(state.engine) as db:
        row = db.get(Submission, job_id)
        assert row.user_id is None and row.mode == "verify"  # nobody's learning history


def test_exercise_is_verified_by_execution_then_released(client, published, web):  # noqa: F811
    wants_code(client)
    package = Scripted(
        author=[lesson()], quiz=[QUIZ], atoms=[ATOMS], facts=[FACTS_OK], reviewer=[PASS]
    )
    release(client, web, package, Local())
    queued = latest(client, "exercise")
    assert queued.state == "queued" and queued.input["trigger"] == "release"

    script = Scripted(
        engineer=[
            engineered(example=("2\n1 2\n2 4", "6")),  # the documented example is wrong
            # Every error is 0 or 1, so the absolute error equals the squared one.
            engineered(low=0, high=1, example=("2\n1 2\n2 3", "2")),
            engineered(),
        ],
        checker=[CHECKED],
    )
    run(client, script.make, Local())
    assert "the statement says '6' but the reference prints '5" in script.prompts["engineer"][1]
    assert "The wrong solution passes every test" in script.prompts["engineer"][2]
    assert latest(client, "exercise").state == "done"

    catalog = generated.merged(default_catalog())
    course_id, problem = catalog.problems["squared-error"]
    assert course_id == "ai-basics"
    assert "squared-error" in catalog.concept("ai-basics:what-is-ml").problems
    assert [t.public for t in problem.tests].count(True) == 1
    assert sum(not t.public for t in problem.tests) >= 3
    assert problem.tests[0].expected == "5\n"
    assert "Not reviewed by a person" in problem.provenance.attribution_md

    admin = published
    again = client.post(
        "/api/v1/admin/courses/ai-basics/concepts/what-is-ml/exercise", headers=admin
    )
    assert again.json()["kind"] == "exercise"
    renamed = engineered()
    renamed["problem"] = renamed["problem"] | {"id": "squared-error-again"}
    second = Scripted(engineer=[engineered(), renamed], checker=[CHECKED])
    run(client, second.make, Local())
    assert "The id squared-error is taken" in second.prompts["engineer"][1]
    concept = generated.merged(default_catalog()).concept("ai-basics:what-is-ml")
    assert concept.problems == ["squared-error", "squared-error-again"]


def test_exercises_wait_for_the_execution_service(client, published, web):  # noqa: F811
    wants_code(client)
    package = Scripted(
        author=[lesson()], quiz=[QUIZ], atoms=[ATOMS], facts=[FACTS_OK], reviewer=[PASS]
    )
    release(client, web, package, Local(languages=()))
    assert latest(client, "exercise") is None
    done = latest(client, "package")
    assert done.log[-1]["exercise"] == "waiting for the execution service"
    assert "Code items are allowed" not in package.prompts["quiz"][0]

    admin = published
    client.post("/api/v1/admin/courses/ai-basics/concepts/what-is-ml/exercise", headers=admin)
    run(client, Scripted().make, Local(languages=()))
    failed = latest(client, "exercise")
    assert failed.state == "failed" and failed.log[-1]["event"] == "execution_unavailable"


OUTPUT_ITEM = {
    "id": "fit-output",
    "kind": "output",
    "prompt": "What does this program print?",
    "code": {"python": "w = 2\nprint(w * 3)\n"},
    "options": ["5", "6", "8"],
    "answer": 0,  # wrong: it prints 6
    "explanation": "The fitted weight times the input.",
    "difficulty": 2,
}
ADAPTER = {
    "python": {"code": "pairs = [(1, 2), (2, 4)]\nprint(all(y == 2 * x for x, y in pairs))\n"}
}


def test_code_items_and_adapters_are_run_before_release(client, published, web):  # noqa: F811
    quiz_bad = QUIZ | {"quiz": [*QUIZ["quiz"], OUTPUT_ITEM]}
    quiz_good = QUIZ | {"quiz": [*QUIZ["quiz"], OUTPUT_ITEM | {"answer": 1}]}
    atoms = {"atoms": [*ATOMS["atoms"][:3], ATOMS["atoms"][3] | {"adapters": ADAPTER}]}
    script = Scripted(
        author=[lesson()],
        quiz=[quiz_bad, quiz_good],
        atoms=[atoms],
        facts=[FACTS_OK],
        reviewer=[PASS],
    )
    release(client, web, script, Local())
    assert "Code items are allowed" in script.prompts["quiz"][0]
    assert "Code adapters are allowed" in script.prompts["atoms"][0]
    assert "prints '6\\n', not the answer '5'" in script.prompts["quiz"][1]
    assert len(script.prompts["atoms"]) == 1  # the adapter ran fine, so atoms were kept
    assert '"expected": "True\\n"' in script.prompts["facts"][0]  # checkers see real output

    catalog = generated.merged(default_catalog())
    pack = catalog.atom_packs["ai-basics:what-is-ml"]
    assert pack.status == "released"
    assert pack.atoms[3].adapters["python"].expected == "True\n"
    item = catalog.concept("ai-basics:what-is-ml").quiz[-1]
    assert item.kind == "output" and item.options[item.answer] == "6"


def test_adapters_are_refused_without_a_runtime(client, published, web):  # noqa: F811
    atoms = {"atoms": [*ATOMS["atoms"][:3], ATOMS["atoms"][3] | {"adapters": ADAPTER}]}
    script = Scripted(
        author=[lesson()],
        quiz=[QUIZ],
        atoms=[atoms, ATOMS],
        facts=[FACTS_OK],
        reviewer=[PASS],
    )
    release(client, web, script, Local(languages=()))
    assert "no code adapters in this course" in script.prompts["atoms"][1]
    assert generated.merged(default_catalog()).concept("ai-basics:what-is-ml").status == "live"


def test_learner_is_judged_on_a_generated_exercise(client, published, web):  # noqa: F811
    wants_code(client)
    package = Scripted(
        author=[lesson()], quiz=[QUIZ], atoms=[ATOMS], facts=[FACTS_OK], reviewer=[PASS]
    )
    release(client, web, package, Local())
    run(client, Scripted(engineer=[engineered()], checker=[CHECKED]).make, Local())

    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner, course="ai-basics")
    heartbeat(client)
    view = client.get("/api/v1/problems/squared-error").json()
    assert view["title"] == "Squared error"

    def submit(source):
        client.post(
            "/api/v1/problems/squared-error/submit", json={"source": source}, headers=learner
        )
        return work(client)[1]

    assert submit(WRONG)["verdict"] == "wrong_answer"  # the generated tests catch the mistake
    accepted = submit(REFERENCE)
    assert accepted["verdict"] == "accepted" and accepted["total"] >= 4
