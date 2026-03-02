import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.wellness import Wellness
from backend.app.models.fitness import FitnessMetrics
from backend.app.models.activity import Activity
from backend.app.models.sync_log import SyncLog

router = APIRouter()


@router.get("/status")
def get_status(db: Session = Depends(get_db)):
    """Return sync health, data freshness, and scheduler state."""
    from backend.app.main import scheduler

    # Latest sync log per source
    sources = {}
    for source_name in ("garmin", "intervals_icu"):
        log = db.execute(
            select(SyncLog)
            .where(SyncLog.source == source_name)
            .order_by(SyncLog.started_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if log:
            sources[source_name] = {
                "status": log.status,
                "message": log.message,
                "rows_synced": log.rows_synced,
                "started_at": log.started_at.isoformat() if log.started_at else None,
                "finished_at": log.finished_at.isoformat() if log.finished_at else None,
            }
        else:
            sources[source_name] = {"status": "never_synced"}

    # Data counts and freshness
    wellness_count = db.execute(select(func.count()).select_from(Wellness)).scalar()
    wellness_latest = db.execute(select(func.max(Wellness.date))).scalar()

    fitness_count = db.execute(select(func.count()).select_from(FitnessMetrics)).scalar()
    fitness_latest = db.execute(select(func.max(FitnessMetrics.date))).scalar()

    activity_count = db.execute(select(func.count()).select_from(Activity)).scalar()
    activity_latest = db.execute(select(func.max(Activity.date))).scalar()

    # Scheduler state
    scheduler_info = {"running": False}
    if scheduler and scheduler.running:
        jobs = scheduler.get_jobs()
        scheduler_info = {
            "running": True,
            "jobs": [
                {
                    "id": j.id,
                    "name": j.name,
                    "next_run": j.next_run_time.isoformat() if j.next_run_time else None,
                }
                for j in jobs
            ],
        }

    return {
        "status": "ok",
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "sources": sources,
        "data": {
            "wellness": {"count": wellness_count, "latest": str(wellness_latest) if wellness_latest else None},
            "fitness_metrics": {"count": fitness_count, "latest": str(fitness_latest) if fitness_latest else None},
            "activities": {"count": activity_count, "latest": str(activity_latest) if activity_latest else None},
        },
        "scheduler": scheduler_info,
    }
