"""Email-and-password accounts: sign-up and password reset are confirmed by an emailed code.

Responses never reveal whether an address has an account. A verified email links to the Google
account with the same address (see ``auth.establish_session``).
"""

import base64
import functools
import hashlib
import hmac
import html
import logging
import re
import secrets

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from socrat.auth import open_session
from socrat.config import Settings
from socrat.database import record_event
from socrat.models import EmailCode, LoginSession, User, now
from socrat.trial import allow, visitor

router = APIRouter(prefix="/api/v1/auth/email")
CODE_SECONDS = 600
MAX_ATTEMPTS = 5
ADDRESS = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# ponytail: scrypt at 64 MiB per hash. OWASP's floor is N=2^17; 2^16 keeps concurrent logins
# inside the API container's memory. The parameters are stored per hash, so raising them later
# only needs rehash-on-login.
SCRYPT = dict(n=2**16, r=8, p=1)
log = logging.getLogger("socrat.email_auth")


class Address(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=254)

    @field_validator("email")
    @classmethod
    def normalized(cls, value: str) -> str:
        value = value.strip().lower()
        if not ADDRESS.match(value):
            raise ValueError("Enter a valid email address")
        return value


class Signup(Address):
    # Passwords are used exactly as typed: no trimming, no composition rules (NIST 800-63B).
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=80)


class Credentials(Address):
    password: str = Field(min_length=1, max_length=128)


class Confirm(Address):
    code: str = Field(pattern=r"^\d{6}$")


class Reset(Confirm):
    password: str = Field(min_length=8, max_length=128)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, maxmem=2**27, dklen=32, **SCRYPT)
    encode = base64.b64encode
    params = f"{SCRYPT['n']}${SCRYPT['r']}${SCRYPT['p']}"
    return f"scrypt${params}${encode(salt).decode()}${encode(digest).decode()}"


def password_matches(password: str, stored: str) -> bool:
    _, n, r, p, salt, digest = stored.split("$")
    actual = hashlib.scrypt(
        password.encode(),
        salt=base64.b64decode(salt),
        n=int(n),
        r=int(r),
        p=int(p),
        maxmem=2**27,
        dklen=32,
    )
    return hmac.compare_digest(actual, base64.b64decode(digest))


@functools.cache
def decoy() -> str:
    """Checked against when no account matches, so a miss takes as long as a wrong password."""
    return hash_password(secrets.token_urlsafe(16))


def code_hash(settings: Settings, email: str, purpose: str, code: str) -> str:
    key = settings.session_secret.get_secret_value().encode()
    return hmac.new(key, f"{purpose}:{email}:{code}".encode(), hashlib.sha256).hexdigest()


def available(request: Request) -> Settings:
    settings = request.app.state.settings
    if not settings.email_login_enabled:
        raise HTTPException(404, "not_found")
    return settings


def throttle(request: Request, email: str, action: str, per_visitor: int, per_email: int):
    # ponytail: in-process windows (one API process); move to the database if the API scales out.
    if not allow(f"{action}:{visitor(request)}", per_visitor) or not allow(
        f"{action}:{email}", per_email
    ):
        raise HTTPException(429, "too_many_attempts")


def issue(db: Session, settings: Settings, email: str, purpose: str, **pending) -> str:
    """A fresh code for this address and purpose; any earlier one stops working."""
    db.execute(delete(EmailCode).where(EmailCode.email == email, EmailCode.purpose == purpose))
    code = f"{secrets.randbelow(10**6):06d}"
    db.add(
        EmailCode(
            email=email,
            purpose=purpose,
            code_hash=code_hash(settings, email, purpose, code),
            expires_at=now() + CODE_SECONDS,
            created_at=now(),
            **pending,
        )
    )
    return code


def redeem(request: Request, email: str, purpose: str, code: str) -> dict:
    """Consume a matching code and return what it carried; a wrong guess still counts."""
    settings = request.app.state.settings
    with Session(request.app.state.engine) as db, db.begin():
        row = db.scalars(
            select(EmailCode)
            .where(EmailCode.email == email, EmailCode.purpose == purpose)
            .with_for_update()
        ).first()
        valid = row is not None and row.expires_at > now() and row.attempts < MAX_ATTEMPTS
        if row is not None and valid:
            if hmac.compare_digest(row.code_hash, code_hash(settings, email, purpose, code)):
                carried = dict(password_hash=row.password_hash, display_name=row.display_name)
                db.delete(row)
                return carried
            row.attempts += 1
    raise HTTPException(400, "email_code_invalid")


def send(settings: Settings, to: str, subject: str, text: str):
    key = settings.resend_api_key.get_secret_value()
    if not key:
        if settings.secure:
            raise HTTPException(503, "email_unavailable")
        log.warning("email not sent (no Resend key; development only) to %s: %s", to, text)
        return
    body = "".join(f"<p>{html.escape(part)}</p>" for part in text.split("\n\n"))
    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "from": settings.email_from,
                "to": [to],
                "subject": subject,
                "text": text,
                "html": body,
            },
            timeout=10,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        # The status or error type only; never the request, whose header carries the key.
        reason = (
            exc.response.status_code
            if isinstance(exc, httpx.HTTPStatusError)
            else type(exc).__name__
        )
        log.warning("resend delivery failed: %s", reason)
        raise HTTPException(503, "email_unavailable") from exc


def code_email(code: str, purpose: str) -> tuple[str, str]:
    action = "create your Socrat account" if purpose == "signup" else "reset your Socrat password"
    return (
        f"{code} is your Socrat code",
        f"Your code is {code}. Use it to {action}. It expires in 10 minutes.\n\n"
        "If you did not ask for this, you can ignore this email.",
    )


@router.post("/signup", status_code=202)
def signup(body: Signup, request: Request):
    settings = available(request)
    throttle(request, body.email, "send", per_visitor=10, per_email=5)
    with Session(request.app.state.engine) as db, db.begin():
        user = db.scalar(select(User).where(User.email == body.email))
        if user is not None and user.password_hash:
            # Tell the owner, not the requester, that the account exists.
            subject = "You already have a Socrat account"
            text = (
                "Someone tried to create a Socrat account with this email, but you already have "
                "one. Log in with your password, or use Forgot password to set a new one.\n\n"
                "If this was not you, you can ignore this email."
            )
        else:
            code = issue(
                db,
                settings,
                body.email,
                "signup",
                password_hash=hash_password(body.password),
                display_name=body.display_name.strip(),
            )
            subject, text = code_email(code, "signup")
    send(settings, body.email, subject, text)
    return {"sent": True}


@router.post("/verify")
def verify(body: Confirm, request: Request):
    available(request)
    throttle(request, body.email, "verify", per_visitor=30, per_email=15)
    pending = redeem(request, body.email, "signup", body.code)
    with Session(request.app.state.engine) as db, db.begin():
        user = db.scalar(select(User).where(User.email == body.email))
        if user is None:
            user = User(
                issuer="email",
                subject=body.email,
                email=body.email,
                display_name=pending["display_name"],
            )
            db.add(user)
        # On an existing (Google) account with this verified email, this adds the password.
        user.password_hash = pending["password_hash"]
        db.flush()
        record_event(db, user.id, "auth.email_verified")
        user_id = user.id
    return open_session(request, JSONResponse({"authenticated": True}), user_id)


@router.post("/login")
def login(body: Credentials, request: Request):
    available(request)
    throttle(request, body.email, "login", per_visitor=30, per_email=20)
    with Session(request.app.state.engine) as db:
        user = db.scalar(select(User).where(User.email == body.email))
        stored = user.password_hash if user is not None else None
        matched = password_matches(body.password, stored or decoy())
        if not stored or not matched or user is None:
            raise HTTPException(401, "invalid_credentials")
        user_id = user.id
    return open_session(request, JSONResponse({"authenticated": True}), user_id)


@router.post("/reset", status_code=202)
def reset(body: Address, request: Request, background: BackgroundTasks):
    settings = available(request)
    throttle(request, body.email, "send", per_visitor=10, per_email=5)
    with Session(request.app.state.engine) as db, db.begin():
        # A Google account with this verified email may set a password here too.
        known = db.scalar(select(User.id).where(User.email == body.email)) is not None
        code = issue(db, settings, body.email, "reset") if known else None
    if code:
        # Sent after the response, so its timing does not reveal that the account exists.
        background.add_task(send_quietly, settings, body.email, *code_email(code, "reset"))
    return {"sent": True}


def send_quietly(settings: Settings, to: str, subject: str, text: str):
    try:
        send(settings, to, subject, text)
    except HTTPException:
        pass  # already logged; the learner can ask again


@router.post("/reset/confirm")
def reset_confirm(body: Reset, request: Request):
    available(request)
    throttle(request, body.email, "verify", per_visitor=30, per_email=15)
    redeem(request, body.email, "reset", body.code)
    with Session(request.app.state.engine) as db, db.begin():
        user = db.scalar(select(User).where(User.email == body.email))
        if user is None:
            raise HTTPException(400, "email_code_invalid")
        user.password_hash = hash_password(body.password)
        # A new password signs out every existing session.
        db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
        record_event(db, user.id, "auth.password_reset")
        user_id = user.id
    return open_session(request, JSONResponse({"authenticated": True}), user_id)
