"""The architect plans a skeleton fast; each module's concept details are written in parallel,
and code repairs related-concept slips instead of rejecting the whole outline."""

import asyncio
import copy
import json

from test_coursegen import BRIEF, OUTLINE, admin  # noqa: F401
from test_learner_api import client, login, onboard  # noqa: F401

from socrat.assistant.gateway import Event, usage_event
from socrat.catalog.registry import default_catalog
from socrat.coursegen import jobs
from socrat.coursegen.outline import (
    ARCHITECT,
    DETAIL_FIELDS,
    DETAILER,
    Brief,
    skeleton_of,
    tidy,
    to_course,
)

PASS = json.dumps({"verdict": "pass", "summary": "Solid.", "issues": []})


def details_of(module: dict) -> str:
    return json.dumps(
        {
            "concepts": [
                {k: c[k] for k in ("id", *DETAIL_FIELDS) if k in c} for c in module["concepts"]
            ]
        }
    )


class Split:
    """Architect replies with a skeleton; the detailer answers per module from the full outline."""

    def __init__(self, skeleton: dict, full: dict, broken_first: set[str] = frozenset()):
        self.skeleton, self.full = skeleton, full
        self.broken = set(broken_first)
        self.calls: list[tuple[str, str]] = []
        self.active = self.peak = 0
        self.critic = PASS

    def make(self, settings):
        script = self

        class Provider:
            name = "anthropic"

            async def converse(self, system, turns, max_tokens, *args, **kwargs):
                prompt = turns[0].content
                if system == ARCHITECT:
                    script.calls.append(("architect", prompt))
                    text = json.dumps(script.skeleton)
                elif system == DETAILER:
                    asked = prompt.split("details of these concepts:")[1].split("A reviewer")[0]
                    module = next(
                        m for m in script.full["modules"] if f"Module {m['id']}:" in prompt
                    )
                    module = dict(
                        module,
                        concepts=[c for c in module["concepts"] if f'"id": "{c["id"]}"' in asked],
                    )
                    script.calls.append(("detail", module["id"]))
                    script.active += 1
                    script.peak = max(script.peak, script.active)
                    await asyncio.sleep(0.01)
                    script.active -= 1
                    if module["id"] in script.broken:
                        script.broken.discard(module["id"])
                        text = "not json"
                    else:
                        text = details_of(module)
                else:
                    script.calls.append(("critic", prompt))
                    text = script.critic
                yield Event("text", text=text)
                yield usage_event(100, 200)

        return Provider()


def two_modules() -> dict:
    full = copy.deepcopy(OUTLINE)
    first = full["modules"][0]
    full["modules"] = [
        dict(first, concepts=first["concepts"][:1]),
        dict(first, id="training", title="Training", concepts=first["concepts"][1:]),
    ]
    return full


def run(client, script):  # noqa: F811
    return asyncio.run(
        jobs.run_once(
            client.app.state.engine, client.app.state.settings, default_catalog(), script.make
        )
    )


def test_skeleton_then_parallel_details_make_the_outline(client, admin):  # noqa: F811
    full = two_modules()
    script = Split(skeleton_of(full), full)
    assert client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin).status_code == 200
    assert run(client, script)
    kinds = [k for k, _ in script.calls]
    assert kinds[0] == "architect" and sorted(kinds[1:]) == ["critic", "detail", "detail"]
    assert script.peak == 2  # both modules were written at the same time
    concepts = client.get("/api/v1/admin/courses/ai-basics").json()["course"]["concepts"]
    assert concepts[1]["outline"]["objectives"] == ["Explain loss with an example"]
    # The critic reviewed the skeleton while the details were being written.
    critic = next(p for k, p in script.calls if k == "critic")
    assert '"id": "loss"' in critic and "Explain loss with an example" not in critic


def test_a_module_with_an_unusable_reply_is_asked_once_more(client, admin):  # noqa: F811
    full = two_modules()
    script = Split(skeleton_of(full), full, broken_first={"training"})
    client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin)
    assert run(client, script)
    assert [k for k, _ in script.calls].count("detail") == 3
    assert client.get("/api/v1/admin/courses/ai-basics").json()["status"] == "review"


def test_tidy_drops_bad_related_links_and_keeps_good_ones():
    outline = copy.deepcopy(OUTLINE)
    loss = outline["modules"][0]["concepts"][1]  # needs what-is-ml
    loss["related"] = [
        "loss",
        "what-is-ml",
        "no-such-thing",
        "zero:programs-and-output",
        "zero:programs-and-output",
    ]
    tidy(outline, default_catalog())
    assert loss["related"] == ["zero:programs-and-output"]


def test_tidy_repairs_values_code_can_fix_instead_of_a_new_round():
    outline = copy.deepcopy(OUTLINE)
    loss = outline["modules"][0]["concepts"][1]
    loss.update(
        assessment=["quiz", "lab", "quiz"],
        evidence=["application", "vibes"],
        practice=["lab", "lab", "dancing"],
        category="skillful",
        expected="Builds and measures a circuit " * 20,
    )
    outline["modules"][0]["concepts"][0]["assessment"] = ["lab"]
    tidy(outline, default_catalog())
    assert loss["assessment"] == ["quiz"] and loss["evidence"] == ["application"]
    assert loss["practice"] == ["lab"] and "category" not in loss
    assert len(loss["expected"]) <= 300 and loss["expected"].endswith("…")
    assert outline["modules"][0]["concepts"][0]["assessment"] == ["quiz"]
    to_course(Brief.model_validate(BRIEF), outline)  # now valid


def test_one_review_keeps_the_revised_outline_without_a_second_critic(client, admin):  # noqa: F811
    client.app.state.settings.gen_outline_reviews = 1
    full = two_modules()
    script = Split(skeleton_of(full), full)
    script.critic = json.dumps(
        {
            "verdict": "revise",
            "summary": "Thin.",
            "issues": [{"where": "loss", "problem": "Vague", "fix": "Sharpen"}],
        }
    )
    client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin)
    assert run(client, script)
    kinds = [k for k, _ in script.calls]
    assert [kinds.count(k) for k in ("architect", "detail", "critic")] == [2, 4, 1]
    revised = [p for k, p in script.calls if k == "architect"][1]
    assert "loss: Vague Fix: Sharpen" in revised
    detail = client.get("/api/v1/admin/courses/ai-basics").json()
    assert detail["status"] == "review"
    assert any(e.get("event") == "kept_after_review" for e in detail["jobs"][0]["log"])


def test_a_large_module_is_detailed_in_small_parallel_chunks(client, admin):  # noqa: F811
    from test_coursegen import concept

    full = copy.deepcopy(OUTLINE)
    first = full["modules"][0]
    first["concepts"] = [concept("what-is-ml", ["zero:programs-and-output"])] + [
        concept(f"step-{i}", ["what-is-ml"]) for i in range(9)
    ]
    full["levels"][1]["start_concept"] = "step-0"
    script = Split(skeleton_of(full), full)
    client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin)
    assert run(client, script)
    assert [k for k, _ in script.calls].count("detail") == 3  # 10 concepts, 4 per call
    assert script.peak == 3
    concepts = client.get("/api/v1/admin/courses/ai-basics").json()["course"]["concepts"]
    assert all(c["outline"]["objectives"] for c in concepts) and len(concepts) == 10


def test_an_advisory_review_is_logged_but_never_triggers_a_rewrite(client, admin):  # noqa: F811
    client.app.state.settings.gen_outline_reviews = 0
    full = two_modules()
    script = Split(skeleton_of(full), full)
    script.critic = json.dumps({"verdict": "revise", "summary": "Thin.", "issues": []})
    client.post("/api/v1/admin/courses/briefs", json=BRIEF, headers=admin)
    assert run(client, script)
    kinds = [k for k, _ in script.calls]
    assert [kinds.count(k) for k in ("architect", "detail", "critic")] == [1, 2, 1]
    log = client.get("/api/v1/admin/courses/ai-basics").json()["jobs"][0]["log"]
    assert [e.get("verdict") for e in log if e["role"] == "critic"] == ["revise"]
    assert any(e.get("event") == "kept_after_review" for e in log)


def test_tidy_keeps_only_what_the_studio_supports():
    outline = copy.deepcopy(OUTLINE)
    outline["shape"] = dict(
        studio="drawing-studio", loop="sketch", evidence=["portfolio"], tools=["editor"]
    )
    tidy(outline, default_catalog())
    assert outline["shape"] == dict(
        studio="reading", loop="read-reflect", evidence=["quiz"], tools=[]
    )
    outline["shape"] = dict(
        studio="lab",
        loop="derive",
        evidence=["numeric", "tests", "numeric"],
        tools=["simulation", "cas"],
    )
    tidy(outline, default_catalog())
    assert outline["shape"] == dict(
        studio="lab", loop="solve", evidence=["numeric"], tools=["simulation"]
    )
