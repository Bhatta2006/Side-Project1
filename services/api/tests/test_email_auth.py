import re

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import Response
from test_learner_api import ORIGIN, client  # noqa: F401

from socrat import auth, email_auth, trial
from socrat.models import LoginSession, User

H = {"Origin": ORIGIN}
EMAIL = "ada@example.com"


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(email_auth, "send", lambda _s, to, subject, text: sent.append((to, text)))
    trial._recent.clear()
    yield sent
    trial._recent.clear()


def code_in(text):
    return re.search(r"\b(\d{6})\b", text).group(1)


def signup(client, outbox, email=EMAIL, password="correct horse"):  # noqa: F811
    response = client.post(
        "/api/v1/auth/email/signup",
        json={"email": email, "password": password, "display_name": "Ada"},
        headers=H,
    )
    assert response.status_code == 202, response.text
    return code_in(outbox[-1][1])


def test_signup_verify_login_and_logout(client, outbox):  # noqa: F811
    assert client.get("/api/v1/features").json()["email_login"] is True
    code = signup(client, outbox, email=" Ada@Example.com ")
    assert outbox[-1][0] == EMAIL  # addresses are normalized
    assert client.get("/api/v1/me").status_code == 401  # no account until the code is confirmed
    wrong = "000000" if code != "000000" else "111111"
    bad = client.post("/api/v1/auth/email/verify", json={"email": EMAIL, "code": wrong}, headers=H)
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "email_code_invalid"
    ok = client.post("/api/v1/auth/email/verify", json={"email": EMAIL, "code": code}, headers=H)
    assert ok.status_code == 200
    me = client.get("/api/v1/me").json()
    assert me["display_name"] == "Ada"
    # The code is single use.
    again = client.post("/api/v1/auth/email/verify", json={"email": EMAIL, "code": code}, headers=H)
    assert again.status_code == 400
    assert (
        client.post(
            "/api/v1/auth/logout", headers={**H, "X-CSRF-Token": me["csrf_token"]}
        ).status_code
        == 204
    )
    creds = {"email": EMAIL, "password": "wrong password"}
    denied = client.post("/api/v1/auth/email/login", json=creds, headers=H)
    assert denied.status_code == 401 and denied.json()["error"]["code"] == "invalid_credentials"
    missing = client.post(
        "/api/v1/auth/email/login", json={**creds, "email": "nobody@example.com"}, headers=H
    )
    assert missing.json()["error"]["code"] == "invalid_credentials"  # same answer as a bad password
    login = client.post(
        "/api/v1/auth/email/login", json={"email": EMAIL, "password": "correct horse"}, headers=H
    )
    assert login.status_code == 200 and client.get("/api/v1/me").json()["id"] == me["id"]
    # Cross-site posts are refused before any of this runs.
    assert client.post("/api/v1/auth/email/login", json=creds).status_code == 403


def test_existing_account_and_unknown_reset_reveal_nothing(client, outbox):  # noqa: F811
    code = signup(client, outbox)
    client.post("/api/v1/auth/email/verify", json={"email": EMAIL, "code": code}, headers=H)
    second = client.post(
        "/api/v1/auth/email/signup",
        json={"email": EMAIL, "password": "another password"},
        headers=H,
    )
    assert second.status_code == 202  # the same answer as a new address
    assert "already have one" in outbox[-1][1] and not re.search(r"\b\d{6}\b", outbox[-1][1])
    before = len(outbox)
    unknown = client.post("/api/v1/auth/email/reset", json={"email": "x@example.com"}, headers=H)
    assert unknown.status_code == 202 and len(outbox) == before


def test_codes_lock_after_five_wrong_guesses(client, outbox):  # noqa: F811
    code = signup(client, outbox)
    wrong = [c for c in ("000000", "111111", "222222", "333333", "444444", "555555") if c != code]
    for guess in wrong[:5]:
        client.post("/api/v1/auth/email/verify", json={"email": EMAIL, "code": guess}, headers=H)
    late = client.post("/api/v1/auth/email/verify", json={"email": EMAIL, "code": code}, headers=H)
    assert late.status_code == 400


def test_reset_sets_the_password_and_signs_out_other_sessions(client, outbox):  # noqa: F811
    code = signup(client, outbox)
    client.post("/api/v1/auth/email/verify", json={"email": EMAIL, "code": code}, headers=H)
    with Session(client.app.state.engine) as db:
        user_id = db.scalar(select(User.id).where(User.email == EMAIL))
        old_sessions = set(db.scalars(select(LoginSession.token_hash)))
    assert (
        client.post("/api/v1/auth/email/reset", json={"email": EMAIL}, headers=H).status_code == 202
    )
    reset = code_in(outbox[-1][1])
    confirmed = client.post(
        "/api/v1/auth/email/reset/confirm",
        json={"email": EMAIL, "code": reset, "password": "a new password"},
        headers=H,
    )
    assert confirmed.status_code == 200
    with Session(client.app.state.engine) as db:
        remaining = set(
            db.scalars(select(LoginSession.token_hash).where(LoginSession.user_id == user_id))
        )
    assert remaining and not remaining & old_sessions
    old = {"email": EMAIL, "password": "correct horse"}
    assert client.post("/api/v1/auth/email/login", json=old, headers=H).status_code == 401
    new = {**old, "password": "a new password"}
    assert client.post("/api/v1/auth/email/login", json=new, headers=H).status_code == 200


def test_login_attempts_are_rate_limited(client, outbox):  # noqa: F811
    creds = {"email": EMAIL, "password": "guess"}
    codes = [
        client.post("/api/v1/auth/email/login", json=creds, headers=H).status_code
        for _ in range(21)
    ]
    assert codes[:20] == [401] * 20 and codes[20] == 429


def google(client, subject, email):  # noqa: F811
    request = Request({"type": "http", "app": client.app, "headers": []})
    auth.establish_session(request, Response(), "https://accounts.google.com", subject, email=email)


def test_verified_emails_link_google_and_password_accounts(client, outbox):  # noqa: F811
    # Password first: a Google login with the same verified email takes over that account.
    code = signup(client, outbox)
    client.post("/api/v1/auth/email/verify", json={"email": EMAIL, "code": code}, headers=H)
    google(client, "google-ada", EMAIL)
    with Session(client.app.state.engine) as db:
        users = db.scalars(select(User).where(User.email == EMAIL)).all()
        assert len(users) == 1 and users[0].subject == "google-ada" and users[0].password_hash
    login = {"email": EMAIL, "password": "correct horse"}
    assert client.post("/api/v1/auth/email/login", json=login, headers=H).status_code == 200
    # Google first: confirming an emailed code adds a password to that Google account.
    google(client, "google-bob", "bob@example.com")
    code = signup(client, outbox, email="bob@example.com", password="bob password")
    client.post(
        "/api/v1/auth/email/verify", json={"email": "bob@example.com", "code": code}, headers=H
    )
    with Session(client.app.state.engine) as db:
        bob = db.scalars(select(User).where(User.email == "bob@example.com")).all()
        assert len(bob) == 1 and bob[0].subject == "google-bob" and bob[0].password_hash
    # An unverified provider email (email=None) never links or claims anything.
    google(client, "google-mallory", None)
    with Session(client.app.state.engine) as db:
        assert db.scalar(select(User.email).where(User.subject == "google-mallory")) is None


def test_password_hashes_are_salted_and_verified():
    first, second = email_auth.hash_password("pw secret"), email_auth.hash_password("pw secret")
    assert first != second and first.startswith("scrypt$65536$8$1$")
    assert email_auth.password_matches("pw secret", first)
    assert not email_auth.password_matches("pw secreT", first)
