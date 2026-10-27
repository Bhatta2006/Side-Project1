"""Paid plans via Razorpay Subscriptions.

Checkout creates a subscription, the browser pays it in Razorpay's modal, `verify` checks the
modal's signature and grants access at once, and the webhook keeps renewals and cancellations
in step. Plan limits live in `socrat.entitlements`.
"""

import hashlib
import hmac
import json
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat import entitlements
from socrat.database import record_event
from socrat.learn.routes import catalog, engine, user_of
from socrat.models import BillingPlan, Subscription, now

router = APIRouter(prefix="/api/v1/billing")
API = "https://api.razorpay.com/v1"

# plan -> interval -> currency -> minor units (paise / cents). Yearly = 12 months less 20%.
PRICES = {
    "plus": {"month": {"INR": 9900, "USD": 199}, "year": {"INR": 95000, "USD": 1900}},
    "pro": {"month": {"INR": 99900, "USD": 1000}, "year": {"INR": 959000, "USD": 9600}},
}
RANK = entitlements.RANK
NAMES = {"plus": "Founding Member", "pro": "Pro"}
# interval -> (Razorpay period, billing cycles to authorise, seconds granted until the webhook)
PERIOD = {"month": ("monthly", 120, 31 * 86400), "year": ("yearly", 10, 366 * 86400)}


class Checkout(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan: Literal["plus", "pro"]
    interval: Literal["month", "year"]
    currency: Literal["INR", "USD"] = "INR"


class Verify(BaseModel):
    model_config = ConfigDict(extra="forbid")
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str


def razorpay(settings, method: str, path: str, **body) -> dict:
    secret = settings.razorpay_key_secret.get_secret_value()
    if not (settings.razorpay_key_id and secret):
        raise HTTPException(503, "billing_unavailable")
    try:
        reply = httpx.request(
            method,
            f"{API}{path}",
            json=body or None,
            auth=(settings.razorpay_key_id, secret),
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(502, "billing_provider_error") from exc
    if reply.status_code == 401:
        raise HTTPException(503, "billing_unavailable")
    if reply.status_code >= 400:
        raise HTTPException(502, "billing_provider_error")
    return reply.json()


def sign(secret: str, message: str) -> str:
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def is_comp(sub: Subscription | None) -> bool:
    return sub is not None and sub.razorpay_subscription_id.startswith("comp_")


def comp(
    db: Session, user_id: str, plan: str, days: int, stamp: int, replace: bool = False
) -> bool:
    """Grant a free plan for some days. Refused (False) while the learner pays through Razorpay
    or has a checkout open, and, unless `replace`, while a granted higher plan still runs."""
    sub = db.get(Subscription, user_id)
    live = sub is not None and sub.plan in RANK and sub.current_end > stamp
    if sub is not None and not is_comp(sub) and (live or sub.status == "created" or sub.pending):
        return False
    if sub is None:
        sub = Subscription(
            user_id=user_id,
            razorpay_subscription_id=f"comp_{user_id}",
            interval="month",
            currency="INR",
        )
        db.add(sub)
    if not live or not is_comp(sub):
        sub.razorpay_subscription_id, sub.current_end = f"comp_{user_id}", stamp
    elif RANK[plan] < RANK[sub.plan]:
        if not replace:
            return False
        sub.current_end = stamp  # an admin downgrade starts now
    # An upgrade keeps the days left: they run on the better plan.
    sub.plan, sub.status, sub.pending = plan, "active", None
    sub.current_end = max(sub.current_end or 0, stamp) + days * 86400
    sub.cancel_at_period_end, sub.updated_at = False, stamp
    return True


def plan_id(db: Session, settings, body: Checkout) -> str:
    amount = PRICES[body.plan][body.interval][body.currency]
    key = f"{body.plan}:{body.interval}:{body.currency}:{amount}"  # a new price is a new Razorpay plan
    cached = db.get(BillingPlan, key)
    if cached:
        return cached.razorpay_plan_id
    made = razorpay(
        settings,
        "POST",
        "/plans",
        period=PERIOD[body.interval][0],
        interval=1,
        item=dict(
            name=f"Socrat {NAMES[body.plan]} ({PERIOD[body.interval][0]})",
            amount=amount,
            currency=body.currency,
        ),
    )
    db.add(BillingPlan(key=key, razorpay_plan_id=made["id"]))
    return made["id"]


@router.get("/prices")
def prices():
    return PRICES


@router.get("/status")
def status(request: Request):
    from socrat import referrals  # it imports billing

    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        stamp = now()
        referrals.sync(db, user.id, stamp)  # rewards land on the next app load
        plan = entitlements.plan_of(db, user.id, stamp)
        sub = db.get(Subscription, user.id)
        paid = sub is not None and plan != "free"
        return dict(
            enabled=entitlements.ENABLED,
            plan=plan,
            usage=entitlements.usage(db, user.id, stamp),
            free_concepts=None if paid else sorted(entitlements.free_concepts(catalog())),
            renews_at=sub.current_end if sub and paid else None,
            cancel_at_period_end=bool(sub and paid and sub.cancel_at_period_end),
            prices=PRICES,
        )


@router.post("/checkout")
def checkout(body: Checkout, request: Request):
    settings = request.app.state.settings
    if not entitlements.ENABLED:
        raise HTTPException(404, "not_found")
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        sub = db.get(Subscription, user.id)
        # A granted plan (admin or referral) never blocks buying; paying replaces it.
        current = "free" if is_comp(sub) else entitlements.plan_of(db, user.id)
        if RANK[body.plan] <= RANK[current]:  # only moving up is allowed while subscribed
            raise HTTPException(409, "already_subscribed")
        made = razorpay(
            settings,
            "POST",
            "/subscriptions",
            plan_id=plan_id(db, settings, body),
            total_count=PERIOD[body.interval][1],
            customer_notify=1,
            notes=dict(user_id=user.id),
        )
        if sub is not None and current != "free":
            # Upgrade: keep the paid plan working until the new payment is verified.
            sub.pending = f"{body.plan}:{body.interval}:{body.currency}:{made['id']}"
        else:
            if sub is None:
                sub = Subscription(user_id=user.id, razorpay_subscription_id=made["id"])
                db.add(sub)
            sub.plan, sub.interval, sub.currency = body.plan, body.interval, body.currency
            sub.status, sub.razorpay_subscription_id = "created", made["id"]
            sub.current_end, sub.cancel_at_period_end, sub.pending = 0, False, None
        sub.updated_at = now()
        return dict(
            key_id=settings.razorpay_key_id,
            subscription_id=made["id"],
            name="Socrat",
            description=f"{NAMES[body.plan]} plan, billed every {body.interval}",
        )


@router.post("/verify")
def verify(body: Verify, request: Request):
    settings = request.app.state.settings
    expected = sign(
        settings.razorpay_key_secret.get_secret_value(),
        f"{body.razorpay_payment_id}|{body.razorpay_subscription_id}",
    )
    if not hmac.compare_digest(expected, body.razorpay_signature):
        raise HTTPException(400, "payment_signature_invalid")
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        sub = db.get(Subscription, user.id)
        upgrading = sub is not None and (sub.pending or "").endswith(
            f":{body.razorpay_subscription_id}"
        )
        if sub is None or not (
            upgrading or sub.razorpay_subscription_id == body.razorpay_subscription_id
        ):
            raise HTTPException(400, "payment_signature_invalid")
        stamp = now()
        if upgrading:
            old = sub.razorpay_subscription_id
            sub.plan, sub.interval, sub.currency, _ = (sub.pending or "").split(":")
            sub.razorpay_subscription_id, sub.pending = body.razorpay_subscription_id, None
            sub.current_end, sub.cancel_at_period_end = 0, False  # the new plan starts now
            try:  # stop billing the old plan; no proration, the new period starts today
                razorpay(settings, "POST", f"/subscriptions/{old}/cancel", cancel_at_cycle_end=0)
            except HTTPException:
                pass  # ponytail: a failed cancel needs a manual look in the Razorpay dashboard
        # The webhook later sets the exact renewal date; until then grant the paid period.
        sub.status = "active"
        sub.current_end = max(sub.current_end, stamp + PERIOD[sub.interval][2])
        sub.updated_at = stamp
        record_event(db, user.id, "billing.subscribed", sub.plan)
        return dict(plan=sub.plan)


@router.post("/cancel")
def cancel(request: Request):
    settings = request.app.state.settings
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        sub = db.get(Subscription, user.id)
        if sub is None or entitlements.plan_of(db, user.id) == "free":
            raise HTTPException(404, "not_found")
        razorpay(
            settings,
            "POST",
            f"/subscriptions/{sub.razorpay_subscription_id}/cancel",
            cancel_at_cycle_end=1,
        )
        sub.cancel_at_period_end, sub.updated_at = True, now()
        record_event(db, user.id, "billing.cancelled", sub.plan)
        return dict(ok=True)


@router.post("/webhook")
async def webhook(request: Request):
    secret = request.app.state.settings.razorpay_webhook_secret.get_secret_value()
    if not secret:
        raise HTTPException(404, "not_found")
    raw = await request.body()
    given = request.headers.get("x-razorpay-signature", "")
    if not hmac.compare_digest(sign(secret, raw.decode()), given):
        raise HTTPException(400, "signature_invalid")
    event = json.loads(raw)
    entity = event.get("payload", {}).get("subscription", {}).get("entity", {})
    with Session(engine(request)) as db, db.begin():
        sub = db.scalar(
            select(Subscription).where(Subscription.razorpay_subscription_id == entity.get("id"))
        )
        if sub is None:
            return dict(ok=True)  # not ours, or not yet checked out
        name = event.get("event", "")
        if name in {"subscription.activated", "subscription.charged"} and entity.get("current_end"):
            sub.status, sub.current_end = "active", int(entity["current_end"])
        elif name in {"subscription.cancelled", "subscription.completed", "subscription.halted"}:
            # Access runs out at current_end; nothing more is charged.
            sub.status = name.removeprefix("subscription.")
        sub.updated_at = now()
        return dict(ok=True)
