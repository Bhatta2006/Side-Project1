"""Queue Run/Submit jobs, lease them to authenticated workers, and accept signed results.

The worker protocol (heartbeat → claim → result) and the signed JobEnvelope are unchanged
from the original execution plane, so services/execution/src/runner/worker.py runs as-is.
Hidden test inputs and outputs never leave the server; workers already blank hidden output.

Languages in ``settings.browser_runtimes`` run in the learner's browser instead (Pyodide,
Clang/WASI). Such a job is created already "running" for the pseudo-worker ``browser``: the
browser receives the test inputs (never the expected outputs), runs the code locally and
reports a digest of each normalized output. The server decides pass or fail by comparing
digests, so a browser can only report "passed" by producing the right output.
"""

import hashlib
import secrets

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.catalog.schema import Problem
from socrat.config import Settings
from socrat.execution.protocol import (
    COMMANDS,
    JobEnvelope,
    JobManifest,
    ResultEnvelope,
    RuntimeProfile,
    TestInput,
    canonical,
    hashed,
    sign,
    verify,
)
from socrat.models import JudgeWorker, Submission, identifier

LEASE_SECONDS = 600
WORKER_FRESH_SECONDS = 30
CUSTOM_INPUT_LIMIT = 20_000


def profile_for(settings: Settings, language: str) -> RuntimeProfile:
    for raw in settings.execution_profiles:
        profile = RuntimeProfile.model_validate(raw)
        if profile.language == language:
            return profile
    raise HTTPException(503, "execution_unavailable")


def healthy_images(db: Session, settings: Settings, now: int) -> set[str]:
    allowed = {x["image"] for x in settings.execution_profiles}
    workers = db.scalars(
        select(JudgeWorker).where(JudgeWorker.seen_at >= now - WORKER_FRESH_SECONDS)
    )
    return {image for worker in workers for image in worker.images if image in allowed}


BROWSER = "browser"
# Browser runtimes are slower than native ones (WebAssembly, an interpreter compiled to it).
BROWSER_TIME_FACTOR = {"python": 3, "cpp": 2}
BROWSER_CLIENT_STATUSES = {"executed", "compile_error", "runtime_error", "timeout", "output_limit"}


def in_browser(settings: Settings, language: str) -> bool:
    return language in settings.browser_runtimes


def runtimes(db: Session, settings: Settings, now: int) -> dict[str, bool]:
    healthy = healthy_images(db, settings, now)
    ready = {x["language"]: x["image"] in healthy for x in settings.execution_profiles}
    return ready | {language: True for language in settings.browser_runtimes}


def normalized(text: str) -> str:
    """The judge comparison of ``same_output``, as one canonical string."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).strip("\n")


def output_digest(text: str) -> str:
    return hashlib.sha256(normalized(text).encode()).hexdigest()


def create(
    db: Session,
    settings: Settings,
    user_id: str,
    enrollment_id: str | None,
    problem: Problem,
    language: str,
    source: str,
    mode: str,
    custom_input: str | None,
    assistance: int,
    now: int,
    force_native: bool = False,
    recheck_of: str | None = None,
) -> Submission:
    browser = in_browser(settings, language) and not force_native
    if not browser:
        profile = profile_for(settings, language)
        if profile.image not in healthy_images(db, settings, now):
            raise HTTPException(503, "runtime_offline")
    if not source.strip():
        raise HTTPException(422, "empty_source")
    if recheck_of is None:  # A re-run is the server's own check, not the learner's run.
        today_count = db.scalar(
            select(func.count())
            .select_from(Submission)
            .where(Submission.user_id == user_id, Submission.created_at >= now - 86400)
        )
        if (today_count or 0) >= settings.execution_daily_quota:
            raise HTTPException(429, "daily_run_quota")
        pending = db.scalar(
            select(func.count())
            .select_from(Submission)
            .where(Submission.user_id == user_id, Submission.status.in_(["queued", "running"]))
        )
        if (pending or 0) >= settings.execution_queue_limit:
            raise HTTPException(429, "too_many_pending_runs")
    if mode == "run" and custom_input is not None:
        if len(custom_input) > CUSTOM_INPUT_LIMIT:
            raise HTTPException(422, "custom_input_too_large")
        tests = [dict(input=custom_input, expected=None, visibility="public")]
    else:
        tests = [
            dict(
                input=t.input,
                expected=t.expected,
                visibility="public" if t.public else "hidden",
            )
            for t in problem.tests
            if mode == "submit" or t.public
        ]
    if not tests:
        raise HTTPException(409, "problem_has_no_tests")
    job_id = identifier()
    if browser:
        nonce = secrets.token_hex(32)
        submission = Submission(
            id=job_id,
            user_id=user_id,
            enrollment_id=enrollment_id,
            problem_id=problem.id,
            language=language,
            mode=mode,
            source=source,
            custom_input=custom_input,
            status="running",
            total=len(tests),
            assistance=assistance,
            manifest=dict(
                backend=BROWSER,
                job_id=job_id,
                nonce=nonce,
                issued_at=now,
                expires_at=now + LEASE_SECONDS,
                language=language,
                mode="submit" if mode == "submit" else "run",
                code_hash=hashed(source.encode()),
                test_digest=hashed(canonical(tests)),
                time_limit_ms=problem.time_limit_ms * BROWSER_TIME_FACTOR[language],
            ),
            signature=hashlib.sha256(nonce.encode()).hexdigest(),
            tests=tests,
            worker_id=BROWSER,
            lease_until=now + LEASE_SECONDS,
            created_at=now,
        )
        db.add(submission)
        db.flush()
        return submission
    manifest = JobManifest(
        job_id=job_id,
        attempt_id=identifier(),
        nonce=secrets.token_hex(32),
        issued_at=now,
        expires_at=now + LEASE_SECONDS,
        language=profile.language,
        image=profile.image,
        runtime_id=profile.id,
        code_hash=hashed(source.encode()),
        test_digest=hashed(canonical(tests)),
        pack_digest=hashed(problem.id.encode()),
        mode="submit" if mode == "submit" else "run",
        limits=profile.limits,
        time_limit_ms=problem.time_limit_ms,
        compile_config=COMMANDS[profile.language],
    ).model_dump()
    submission = Submission(
        id=job_id,
        user_id=user_id,
        enrollment_id=enrollment_id,
        problem_id=problem.id,
        language=language,
        mode=mode,
        source=source,
        custom_input=custom_input,
        status="queued",
        total=len(tests),
        assistance=assistance,
        manifest=manifest,
        signature=sign(manifest, settings.execution_signing_secret.get_secret_value()),
        tests=tests,
        created_at=now,
        recheck_of=recheck_of,
    )
    db.add(submission)
    db.flush()
    return submission


def native_ready(db: Session, settings: Settings, language: str, now: int) -> bool:
    """Is there a fresh native worker that can run this language?"""
    for raw in settings.execution_profiles:
        profile = RuntimeProfile.model_validate(raw)
        if profile.language == language:
            return profile.image in healthy_images(db, settings, now)
    return False


def wants_recheck(db: Session, settings: Settings, job: Submission, now: int) -> bool:
    """A browser report is only a claim. An accepted submit that would earn credit is re-run on
    a native worker first when one is available; otherwise the browser result stands."""
    return (
        job.worker_id == BROWSER
        and job.mode == "submit"
        and job.verdict == "accepted"
        and job.enrollment_id is not None
        and native_ready(db, settings, job.language, now)
    )


def start_recheck(
    db: Session, settings: Settings, job: Submission, problem: Problem, now: int
) -> Submission:
    """Queue the native re-run. It never earns credit itself (no enrollment); its verdict is
    adopted by the browser submission through ``apply_recheck``."""
    assert job.user_id is not None  # Only learners' submits are re-run.
    check = create(
        db,
        settings,
        job.user_id,
        None,
        problem,
        job.language,
        job.source,
        "submit",
        None,
        job.assistance,
        now,
        force_native=True,
        recheck_of=job.id,
    )
    # Until the re-run answers, the submission is in flight, not accepted: every query that
    # counts accepted submits (solved, evidence, achievements) must not see it yet.
    job.manifest = {**job.manifest, "recheck_job": check.id, "browser_verdict": job.verdict}
    job.status, job.verdict = "running", ""
    return check


def apply_recheck(original: Submission, check: Submission, now: int) -> bool:
    """Adopt the native verdict. True the first time it is applied, False afterwards.

    A re-run that could not finish (worker error, never claimed) leaves the browser's result
    standing: an outage must not punish a learner."""
    if original.manifest.get("rechecked"):
        return False
    source = "browser"
    original.verdict = original.manifest["browser_verdict"]
    if check.status == "done":
        original.cases, original.passed = check.cases, check.passed
        original.verdict, source = check.verdict, "native"
    original.manifest = {**original.manifest, "rechecked": source}
    original.status, original.finished_at = "done", now
    return True


def recheck_due(db: Session, original: Submission, now: int) -> Submission | None:
    """The finished (or abandoned) re-run of this browser submission, if it can be applied."""
    check_id = original.manifest.get("recheck_job")
    if not check_id or original.manifest.get("rechecked"):
        return None
    check = db.get(Submission, check_id, with_for_update=True)
    if check is None:
        return None
    if check.status in {"done", "failed"}:
        return check
    if now > check.created_at + LEASE_SECONDS + WORKER_FRESH_SECONDS:
        check.status, check.verdict, check.finished_at = "failed", "system_error", now
        return check
    return None


def heartbeat(db: Session, settings: Settings, worker_id: str, images: list[str], now: int):
    allowed = {x["image"] for x in settings.execution_profiles}
    if len(images) != len(set(images)) or not set(images) <= allowed:
        raise HTTPException(422, "worker_runtime_mismatch")
    worker = db.get(JudgeWorker, worker_id)
    if worker is None:
        db.add(JudgeWorker(id=worker_id, images=images, seen_at=now))
    else:
        worker.images, worker.seen_at = images, now


def claim(db: Session, worker_id: str, now: int) -> dict | None:
    worker = db.get(JudgeWorker, worker_id)
    if worker is None or worker.seen_at < now - WORKER_FRESH_SECONDS:
        raise HTTPException(403, "worker_capability_expired")
    for stale in db.scalars(
        select(Submission)
        .where(
            Submission.status.in_(["queued", "running"]),
            Submission.created_at < now - LEASE_SECONDS,
        )
        .with_for_update(skip_locked=True)
    ):
        stale.status, stale.verdict, stale.finished_at = "failed", "system_error", now
    for job in db.scalars(
        select(Submission)
        .where(Submission.status == "queued")
        .order_by(Submission.created_at, Submission.id)
        .limit(20)
        .with_for_update(skip_locked=True)
    ):
        if job.manifest["image"] not in worker.images:
            continue
        job.status, job.worker_id, job.lease_until = (
            "running",
            worker_id,
            job.manifest["expires_at"],
        )
        return JobEnvelope(
            manifest=JobManifest.model_validate(job.manifest),
            signature=job.signature,
            source=job.source,
            tests=[TestInput.model_validate(x) for x in job.tests],
        ).model_dump()
    return None


def verdict_of(cases: list[dict], mode: str, custom: bool) -> str:
    statuses = [case["status"] for case in cases]
    if "compile_error" in statuses:
        return "compile_error"
    if custom:
        return next((s for s in statuses if s != "executed"), "ran")
    for status in statuses:
        if status != "passed":
            return status
    return "accepted"


def finalize(db: Session, settings: Settings, worker_id: str, envelope: ResultEnvelope, now: int):
    result = envelope.result
    try:
        verify(
            result.model_dump(),
            envelope.signature,
            settings.execution_signing_secret.get_secret_value(),
        )
    except ValueError as exc:
        raise HTTPException(409, "execution_signature_invalid") from exc
    job = db.get(Submission, result.job_id)
    if job is None or job.worker_id != worker_id:
        raise HTTPException(404, "not_found")
    for field in ("nonce", "code_hash", "test_digest", "image"):
        if getattr(result, field) != job.manifest[field]:
            raise HTTPException(409, "execution_result_mismatch")
    if job.status in {"done", "failed"}:
        return job, False  # Duplicate delivery after a retry: idempotent.
    if job.status != "running" or job.lease_until is None or now > job.lease_until:
        raise HTTPException(409, "execution_lease_expired")
    job.finished_at = now
    if result.operational_status != "healthy":
        job.status, job.verdict = "failed", "system_error"
        return job, True
    if [x.index for x in result.cases] != list(range(len(job.tests))):
        raise HTTPException(409, "execution_result_incomplete")
    settle(job, [x.model_dump() for x in result.cases])
    return job, True


def settle(job: Submission, results: list[dict]):
    """Store per-case results (public detail only) and the verdict on a finished job."""
    if job.mode == "verify":
        # Generator verification: the full output becomes a test's expected output.
        job.cases = [
            dict(status=c["status"], stdout=c["stdout"], stderr=c["stderr"]) for c in results
        ]
        job.status = "done"
        return
    cases = []
    for case, test in zip(results, job.tests, strict=True):
        public = test["visibility"] == "public"
        cases.append(
            dict(
                status=case["status"],
                wall_ms=case["wall_ms"],
                public=public,
                input=test["input"][:4000] if public else None,
                expected=(test["expected"] or "")[:4000]
                if public and test["expected"] is not None
                else None,
                stdout=case["stdout"][:4000] if public else None,
                stderr=case["stderr"][:4000]
                if public or case["status"] == "compile_error"
                else None,
            )
        )
    job.cases = cases
    job.passed = sum(c["status"] == "passed" for c in cases)
    job.verdict = verdict_of(cases, job.mode, job.custom_input is not None)
    job.status = "done"


def browser_task(job: Submission) -> dict | None:
    """What the learner's browser needs to run a pending browser job: inputs, never outputs."""
    if job.worker_id != BROWSER or job.status != "running" or job.manifest.get("recheck_job"):
        return None  # A report was already taken; a re-run is deciding it.
    return dict(
        token=job.manifest["nonce"],
        language=job.language,
        time_limit_ms=job.manifest["time_limit_ms"],
        expires_at=job.manifest["expires_at"],
        tests=[dict(index=i, input=t["input"]) for i, t in enumerate(job.tests)],
    )


def finalize_browser(job: Submission, token: str, results: list[dict], now: int) -> bool:
    """Judge a browser job from its reported output digests. False if already finished."""
    if job.worker_id != BROWSER:
        raise HTTPException(404, "not_found")
    if not secrets.compare_digest(token, job.manifest["nonce"]):
        raise HTTPException(409, "execution_token_invalid")
    if job.status in {"done", "failed"} or job.manifest.get("recheck_job"):
        return False  # A retried report: idempotent.
    if job.lease_until is None or now > job.lease_until:
        raise HTTPException(409, "execution_lease_expired")
    if [x["index"] for x in results] != list(range(len(job.tests))):
        raise HTTPException(409, "execution_result_incomplete")
    judged = []
    for case, test in zip(results, job.tests, strict=True):
        status = case["status"]
        if status not in BROWSER_CLIENT_STATUSES:
            raise HTTPException(422, "execution_status_invalid")
        if status == "executed" and test["expected"] is not None:
            status = (
                "passed"
                if secrets.compare_digest(case["digest"], output_digest(test["expected"]))
                else "wrong_answer"
            )
        judged.append(case | dict(status=status))
    job.finished_at = now
    settle(job, judged)
    return True


def view(job: Submission) -> dict:
    from socrat.learn.feedback import submission_copy

    return dict(
        id=job.id,
        problem_id=job.problem_id,
        language=job.language,
        mode=job.mode,
        status=job.status,
        verdict=job.verdict,
        passed=job.passed,
        total=job.total,
        cases=job.cases,
        assistance=job.assistance,
        created_at=job.created_at,
        finished_at=job.finished_at,
        learning_feedback=submission_copy(job),
        browser=browser_task(job),
        verification=verification(job),
    )


def verification(job: Submission) -> str | None:
    """pending: awaiting the native re-run; native or browser: whose verdict stands."""
    if not job.manifest.get("recheck_job"):
        return None
    return job.manifest.get("rechecked") or "pending"
