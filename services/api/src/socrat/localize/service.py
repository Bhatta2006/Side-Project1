"""Storing translations and laying them over a concept view.

A translation is shown only while it matches the English it came from (same hash). If the
lesson changed since, the learner sees the current English rather than a translation of old
text, and the admin queue lists it as stale. English is never replaced in storage.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.catalog.schema import Concept
from socrat.localize import glossary, locales, translate
from socrat.models import ContentTranslation, now


def save(
    db: Session, qualified: str, tag: str, concept: Concept, result: translate.Result
) -> ContentTranslation:
    """Store (or replace) a machine translation. A new text always starts unreviewed."""
    stamp = now()
    row = db.get(ContentTranslation, (qualified, tag))
    if row is None:
        row = ContentTranslation(concept=qualified, locale=tag, created_at=stamp)
        db.add(row)
    row.source_hash = translate.source_hash(translate.units_of(concept))
    row.units = result.units
    row.status, row.reviewer = "machine", None
    row.model, row.glossary_version = result.model, glossary.VERSION
    row.updated_at = stamp
    db.flush()
    return row


def current(db: Session, qualified: str, tag: str, concept: Concept) -> ContentTranslation | None:
    """The translation for this concept and locale if it still matches the English."""
    if tag == locales.DEFAULT or not locales.supported(tag):
        return None
    row = db.get(ContentTranslation, (qualified, tag))
    if row is None or row.source_hash != translate.source_hash(translate.units_of(concept)):
        return None
    return row


def overlay(db: Session, qualified: str, concept: Concept, tag: str, view: dict) -> dict:
    """``view`` with translated text where a current translation exists; code, numbers, keys,
    structure and every non-text field stay as the English source defined them."""
    row = current(db, qualified, tag, concept)
    if row is None:
        return {**view, "translation": None}
    u = row.units
    out = dict(view)
    for field in ("title", "summary", "lesson"):
        out[field] = u.get(field, view[field])
    out["key_points"] = [u.get(f"key_points.{i}", t) for i, t in enumerate(view["key_points"])]
    out["pitfalls"] = [u.get(f"pitfalls.{i}", t) for i, t in enumerate(view.get("pitfalls", []))]
    out["visuals"] = [
        {
            **v,
            **{
                f: u.get(f"visuals.{i}.{f}", v[f]) for f in ("purpose", "fallback_text", "alt_text")
            },
        }
        for i, v in enumerate(view.get("visuals", []))
    ]
    loc = locales.get(tag)
    out["translation"] = dict(
        locale=tag,
        status=row.status,  # machine | reviewed
        reviewer=row.reviewer,
        preview=loc.preview,
        rtl=loc.rtl,
    )
    return out


def stale(db: Session, catalog) -> list[dict]:
    """Stored translations whose English source has changed since."""
    out = []
    for row in db.scalars(select(ContentTranslation)):
        if row.concept not in catalog.concepts:
            continue
        concept = catalog.concept(row.concept)
        if row.source_hash != translate.source_hash(translate.units_of(concept)):
            out.append(dict(concept=row.concept, locale=row.locale, status=row.status))
    return out
