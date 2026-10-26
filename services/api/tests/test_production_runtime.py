"""Static invariants of the Oracle single-host production runtime and its delivery pipeline."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "infra" / "runtime" / "production"


def compose():
    return yaml.safe_load((RUNTIME / "compose.yaml").read_text(encoding="utf-8"))


def test_production_services_and_networks_are_locked_down():
    spec = compose()
    services = spec["services"]
    assert set(services) == {
        "postgres",
        "migrate",
        "api",
        "worker",
        "web",
        "explainer-checker",
        "caddy",
    }
    assert spec["networks"]["backend"]["internal"] is True
    # Only the API and worker may reach the internet (OIDC and the AI provider); the checker and
    # database may not.
    egress = {n for n, s in services.items() if "egress" in s.get("networks", [])}
    assert egress == {"api", "worker"}
    assert services["explainer-checker"]["networks"] == ["backend"]
    for name, service in services.items():
        assert "build" not in service
        if name != "caddy":
            assert "ports" not in service, f"{name} must not publish a host port"
    assert services["caddy"]["ports"] == ["80:80", "443:443", "443:443/udp"]


def test_production_secrets_are_files_and_never_inline():
    spec = compose()
    api = spec["services"]["api"]
    env = api["environment"]
    assert env["SOCRAT_ENVIRONMENT"] == "production"
    assert env["SOCRAT_DEV_LOGIN_ENABLED"] == "false"
    assert env["SOCRAT_EXECUTION_ENABLED"] == "false"
    for key in (
        "SOCRAT_SESSION_SECRET_FILE",
        "SOCRAT_OIDC_CLIENT_SECRET_FILE",
        "SOCRAT_OPENAI_API_KEY_FILE",
        "SOCRAT_EXPLAINER_CHECKER_SECRET_FILE",
        "SOCRAT_RAZORPAY_KEY_SECRET_FILE",
        "SOCRAT_RAZORPAY_WEBHOOK_SECRET_FILE",
    ):
        assert env[key].startswith("/run/secrets/")
    for key in env:
        assert not re.search(r"(SECRET|TOKEN|API_KEY|PASSWORD)$", key), f"{key} must be a *_FILE"
    assert set(spec["secrets"]) == {
        "postgres_password",
        "session_secret",
        "oidc_client_secret",
        "metrics_token",
        "ai_api_key",
        "explainer_checker_secret",
        "razorpay_key_secret",
        "razorpay_webhook_secret",
        "resend_api_key",
    }
    sandbox = env["SOCRAT_EXPLAINER_SANDBOX_ORIGIN"]
    assert sandbox.startswith("https://${SANDBOX_HOST")


def test_caddy_serves_the_sandbox_host_frames_only():
    text = (RUNTIME / "Caddyfile").read_text(encoding="utf-8")
    assert "{$APP_HOST}" in text and "{$SANDBOX_HOST}" in text
    assert "respond @metrics 404" in text
    assert "/api/v1/playground/artifacts/" in text and "respond 404" in text


def test_deploy_workflow_is_gated_on_ci_and_uses_digest_pinned_images():
    path = ROOT / ".github" / "workflows" / "deploy.yml"
    text = path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    triggers = workflow.get("on") or workflow[True]
    assert triggers["workflow_run"]["workflows"] == ["continuous-integration"]
    assert triggers["workflow_run"]["branches"] == ["main"]
    job = workflow["jobs"]["deploy"]
    assert job["environment"] == "production"
    assert "conclusion == 'success'" in job["if"]
    assert "@${digest}" in text  # images are deployed by digest, never by mutable tag
    assert not re.search(r"uses:\s+[^\s]+@v\d+(?:\s|$)", text)
    assert "password-stdin" in text


def test_deploy_script_enforces_secret_files_and_rolls_back():
    script = (ROOT / "scripts" / "operations" / "deploy-production.sh").read_text(encoding="utf-8")
    assert "set -euo pipefail" in script
    assert "unsafe mode" in script and "must be mode 0700" in script
    assert "rolling back" in script
    assert "--wait" in script
