import threading

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401,F811

from socrat import entitlements
from socrat.models import LaunchGrant, Subscription, User

DAY = 86400


@pytest.fixture
def promo(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(entitlements, "ENABLED", True)
    monkeypatch.setattr(entitlements, "LAUNCH_PROMO_SLOTS", 3)
    monkeypatch.setattr(entitlements, "LAUNCH_PROMO_DAYS", 30)
    monkeypatch.setattr(entitlements, "NO_PROMO_ISSUERS", set())  # dev sign-in stands in here
    return client


def new_device(api):
    """Sign-ins after this come from a different browser."""
    api.cookies.clear()


def arrive(api, subject="ada", name="Ada"):
    """Sign up, finish onboarding and open the dashboard, which is where the offer is claimed."""
    headers = login(api, subject=subject, name=name)
    onboard(api, headers)
    assert api.get("/api/v1/billing/status").status_code == 200
    return headers


def grants(api):
    with Session(api.app.state.engine) as db:
        return db.scalar(select(func.count()).select_from(LaunchGrant))


def test_first_learners_to_reach_the_dashboard_get_plus_for_a_month_up_to_the_cap(promo):
    for n in range(5):
        new_device(promo)
        arrive(promo, subject=f"learner{n}", name=f"L{n}")
    assert grants(promo) == 3
    with Session(promo.app.state.engine) as db:
        rows = db.scalars(select(LaunchGrant).order_by(LaunchGrant.slot)).all()
        assert [r.slot for r in rows] == [1, 2, 3]
        first = rows[0]
        assert first.expires_at - first.granted_at == 30 * DAY
        late = db.scalar(select(User).where(User.subject == "learner4"))
        assert entitlements.plan_of(db, first.user_id, first.granted_at + 29 * DAY) == "plus"
        assert entitlements.plan_of(db, first.user_id, first.granted_at + 31 * DAY) == "free"
        assert entitlements.plan_of(db, late.id) == "free"


def test_the_grant_waits_for_the_dashboard_and_is_made_once(promo):
    headers = login(promo, subject="new", name="New")
    assert grants(promo) == 0  # signing up alone does not start the month
    assert promo.get("/api/v1/billing/status").json()["promo"] is None  # no plan yet
    assert grants(promo) == 0
    onboard(promo, headers)
    first = promo.get("/api/v1/billing/status").json()["promo"]
    assert first and grants(promo) == 1
    login(promo, subject="new", name="New")  # signing in again, opening it again
    again = promo.get("/api/v1/billing/status").json()["promo"]
    assert again["ends_at"] == first["ends_at"] and grants(promo) == 1


def test_an_account_from_before_the_offer_gets_it_on_its_next_visit(
    client,  # noqa: F811
    monkeypatch,
):
    monkeypatch.setattr(entitlements, "ENABLED", True)
    monkeypatch.setattr(entitlements, "NO_PROMO_ISSUERS", set())
    arrive(client, subject="early", name="Early")  # offer off: nothing to claim
    assert grants(client) == 0
    monkeypatch.setattr(entitlements, "LAUNCH_PROMO_SLOTS", 20)
    status = client.get("/api/v1/billing/status").json()
    assert status["plan"] == "plus" and status["promo"]["seen"] is False
    assert grants(client) == 1


def test_local_dev_sign_ins_never_use_a_slot(client, monkeypatch):  # noqa: F811
    monkeypatch.setattr(entitlements, "LAUNCH_PROMO_SLOTS", 20)
    arrive(client)
    assert grants(client) == 0


def test_racing_signups_cannot_exceed_the_cap(promo, monkeypatch):
    monkeypatch.setattr(entitlements, "LAUNCH_PROMO_SLOTS", 20)
    engine = promo.app.state.engine
    with Session(engine) as db, db.begin():
        ids = []
        for n in range(40):
            user = User(issuer="email", subject=f"race{n}")
            db.add(user)
            db.flush()
            ids.append(user.id)
    barrier = threading.Barrier(8)

    def worker(chunk):
        barrier.wait()
        for uid in chunk:
            try:
                with Session(engine) as db, db.begin():
                    entitlements.grant_launch_promo(db, db.get(User, uid), f"device-{uid}")
            except Exception:  # sqlite may report "database is locked"; the cap is what matters
                pass

    threads = [threading.Thread(target=worker, args=(ids[i::8],)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    with Session(engine) as db:
        slots = db.scalars(select(LaunchGrant.slot)).all()
    assert len(slots) <= 20 and all(1 <= s <= 20 for s in slots)


def test_status_reports_the_offer_once_and_unlocks_content(promo):
    headers = login(promo)
    onboard(promo, headers)
    status = promo.get("/api/v1/billing/status").json()
    assert status["plan"] == "plus" and status["free_concepts"] is None
    assert status["promo"]["seen"] is False and status["promo"]["ends_at"]
    assert promo.post("/api/v1/billing/promo/seen", headers=headers).status_code == 200
    assert promo.get("/api/v1/billing/status").json()["promo"]["seen"] is True


def test_a_paid_plan_wins_over_the_offer(promo):
    headers = login(promo)
    onboard(promo, headers)
    with Session(promo.app.state.engine) as db, db.begin():
        uid = db.scalar(select(User.id))
        db.add(
            Subscription(
                user_id=uid,
                razorpay_subscription_id="sub_x",
                plan="pro",
                interval="month",
                currency="INR",
                status="active",
                current_end=4_000_000_000,
            )
        )
    status = promo.get("/api/v1/billing/status").json()
    assert status["plan"] == "pro" and status["promo"] is None
    assert grants(promo) == 0  # a paying learner leaves the slot for someone else


def test_one_device_gets_one_grant_whichever_account_signs_up(promo):
    headers = arrive(promo, subject="google-one", name="One")
    assert promo.post("/api/v1/auth/logout", headers=headers).status_code == 204
    arrive(promo, subject="google-two", name="Two")  # same browser, another account
    arrive(promo, subject="google-three", name="Three")
    assert grants(promo) == 1
    new_device(promo)
    arrive(promo, subject="google-four", name="Four")
    assert grants(promo) == 2


def test_a_forged_device_cookie_is_replaced_not_trusted(promo):
    promo.cookies.set("socrat_device", "x")  # too short to be one of ours
    arrive(promo, subject="a", name="A")
    minted = [c.value for c in promo.cookies.jar if c.name == "socrat_device" and c.value != "x"]
    assert minted and len(minted[0]) >= 32
    arrive(promo, subject="b", name="B")
    assert grants(promo) == 1


def test_deleting_the_account_keeps_the_slot_and_the_device_used(promo):
    arrive(promo, subject="leaver", name="Leaver")
    with Session(promo.app.state.engine) as db, db.begin():
        db.delete(db.scalar(select(User).where(User.subject == "leaver")))
    with Session(promo.app.state.engine) as db:
        row = db.scalar(select(LaunchGrant))
        assert row is not None and row.user_id is None and row.device_hash
    arrive(promo, subject="returner", name="Returner")  # same browser, new account
    assert grants(promo) == 1
