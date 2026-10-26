import json
import uuid
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401,F811

from socrat import billing, entitlements
from socrat.catalog.registry import default_catalog
from socrat.models import AssistantMessage, AssistantThread, PlaygroundJob, User


@pytest.fixture
def paid(client, monkeypatch):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    settings = client.app.state.settings
    settings.razorpay_key_id = "rzp_test_x"
    settings.razorpay_key_secret = type(settings.razorpay_key_secret)("secret")
    monkeypatch.setattr(entitlements, "ENABLED", True)
    calls = []

    def fake(_settings, method, path, **body):
        calls.append(path)
        return {"id": "sub_1" if path == "/subscriptions" else "plan_1"}

    monkeypatch.setattr(billing, "razorpay", fake)
    return client, headers, calls


def user_id(api):
    with Session(api.app.state.engine) as db:
        return db.query(User).one().id


def test_windows_are_calendar_day_and_monday_week():
    user = User(issuer="i", subject="s", timezone="Asia/Kolkata")
    wednesday = int(datetime(2026, 10, 21, 10, 0, tzinfo=UTC).timestamp())  # 15:30 IST
    day = entitlements.window_start(user, "day", wednesday)
    week = entitlements.window_start(user, "week", wednesday)
    assert datetime.fromtimestamp(day, UTC).isoformat() == "2026-10-20T18:30:00+00:00"
    assert datetime.fromtimestamp(week, UTC).isoformat() == "2026-10-18T18:30:00+00:00"


def test_free_content_is_the_first_two_modules_of_each_course():
    catalog = default_catalog()
    free = entitlements.free_concepts(catalog)
    for course_id, course in catalog.courses.items():
        assert {f"{course_id}:{c}" for m in course.modules[:2] for c in m.concepts} <= free
        later = [c for m in course.modules[2:] for c in m.concepts]
        assert later and not {f"{course_id}:{c}" for c in later} & free


def test_free_plan_limits_then_paid_unlocks(paid):
    api, headers, _ = paid
    uid = user_id(api)
    catalog = default_catalog()
    locked = next(f"dsa:{c}" for m in catalog.course("dsa").modules[2:] for c in m.concepts)
    with Session(api.app.state.engine) as db, db.begin():
        with pytest.raises(HTTPException) as err:
            entitlements.require_concept(db, catalog, uid, locked, 0)
        assert err.value.status_code == 402
        with pytest.raises(HTTPException) as err:
            entitlements.enforce(db, uid, "playground", 1_800_000_000)
        assert err.value.status_code == 402
        thread = AssistantThread(user_id=uid, scope="general")
        db.add(thread)
        db.flush()
        for _ in range(5):
            db.add(
                AssistantMessage(
                    thread_id=thread.id, role="user", content="hi", created_at=1_800_000_000
                )
            )
        db.flush()
        with pytest.raises(HTTPException) as err:
            entitlements.enforce(db, uid, "chat", 1_800_000_100)
        assert err.value.status_code == 429 and err.value.detail == "chat_week_limit"


def test_failed_and_cancelled_visuals_are_not_charged_to_the_plan(paid, monkeypatch):
    api, _, _ = paid
    uid = user_id(api)
    monkeypatch.setattr(entitlements, "plan_of", lambda *args: "plus")  # 3 visuals a day
    stamp = 1_800_000_000

    def job(db, thread, status):
        db.add(
            PlaygroundJob(
                id=str(uuid.uuid4()),
                user_id=uid,
                thread_id=thread.id,
                prompt="Explain heaps",
                level="standard",
                language="python",
                status=status,
                progress={},
                error="",
                tries=0,
                heartbeat_at=0,
                created_at=stamp,
            )
        )
        db.flush()

    with Session(api.app.state.engine) as db, db.begin():
        thread = AssistantThread(user_id=uid, scope=entitlements.PLAYGROUND_SCOPE)
        db.add(thread)
        db.flush()
        for status in ["failed", "cancelled", "failed", "ready", "ready"]:
            job(db, thread, status)
        entitlements.enforce(db, uid, "playground", stamp + 60)  # 2 of 3 used
        assert entitlements.usage(db, uid, stamp + 60)["playground"]["used"] == 2
        job(db, thread, "ready")
        with pytest.raises(HTTPException) as err:
            entitlements.enforce(db, uid, "playground", stamp + 60)
        assert err.value.status_code == 429 and err.value.detail == "playground_day_limit"


def test_checkout_verify_grants_plan_and_rejects_bad_signature(paid):
    api, headers, calls = paid
    body = dict(plan="plus", interval="month", currency="INR")
    started = api.post("/api/v1/billing/checkout", json=body, headers=headers)
    assert started.status_code == 200 and started.json()["subscription_id"] == "sub_1"
    assert "key_secret" not in json.dumps(started.json())
    pay = dict(razorpay_payment_id="pay_1", razorpay_subscription_id="sub_1")
    bad = api.post(
        "/api/v1/billing/verify", json=dict(pay, razorpay_signature="nope"), headers=headers
    )
    assert bad.status_code == 400
    assert api.get("/api/v1/billing/status").json()["plan"] == "free"
    good = billing.sign("secret", "pay_1|sub_1")
    ok = api.post(
        "/api/v1/billing/verify", json=dict(pay, razorpay_signature=good), headers=headers
    )
    assert ok.status_code == 200
    status = api.get("/api/v1/billing/status").json()
    assert status["plan"] == "plus" and status["usage"]["playground"]["limit"] == 3
    assert api.post("/api/v1/billing/checkout", json=body, headers=headers).status_code == 409


def test_webhook_needs_a_valid_signature_and_sets_the_renewal_date(paid):
    api, headers, _ = paid
    api.post(
        "/api/v1/billing/checkout",
        json=dict(plan="pro", interval="year", currency="USD"),
        headers=headers,
    )
    settings = api.app.state.settings
    settings.razorpay_webhook_secret = type(settings.razorpay_key_secret)("hook")
    raw = json.dumps(
        dict(
            event="subscription.charged",
            payload=dict(subscription=dict(entity=dict(id="sub_1", current_end=4_000_000_000))),
        )
    )
    assert api.post("/api/v1/billing/webhook", content=raw).status_code == 400
    ok = api.post(
        "/api/v1/billing/webhook",
        content=raw,
        headers={"x-razorpay-signature": billing.sign("hook", raw)},
    )
    assert ok.status_code == 200
    status = api.get("/api/v1/billing/status").json()
    assert status["plan"] == "pro" and status["renews_at"] == 4_000_000_000


def test_plus_upgrades_to_pro_without_losing_access_and_cancels_the_old_plan(paid, monkeypatch):
    api, headers, calls = paid
    made = iter(["sub_plus", "sub_pro"])
    monkeypatch.setattr(
        billing,
        "razorpay",
        lambda _s, _m, path, **b: (
            calls.append(path) or {"id": next(made) if path == "/subscriptions" else "plan_1"}
        ),
    )
    pay = lambda sub: dict(  # noqa: E731
        razorpay_payment_id="pay",
        razorpay_subscription_id=sub,
        razorpay_signature=billing.sign("secret", f"pay|{sub}"),
    )
    plus = dict(plan="plus", interval="month", currency="INR")
    api.post("/api/v1/billing/checkout", json=plus, headers=headers)
    api.post("/api/v1/billing/verify", json=pay("sub_plus"), headers=headers)
    assert api.post("/api/v1/billing/checkout", json=plus, headers=headers).status_code == 409
    started = api.post("/api/v1/billing/checkout", json=dict(plus, plan="pro"), headers=headers)
    assert started.status_code == 200
    assert api.get("/api/v1/billing/status").json()["plan"] == "plus"  # still Plus while paying
    assert (
        api.post("/api/v1/billing/verify", json=pay("sub_pro"), headers=headers).status_code == 200
    )
    assert api.get("/api/v1/billing/status").json()["plan"] == "pro"
    assert "/subscriptions/sub_plus/cancel" in calls


def test_free_learners_cannot_reach_paid_content_by_any_route(paid):
    api, headers, _ = paid
    catalog = default_catalog()
    locked = next(f"zero:{c}" for m in catalog.course("zero").modules[2:] for c in m.concepts)
    module = catalog.course("zero").modules[2].id
    for method, path in [
        ("get", f"/api/v1/concepts/{locked}"),
        ("get", f"/api/v1/quiz/quiz:{locked}"),
        ("get", f"/api/v1/quiz/review:{locked}"),
        ("get", f"/api/v1/quiz/checkpoint:zero:{module}"),
        ("post", f"/api/v1/activities/lesson:{locked}/start"),
        ("post", "/api/v1/assessments/start"),
    ]:
        reply = getattr(api, method)(
            path, headers=headers, **({"json": {}} if method == "post" else {})
        )
        assert reply.status_code == 402, (path, reply.status_code, reply.text)
    with Session(api.app.state.engine) as db:
        from socrat.learn import service as learn

        enrollment = learn.active_enrollment(db, user_id(api))
        assert learn.locked_concepts(db, catalog, enrollment, 0)[locked] == "plan"
        assert not set(
            learn.practice_topics(db, catalog, enrollment, 0)
        ) - entitlements.free_concepts(catalog)


def test_company_questions_are_pro_only(paid):
    api, headers, _ = paid
    assert api.get("/api/v1/companies", headers=headers).json()["locked"] is True
    slug = next(
        iter(__import__("socrat.catalog.practice", fromlist=["x"]).default_index().companies)
    )
    reply = api.get(f"/api/v1/companies/{slug}", headers=headers)
    assert reply.status_code == 402 and reply.json()["error"]["code"] == "pro_required"
    with Session(api.app.state.engine) as db, db.begin():
        from socrat.models import Subscription

        db.add(
            Subscription(
                user_id=user_id(api),
                plan="plus",
                interval="month",
                currency="INR",
                status="active",
                razorpay_subscription_id="sub_x",
                current_end=2**31 - 1,
            )
        )
    assert api.get(f"/api/v1/companies/{slug}", headers=headers).status_code == 402
    assert api.post("/api/v1/assessments/start", headers=headers, json={}).status_code != 402
