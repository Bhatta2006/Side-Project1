"""Curated reading, personalised: each learner sees the few resources that fit them now.

Resources are ranked by how well their level fits the learner's band on the concept, by
how helpful other learners found them (Bayesian-smoothed so a single vote cannot swing
it), and by this learner's own history (unhelpful ones sink, already-read ones step back).
"""

import json
from functools import cache

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from socrat.catalog.registry import REPO_ROOT
from socrat.catalog.schema import Concept
from socrat.models import ResourceEvent, ResourceHealth

PICKS = 3
TARGET_LEVEL = {
    "not_started": "intro",
    "needs_practice": "intro",
    "developing": "core",
    "likely_known": "deep",
    "strong": "deep",
}
LEVEL_ORDER = ["intro", "core", "deep"]


@cache
def course_links() -> dict:
    return json.loads(
        (REPO_ROOT / "content" / "learning-resources.json").read_text(encoding="utf-8")
    )["concepts"]


def selected(concept: str, language: str, kind: str) -> list[dict]:
    return [
        item
        for item in course_links().get(concept, {}).get(kind, [])
        if item.get("language") in {None, language}
    ]


def community(db: Session, concept: str) -> dict[str, tuple[int, int]]:
    rows = db.execute(
        select(ResourceEvent.url, ResourceEvent.helpful, func.count())
        .where(ResourceEvent.concept == concept, ResourceEvent.helpful.is_not(None))
        .group_by(ResourceEvent.url, ResourceEvent.helpful)
    )
    votes: dict[str, list[int]] = {}
    for url, helpful, count in rows:
        votes.setdefault(url, [0, 0])[0 if helpful else 1] += count
    return {url: (up, down) for url, (up, down) in votes.items()}


def personalised(
    db: Session, user_id: str, concept_id: str, concept: Concept, language: str, band: str
) -> list[dict]:
    mine = {
        e.url: e
        for e in db.scalars(
            select(ResourceEvent).where(
                ResourceEvent.user_id == user_id, ResourceEvent.concept == concept_id
            )
        )
    }
    votes = community(db, concept_id)
    # Links the maintainer found dead are not offered while a person decides what replaces them.
    dead = set(
        db.scalars(
            select(ResourceHealth.url).where(
                ResourceHealth.concept == concept_id, ResourceHealth.status == "dead"
            )
        )
    )
    target = LEVEL_ORDER.index(TARGET_LEVEL.get(band, "core"))
    scored = []
    for index, r in enumerate(concept.resources):
        if r.languages and language not in r.languages:
            continue
        url = str(r.url)
        if url in dead:
            continue
        event = mine.get(url)
        up, down = votes.get(url, (0, 0))
        score = 3 - abs(LEVEL_ORDER.index(r.level) - target) * 1.5
        score += 2 * (up + 1) / (up + down + 2)
        if event is not None and event.helpful is False:
            score -= 6
        if event is not None and event.opened_at:
            score -= 1
        scored.append((-score, index, r, event))
    scored.sort(key=lambda x: (x[0], x[1]))
    return [
        dict(
            r.model_dump(mode="json"),
            picked=rank < PICKS,
            opened=bool(event and event.opened_at),
            helpful=event.helpful if event else None,
        )
        for rank, (_, _, r, event) in enumerate(scored)
    ]


def record(
    db: Session, user_id: str, concept_id: str, concept: Concept, url: str, action: str, now: int
) -> dict:
    if url not in {str(r.url) for r in concept.resources}:
        raise HTTPException(404, "not_found")
    event = db.scalar(
        select(ResourceEvent).where(
            ResourceEvent.user_id == user_id,
            ResourceEvent.concept == concept_id,
            ResourceEvent.url == url,
        )
    )
    if event is None:
        event = ResourceEvent(user_id=user_id, concept=concept_id, url=url)
        db.add(event)
    if action == "open":
        event.opened_at = now
    else:
        event.helpful = action == "helpful"
    event.updated_at = now
    return {"opened": bool(event.opened_at), "helpful": event.helpful}
