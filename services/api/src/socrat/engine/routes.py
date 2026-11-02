"""What the engine can do (domains, renderers) and the vetted simulations lessons can embed."""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from socrat import harness, httpcache, limits
from socrat.engine import domains, renderers
from socrat.harness import physics
from socrat.learn.routes import engine, user_of

router = APIRouter(prefix="/api/v1/engine")


@router.get("/domains")
def list_domains(request: Request):
    return httpcache.shared(request, {"items": [asdict(a) for a in domains.ADAPTERS.values()]})


@router.get("/renderers")
def list_renderers(request: Request):
    items = [renderers.describe(m) for m in renderers.all_manifests().values()]
    return httpcache.shared(request, {"items": items})


@router.get("/simulations")
def list_simulations(request: Request):
    """Each vetted experiment with its parameters (unit, range, default) and what it reports,
    so a lesson's simulation can draw sliders that cannot leave the valid range."""
    return httpcache.shared(
        request,
        {
            "items": [
                dict(
                    id=name,
                    title=m.title,
                    params=[dict(name=k, **asdict(p)) for k, p in m.params.items()],
                    outputs=[dict(name=k, unit=u) for k, u in m.outputs.items()],
                )
                for name, m in physics.MODELS.items()
            ]
        },
    )


class Simulate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = Field(min_length=1, max_length=40)
    inputs: dict[str, float] = Field(default_factory=dict, max_length=8)


@router.post("/simulate")
def simulate(body: Simulate, request: Request):
    """Run one vetted experiment on the server (never in the browser, never model-written code).
    Inputs not given use the experiment's defaults; out-of-range inputs are refused."""
    with Session(engine(request)) as db:
        user = user_of(request, db, write=True)
        user_id = user.id
    limits.enforce("simulate", user_id, request.app.state.settings.simulate_per_minute, 60)
    found = physics.MODELS.get(body.model)
    if found is None:
        raise HTTPException(404, "not_found")
    params = {k: p.default for k, p in found.params.items()} | body.inputs
    bad = physics.problems(body.model, params)
    if bad:
        raise HTTPException(422, detail=dict(code="invalid_inputs", problems=bad))
    result = harness.call("physics.simulate", dict(model=body.model, params=params))
    if not result.ok:
        raise HTTPException(503, "simulation_unavailable")
    return result.output
