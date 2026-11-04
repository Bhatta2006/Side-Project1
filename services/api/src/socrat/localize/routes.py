"""Locale catalogue for everyone; translation management for the owner."""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.admin.routes import require_admin
from socrat.assistant.gateway import ProviderError
from socrat.database import record_event
from socrat.learn.routes import catalog, engine
from socrat.localize import locales, service, translate
from socrat.models import ContentTranslation, now

public = APIRouter(prefix="/api/v1/locales")
admin = APIRouter(prefix="/api/v1/admin/translations")
make = None  # replaced in tests; None uses the configured provider


class Translate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    concept: str
    locale: str


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewer: str = Field(min_length=5, max_length=80)  # a full, real name


@public.get("")
def list_locales(request: Request):
    """Locales and, from the Accept-Language header, the one to suggest."""
    return dict(
        items=[asdict(loc) for loc in locales.LOCALES.values()],
        suggested=locales.negotiate(request.headers.get("accept-language", "")),
    )


@admin.post("")
async def create(body: Translate, request: Request):
    cat = catalog()
    if body.concept not in cat.concepts:
        raise HTTPException(404, "not_found")
    if not locales.supported(body.locale) or body.locale == locales.DEFAULT:
        raise HTTPException(422, "unsupported_locale")
    eng = engine(request)
    with Session(eng) as db:
        user = require_admin(request, db, write=True)
        user_id = user.id
    concept = cat.concept(body.concept)
    if concept.status != "live":
        raise HTTPException(409, "concept_not_ready")
    try:
        result = await translate.translate(
            eng, request.app.state.settings, concept, body.locale, make, user_id
        )
    except ProviderError as exc:
        raise HTTPException(503, "translation_unavailable") from exc
    except translate.TranslationError as exc:
        raise HTTPException(422, "translation_rejected") from exc
    with Session(eng) as db, db.begin():
        row = service.save(db, body.concept, body.locale, concept, result)
        record_event(db, user_id, "translation.saved", f"{body.concept}:{body.locale}")
        return dict(concept=row.concept, locale=row.locale, status=row.status, rounds=result.rounds)


@admin.get("")
def queue(request: Request):
    """Everything stored, with stale ones flagged, machine-only first."""
    cat = catalog()
    with Session(engine(request)) as db:
        require_admin(request, db)
        stale = {(s["concept"], s["locale"]) for s in service.stale(db, cat)}
        rows = db.scalars(select(ContentTranslation).order_by(ContentTranslation.status)).all()
        return {
            "items": [
                dict(
                    concept=r.concept,
                    locale=r.locale,
                    status=r.status,
                    reviewer=r.reviewer,
                    model=r.model,
                    stale=(r.concept, r.locale) in stale,
                )
                for r in rows
            ]
        }


@admin.post("/{concept}/{locale}/review")
def review(concept: str, locale: str, body: Review, request: Request):
    """A named person confirms one translation. One at a time by design: no bulk approval."""
    with Session(engine(request)) as db, db.begin():
        user = require_admin(request, db, write=True)
        row = db.get(ContentTranslation, (concept, locale))
        if row is None:
            raise HTTPException(404, "not_found")
        row.status, row.reviewer, row.updated_at = "reviewed", body.reviewer.strip(), now()
        record_event(db, user.id, "translation.reviewed", f"{concept}:{locale}")
        return dict(concept=concept, locale=locale, status=row.status, reviewer=row.reviewer)
