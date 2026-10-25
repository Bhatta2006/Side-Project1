"""Generate local throwaway configuration without reading or printing secrets."""

import hashlib
import json
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / ".env.local"
old = {}
if path.exists():
    for line in path.read_text().splitlines():
        if "=" in line:
            name, value = line.split("=", 1)
            old[name] = json.loads(value)
profiles = [
    dict(
        id="local_" + language,
        language=language,
        image="socrat/local-"
        + language
        + "@sha256:"
        + hashlib.sha256((language + sys.executable + sys.version).encode()).hexdigest(),
        attestation_reference="Insecure native development profile; not a signed production image",
        limits=dict(
            cpu_seconds=2,
            wall_seconds=5,
            memory_mb=512 if language == "cpp" else 256,
            pids=16,
            output_bytes=8000000,
            disk_mb=16,
            compile_seconds=20,
        ),
    )
    for language in ("python", "cpp", "java")
]
values = dict(
    SOCRAT_ENVIRONMENT="development",
    SOCRAT_DEMO_MODE="true",
    SOCRAT_EXECUTION_BACKEND="local_process",
    SOCRAT_EXECUTION_ENABLED="true",
    SOCRAT_EXECUTION_PROFILES=json.dumps(profiles),
    SOCRAT_EXECUTION_SIGNING_SECRET=old.get("SOCRAT_EXECUTION_SIGNING_SECRET")
    or secrets.token_hex(48),
    SOCRAT_EXECUTION_WORKER_SECRET=old.get("SOCRAT_EXECUTION_WORKER_SECRET")
    or secrets.token_hex(48),
    SOCRAT_SESSION_SECRET=old.get("SOCRAT_SESSION_SECRET") or secrets.token_hex(48),
    SOCRAT_EXECUTION_WORKER_ID="native-demo",
    SOCRAT_EXECUTION_API_URL="http://127.0.0.1:8000",
    SOCRAT_PUBLIC_ORIGIN="http://localhost:3000",
    API_INTERNAL_URL="http://127.0.0.1:8000",
    SOCRAT_DATABASE_URL="sqlite:///" + (ROOT / ".cache" / "native-demo.db").as_posix(),
    SOCRAT_TUTOR_ENABLED="true",
    SOCRAT_TUTOR_MODEL_ENABLED="false",
    SOCRAT_TUTOR_ADVISOR_SHADOW_ENABLED="false",
    SOCRAT_DEV_LOGIN_ENABLED="true",
    SOCRAT_PREWARM_CONTENT="true",
)
for feature in (
    "ONBOARDING",
    "DIAGNOSTICS",
    "PLANNING",
    "LEARNING_SESSIONS",
    "ASSESSMENTS",
    "DASHBOARD",
    "REMINDERS",
):
    values["SOCRAT_" + feature + "_ENABLED"] = "true"
(ROOT / ".cache").mkdir(exist_ok=True)
path.write_text("\n".join(name + "=" + json.dumps(value) for name, value in values.items()) + "\n")
path.chmod(0o600)
print("Generated untracked .env.local; credentials are not printed.")
