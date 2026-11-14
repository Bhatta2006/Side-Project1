"""Setup and placement run as a guest; signing in afterwards keeps the plan."""

from test_learner_api import ORIGIN, client, login, onboard  # noqa: F401


def guest(client):
    response = client.post("/api/v1/auth/guest", headers={"Origin": ORIGIN})
    assert response.status_code == 200
    me = client.get("/api/v1/me").json()
    assert me["guest"] is True
    return {"Origin": ORIGIN, "X-CSRF-Token": me["csrf_token"]}


def test_guest_plan_moves_to_the_new_account(client):  # noqa: F811
    headers = guest(client)
    enrollment = onboard(client, headers, course="dsa", level="knows-basics")
    plan_id = enrollment["enrollment"]["id"] if "enrollment" in enrollment else enrollment["id"]

    login(client, subject="grace", name="Grace")
    me = client.get("/api/v1/me").json()
    assert me["guest"] is False
    assert me["birth_year"] == 2001
    assert me["timezone"] == "Asia/Kolkata"
    assert me["enrollment"]["id"] == plan_id


def test_returning_learner_keeps_their_own_plan(client):  # noqa: F811
    headers = login(client, subject="ada", name="Ada")
    own = onboard(client, headers)
    own_id = own["enrollment"]["id"] if "enrollment" in own else own["id"]
    client.post("/api/v1/auth/logout", headers=headers)

    headers = guest(client)
    onboard(client, headers, course="dsa", level="knows-basics")
    login(client, subject="ada", name="Ada")
    me = client.get("/api/v1/me").json()
    assert me["enrollment"]["id"] == own_id
