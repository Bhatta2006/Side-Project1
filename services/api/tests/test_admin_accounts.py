"""Admin account control: one learner's record, notes, sign-out, deletion, failed generations."""

from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401  (client is a fixture)

from socrat.models import AssistantThread, AuditEvent, PlaygroundJob, User, UserNotification


def people(client):  # noqa: F811
    """A learner (Ada) who has onboarded, then the admin (Boss) signed in."""
    learner = login(client, subject="ada", name="Ada")
    onboard(client, learner)
    ada = client.get("/api/v1/me", headers=learner).json()["id"]
    client.app.state.settings.admin_subjects = ["boss"]
    boss = login(client, subject="boss", name="Boss")
    return ada, boss


def test_everything_here_is_admin_only(client):  # noqa: F811
    learner = login(client, subject="ada", name="Ada")
    ada = client.get("/api/v1/me", headers=learner).json()["id"]
    for method, path in [
        ("get", f"/api/v1/admin/users/{ada}"),
        ("delete", f"/api/v1/admin/users/{ada}"),
        ("post", f"/api/v1/admin/users/{ada}/sign-out"),
        ("get", "/api/v1/admin/generations/failed"),
    ]:
        assert getattr(client, method)(path, headers=learner).status_code == 403
    for path in [f"/api/v1/admin/users/{ada}/notify", "/api/v1/admin/notifications/broadcast"]:
        assert client.post(path, json={"body": "hi"}, headers=learner).status_code == 403


def test_account_record_shows_plan_course_and_activity(client):  # noqa: F811
    ada, boss = people(client)
    detail = client.get(f"/api/v1/admin/users/{ada}", headers=boss).json()
    assert detail["name"] == "Ada" and detail["plan"] == "free" and detail["admin"] is False
    assert detail["enrollments"][0]["course"] == "zero"
    assert detail["enrollments"][0]["status"] == "active"
    assert detail["signed_in_devices"] == 0  # Boss signed in on the same browser after her
    assert isinstance(detail["activity"], list) and detail["notifications"] == []
    assert client.get("/api/v1/admin/users/nobody", headers=boss).status_code == 404


def test_a_note_reaches_the_learner_once(client):  # noqa: F811
    ada, boss = people(client)
    sent = client.post(
        f"/api/v1/admin/users/{ada}/notify",
        json={"title": "Fixed", "body": "The bug you hit is fixed."},
        headers=boss,
    )
    assert sent.status_code == 200 and sent.json()["seen_at"] is None
    assert (
        client.post(
            f"/api/v1/admin/users/{ada}/notify", json={"body": ""}, headers=boss
        ).status_code
        == 422
    )
    assert client.get("/api/v1/me/notifications").json()["items"] == []  # not Boss's note

    learner = login(client, subject="ada", name="Ada")
    items = client.get("/api/v1/me/notifications").json()["items"]
    assert [(i["title"], i["body"]) for i in items] == [("Fixed", "The bug you hit is fixed.")]
    seen = client.post(
        "/api/v1/me/notifications/seen", json={"ids": [items[0]["id"]]}, headers=learner
    )
    assert seen.status_code == 200
    assert client.get("/api/v1/me/notifications").json()["items"] == []

    boss = login(client, subject="boss", name="Boss")
    record = client.get(f"/api/v1/admin/users/{ada}", headers=boss).json()["notifications"]
    assert len(record) == 1 and record[0]["seen_at"]  # the admin sees it was read


def test_a_broadcast_reaches_every_account(client):  # noqa: F811
    _, boss = people(client)
    sent = client.post(
        "/api/v1/admin/notifications/broadcast", json={"body": "Maintenance at 9."}, headers=boss
    ).json()
    assert sent == {"sent": 2}
    with Session(client.app.state.engine) as db:
        assert len(db.scalars(select_all()).all()) == 2


def select_all():
    from sqlalchemy import select

    return select(UserNotification)


def test_sign_out_everywhere_and_delete(client):  # noqa: F811
    ada, boss = people(client)
    me = client.get("/api/v1/me", headers=boss).json()["id"]
    assert client.delete(f"/api/v1/admin/users/{me}", headers=boss).status_code == 409  # not self

    assert client.post(f"/api/v1/admin/users/{ada}/sign-out", headers=boss).json() == {"ended": 0}
    deleted = client.delete(f"/api/v1/admin/users/{ada}", headers=boss)
    assert deleted.status_code == 200 and deleted.json() == {"deleted": True}
    assert client.get(f"/api/v1/admin/users/{ada}", headers=boss).status_code == 404
    with Session(client.app.state.engine) as db:
        assert db.get(User, ada) is None
        kinds = {e.kind for e in db.query(AuditEvent).filter(AuditEvent.actor_id == me)}
        assert {"admin.user_signed_out", "admin.user_deleted"} <= kinds
        assert db.query(AuditEvent).filter(AuditEvent.actor_id == ada).count() == 0


def test_failed_generations_are_listed_with_who_and_why(client):  # noqa: F811
    ada, boss = people(client)
    with Session(client.app.state.engine) as db, db.begin():
        thread = AssistantThread(user_id=ada, scope="playground")
        db.add(thread)
        db.flush()
        for job_id, status, error in [
            ("job-1", "failed", "playground_generation_failed"),
            ("job-2", "ready", ""),
            ("job-3", "failed", "playground_generation_interrupted"),
        ]:
            db.add(
                PlaygroundJob(
                    id=job_id,
                    user_id=ada,
                    thread_id=thread.id,
                    prompt="Show me how binary search halves the range",
                    level="simple",
                    language="python",
                    status=status,
                    error=error,
                )
            )
    log = client.get("/api/v1/admin/generations/failed", headers=boss).json()
    assert {j["id"] for j in log["playground"]} == {"job-1", "job-3"}
    assert all(j["user"]["name"] == "Ada" and j["prompt"] for j in log["playground"])
    assert log["summary"]["last_day"] == {"failed": 2, "total": 3}
    assert {r["error"] for r in log["summary"]["reasons"]} == {
        "playground_generation_failed",
        "playground_generation_interrupted",
    }
    mine = client.get(f"/api/v1/admin/users/{ada}", headers=boss).json()["generations"]
    assert len(mine) == 3
