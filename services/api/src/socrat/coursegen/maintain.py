"""Course Maintainer: keep released generated courses healthy without a model and without
touching what learners have done.

What it does, all deterministic:
- checks every resource link of released concepts on a schedule; a link is *dead* only after
  repeated failures over several days, never after one blip;
- drops a dead link when at least two good ones remain (a new version; the old is kept);
- lists what it cannot fix alone (fewer than two good links left, ageing lessons, resources
  learners keep marking unhelpful) in a queue for the owner, who can revise (the existing
  quarantine rewrite), roll back to a kept version, or leave it;
- never rewrites prose, never deletes evidence, and every change is a recorded version.

Progress is keyed by concept id, so a new version of a concept keeps every learner's state.
``lost_ids`` states which quiz/problem/exercise ids a rewrite would orphan.
"""

import logging

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog import generated
from socrat.catalog.atoms import AtomPack
from socrat.catalog.registry import Catalog
from socrat.catalog.schema import Concept
from socrat.config import Settings
from socrat.coursegen import jobs, links
from socrat.learn import resources
from socrat.models import ConceptVersion, GeneratedConcept, GeneratedCourse, ResourceHealth, need

log = logging.getLogger(__name__)

DAY = 86400
DEAD_AFTER_FAILURES = 3  # consecutive failed checks ...
DEAD_AFTER_SECONDS = 2 * DAY  # ... spread over at least this long
CODE_REVIEW_DAYS = 180  # lessons with code age faster than the rest
MIN_RESOURCES = 2  # what a live concept needs
DOWNVOTES = 3  # learners marking a resource unhelpful before it is listed


def _live(db: Session) -> list[tuple[GeneratedConcept, Concept, list[str]]]:
    """Released concepts of published, unremoved generated courses (with the course languages)."""
    out = []
    rows = db.execute(
        select(GeneratedConcept, GeneratedCourse)
        .join(GeneratedCourse, GeneratedCourse.id == GeneratedConcept.course_id)
        .where(GeneratedCourse.status == "published", GeneratedCourse.moderation != "removed")
    )
    for row, course in rows:
        if row.payload.get("status") != "live":
            continue
        out.append(
            (row, Concept.model_validate(row.payload), list(course.payload.get("languages", [])))
        )
    return out


def _key(row: GeneratedConcept) -> str:
    return f"{row.course_id}:{row.concept_id}"


def lost_ids(old: Concept, new: Concept) -> list[str]:
    """Quiz, problem and exercise ids of ``old`` that ``new`` neither keeps nor lists as a
    former id: stored attempts against them would no longer resolve."""
    kept = {q.id for q in new.quiz} | {i for q in new.quiz for i in q.former_ids}
    lost = [f"quiz:{q.id}" for q in old.quiz if not any(q.matches(i) for i in kept)]
    lost += [f"problem:{p}" for p in old.problems if p not in new.problems]
    kept_ex = {e.id for e in new.exercises}
    lost += [f"exercise:{e.id}" for e in old.exercises if e.id not in kept_ex]
    return lost


# ---------------------------------------------------------------- link health


async def check_links(
    engine, now: int, batch: int = 200, http: httpx.AsyncClient | None = None
) -> dict:
    """Check up to ``batch`` resource links, least recently checked first, and record each
    result. Network only; no model, no cost."""
    with Session(engine) as db:
        wanted = [(_key(row), str(r.url)) for row, c, _ in _live(db) for r in c.resources]
        seen = {(h.concept, h.url): h.last_checked_at for h in db.scalars(select(ResourceHealth))}
    wanted.sort(key=lambda pair: seen.get(pair, 0))
    chosen = wanted[:batch]
    bad = set(await links.broken(sorted({url for _, url in chosen}), http))
    with Session(engine) as db, db.begin():
        for concept, url in chosen:
            row = db.get(ResourceHealth, (concept, url))
            if row is None:
                row = ResourceHealth(
                    concept=concept, url=url, last_checked_at=now, failures=0, status="ok"
                )
                db.add(row)
            row.last_checked_at = now
            if url in bad:
                row.failures += 1
                row.first_failed_at = row.first_failed_at or now
                dead = (
                    row.failures >= DEAD_AFTER_FAILURES
                    and now - row.first_failed_at >= DEAD_AFTER_SECONDS
                )
                row.status = "dead" if dead else "failing"
            else:
                row.failures, row.first_failed_at, row.last_ok_at, row.status = 0, None, now, "ok"
    return {"checked": len(chosen), "failed": len([1 for _, u in chosen if u in bad])}


def dead_links(db: Session) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for h in db.scalars(select(ResourceHealth).where(ResourceHealth.status == "dead")):
        out.setdefault(h.concept, set()).add(h.url)
    return out


def repair(db: Session, base: Catalog) -> list[dict]:
    """Drop dead links where at least two good ones remain, as a new version of the concept.
    Returns what it changed. No commit."""
    dead = dead_links(db)
    changed = []
    for row, concept, _ in _live(db):
        gone = dead.get(_key(row), set())
        if not gone or concept.status != "live":
            continue
        kept = [r for r in concept.resources if str(r.url) not in gone]
        if len(kept) == len(concept.resources) or len(kept) < MIN_RESOURCES:
            continue
        provenance = concept.provenance
        bumped = (
            provenance.model_copy(update={"version": provenance.version + 1})
            if provenance
            else None
        )
        fixed = concept.model_copy(update={"resources": kept, "provenance": bumped})
        pack = AtomPack.model_validate(row.atoms) if row.atoms else None
        key = _key(row)
        generated.store_concept(db, base, row.course_id, fixed, pack, reason="dead-link")
        for url in gone:
            health = db.get(ResourceHealth, (key, url))
            if health is not None:
                db.delete(health)
        changed.append(dict(concept=key, removed=sorted(gone)))
    return changed


# ---------------------------------------------------------------- what needs a person


def attention(db: Session, now: int, review_days: int) -> dict[str, list[dict]]:
    """Everything the maintainer will not decide alone."""
    dead = dead_links(db)
    failing = [
        dict(concept=h.concept, url=h.url, failures=h.failures)
        for h in db.scalars(select(ResourceHealth).where(ResourceHealth.status == "failing"))
    ]
    stuck, stale, downvoted = [], [], []
    for row, concept, languages in _live(db):
        key = _key(row)
        good = [r for r in concept.resources if str(r.url) not in dead.get(key, set())]
        if len(good) < MIN_RESOURCES and key in dead:
            stuck.append(
                dict(concept=key, dead=sorted(dead[key]), good=len(good), needs=MIN_RESOURCES)
            )
        age_days = (now - row.updated_at) // DAY
        limit = min(review_days, CODE_REVIEW_DAYS) if languages else review_days
        if age_days >= limit:
            stale.append(dict(concept=key, age_days=age_days, review_after_days=limit))
        for url, (up, down) in resources.community(db, key).items():
            if down >= DOWNVOTES and down > 2 * up:
                downvoted.append(dict(concept=key, url=url, helpful=up, unhelpful=down))
    return dict(dead_without_replacement=stuck, failing=failing, stale=stale, unhelpful=downvoted)


def history(db: Session, course_id: str, concept_id: str) -> list[dict]:
    rows = db.scalars(
        select(ConceptVersion)
        .where(ConceptVersion.course_id == course_id, ConceptVersion.concept_id == concept_id)
        .order_by(ConceptVersion.created_at.desc(), ConceptVersion.id)
    )
    return [
        dict(id=v.id, version=v.version, reason=v.reason, created_at=v.created_at) for v in rows
    ]


def rollback(db: Session, base: Catalog, course_id: str, concept_id: str, version_id: str) -> dict:
    """Make a kept version the current one again. The current version is kept first, so a
    rollback can itself be undone. Refused while the concept is being rewritten.
    Returns what changed. No commit."""
    old = db.get(ConceptVersion, version_id)
    if old is None or (old.course_id, old.concept_id) != (course_id, concept_id):
        raise LookupError("no such version")
    row = need(db.get(GeneratedConcept, (course_id, concept_id)))
    if jobs.active(db, course_id, concept_id) is not None:
        raise RuntimeError("being rewritten")
    current = Concept.model_validate(row.payload)
    restored = Concept.model_validate(old.payload)
    pack = AtomPack.model_validate(old.atoms) if old.atoms else None
    problems = None
    if old.problems is not None:
        from socrat.catalog.schema import Problem

        problems = [Problem.model_validate(p) for p in old.problems]
    generated.store_concept(
        db,
        base,
        course_id,
        restored,
        pack,
        problems if problems is not None else [],
        reason="rollback",
    )
    return dict(
        concept=f"{course_id}:{concept_id}",
        restored_version=old.version,
        lost=lost_ids(current, restored) if current.status == "live" else [],
    )


# ---------------------------------------------------------------- the sweep


async def sweep(
    engine, settings: Settings, base: Catalog, now: int, http: httpx.AsyncClient | None = None
) -> dict:
    """One maintenance pass: check a batch of links, then repair what is certain."""
    checked = await check_links(engine, now, settings.maintainer_batch, http)
    with Session(engine) as db, db.begin():
        changed = repair(db, base)
    for item in changed:
        log.warning("maintainer removed dead links from %s: %s", item["concept"], item["removed"])
    return {**checked, "repaired": changed}
