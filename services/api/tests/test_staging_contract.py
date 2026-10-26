"""Static staging invariants that must hold before any cloud deployment."""

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
STAGING = ROOT / "infra" / "runtime" / "staging"


def load_yaml(name: str):
    return yaml.safe_load((STAGING / name).read_text(encoding="utf-8"))


def test_staging_compose_uses_immutable_images_and_private_networks():
    compose = load_yaml("compose.yaml")
    services = compose["services"]
    assert set(services) == {
        "postgres",
        "migrate",
        "api",
        "worker",
        "web",
        "caddy",
        "prometheus",
        "grafana",
    }
    assert "build" not in services["api"]
    assert "build" not in services["web"]
    assert services["api"]["image"].startswith("${SOCRAT_API_IMAGE:?")
    assert services["web"]["image"].startswith("${SOCRAT_WEB_IMAGE:?")
    assert "@sha256:" in services["api"]["image"]
    assert "@sha256:" in services["web"]["image"]
    assert compose["networks"]["backend"]["internal"] is True
    assert services["postgres"]["networks"] == ["backend"]
    assert services["api"]["networks"] == ["backend", "identity-egress"]
    assert compose["networks"]["identity-egress"]["driver"] == "bridge"
    assert not compose["networks"]["identity-egress"].get("internal", False)
    assert {
        name
        for name, service in services.items()
        if "identity-egress" in service.get("networks", [])
    } == {"api"}
    for name in {"postgres", "migrate", "worker", "web", "prometheus", "grafana"}:
        assert services[name]["networks"] == ["backend"]
    assert services["web"]["networks"] == ["backend"]
    assert services["caddy"]["ports"] == ["80:80", "443:443", "443:443/udp"]
    assert services["grafana"]["ports"] == ["127.0.0.1:3001:3000"]
    for name, service in services.items():
        if name not in {"caddy", "grafana"}:
            assert "ports" not in service, f"{name} must not publish a host port"


def test_staging_secrets_are_service_scoped():
    services = load_yaml("compose.yaml")["services"]
    assert services["postgres"]["secrets"] == ["postgres_password"]
    assert services["migrate"]["secrets"] == ["postgres_password"]
    assert services["worker"]["secrets"] == ["postgres_password"]
    assert services["prometheus"]["secrets"] == ["metrics_token"]
    assert services["grafana"]["secrets"] == ["grafana_admin_password"]
    assert set(services["api"]["secrets"]) == {
        "postgres_password",
        "session_secret",
        "oidc_client_secret",
        "metrics_token",
    }
    assert services["api"]["environment"]["SOCRAT_ENVIRONMENT"] == "staging"
    assert services["api"]["environment"]["SOCRAT_DEV_LOGIN_ENABLED"] == "false"
    assert services["api"]["environment"]["SOCRAT_SESSION_SECRET_FILE"].startswith("/run/secrets/")


def test_staging_services_are_health_gated_and_resource_bounded():
    services = load_yaml("compose.yaml")["services"]
    assert services["api"]["depends_on"]["migrate"]["condition"] == (
        "service_completed_successfully"
    )
    assert services["caddy"]["depends_on"]["api"]["condition"] == "service_healthy"
    assert services["caddy"]["depends_on"]["web"]["condition"] == "service_healthy"
    for name in {"postgres", "api", "web", "caddy", "prometheus", "grafana"}:
        assert "healthcheck" in services[name]
        assert "limits" in services[name]["deploy"]["resources"]
    for name in {"api", "worker", "web", "caddy", "prometheus", "grafana"}:
        assert "no-new-privileges:true" in services[name]["security_opt"]


def test_prometheus_scrape_and_alert_contracts_are_private_and_actionable():
    config = load_yaml("prometheus.yml")
    job = config["scrape_configs"][0]
    assert job["metrics_path"] == "/api/metrics"
    assert job["authorization"]["credentials_file"] == "/run/secrets/metrics_token"
    assert job["static_configs"][0]["targets"] == ["api:8000"]
    assert config["rule_files"] == ["/etc/prometheus/alerts.yml"]

    groups = load_yaml("alerts.yml")["groups"]
    alerts = {rule["alert"]: rule for group in groups for rule in group["rules"]}
    assert set(alerts) == {
        "SocratApiUnavailable",
        "SocratHighServerErrorRate",
        "SocratHighLatency",
        "SocratDiagnosticContentBlocked",
        "SocratDiagnosticReviewBacklog",
        "SocratTutorBudgetExhausted",
        "SocratTutorLatency",
        "SocratPrivacyCleanupOverdue",
        "SocratPrivacyWorkerBacklog",
    }
    assert alerts["SocratApiUnavailable"]["labels"]["severity"] == "page"
    assert alerts["SocratHighServerErrorRate"]["labels"]["severity"] == "ticket"
    assert (
        alerts["SocratDiagnosticContentBlocked"]["annotations"]["runbook"]
        == "docs/operations/m4-diagnostics.md#blocked-diagnostics"
    )


def test_caddy_terminates_tls_and_hides_the_metrics_endpoint():
    caddyfile = (STAGING / "Caddyfile").read_text(encoding="utf-8")
    assert "{$STAGING_HOST}" in caddyfile
    assert "tls {$TLS_EMAIL}" in caddyfile
    assert "admin off" in caddyfile
    assert "respond @metrics 404" in caddyfile
    assert "reverse_proxy @api api:8000" in caddyfile
    assert "reverse_proxy web:3000" in caddyfile


def test_grafana_provisions_a_private_operational_dashboard():
    datasource = yaml.safe_load(
        (STAGING / "grafana" / "provisioning" / "datasources" / "prometheus.yml").read_text(
            encoding="utf-8"
        )
    )
    assert datasource["datasources"][0]["url"] == "http://prometheus:9090"
    assert datasource["datasources"][0]["isDefault"] is True

    dashboard = json.loads(
        (STAGING / "grafana" / "dashboards" / "socrat-api.json").read_text(encoding="utf-8")
    )
    assert dashboard["uid"] == "socrat-api"
    assert {panel["title"] for panel in dashboard["panels"]} == {
        "Request rate",
        "5xx error ratio",
        "p95 latency",
    }


def test_ci_validates_operations_and_publishes_attested_arm64_images():
    workflow_path = ROOT / ".github" / "workflows" / "ci.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    verify_steps = workflow["jobs"]["verify"]["steps"]
    verify_commands = "\n".join(str(step.get("run", "")) for step in verify_steps)
    assert "restore-smoke.sh" in verify_commands
    assert "infra/runtime/staging/compose.yaml config --quiet" in verify_commands
    assert "--entrypoint /bin/promtool" in verify_commands
    assert "check config /etc/prometheus/prometheus.yml" in verify_commands
    assert "caddy validate --config /etc/caddy/Caddyfile" in verify_commands

    publish = workflow["jobs"]["publish-images"]
    assert set(publish["needs"]) == {"secret-scan", "verify"}
    assert publish["permissions"] == {
        "contents": "read",
        "packages": "write",
        "id-token": "write",
        "attestations": "write",
    }
    publish_text = json.dumps(publish)
    # Oracle Ampere (ARM) is the only deploy target: every image is built for it, and only it.
    platforms = [
        s["with"]["platforms"] for s in publish["steps"] if "platforms" in s.get("with", {})
    ]
    assert platforms == ["linux/arm64"] * 3  # api, web, visual checker
    assert publish_text.count("actions/attest@") == 3  # api, web, visual checker
    assert ":sha-${{ github.sha }}" in publish_text

    workflow_text = workflow_path.read_text(encoding="utf-8")
    assert not re.search(r"uses:\s+[^\s]+@v\d+(?:\s|$)", workflow_text)


def test_host_bootstrap_and_runbook_match_the_release_contract():
    cloud_init = (
        ROOT / "infra" / "oci" / "modules" / "staging-foundation" / "cloud-init.yaml"
    ).read_text(encoding="utf-8")
    assert "/opt/socrat/secrets" in cloud_init
    assert "/var/lib/socrat/releases" in cloud_init
    assert "usermod" in cloud_init and "docker" in cloud_init and "ubuntu" in cloud_init

    backup = (ROOT / "scripts" / "operations" / "backup-postgres.ps1").read_text(encoding="utf-8")
    restore = (ROOT / "scripts" / "operations" / "restore-smoke.ps1").read_text(encoding="utf-8")
    for script in (backup, restore):
        assert "ComposeFile" in script
        assert "ProjectName" in script
        assert "EnvFile" in script

    runbook = (ROOT / "docs" / "operations" / "m1-staging-runbook.md").read_text(encoding="utf-8")
    assert "# API unavailable" in runbook
    assert "# High server error rate" in runbook
    assert "# High latency" in runbook
    assert "release.py" in runbook
    assert "restore-smoke.sh" in runbook
