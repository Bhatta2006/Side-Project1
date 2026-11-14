import hashlib
import re
import secrets
import time
import unicodedata

from fastapi import HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.database import record_event
from socrat.models import LoginSession, User

COOKIE = "socrat_session"
# A random id for the browser, kept across sign-outs and accounts. Only its hash is stored, and
# only to allow one launch-offer grant per device.
DEVICE_COOKIE = "socrat_device"
DEVICE_SECONDS = 2 * 365 * 86400


def device_hash(request: Request) -> str:
    """Hash of this browser's device id, minting one for the response if it has none yet."""
    token = request.cookies.get(DEVICE_COOKIE, "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,64}", token):
        token = getattr(request.state, "device_token", None) or secrets.token_urlsafe(32)
        request.state.device_token = token  # open_session sets it on the response
    return hashlib.sha256(f"device:{token}".encode()).hexdigest()


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def require_session(request: Request, db: Session) -> LoginSession:
    session = db.get(LoginSession, token_hash(request.cookies.get(COOKIE, "")))
    if session is None or session.expires_at <= int(time.time()):
        raise HTTPException(401, "authentication_required")
    return session


def require_csrf(request: Request, session: LoginSession):
    if not secrets.compare_digest(request.headers.get("x-csrf-token", ""), session.csrf_token):
        raise HTTPException(403, "csrf_rejected")


def returning_dev_user(db: Session, subject: str, display_name: str) -> User | None:
    """Recover a pre-hash dev identity only when its recorded name agrees.

    Old slugs collided for punctuation and non-Latin names. Never claim an old
    account just because its slug matches; the saved display name must match too.
    """
    identity = unicodedata.normalize("NFKC", display_name.strip())
    slug = re.sub(r"[^a-z0-9]+", "-", display_name.lower()).strip("-")
    prefix = (slug or "learner")[:53]
    expected = f"{prefix}-{hashlib.sha256(identity.encode()).hexdigest()[:10]}"
    if subject != expected:
        return None
    user = db.scalar(
        select(User).where(
            User.issuer == "local-development", User.subject == (slug[:64] or "learner")
        )
    )
    if user and unicodedata.normalize("NFKC", user.display_name.strip()) == identity:
        return user
    return None


def establish_session(
    request: Request,
    response,
    issuer: str,
    subject: str,
    display_name: str = "",
    email: str | None = None,
):
    """Sign in an external identity. ``email`` must already be verified by the identity provider."""
    with Session(request.app.state.engine) as db, db.begin():
        user = db.scalar(select(User).where(User.issuer == issuer, User.subject == subject))
        if user is None and issuer == "local-development" and display_name:
            user = returning_dev_user(db, subject, display_name)
            if user is not None:
                user.subject = subject
        if user is None and email:
            # A verified email claims the email-and-password account that owns it.
            user = db.scalar(select(User).where(User.email == email, User.issuer == "email"))
            if user is not None:
                user.issuer, user.subject = issuer, subject
        if user is None:
            user = User(issuer=issuer, subject=subject)
            db.add(user)
        if (
            email
            and user.email is None
            and db.scalar(select(User.id).where(User.email == email)) is None
        ):
            user.email = email
        db.flush()
        user_id = user.id
    return open_session(request, response, user_id)


def open_session(request: Request, response, user_id: str):
    # Every signed-in browser carries a device id (the cookie is set below): the launch offer is
    # one per device, and it is claimed later, when the learner reaches the dashboard.
    device_hash(request)
    """Start a session for an authenticated user and set its cookie on ``response``."""
    settings = request.app.state.settings
    with Session(request.app.state.engine) as db, db.begin():
        old = db.get(LoginSession, token_hash(request.cookies.get(COOKIE, "")))
        if old:
            db.delete(old)
        token = secrets.token_urlsafe(48)
        db.add(
            LoginSession(
                token_hash=token_hash(token),
                user_id=user_id,
                csrf_token=secrets.token_urlsafe(32),
                expires_at=int(time.time()) + settings.session_ttl_seconds,
            )
        )
        record_event(db, user_id, "auth.login")
    response.set_cookie(
        COOKIE,
        token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.secure,
        samesite="lax",
        path="/",
    )
    minted = getattr(request.state, "device_token", None)
    if minted:
        response.set_cookie(
            DEVICE_COOKIE,
            minted,
            max_age=DEVICE_SECONDS,
            httponly=True,
            secure=settings.secure,
            samesite="lax",
            path="/",
        )
    return response
