"""Study reminders: opt-in, one a day, only on study days in the evening, and they go quiet."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from test_learner_api import ORIGIN, login, onboard

from socrat import reminders

KOLKATA = ZoneInfo("Asia/Kolkata")


def at(day: int, hour: int) -> int:
    """A Monday-based moment in November 2026, local to Asia/Kolkata (2 Nov 2026 is a Monday)."""
    return int(datetime(2026, 11, day, hour, 5, tzinfo=KOLKATA).timestamp())


@pytest.fixture
def client(tmp_path):
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient

    from socrat.config import Settings
    from socrat.main import create_app

    url = f"sqlite:///{tmp_path / 'remind.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    app = create_app(Settings(database_url=url, environment="test", dev_login_enabled=True))
    with TestClient(app, base_url=ORIGIN) as test_client:
        yield test_client
    app.state.engine.dispose()


class Outbox:
    def __init__(self):
        self.mail = []

    def __call__(self, settings, to, subject, text):
        self.mail.append((to, subject, text))


def learner(client, subject="ada", email="ada@example.com"):
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from socrat.models import User

    headers = login(client, subject=subject, name="Ada Lovelace")
    onboard(client, headers)
    with Session(client.app.state.engine) as db, db.begin():
        user = db.scalar(select(User).where(User.subject == subject))
        user.email = email
    return headers


def sweep(client, stamp, outbox):
    return reminders.sweep(client.app.state.engine, client.app.state.settings, stamp, send=outbox)


def test_reminders_are_off_until_the_learner_turns_them_on(client):
    learner(client)
    outbox = Outbox()
    assert sweep(client, at(2, 19), outbox) == 0 and outbox.mail == []


def test_a_reminder_needs_an_email_address(client):
    headers = login(client)
    onboard(client, headers)  # a dev-login account has no email
    refused = client.patch("/api/v1/me", json={"reminders": True}, headers=headers)
    assert refused.status_code == 409
    assert client.get("/api/v1/me").json()["can_remind"] is False


def test_one_friendly_email_in_the_evening_of_a_study_day_and_no_second(client):
    headers = learner(client)
    on = client.patch("/api/v1/me", json={"reminders": True}, headers=headers)
    assert on.status_code == 200 and on.json()["reminders"] is True
    outbox = Outbox()
    assert sweep(client, at(2, 10), outbox) == 0, "not in the morning"
    assert sweep(client, at(2, 19), outbox) == 1
    to, subject, text = outbox.mail[0]
    assert to == "ada@example.com" and "Ada" in text and "/settings" in text
    assert sweep(client, at(2, 20), outbox) == 0, "never twice in a day"
    assert len(outbox.mail) == 1


def test_no_reminder_on_a_day_off_or_after_the_learner_already_studied(client):
    from sqlalchemy.orm import Session

    from socrat.models import DailyActivity, Enrollment

    headers = learner(client)
    client.patch("/api/v1/me", json={"reminders": True}, headers=headers)
    with Session(client.app.state.engine) as db, db.begin():
        db.query(Enrollment).update({"weekdays": [0, 1, 2, 3, 4]})  # Saturday is a day off
    outbox = Outbox()
    assert sweep(client, at(7, 19), outbox) == 0, "Saturday"
    with Session(client.app.state.engine) as db, db.begin():
        user_id = db.query(Enrollment.user_id).scalar()
        db.add(DailyActivity(user_id=user_id, day="2026-11-03", activities=1, minutes=10, solved=0))
    assert sweep(client, at(3, 19), outbox) == 0, "they already studied today"
    assert sweep(client, at(4, 19), outbox) == 1


def test_it_goes_quiet_after_three_ignored_and_wakes_when_they_study(client):
    from sqlalchemy.orm import Session

    from socrat.models import DailyActivity, Enrollment

    headers = learner(client)
    client.patch("/api/v1/me", json={"reminders": True}, headers=headers)
    outbox = Outbox()
    assert [sweep(client, at(day, 19), outbox) for day in (2, 3, 4, 5, 6)] == [1, 1, 1, 0, 0]
    with Session(client.app.state.engine) as db, db.begin():
        user_id = db.query(Enrollment.user_id).scalar()
        db.add(DailyActivity(user_id=user_id, day="2026-11-06", activities=2, minutes=20, solved=0))
    assert sweep(client, at(9, 19), outbox) == 1, "they came back, so reminders resume"


def test_turning_reminders_off_stops_them(client):
    headers = learner(client)
    client.patch("/api/v1/me", json={"reminders": True}, headers=headers)
    client.patch("/api/v1/me", json={"reminders": False}, headers=headers)
    outbox = Outbox()
    assert sweep(client, at(2, 19), outbox) == 0
