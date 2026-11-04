"""Practice library API: browse, recommendations, marks and the Codeforces link."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from socrat import entitlements
from socrat.catalog import practice
from socrat.database import record_event
from socrat.learn import service as learn_service
from socrat.learn.routes import active, catalog, engine, require_feature, user_of
from socrat.library import codeforces, company_sprint, sprints
from socrat.library import service as library
from socrat.models import CompanySprint, FocusSprint, LinkedAccount, now


def in_a_library_course(request: Request) -> None:
    """The library belongs to the programming courses; another course's Practice is its own."""
    with Session(engine(request)) as db:
        require_feature(db, user_of(request, db), "library")


router = APIRouter(prefix="/api/v1/library", dependencies=[Depends(in_a_library_course)])
SYNC_COOLDOWN_SECONDS = 600


class MarkInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["todo", "attempted", "solved"] | None = None
    bookmarked: bool | None = None


class LinkInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    handle: str = Field(pattern=codeforces.HANDLE.pattern)


def problem_or_404(problem_id: str) -> str:
    if problem_id not in practice.default_index().problems:
        raise HTTPException(404, "not_found")
    return problem_id


@router.get("")
def browse(
    request: Request,
    q: str = "",
    platform: str = "",
    concept: str = "",
    difficulty: Literal["", "easy", "medium", "hard"] = "",
    rating_min: int = 0,
    rating_max: int = 0,
    sheet: str = "",
    status: Literal["all", "unsolved", "todo", "attempted", "solved", "bookmarked"] = "all",
    sort: Literal["recommended", "easiest", "hardest", "popular", "title"] = "recommended",
    offset: int = 0,
    limit: int = 30,
):
    platforms = tuple(p for p in platform.split(",") if p in practice.PLATFORMS)
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        return library.listing(
            db,
            cat,
            user,
            now(),
            q=q[:80],
            platforms=platforms,
            concept=concept,
            difficulty=difficulty,
            rating_min=rating_min,
            rating_max=rating_max,
            sheet=sheet,
            status=status,
            sort=sort,
            offset=offset,
            limit=limit,
        )


@router.get("/stats")
def stats():
    cat = catalog()
    return {
        "courses": len(cat.courses),
        "concepts": len(cat.concepts),
        "problems": len(cat.problems),
        "library": len(practice.default_index().problems),
    }


@router.get("/solved")
def solved_board(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        return library.solved_board(db, catalog(), user, enrollment, now())


@router.get("/meta")
def library_meta(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        return library.meta(db, catalog(), user, now())


@router.get("/recommendations")
def recommendations(request: Request, limit: int = 6):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        return library.recommendations(db, cat, user, now(), max(1, min(limit, 12)))


@router.put("/problems/{problem_id}")
def set_mark(problem_id: str, body: MarkInput, request: Request):
    problem_or_404(problem_id)
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        return library.mark(db, cat, user, problem_id, now(), body.status, body.bookmarked)


@router.post("/problems/{problem_id}/opened")
def opened(problem_id: str, request: Request):
    problem_or_404(problem_id)
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        return library.mark(db, cat, user, problem_id, now(), opened=True)


@router.get("/codeforces")
def codeforces_account(request: Request):
    with Session(engine(request)) as db:
        user = user_of(request, db)
        return {"account": library.account_view(library.account_for(db, user.id))}


async def _sync(request: Request, handle: str | None) -> dict:
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        user_id = user.id
        account = library.account_for(db, user.id)
        if handle is None:
            if account is None:
                raise HTTPException(404, "not_linked")
            if account.synced_at and now() - account.synced_at < SYNC_COOLDOWN_SECONDS:
                return {"account": library.account_view(account), "synced": False}
            handle = account.handle
    try:
        profile = await codeforces.fetch_profile(handle)
    except codeforces.CodeforcesError as exc:
        code = str(exc)
        if code in {"handle_not_found", "invalid_handle"}:
            raise HTTPException(422, f"codeforces_{code}") from exc
        with Session(engine(request)) as db, db.begin():
            account = db.get(LinkedAccount, (user_id, "codeforces"))
            if account is not None:
                account.sync_error = code
        raise HTTPException(503, "codeforces_unavailable") from exc
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        account = library.apply_profile(db, catalog(), user, profile, now())
        record_event(db, user.id, "library.codeforces_synced")
        return {"account": library.account_view(account), "synced": True}


@router.post("/codeforces")
async def link_codeforces(body: LinkInput, request: Request):
    return await _sync(request, body.handle)


@router.post("/codeforces/sync")
async def sync_codeforces(request: Request):
    return await _sync(request, None)


@router.delete("/codeforces", status_code=204)
def unlink_codeforces(request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        account = library.account_for(db, user.id)
        if account is not None:
            db.delete(account)


# ---------------------------------------------------------------- focus sprints and rounds


@router.get("/sprints")
def sprint_overview(request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        enrollment = active(db, user)
        stamp = now()
        running = sprints.active(db, enrollment, stamp)
        return {
            "current": sprints.view(db, cat, user, running, stamp) if running else None,
            "history": sprints.history(db, enrollment),
        }


@router.post("/sprints")
def start_sprint(request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        stamp = now()
        sprint = sprints.start(db, cat, user, enrollment, stamp)
        return sprints.view(db, cat, user, sprint, stamp)


def owned_sprint(db: Session, enrollment_id: str, sprint_id: str) -> FocusSprint:
    sprint = db.get(FocusSprint, sprint_id)
    if sprint is None or sprint.enrollment_id != enrollment_id:
        raise HTTPException(404, "not_found")
    return sprint


@router.get("/sprints/{sprint_id}")
def sprint_detail(sprint_id: str, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db)
        enrollment = active(db, user)
        sprint = owned_sprint(db, enrollment.id, sprint_id)
        stamp = now()
        if sprint.finished_at is None and stamp > sprint.deadline:
            sprints.finish(db, user, sprint, stamp)
        return sprints.view(db, cat, user, sprint, stamp)


@router.post("/sprints/{sprint_id}/finish")
def finish_sprint(sprint_id: str, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        sprint = owned_sprint(db, enrollment.id, sprint_id)
        stamp = now()
        sprints.finish(db, user, sprint, stamp)
        return sprints.view(db, cat, user, sprint, stamp)


@router.get("/contests")
async def contests(request: Request):
    with Session(engine(request)) as db:
        user_of(request, db)
    return {"items": await codeforces.upcoming_contests()}


# ---------------------------------------------------------------- company sprints


class CompanySprintInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")
    role: Literal["intern", "sde1", "sde2", "senior"] = "sde1"
    weeks: Literal[4, 6, 8] = 6


@router.get("/company-sprints")
def company_sprint_overview(request: Request, q: str = ""):
    cat = catalog()
    with Session(engine(request)) as db:
        user = user_of(request, db)
        enrollment = active(db, user)
        stamp = now()
        running = company_sprint.active(db, enrollment)
        scope = learn_service.curriculum(cat, enrollment)
        return {
            "current": company_sprint.view(db, cat, user, running, stamp) if running else None,
            "companies": company_sprint.companies(cat, scope, q[:60]),
            "roles": [dict(id=k, label=v) for k, v in company_sprint.ROLE_LABEL.items()],
            "weeks": list(company_sprint.WEEKS),
            "locked": not entitlements.has(db, user.id, "companies"),
        }


@router.post("/company-sprints")
def start_company_sprint(body: CompanySprintInput, request: Request):
    cat = catalog()
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        entitlements.require(db, user.id, "companies")
        enrollment = active(db, user)
        stamp = now()
        sprint = company_sprint.start(
            db, cat, user, enrollment, body.company, body.role, body.weeks, stamp
        )
        record_event(db, user.id, "company_sprint.started", sprint.id)
        return company_sprint.view(db, cat, user, sprint, stamp)


@router.post("/company-sprints/{sprint_id}/stop")
def stop_company_sprint(sprint_id: str, request: Request):
    with Session(engine(request)) as db, db.begin():
        user = user_of(request, db, write=True)
        enrollment = active(db, user)
        sprint = db.get(CompanySprint, sprint_id)
        if sprint is None or sprint.enrollment_id != enrollment.id:
            raise HTTPException(404, "not_found")
        company_sprint.stop(sprint, now())
        return {"stopped": True}
