"""Security and persistence acceptance tests; each test owns a fresh migrated database."""

import hashlib
import importlib.util
from pathlib import Path

import pytest


def test_platform_factory_exists():
    assert importlib.util.find_spec("socrat") is not None, "M1 application package is missing"


@pytest.fixture
def platform(tmp_path):
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient

    from socrat.config import Settings
    from socrat.main import create_app

    url = f"sqlite:///{tmp_path / 'test.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    settings = Settings(database_url=url, environment="test", dev_login_enabled=True)
    app = create_app(settings)
    with TestClient(app, base_url="http://localhost:3000") as client:
        yield app, client
    app.state.engine.dispose()


def login(client, subject="alice"):
    response = client.post(
        "/api/v1/auth/dev-login",
        json={"subject": subject},
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    return response.json()


def test_unauthenticated_profile_denied(platform):
    _, client = platform
    response = client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"
    assert response.headers["x-request-id"]


def test_profile_roundtrip_csrf_and_atomic_events(platform):
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from socrat.models import AuditEvent, OutboxEvent

    app, client = platform
    login(client)
    initial = client.get("/api/v1/me").json()
    patch = {"display_name": "Ada", "timezone": "Asia/Kolkata", "birth_year": 2000}
    assert client.patch("/api/v1/me", json=patch).status_code == 403
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": initial["csrf_token"]}
    response = client.patch("/api/v1/me", json=patch, headers=headers)
    assert response.status_code == 200
    assert client.get("/api/v1/me").json()["display_name"] == "Ada"
    with Session(app.state.engine) as db:
        audits = db.scalars(select(AuditEvent).where(AuditEvent.kind == "profile.updated")).all()
        events = db.scalars(select(OutboxEvent).where(OutboxEvent.kind == "profile.updated")).all()
        assert len(audits) == len(events) == 1
        assert "Ada" not in str(events[0].payload)


def test_logout_revokes_session(platform):
    _, client = platform
    login(client)
    me = client.get("/api/v1/me").json()
    stolen_cookie = client.cookies.get("socrat_session")
    response = client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "http://localhost:3000", "X-CSRF-Token": me["csrf_token"]},
    )
    assert response.status_code == 204
    client.cookies.set("socrat_session", stolen_cookie)
    assert client.get("/api/v1/me").status_code == 401


def test_session_is_hashed_and_expires(platform):
    from sqlalchemy.orm import Session

    from socrat.models import LoginSession

    app, client = platform
    login(client)
    token = client.cookies.get("socrat_session")
    with Session(app.state.engine) as db:
        record = db.get(LoginSession, hashlib.sha256(token.encode()).hexdigest())
        assert record is not None
        record.expires_at = 0
        db.commit()
    assert client.get("/api/v1/me").status_code == 401


def test_invalid_profile_and_cross_origin_rejected(platform):
    _, client = platform
    login(client)
    token = client.get("/api/v1/me").json()["csrf_token"]
    payload = {"display_name": "A", "timezone": "Mars/City", "birth_year": 2000}
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": token}
    assert client.patch("/api/v1/me", json=payload, headers=headers).status_code == 422
    headers["Origin"] = "https://attacker.invalid"
    assert client.patch("/api/v1/me", json={}, headers=headers).status_code == 403


def test_fail_closed_production_settings():
    from pydantic import ValidationError

    from socrat.config import Settings

    with pytest.raises(ValidationError):
        Settings(environment="production", dev_login_enabled=True)
    with pytest.raises(ValidationError):
        Settings(environment="staging", database_url="sqlite:///local.db")


def test_deployed_settings_accept_only_complete_secure_configuration():
    from pydantic import ValidationError

    from socrat.config import Settings

    deployed = Settings(
        environment="staging",
        database_url="postgresql+psycopg://socrat:secret@database:5432/socrat",
        public_origin="https://staging.socrat.example",
        session_secret="s" * 48,
        oidc_issuer="https://identity.socrat.example",
        oidc_client_id="socrat-staging",
        oidc_client_secret="provider-secret",
        metrics_token="m" * 32,
    )
    assert deployed.secure is True
    with pytest.raises(ValidationError):
        Settings(public_origin="http://localhost:3000/path")
    with pytest.raises(ValidationError):
        Settings(session_ttl_seconds=60)


def test_deployed_settings_load_service_scoped_secret_files(tmp_path, monkeypatch):
    from pydantic import SecretStr

    from socrat.config import Settings

    for name in ("SOCRAT_SESSION_SECRET", "SOCRAT_OIDC_CLIENT_SECRET", "SOCRAT_METRICS_TOKEN"):
        monkeypatch.delenv(name, raising=False)

    session_secret = tmp_path / "session-secret"
    oidc_secret = tmp_path / "oidc-secret"
    metrics_token = tmp_path / "metrics-token"
    session_secret.write_text("s" * 48 + "\n", encoding="utf-8")
    oidc_secret.write_text("provider-secret\n", encoding="utf-8")
    metrics_token.write_text("m" * 32 + "\n", encoding="utf-8")

    deployed = Settings(
        environment="staging",
        database_url="postgresql+psycopg://socrat@database:5432/socrat",
        public_origin="https://staging.socrat.example",
        session_secret_file=str(session_secret),
        oidc_issuer="https://identity.socrat.example",
        oidc_client_id="socrat-staging",
        oidc_client_secret_file=str(oidc_secret),
        metrics_token_file=str(metrics_token),
    )

    assert isinstance(deployed.session_secret, SecretStr)
    assert deployed.session_secret.get_secret_value() == "s" * 48
    assert deployed.oidc_client_secret.get_secret_value() == "provider-secret"
    assert deployed.metrics_token.get_secret_value() == "m" * 32
    assert "provider-secret" not in repr(deployed)


def test_secret_files_reject_ambiguous_or_multiline_values(tmp_path, monkeypatch):
    from pydantic import ValidationError

    from socrat.config import Settings

    monkeypatch.delenv("SOCRAT_SESSION_SECRET", raising=False)

    secret = tmp_path / "session-secret"
    secret.write_text("first-line\nsecond-line\n", encoding="utf-8")
    base = {
        "environment": "staging",
        "database_url": "postgresql+psycopg://socrat@database:5432/socrat",
        "public_origin": "https://staging.socrat.example",
        "session_secret_file": str(secret),
        "oidc_issuer": "https://identity.socrat.example",
        "oidc_client_id": "socrat-staging",
        "oidc_client_secret": "provider-secret",
        "metrics_token": "m" * 32,
    }
    with pytest.raises(ValidationError, match="single line"):
        Settings(**base)

    secret.write_text("s" * 48, encoding="utf-8")
    with pytest.raises(ValidationError, match="both directly and by file"):
        Settings(**base, session_secret="different-secret-value")


def test_worker_database_settings_do_not_require_web_secrets(tmp_path):
    from socrat.config import DatabaseSettings

    password = tmp_path / "postgres-password"
    password.write_text("reserved:/?#[]@!$&'()*+,;= value\n", encoding="utf-8")
    settings = DatabaseSettings(
        database_host="database",
        database_name="socrat",
        database_user="socrat",
        database_password_file=str(password),
    )
    assert settings.database_url_value.startswith("postgresql+psycopg://socrat:")
    assert settings.database_url_value.endswith("@database:5432/socrat")
    assert "reserved%3A%2F%3F%23%5B%5D%40" in settings.database_url_value
    assert "reserved:/?#[]" not in repr(settings)


def test_outbox_delivery_idempotent_and_rollback(platform):
    from sqlalchemy import func, select
    from sqlalchemy.orm import Session

    from socrat.models import DeliveredEvent, OutboxEvent
    from socrat.worker import drain_once

    app, client = platform
    login(client)
    assert drain_once(app.state.engine) == 1
    assert drain_once(app.state.engine) == 0
    with Session(app.state.engine) as db:
        assert db.scalar(select(func.count()).select_from(DeliveredEvent)) == 1
        db.add(OutboxEvent(id="rolled-back", kind="test", payload={}))
        db.rollback()
    assert drain_once(app.state.engine) == 0


def test_health_flags_and_security_headers(platform):
    _, client = platform
    assert client.get("/api/health/live").status_code == 200
    assert client.get("/api/health/ready").status_code == 200
    flags = client.get("/api/v1/features").json()
    assert flags["ai_provider"] == "offline"
    assert flags["code_execution"] is True  # Python and C++ run in the browser
    response = client.get("/api/v1/me")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_migration_and_backup_restore(tmp_path):
    import sqlite3

    from alembic import command
    from alembic.config import Config

    from socrat.schema_revision import SCHEMA_REVISION

    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{source}")
    command.upgrade(config, "head")
    with sqlite3.connect(source) as db, sqlite3.connect(backup) as restored:
        db.backup(restored)
        assert (
            restored.execute("select version_num from alembic_version").fetchone()[0]
            == SCHEMA_REVISION
        )
        assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    assert Path(source).exists()


def test_first_run_tour_is_recorded_once(platform):
    from sqlalchemy.orm import Session

    from socrat.models import User

    app, client = platform
    login(client)
    me = client.get("/api/v1/me").json()
    assert me["tour_seen"] is False
    assert client.post("/api/v1/me/tour").status_code == 403
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": me["csrf_token"]}
    assert client.post("/api/v1/me/tour", headers=headers).status_code == 204
    assert client.get("/api/v1/me").json()["tour_seen"] is True
    with Session(app.state.engine) as db:
        first = db.get(User, me["id"]).tour_seen_at
    assert client.post("/api/v1/me/tour", headers=headers).status_code == 204
    with Session(app.state.engine) as db:
        assert db.get(User, me["id"]).tour_seen_at == first


def test_appearance_is_saved_on_the_account(platform):
    _, client = platform
    login(client)
    me = client.get("/api/v1/me").json()
    assert me["appearance"] is None
    headers = {"Origin": "http://localhost:3000", "X-CSRF-Token": me["csrf_token"]}
    response = client.patch("/api/v1/me", json={"appearance": "tide:dark"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["appearance"] == "tide:dark"
    assert client.get("/api/v1/me").json()["appearance"] == "tide:dark"
    for bad in ("neon:dark", "tide:dim", "tide", "<script>:dark"):
        assert (
            client.patch("/api/v1/me", json={"appearance": bad}, headers=headers).status_code == 422
        )
    assert client.get("/api/v1/me").json()["appearance"] == "tide:dark"
