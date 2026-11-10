"""Owner view of generation spend per course and per role."""

from fastapi import APIRouter, Request
from sqlalchemy.orm import Session

from socrat.admin.routes import require_admin
from socrat.assistant import budget
from socrat.coursegen import costs
from socrat.learn.routes import engine
from socrat.models import now

router = APIRouter(prefix="/api/v1/admin/engine-costs")


@router.get("")
def report(request: Request):
    stamp = now()
    settings = request.app.state.settings
    with Session(engine(request)) as db:
        require_admin(request, db)
        month = budget.day_of(stamp)[:8] + "01"
        return dict(
            month_from=month,
            queue=costs.queue(db, stamp),
            lesson_cost_target_usd=settings.gen_lesson_cost_target_usd,
            courses=costs.by_course(db, target_usd=settings.gen_lesson_cost_target_usd),
            roles=costs.by_role(db, since_day=month),
            models=costs.by_model(db, since_day=month),
            tiers=costs.tiers(settings),
            reliability=costs.reliability(db),
        )


@router.get("/outcomes")
def outcomes(request: Request, course: str | None = None):
    """Learning outcomes from the evidence (observational; see engine.outcomes)."""
    from socrat.engine import outcomes as learning

    with Session(engine(request)) as db:
        require_admin(request, db)
        return learning.report(db, course)
