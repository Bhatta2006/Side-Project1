"""Versioned signed manifests and sanitized facts; no client-supplied execution authority."""

import hashlib
import hmac
import json
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)

Language = Literal["python", "cpp", "java"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)


Hash = Annotated[str, Field(pattern=r"^sha256:[a-f0-9]{64}$")]
Image = Annotated[str, Field(pattern=r"^[a-z0-9./:_-]+@sha256:[a-f0-9]{64}$")]


def source_bytes(value: str) -> str:
    if len(value.encode("utf-8")) > 64000:
        raise ValueError("source_exceeds_byte_limit")
    return value


Source = Annotated[str, Field(max_length=64000), AfterValidator(source_bytes)]


def same_output(actual: str, expected: str) -> bool:
    """Judge comparison: ignore CRLF, trailing spaces and surrounding blank lines only.

    Leading spaces stay significant, so whitespace-shaped output (patterns, grids) is
    still checked exactly.
    """

    def normalize(text: str) -> str:
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        return "\n".join(line.rstrip() for line in lines).strip("\n")

    return normalize(actual) == normalize(expected)


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def hashed(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sign(value: dict, secret: str) -> str:
    return hmac.new(secret.encode(), canonical(value), hashlib.sha256).hexdigest()


def verify(value: dict, signature: str, secret: str):
    if not secret or not hmac.compare_digest(sign(value, secret), signature):
        raise ValueError("execution_signature_invalid")


class Limits(Contract):
    cpu_seconds: int = Field(default=2, ge=1, le=5)
    wall_seconds: int = Field(default=5, ge=1, le=15)
    memory_mb: int = Field(default=256, ge=64, le=1024)
    pids: int = Field(default=64, ge=8, le=128)
    output_bytes: int = Field(default=10_000_000, ge=1024, le=10_000_000)
    disk_mb: int = Field(default=10, ge=1, le=32)
    compile_seconds: int = Field(default=15, ge=1, le=30)


class RuntimeProfile(Contract):
    id: str = Field(pattern=r"^[a-z0-9_-]{1,64}$")
    language: Language
    image: Image
    limits: Limits
    attestation_reference: str = Field(min_length=1, max_length=512)


COMMANDS = {
    "python": dict(
        filename="solution.py", compile=[], run=["python3", "-I", "-B", "/work/solution.py"]
    ),
    "cpp": dict(
        filename="solution.cpp",
        compile=["g++", "-std=c++20", "-O2", "/work/solution.cpp", "-o", "/work/solution"],
        run=["/work/solution"],
    ),
    "java": dict(
        filename="Solution.java",
        compile=["javac", "-encoding", "UTF-8", "/work/Solution.java"],
        run=[
            "java",
            "-Xms16m",
            "-Xmx128m",
            "-XX:ActiveProcessorCount=1",
            "-XX:+UseSerialGC",
            "-cp",
            "/work",
            "Solution",
        ],
    ),
}


class JobManifest(Contract):
    version: Literal["1.0.0"] = "1.0.0"
    job_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    attempt_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    nonce: str = Field(pattern=r"^[a-f0-9]{64}$")
    issued_at: int = Field(ge=0)
    expires_at: int = Field(ge=0)
    language: Language
    image: Image
    runtime_id: str
    code_hash: Hash
    test_digest: Hash
    pack_digest: Hash
    mode: Literal["run", "submit"]
    limits: Limits
    time_limit_ms: int | None = Field(default=None, ge=500, le=10000)
    compile_config: dict

    @model_serializer(mode="wrap")
    def signed_fields(self, handler: SerializerFunctionWrapHandler) -> dict:
        fields = handler(self)
        # Preserve signatures of queued jobs issued before per-problem limits.
        if self.time_limit_ms is None:
            fields.pop("time_limit_ms", None)
        return fields

    @property
    def run_seconds(self) -> float:
        problem = self.time_limit_ms / 1000 if self.time_limit_ms is not None else float("inf")
        return min(self.limits.wall_seconds, problem)

    @model_validator(mode="after")
    def fixed_commands(self):
        if (
            self.compile_config != COMMANDS[self.language]
            or not 0 < self.expires_at - self.issued_at <= 600
        ):
            raise ValueError("execution_manifest_invalid")
        return self


class TestInput(Contract):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=False)
    input: str = Field(max_length=2_000_000)
    expected: str | None = Field(default=None, max_length=2_000_000)
    visibility: Literal["public", "hidden"]


class JobEnvelope(Contract):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=False)
    manifest: JobManifest
    signature: str = Field(pattern=r"^[a-f0-9]{64}$")
    source: Source = Field(min_length=1)
    tests: list[TestInput] = Field(min_length=1, max_length=100)

    def authenticate(self, secret: str, timestamp: int):
        manifest = self.manifest.model_dump()
        verify(manifest, self.signature, secret)
        if not self.manifest.issued_at <= timestamp <= self.manifest.expires_at:
            raise ValueError("execution_job_expired")
        if (
            hashed(self.source.encode()) != self.manifest.code_hash
            or hashed(canonical([x.model_dump() for x in self.tests])) != self.manifest.test_digest
        ):
            raise ValueError("execution_artifact_mismatch")


class CaseResult(Contract):
    index: int = Field(ge=0, le=99)
    status: Literal[
        "passed",
        "wrong_answer",
        "executed",
        "compile_error",
        "runtime_error",
        "timeout",
        "memory_limit",
        "output_limit",
    ]
    wall_ms: int = Field(ge=0, le=60000)
    stdout: str = Field(default="", max_length=16000)
    stderr: str = Field(default="", max_length=16000)


class ExecutionResult(Contract):
    version: Literal["1.0.0"] = "1.0.0"
    job_id: str
    nonce: str
    code_hash: Hash
    test_digest: Hash
    image: Image
    operational_status: Literal["healthy", "failed"]
    cases: list[CaseResult] = Field(max_length=100)
    reason_code: Literal[
        "execution_finalized",
        "sandbox_unavailable",
        "worker_failure",
        "lease_expired",
        "content_withdrawn",
    ]


class ResultEnvelope(Contract):
    result: ExecutionResult
    signature: str = Field(pattern=r"^[a-f0-9]{64}$")
