"""Two first requests at once must not build the adaptive item bank together."""

import threading

from test_learner_api import client, login, onboard  # noqa: F401

from socrat.quiz import service


def test_concurrent_first_sessions_share_one_bank_build(client):  # noqa: F811
    headers = login(client, subject="race")
    onboard(client, headers)
    service._BANKS.clear()  # cold start, as on a fresh server
    statuses: list[int] = []

    def start():
        response = client.post(
            "/api/v1/adaptive-quiz/sessions",
            json={"mode": "concept_check", "concepts": ["zero:programs-and-output"]},
            headers=headers,
        )
        statuses.append(response.status_code)

    threads = [threading.Thread(target=start) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert statuses == [200, 200, 200]
