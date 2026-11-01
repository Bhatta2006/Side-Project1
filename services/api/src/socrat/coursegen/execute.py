"""Run generated code in the execution plane (ADR-0005), never in the API process.

Each run is a signed ``Submission`` in mode ``verify`` with no learner: the existing workers
claim it like any job, and the broker keeps every case's full output. The generator then
reads the facts back. Without a healthy worker for a language, that language is simply not
available, and the agents are not offered code in it.
"""

import asyncio
import secrets
import time

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from socrat.config import Settings
from socrat.execution.protocol import (
    COMMANDS,
    JobManifest,
    RuntimeProfile,
    canonical,
    hashed,
    same_output,
    sign,
)
from socrat.judge.service import LEASE_SECONDS, healthy_images
from socrat.models import Submission, identifier, now

MAX_CASES = 100  # the job envelope's limit
MAX_OUTPUT = 15000  # workers return at most 16000 characters; anything near it is cut


class Unavailable(RuntimeError):
    """No worker could run the code (offline, failed or too slow): not the code's fault."""


def ok(case: dict) -> bool:
    return case["status"] == "executed" and len(case["stdout"]) < MAX_OUTPUT


def agree(a: dict, b: dict) -> bool:
    return ok(a) and ok(b) and same_output(a["stdout"], b["stdout"])


def describe(case: dict) -> str:
    if case["status"] == "executed":
        return f"output too long ({len(case['stdout'])} characters)"
    return f"{case['status']}: {(case['stderr'] or case['stdout'])[-600:]}"


class Broker:
    """The execution plane as the course generator sees it. Tests pass a fake instead."""

    def __init__(self, engine: Engine, settings: Settings, timeout: float = 300, poll: float = 1):
        self.engine, self.settings, self.timeout, self.poll = engine, settings, timeout, poll

    def available(self, languages: list[str]) -> list[str]:
        with Session(self.engine) as db:
            healthy = healthy_images(db, self.settings, now())
        images = {x["language"]: x["image"] for x in self.settings.execution_profiles}
        return [lang for lang in languages if images.get(lang) in healthy]

    def _queue(self, language: str, source: str, inputs: list[str]) -> str:
        profile = next(
            RuntimeProfile.model_validate(x)
            for x in self.settings.execution_profiles
            if x["language"] == language
        )
        tests = [dict(input=i, expected=None, visibility="public") for i in inputs]
        stamp = now()
        job_id = identifier()
        manifest = JobManifest(
            job_id=job_id,
            attempt_id=identifier(),
            nonce=secrets.token_hex(32),
            issued_at=stamp,
            expires_at=stamp + LEASE_SECONDS,
            language=profile.language,
            image=profile.image,
            runtime_id=profile.id,
            code_hash=hashed(source.encode()),
            test_digest=hashed(canonical(tests)),
            pack_digest=hashed(b"coursegen"),
            mode="run",
            limits=profile.limits,
            compile_config=COMMANDS[profile.language],
        ).model_dump()
        secret = self.settings.execution_signing_secret.get_secret_value()
        with Session(self.engine) as db, db.begin():
            db.add(
                Submission(
                    id=job_id,
                    user_id=None,
                    problem_id="coursegen",
                    language=language,
                    mode="verify",
                    source=source,
                    status="queued",
                    total=len(tests),
                    manifest=manifest,
                    signature=sign(manifest, secret),
                    tests=tests,
                    created_at=stamp,
                )
            )
        return job_id

    async def run(self, language: str, source: str, inputs: list[str]) -> list[dict]:
        """One result per input: ``status`` (``executed`` when it ran), ``stdout``, ``stderr``."""
        if language not in self.available([language]):
            raise Unavailable(f"no execution worker for {language}")
        if len(source.encode()) > 64000:
            return [dict(status="compile_error", stdout="", stderr="source over 64 KB")] * len(
                inputs
            )
        results: list[dict] = []
        for start in range(0, len(inputs), MAX_CASES):
            job_id = self._queue(language, source, inputs[start : start + MAX_CASES])
            deadline = time.monotonic() + self.timeout
            while True:
                await asyncio.sleep(self.poll)
                with Session(self.engine) as db, db.begin():
                    job = db.get(Submission, job_id)
                    if job is None:
                        raise Unavailable(f"the {language} job disappeared")
                    if job.status == "done":
                        results += job.cases
                        break
                    if job.status == "failed" or time.monotonic() > deadline:
                        job.status = "failed"
                        raise Unavailable(f"the {language} worker did not finish the job")
        return results
