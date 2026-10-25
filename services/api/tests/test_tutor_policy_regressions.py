"""Neither client effort claims nor a transient stream may bypass tutor policy."""

import asyncio
import json

from sqlalchemy.orm import Session
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant.gateway import Event
from socrat.assistant.service import TurnPlan, stream_reply
from socrat.catalog.registry import default_catalog
from socrat.config import Settings
from socrat.models import Submission


def test_a_claimed_attempt_does_not_advance_the_ladder_and_a_real_run_counts_once(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)

    def ask():
        response = client.post(
            "/api/v1/assistant/messages",
            json={"scope": "problem:time-convert", "new_attempt": True},
            headers=headers,
        )
        response.raise_for_status()
        events = [
            json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")
        ]
        return events[0]["allowed_level"]

    assert [ask() for _ in range(4)] == [0, 0, 0, 0]
    user = client.get("/api/v1/me").json()["id"]
    with Session(client.app.state.engine) as db, db.begin():
        db.add(
            Submission(
                user_id=user,
                problem_id="time-convert",
                language="python",
                mode="run",
                source="print(1)",
                status="done",
                verdict="executed",
                manifest={},
                signature="x" * 64,
                tests=[],
            )
        )
    assert ask() == 1
    assert ask() == 1


def test_protected_approach_never_appears_in_a_stream_delta():
    problem = default_catalog().problem("time-convert")
    secret = problem.approach.split(". ")[0]

    class Provider:
        name = "synthetic"

        async def converse(self, *args):
            yield Event("text", "<level>1</level>" + secret)
            yield Event("text", ". Try implementing that.")

    async def run():
        plan = TurnPlan("thread", "problem:time-convert", 1, problem, [], "Safe hint")
        return [item async for item in stream_reply(Provider(), plan, Settings(environment="test"))]

    events = asyncio.run(run())
    assert secret not in "".join(data.get("text", "") for event, data in events if event == "delta")
    assert events[-1][0] == "done"
    assert events[-1][1]["provider"] == "curated"
    assert events[-1][1]["reason"] == "leak_guard"
