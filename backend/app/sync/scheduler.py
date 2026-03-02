import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.sync.garmin import GarminSyncService
from backend.app.sync.intervals_icu import IntervalsIcuSyncService

logger = logging.getLogger(__name__)


def run_sync_all() -> dict:
    """Run all sync jobs. Called by scheduler and by on-demand endpoint."""
    results = {}
    db = SessionLocal()
    try:
        # Garmin sync — failure here must not block Intervals.icu
        try:
            garmin = GarminSyncService()
            results["garmin"] = garmin.sync(db)
        except Exception as e:
            logger.error("Garmin sync failed: %s", e)
            results["garmin"] = {"source": "garmin", "status": "error", "message": str(e)}

        # Intervals.icu sync
        try:
            intervals = IntervalsIcuSyncService()
            results["intervals_icu"] = intervals.sync(db)
        except Exception as e:
            logger.error("Intervals.icu sync failed: %s", e)
            results["intervals_icu"] = {"source": "intervals_icu", "status": "error", "message": str(e)}
    finally:
        db.close()

    logger.info("Sync complete: %s", {k: v.get("status") for k, v in results.items()})
    return results


def run_sync_source(source: str, days_back: int | None = None) -> dict:
    """Run sync for a specific source."""
    db = SessionLocal()
    try:
        if source == "garmin":
            svc = GarminSyncService()
            kwargs = {"days_back": days_back} if days_back is not None else {}
            return svc.sync(db, **kwargs)
        elif source == "intervals_icu":
            svc = IntervalsIcuSyncService()
            kwargs = {"days_back": days_back} if days_back is not None else {}
            return svc.sync(db, **kwargs)
        else:
            return {"source": source, "status": "error", "message": f"Unknown source: {source}"}
    finally:
        db.close()


def setup_scheduler() -> BackgroundScheduler:
    """Create and configure the background scheduler."""
    scheduler = BackgroundScheduler(timezone=settings.tz)
    scheduler.add_job(
        run_sync_all,
        trigger=CronTrigger(hour=settings.sync_hour, minute=settings.sync_minute),
        id="daily_sync",
        name="Daily data sync",
        replace_existing=True,
    )
    return scheduler
