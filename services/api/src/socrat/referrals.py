"""Invite friends: a share link, a double-sided welcome and a reward ladder.

Only real learners count, so the ladder cannot be farmed with empty accounts: a friend is
"active" after finishing ACTIVE_AFTER activities and "paid" once a Razorpay payment went
through. Rewards are free days on a plan (`billing.comp`), so they cost us only the AI the
learner uses, which the per-learner AI budget caps. Paid rungs are funded by the friend's own
subscription. A reward waits (`granted_at` null) while the learner pays, and is applied the
next time `sync` runs after the paid plan ends.
"""

import secrets

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat import billing
from socrat.database import record_event
from socrat.learn.routes import engine, user_of
from socrat.models import AuditEvent, Referral, ReferralReward, Subscription, User, now

router = APIRouter(prefix="/api/v1/referrals")

WELCOME = ("plus", 7)  # what the invited friend gets on joining
ACTIVE_AFTER = 3  # finished activities before a friend counts
CLAIM_WINDOW = 14 * 86400  # only new accounts can be referred
# key -> (counts friends who are, how many, plan, days). Cumulative: every rung reached pays out.
RUNGS = {
    "active:1": ("active", 1, "plus", 7),
    "active:3": ("active", 3, "plus", 30),
    "active:5": ("active", 5, "plus", 60),
    "paid:1": ("paid", 1, "plus", 30),
    "paid:3": ("paid", 3, "pro", 30),
    "paid:10": ("paid", 10, "pro", 90),
}
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=4, max_length=12)


def counts(db: Session, user_id: str) -> dict[str, int]:
    friends = select(Referral.friend_id).where(Referral.referrer_id == user_id)
    joined = db.scalar(select(func.count()).select_from(friends.subquery())) or 0
    finished = (
        select(AuditEvent.actor_id)
        .where(AuditEvent.actor_id.in_(friends), AuditEvent.kind == "activity.completed")
        .group_by(AuditEvent.actor_id)
        .having(func.count() >= ACTIVE_AFTER)
    )
    active = db.scalar(select(func.count()).select_from(finished.subquery())) or 0
    paid = (
        db.scalar(
            select(func.count())
            .select_from(Subscription)
            .where(
                Subscription.user_id.in_(friends),
                ~Subscription.razorpay_subscription_id.startswith("comp_"),
                Subscription.status != "created",  # "created" means checkout was never paid
            )
        )
        or 0
    )
    return dict(joined=joined, active=active, paid=paid)


def sync(db: Session, user_id: str, stamp: int) -> dict[str, int]:
    """Record rungs newly reached and apply every reward still waiting. Idempotent."""
    reached = counts(db, user_id)
    have = {
        r.rung: r
        for r in db.scalars(select(ReferralReward).where(ReferralReward.user_id == user_id))
    }
    for key, (kind, need, _, _) in RUNGS.items():
        if reached[kind] >= need and key not in have:
            have[key] = ReferralReward(user_id=user_id, rung=key, earned_at=stamp)
            db.add(have[key])
    for key, reward in have.items():
        if reward.granted_at is None and key in RUNGS:
            _, _, plan, days = RUNGS[key]
            if billing.comp(db, user_id, plan, days, stamp):
                reward.granted_at = stamp
                record_event(db, user_id, "referral.rewarded", key)
    return reached


def code_of(db: Session, user: User) -> str:
    while user.referral_code is None:
        code = "".join(secrets.choice(ALPHABET) for _ in range(8))
        if db.scalar(select(User.id).where(User.referral_code == code)) is None:
            user.referral_code = code
    return user.referral_code


@router.get("")
def overview(request: Request):
    stamp = now()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        reached = sync(db, user.id, stamp)
        granted = {
            r.rung: r.granted_at is not None
            for r in db.scalars(select(ReferralReward).where(ReferralReward.user_id == user.id))
        }
        return dict(
            code=code_of(db, user),
            friends=reached,
            active_after=ACTIVE_AFTER,
            welcome=dict(plan=WELCOME[0], days=WELCOME[1]),
            rungs=[
                dict(
                    key=k,
                    kind=kind,
                    need=need,
                    plan=plan,
                    days=days,
                    reached=k in granted,
                    granted=granted.get(k, False),
                )
                for k, (kind, need, plan, days) in RUNGS.items()
            ],
            referred=db.get(Referral, user.id) is not None,
        )


@router.post("/claim")
def claim(body: Claim, request: Request):
    """A new learner joined through a friend's link: link them and grant the welcome."""
    stamp = now()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        referrer = db.scalar(select(User).where(User.referral_code == body.code.strip().upper()))
        if referrer is None:
            raise HTTPException(404, "referral_code_invalid")
        if referrer.id == user.id:
            raise HTTPException(409, "referral_own_code")
        if db.get(Referral, user.id) is not None:
            raise HTTPException(409, "referral_already_used")
        if user.created_at < stamp - CLAIM_WINDOW:
            raise HTTPException(409, "referral_not_new")
        db.add(Referral(friend_id=user.id, referrer_id=referrer.id, created_at=stamp))
        welcomed = billing.comp(db, user.id, WELCOME[0], WELCOME[1], stamp)
        record_event(db, user.id, "referral.joined", referrer.id)
        return dict(welcomed=welcomed, days=WELCOME[1], referrer=referrer.display_name)
