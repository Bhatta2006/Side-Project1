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
    with Session(engine(request)) as db:
        require_admin(request, db)
        month = budget.day_of(stamp)[:8] + "01"
        return dict(
            month_from=month,
            queue=costs.queue(db, stamp),
            courses=costs.by_course(db),
            roles=costs.by_role(db, since_day=month),
            reliability=costs.reliability(db),
        )
