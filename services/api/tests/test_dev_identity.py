"""Dev-login upgrades retain progress without reviving old slug collisions."""

import hashlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.auth import returning_dev_user
from socrat.models import Base, User


@pytest.mark.parametrize(
    ("name", "legacy", "prefix"),
    [
        ("Jane.Doe", "jane-doe", "jane-doe"),
        ("Élodie", "lodie", "lodie"),
        ("日本語", "learner", "learner"),
    ],
)
def test_matching_legacy_name_recovers_original_user(name, legacy, prefix):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        original = User(issuer="local-development", subject=legacy, display_name=name)
        db.add(original)
        db.flush()
        subject = f"{prefix}-{hashlib.sha256(name.encode()).hexdigest()[:10]}"
        assert returning_dev_user(db, subject, name) is original
    engine.dispose()


def test_dev_login_upgrade_preserves_enrollment_and_read_lesson(client):  # noqa: F811
    name = "Jane.Doe"
    headers = login(client, subject="jane-doe", name=name)
    onboard(client, headers)
    activity = "lesson:zero:programs-and-output"
    client.post(f"/api/v1/activities/{activity}/complete", headers=headers).raise_for_status()
    before = client.get("/api/v1/me").json()
    subject = "jane-doe-" + hashlib.sha256(name.encode()).hexdigest()[:10]
    login(client, subject=subject, name=name)
    after = client.get("/api/v1/me").json()
    assert after["id"] == before["id"]
    assert after["enrollment"]["id"] == before["enrollment"]["id"]
    first = client.get("/api/v1/plan").json()["modules"][0]["concepts"][0]
    assert first["lesson_done"]


def test_case_variant_never_moves_an_existing_hashed_identity(client):  # noqa: F811
    lower = "jane.doe"
    original_subject = "jane-doe-" + hashlib.sha256(lower.encode()).hexdigest()[:10]
    login(client, subject=original_subject, name=lower)
    original = client.get("/api/v1/me").json()["id"]
    mixed = "Jane.Doe"
    mixed_subject = "jane-doe-" + hashlib.sha256(mixed.encode()).hexdigest()[:10]
    login(client, subject=mixed_subject, name=mixed)
    assert client.get("/api/v1/me").json()["id"] != original
    login(client, subject=original_subject, name=lower)
    assert client.get("/api/v1/me").json()["id"] == original


def test_colliding_legacy_name_does_not_recover_someone_elses_account():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(User(issuer="local-development", subject="learner", display_name="日本語"))
        db.flush()
        name = "Ελληνικά"
        subject = f"learner-{hashlib.sha256(name.encode()).hexdigest()[:10]}"
        assert returning_dev_user(db, subject, name) is None
        assert returning_dev_user(db, "unrelated-client-id", "日本語") is None
    engine.dispose()
