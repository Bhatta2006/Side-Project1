"""Read-only catalogue of what the engine can do: domains and renderers."""

from dataclasses import asdict

from fastapi import APIRouter

from socrat.engine import domains, renderers

router = APIRouter(prefix="/api/v1/engine")


@router.get("/domains")
def list_domains():
    return {"items": [asdict(a) for a in domains.ADAPTERS.values()]}


@router.get("/renderers")
def list_renderers():
    return {"items": [renderers.describe(m) for m in renderers.all_manifests().values()]}
