"""The streak upgrade (item 5): a save for a streak about to break, earn-back, a goal and a
calendar. All derived from minutes per day; with the switch off nothing changes."""

# ruff: noqa: F811
from datetime import date, timedelta

import pytest
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.config import Settings
from socrat.learn import streaks

EVERY_DAY = set(range(7))
START = date(2026, 11, 1)  # a Sunday
GOAL = 10


def d(day: int) -> date:
    return date(2026, 11, day)


def run(minutes: dict[int, int], today: int, extras: bool = True) -> dict:
    return streaks.compute(
        {d(k): v for k, v in minutes.items()}, d(today), EVERY_DAY, START, GOAL, extras
    )


# The rules


def test_switched_off_a_missed_day_still_breaks_the_streak_as_before():
    out = run({2: 15, 3: 15, 4: 15, 6: 15}, today=7, extras=False)
    assert out["current"] == 1 and out["longest"] == 3
    assert "saved" not in out and "earn_back" not in out


def test_a_streak_of_three_about_to_break_is_saved_once_a_month():
    out = run({2: 15, 3: 15, 4: 15, 6: 15}, today=7)
    assert out["current"] == 4  # the save keeps it going but is not a studied day
    assert out["saved"] == [d(5).isoformat()]
    # Short days, so no week goal banks a freeze and no day is long enough to earn one back.
    short = {**{k: 5 for k in (2, 3, 4)}, **{k: 5 for k in range(6, 16)}, 17: 5}
    later = run(short, today=18)
    assert later["saved"] == [d(5).isoformat()]  # the 16th is not saved again within 30 days
    assert later["current"] == 1


def test_ten_minutes_soon_after_a_missed_day_earns_it_back():
    kept = run({2: 15, 3: 15, 5: 12}, today=6)
    assert kept["current"] == 3 and kept["repaired"] == [d(4).isoformat()]
    short = run({2: 15, 3: 15, 5: 5}, today=6)
    assert short["current"] == 1 and short["repaired"] == []


def test_the_offer_stands_until_done_and_today_can_complete_it():
    waiting = run({2: 15, 3: 15}, today=5)
    assert waiting["current"] == 0
    assert waiting["earn_back"] == {
        "missed": d(4).isoformat(),
        "by": d(6).isoformat(),
        "keep": 2,
        "minutes": streaks.REPAIR_MINUTES,
        "done_today": 0,
    }
    started = run({2: 15, 3: 15, 5: 4}, today=5)
    assert started["earn_back"]["done_today"] == 4 and started["current"] == 1
    done = run({2: 15, 3: 15, 5: 10}, today=5)
    assert done["earn_back"] is None and done["repaired_today"] is True
    assert done["current"] == 3


def test_no_earn_back_after_two_missed_study_days_or_after_the_window():
    assert run({2: 15, 3: 15, 6: 20}, today=7)["current"] == 1
    late = run({2: 15, 3: 15}, today=7)
    assert late["earn_back"] is None and late["current"] == 0


def test_rest_days_neither_break_nor_need_repair():
    weekdays = {0, 1, 2, 3, 4}  # Monday to Friday
    out = streaks.compute({d(6): 15, d(9): 15}, d(10), weekdays, START, GOAL, True)
    assert out["current"] == 2 and out["repaired"] == [] and out["saved"] == []


def test_the_calendar_labels_every_day_of_the_month(monkeypatch):
    monkeypatch.setattr(streaks, "EXTRAS", True)
    minutes = {d(2): 15, d(3): 15, d(4): 15, d(6): 15}
    days = streaks.calendar(minutes, d(7), {0, 1, 2, 3, 4, 5}, d(2), GOAL, d(1))
    status = {x["day"]: x["status"] for x in days}
    assert len(days) == 30
    assert status[d(1).isoformat()] == "none"  # before the course
    late = streaks.calendar({d(4): 15}, d(5), EVERY_DAY, d(1), GOAL, d(1))
    assert [x["status"] for x in late[:5]] == ["none", "none", "none", "studied", "today"]
    assert status[d(5).isoformat()] == "saved"
    assert status[d(7).isoformat()] == "today"
    assert status[d(8).isoformat()] == "future"  # a Sunday, not a study day
    assert status[d(9).isoformat()] == "planned"
    assert [x["minutes"] for x in days[1:4]] == [15, 15, 15]


# The endpoints


@pytest.fixture
def enabled(client, monkeypatch):
    settings = client.app.state.settings
    settings.streak_plus_enabled = True
    monkeypatch.setattr(streaks, "EXTRAS", True)
    yield client
    settings.streak_plus_enabled = False


def test_defaults_off_and_hidden(client):
    assert Settings().streak_plus_enabled is False
    assert streaks.EXTRAS is False
    assert client.get("/api/v1/features").json()["streak_plus"] is False
    headers = login(client)
    onboard(client, headers)
    assert client.get("/api/v1/streak", headers=headers).status_code == 404
    assert client.put("/api/v1/streak/goal", json={"days": 7}, headers=headers).status_code == 404
    today = client.get("/api/v1/today", headers=headers).json()
    assert "earn_back" not in today["streak"] and "goal" not in today["streak"]


def test_commit_to_a_goal_and_change_your_mind(enabled):
    client = enabled
    headers = login(client)
    onboard(client, headers)
    first = client.get("/api/v1/streak", headers=headers).json()
    assert first["goal"] is None and first["goals"] == [7, 14, 30]

    set_ = client.put("/api/v1/streak/goal", json={"days": 14}, headers=headers)
    assert set_.status_code == 200 and set_.json()["goal"] == {"days": 14, "reached": False}
    assert client.get("/api/v1/streak", headers=headers).json()["goal"]["days"] == 14
    assert client.put("/api/v1/streak/goal", json={"days": 10}, headers=headers).status_code == 422
    assert client.delete("/api/v1/streak/goal", headers=headers).json() == {"goal": None}
    assert client.get("/api/v1/streak", headers=headers).json()["goal"] is None


def test_setting_a_goal_needs_the_csrf_token(enabled):
    client = enabled
    headers = login(client)
    onboard(client, headers)
    bare = {"Origin": headers["Origin"]}
    assert client.put("/api/v1/streak/goal", json={"days": 7}, headers=bare).status_code == 403


def test_the_calendar_covers_course_months_only(enabled):
    client = enabled
    headers = login(client)
    onboard(client, headers)
    this = client.get("/api/v1/streak/calendar", headers=headers).json()
    assert this["month"] == this["earliest"] == this["latest"]
    assert 28 <= len(this["days"]) <= 31
    first = date.fromisoformat(this["days"][0]["day"])
    before = (first - timedelta(days=1)).isoformat()[:7]
    response = client.get(f"/api/v1/streak/calendar?month={before}", headers=headers)
    assert response.status_code == 404
    assert client.get("/api/v1/streak/calendar?month=2026-13", headers=headers).status_code == 422


def test_day_one_offers_a_goal_at_the_end_of_the_session(enabled):
    client = enabled
    client.app.state.settings.session_end_enabled = True
    try:
        headers = login(client)
        onboard(client, headers)
        lesson = "lesson:basics:values"
        assert client.post(f"/api/v1/activities/{lesson}/complete", headers=headers).json()[
            "completed"
        ]
        screens = client.post(
            "/api/v1/session-end", json={"activity": lesson}, headers=headers
        ).json()["screens"]
        streak = next(s for s in screens if s["kind"] == "streak")
        assert streak["first_day"] is True
        assert streak["offer_goal"] == [7, 14, 30] and streak["goal"] is None
        assert streak["earned_back"] is False
        assert all(day["kept"] is None for day in streak["week"])
    finally:
        client.app.state.settings.session_end_enabled = False


def test_the_end_screen_week_marks_kept_days(monkeypatch):
    from socrat.learn import session_end

    week = [{"day": d(k).isoformat(), "studied": k == 17} for k in (16, 17, 18)]
    streak = {"frozen": [d(16).isoformat()], "saved": [], "repaired": [d(18).isoformat()]}
    monkeypatch.setattr(streaks, "EXTRAS", False)
    assert session_end._kept(week, streak) == week
    monkeypatch.setattr(streaks, "EXTRAS", True)
    assert [x["kept"] for x in session_end._kept(week, streak)] == ["frozen", None, "repaired"]
