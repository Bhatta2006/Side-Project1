"""Field performance: browsers report Core Web Vitals, the owner sees p75 per page.

Samples carry no user, session or URL — only a route pattern, the metric, its value and
a coarse device class — so they are collected without consent prompts. The endpoint
accepts same-origin beacons only, bounds every value and caps batch size.
"""

from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from socrat.models import WebVital

router = APIRouter(prefix="/api/v1")

ROUTES = {
    "/",
    "/login",
    "/start",
    "/placement",
    "/today",
    "/plan",
    "/assessments",
    "/progress",
    "/settings",
    "/admin",
    "/learn/[...concept]",
    "/problems/[id]",
    "/quiz/[...activity]",
}
# Upper bounds (ms, or unitless for CLS) beyond which a sample is noise, not a page view.
LIMITS = {"LCP": 60_000, "INP": 20_000, "CLS": 10.0, "FCP": 60_000, "TTFB": 60_000}
# Google's "good" thresholds at the 75th percentile; the page budgets.
BUDGETS = {"LCP": 2500, "INP": 200, "CLS": 0.1}


class Sample(BaseModel):
    route: str = Field(max_length=80)
    metric: Literal["LCP", "INP", "CLS", "FCP", "TTFB"]
    value: float = Field(ge=0)
    device: Literal["mobile", "desktop"]


class Batch(BaseModel):
    samples: list[Sample] = Field(min_length=1, max_length=10)


@router.post("/vitals", status_code=204)
async def collect(request: Request):
    settings = request.app.state.settings
    if request.headers.get("origin") != settings.public_origin.rstrip("/"):
        raise HTTPException(403, "origin_rejected")
    # sendBeacon posts text/plain to avoid a preflight, so parse the body ourselves.
    try:
        batch = Batch.model_validate_json(await request.body())
    except ValueError as exc:
        raise HTTPException(422, "invalid_samples") from exc
    today = datetime.now(UTC).date().isoformat()
    rows = [
        WebVital(day=today, route=s.route, metric=s.metric, value=s.value, device=s.device)
        for s in batch.samples
        if s.route in ROUTES and s.value <= LIMITS[s.metric]
    ]
    if rows:
        with Session(request.app.state.engine) as db, db.begin():
            db.add_all(rows)


def p75(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(0.75 * len(ordered)))]


def summary(db: Session, today: date, days: int = 7) -> dict:
    """p75 per route and metric over the last `days` days, with the budget verdict."""
    since = (today - timedelta(days=days - 1)).isoformat()
    groups: dict[tuple[str, str], list[float]] = {}
    for route, metric, value in db.execute(
        select(WebVital.route, WebVital.metric, WebVital.value).where(WebVital.day >= since)
    ):
        groups.setdefault((route, metric), []).append(value)
    pages: dict[str, dict] = {}
    for (route, metric), values in groups.items():
        if metric not in BUDGETS:
            continue
        page = pages.setdefault(route, {"route": route, "samples": 0})
        value = p75(values)
        page[metric] = dict(
            p75=round(value, 3 if metric == "CLS" else 0), ok=value <= BUDGETS[metric]
        )
        page["samples"] = max(page["samples"], len(values))
    return dict(
        days=days,
        budgets=BUDGETS,
        pages=sorted(pages.values(), key=lambda p: -p["samples"]),
    )
