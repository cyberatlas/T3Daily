from fastapi import APIRouter
from pydantic import BaseModel

from backend.app.sync.scheduler import run_sync_all, run_sync_source

router = APIRouter()


class SyncRequest(BaseModel):
    source: str = "all"  # "all", "garmin", or "intervals_icu"
    days_back: int | None = None


@router.post("/sync")
def trigger_sync(request: SyncRequest = SyncRequest()):
    """Trigger an on-demand sync. Runs synchronously and returns results."""
    if request.source == "all":
        results = run_sync_all()
    else:
        results = {request.source: run_sync_source(request.source, request.days_back)}

    return {"results": results}
