"""Learning Evidence Library and Pedagogical Strategist (master prompt 7.5, 8, 8.2)."""

# ruff: noqa: F811
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.catalog.registry import default_catalog
from socrat.engine import domains, evidence_library, strategy

CONCEPT = "zero:programs-and-output"


def test_every_technique_in_the_prompt_is_in_the_library_with_its_evidence():
    ids = {t.id for t in evidence_library.LIBRARY}
    assert len(ids) == 15  # the fifteen techniques of prompt 8.1
    for t in evidence_library.LIBRARY:
        for name in (
            "definition",
            "outcomes",
            "studied",
            "limits",
            "useful_when",
            "unsuitable_when",
            "rule",
            "measure",
        ):
            assert len(getattr(t, name)) > 10, (t.id, name)
        assert t.strength in {"high", "moderate", "mixed", "low"}
        assert t.references
    # Honest about its own status.
    assert evidence_library.REVIEWED_BY is None
    assert "not re-checked" in evidence_library.as_dict()["note"]
    assert "learning style" in evidence_library.AVOID[0][0]


def test_the_strategist_chooses_only_library_techniques_by_stage():
    concept = default_catalog().concept(CONCEPT)
    software = domains.ADAPTERS["software"]
    new = strategy.plan(concept, "unknown", software)
    ids = [t["id"] for t in new.techniques]
    assert {"worked-examples", "scaffolding", "retrieval", "feedback"} <= set(ids)
    assert new.guidance == "high" and "transfer" not in ids and "calibration" not in ids
    later = strategy.plan(concept, "proficient", software)
    later_ids = {t["id"] for t in later.techniques}
    assert {
        "transfer",
        "spacing",
        "cumulative-review",
    } <= later_ids and "worked-examples" not in later_ids
    assert later.guidance == "low"
    for p in (new, later):
        assert all(t["id"] in evidence_library.BY_ID and t["why"] for t in p.techniques)
    music = strategy.plan(concept, "developing", domains.ADAPTERS["music"])
    assert "deliberate-practice" in {t["id"] for t in music.techniques}
    assert "recording" in music.representation


def test_the_author_brief_carries_rules_and_forbids_learning_styles():
    concept = default_catalog().concept(CONCEPT)
    text = strategy.brief(strategy.plan(concept))
    assert evidence_library.VERSION in text and "Worked examples" in text
    assert "no learning styles" in text


def test_lesson_view_and_library_route(client):
    headers = login(client)
    onboard(client, headers)
    teaching = client.get(f"/api/v1/concepts/{CONCEPT}").json()["teaching"]
    assert teaching["stage"] == "unknown" and teaching["techniques"]
    assert all(set(t) == {"name", "why"} for t in teaching["techniques"])
    library = client.get("/api/v1/engine/strategies")
    assert library.status_code == 200 and "public" in library.headers["cache-control"]
    assert len(library.json()["techniques"]) == 15
