from sqlalchemy.orm import Session
from test_learner_api import client, login  # noqa: F401

from socrat import billing, entitlements
from socrat.models import AuditEvent, Subscription, User


def me(api):
    return api.get("/api/v1/me").json()["id"]


def finish(api, user_id, n):
    with Session(api.app.state.engine) as db, db.begin():
        db.add_all(AuditEvent(actor_id=user_id, kind="activity.completed") for _ in range(n))


def plan(api, user_id):
    with Session(api.app.state.engine) as db:
        return entitlements.plan_of(db, user_id)


def test_referral_ladder_counts_only_active_friends_and_waits_for_paid_plans(client):  # noqa: F811
    ada_h = login(client, "ada", "Ada")
    ada = me(client)
    code = client.get("/api/v1/referrals").json()["code"]
    assert len(code) == 8
    own = client.post("/api/v1/referrals/claim", json={"code": code}, headers=ada_h)
    assert own.status_code == 409 and own.json()["error"]["code"] == "referral_own_code"

    friends = []
    for i in range(3):
        headers = login(client, f"friend{i}", f"Friend {i}")
        friends.append(me(client))
        joined = client.post(
            "/api/v1/referrals/claim", json={"code": code.lower()}, headers=headers
        )
        assert joined.status_code == 200 and joined.json()["welcomed"]
        assert plan(client, friends[-1]) == "plus"  # the welcome week
        again = client.post("/api/v1/referrals/claim", json={"code": code}, headers=headers)
        assert again.json()["error"]["code"] == "referral_already_used"

    # Joining alone earns nothing; 3 finished activities make a friend count.
    login(client, "ada", "Ada")
    assert client.get("/api/v1/referrals").json()["friends"] == dict(joined=3, active=0, paid=0)
    assert plan(client, ada) == "free"
    for f in friends:
        finish(client, f, 3)
    body = client.get("/api/v1/referrals").json()
    assert body["friends"]["active"] == 3
    assert [r["key"] for r in body["rungs"] if r["granted"]] == ["active:1", "active:3"]
    with Session(client.app.state.engine) as db:
        sub = db.get(Subscription, ada)
        assert sub.plan == "plus" and sub.current_end - sub.updated_at == 37 * 86400

    # A paying referrer's reward waits; nothing touches the Razorpay subscription.
    with Session(client.app.state.engine) as db, db.begin():
        sub = db.get(Subscription, ada)
        sub.razorpay_subscription_id, end = "sub_real", sub.current_end
        sub = db.get(Subscription, friends[0])
        sub.razorpay_subscription_id = "sub_friend"  # the friend paid
    body = client.get("/api/v1/referrals").json()
    assert body["friends"]["paid"] == 1
    paid = next(r for r in body["rungs"] if r["key"] == "paid:1")
    assert paid["reached"] and not paid["granted"]
    with Session(client.app.state.engine) as db:
        assert db.get(Subscription, ada).current_end == end


def test_old_accounts_cannot_be_referred_and_comp_never_blocks_checkout(client):  # noqa: F811
    login(client, "ada", "Ada")
    code = client.get("/api/v1/referrals").json()["code"]
    headers = login(client, "old", "Old")
    old = me(client)
    with Session(client.app.state.engine) as db, db.begin():
        db.get(User, old).created_at -= 30 * 86400
    late = client.post("/api/v1/referrals/claim", json={"code": code}, headers=headers)
    assert late.json()["error"]["code"] == "referral_not_new"
    assert (
        client.post(
            "/api/v1/referrals/claim", json={"code": "NOPE1234"}, headers=headers
        ).status_code
        == 404
    )

    with Session(client.app.state.engine) as db, db.begin():
        assert billing.comp(db, old, "pro", 7, 1_000)
        assert not billing.comp(db, old, "plus", 7, 1_000)  # a lower grant waits
        db.get(Subscription, old).razorpay_subscription_id = "sub_x"
        db.get(Subscription, old).current_end = 2_000_000_000
        assert not billing.comp(db, old, "pro", 7, 1_000)  # paying: never touched


def test_admin_sees_bugs_and_referrals_per_learner(client):  # noqa: F811
    headers = login(client, "ada", "Ada")
    ada = me(client)
    code = client.get("/api/v1/referrals").json()["code"]
    for text, category in [("crash on run", "bug"), ("again", "bug"), ("nice", "feedback")]:
        sent = client.post(
            "/api/v1/problem-reports",
            json={"message": text, "route": "/today", "category": category},
            headers=headers,
        )
        assert sent.status_code == 200
    friend = login(client, "bob", "Bob")
    client.post("/api/v1/referrals/claim", json={"code": code}, headers=friend)

    client.app.state.settings.admin_subjects = ["boss"]
    boss = login(client, "boss", "Boss")
    for sort in ("bugs", "referred"):
        body = client.get(f"/api/v1/admin/users?sort={sort}", headers=boss).json()
        top = body["items"][0]
        assert top["id"] == ada and top["bugs"] == 2 and top["referred"] == 1
    assert body["totals"]["referrals"] == 1
