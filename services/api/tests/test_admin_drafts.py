"""Content review queue: validate, request changes, approve into the course."""

from pathlib import Path

import content_fixture
import yaml
from test_learner_api import client, login  # noqa: F401  (client is a fixture)
from test_validate import problem


def setup(client, tmp_path: Path) -> tuple[dict, Path, Path]:  # noqa: F811
    # The synthetic packs (basics, algo): no course ships with the app any more.
    courses = tmp_path / "courses"
    content_fixture.write(courses, tmp_path / "tests")
    drafts = tmp_path / "drafts" / "basics"
    drafts.mkdir(parents=True)
    draft = problem(id="triangle-total", concepts=["loops"])
    (drafts / "triangle-total.yaml").write_text(
        yaml.safe_dump(draft, sort_keys=False), encoding="utf-8"
    )
    settings = client.app.state.settings
    settings.content_courses_dir = str(courses)
    settings.content_drafts_dir = str(tmp_path / "drafts")
    settings.admin_subjects = ["editor"]
    return login(client, subject="editor", name="Grace Editor"), courses, drafts


def test_only_admins_see_the_queue(client, tmp_path):  # noqa: F811
    setup(client, tmp_path)
    login(client, subject="someone", name="Someone")
    assert client.get("/api/v1/admin/drafts").status_code == 403


def test_failing_gates_block_approval(client, tmp_path):  # noqa: F811
    headers, _, drafts = setup(client, tmp_path)
    path = drafts / "triangle-total.yaml"
    broken = problem(id="triangle-total", concepts=["loops"], brute="print(0)")
    path.write_text(yaml.safe_dump(broken, sort_keys=False), encoding="utf-8")
    checked = client.post("/api/v1/admin/drafts/triangle-total/validate", headers=headers).json()
    assert checked["status"] == "failing"
    blocked = client.post("/api/v1/admin/drafts/triangle-total/approve", json={}, headers=headers)
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "gates_failing"
    assert client.get("/api/v1/admin/drafts/../secrets").status_code == 404


def test_review_decisions_need_the_csrf_token(client, tmp_path):  # noqa: F811
    headers, _, _ = setup(client, tmp_path)
    no_token = {"Origin": headers["Origin"]}
    for action in ("validate", "approve", "request-changes"):
        response = client.post(
            f"/api/v1/admin/drafts/triangle-total/{action}", json={"notes": "x"}, headers=no_token
        )
        assert response.status_code == 403 and response.json()["error"]["code"] == "csrf_rejected"
