import datetime
import json
import logging

import httpx
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.fitness import FitnessMetrics
from backend.app.models.activity import Activity
from backend.app.models.sync_log import SyncLog

logger = logging.getLogger(__name__)

INTERVALS_BASE_URL = "https://intervals.icu/api/v1"


class IntervalsIcuSyncService:
    def __init__(self):
        self.athlete_id = settings.intervals_athlete_id
        self.auth = ("API_KEY", settings.intervals_api_key)

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=INTERVALS_BASE_URL,
            auth=self.auth,
            timeout=30.0,
        )

    def sync(self, db: Session, days_back: int = 14) -> dict:
        """Sync wellness (CTL/ATL/TSB) and activities from Intervals.icu."""
        sync_log = SyncLog(source="intervals_icu", status="in_progress")
        db.add(sync_log)
        db.commit()

        today = datetime.date.today()
        oldest = today - datetime.timedelta(days=days_back)

        errors = []
        wellness_count = 0
        activity_count = 0

        try:
            with self._client() as client:
                wellness_count = self._sync_wellness(client, db, oldest, today)
        except Exception as e:
            logger.error("Intervals.icu wellness sync failed: %s", e)
            errors.append(f"wellness: {e}")

        try:
            with self._client() as client:
                activity_count = self._sync_activities(client, db, oldest, today)
        except Exception as e:
            logger.error("Intervals.icu activities sync failed: %s", e)
            errors.append(f"activities: {e}")

        total = wellness_count + activity_count
        sync_log.status = "success" if not errors else "partial"
        sync_log.rows_synced = total
        sync_log.message = "; ".join(errors) if errors else None
        sync_log.finished_at = datetime.datetime.now(datetime.UTC)
        db.commit()

        return {
            "source": "intervals_icu",
            "status": sync_log.status,
            "rows_synced": total,
            "wellness": wellness_count,
            "activities": activity_count,
            "errors": errors,
        }

    def _sync_wellness(
        self,
        client: httpx.Client,
        db: Session,
        oldest: datetime.date,
        newest: datetime.date,
    ) -> int:
        """Pull CTL/ATL/TSB/VO2max from the wellness endpoint."""
        url = f"/athlete/{self.athlete_id}/wellness"
        resp = client.get(url, params={
            "oldest": oldest.isoformat(),
            "newest": newest.isoformat(),
        })
        resp.raise_for_status()
        data = resp.json()

        count = 0
        for entry in data:
            date_str = entry.get("id")  # wellness entries use "id" as date string
            if not date_str:
                continue

            try:
                date = datetime.date.fromisoformat(date_str)
            except ValueError:
                continue

            values = {
                "ctl": _float(entry.get("ctl")),
                "atl": _float(entry.get("atl")),
                "tsb": None,  # computed below
                "ramp_rate": _float(entry.get("rampRate")),
                "vo2max": _float(entry.get("vo2max")),
            }

            # TSB = CTL - ATL
            if values["ctl"] is not None and values["atl"] is not None:
                values["tsb"] = values["ctl"] - values["atl"]

            existing = db.get(FitnessMetrics, date)
            if existing:
                for key, value in values.items():
                    if value is not None:
                        setattr(existing, key, value)
            else:
                db.add(FitnessMetrics(date=date, **values))
            count += 1

        db.commit()
        logger.info("Intervals.icu: synced %d wellness entries", count)
        return count

    def _sync_activities(
        self,
        client: httpx.Client,
        db: Session,
        oldest: datetime.date,
        newest: datetime.date,
    ) -> int:
        """Pull completed activities."""
        url = f"/athlete/{self.athlete_id}/activities"
        resp = client.get(url, params={
            "oldest": oldest.isoformat(),
            "newest": newest.isoformat(),
        })
        resp.raise_for_status()
        data = resp.json()

        count = 0
        for entry in data:
            activity_id = str(entry.get("id", ""))
            if not activity_id:
                continue

            external_id = entry.get("icu_recording_id") or entry.get("external_id")

            # Parse date from start_date_local
            date_str = entry.get("start_date_local", "")[:10]
            try:
                date = datetime.date.fromisoformat(date_str)
            except ValueError:
                continue

            values = {
                "external_id": str(external_id) if external_id else None,
                "date": date,
                "name": entry.get("name"),
                "activity_type": entry.get("type"),
                "moving_time_seconds": _int(entry.get("moving_time")),
                "elapsed_time_seconds": _int(entry.get("elapsed_time")),
                "distance_meters": _float(entry.get("distance")),
                "load": _float(entry.get("icu_training_load")),
                "intensity": _float(entry.get("icu_intensity")),
                "avg_hr": _int(entry.get("average_heartrate")),
                "max_hr": _int(entry.get("max_heartrate")),
                "avg_power": _float(entry.get("icu_average_watts")),
                "normalized_power": _float(entry.get("icu_weighted_avg_watts")),
                "avg_pace": _float(entry.get("icu_average_pace")),
                "source": "intervals.icu",
                "raw_json": json.dumps(entry),
            }

            # Upsert by activity id
            existing = db.get(Activity, activity_id)
            if existing:
                for key, value in values.items():
                    if value is not None:
                        setattr(existing, key, value)
            else:
                db.add(Activity(id=activity_id, **values))
            count += 1

        db.commit()
        logger.info("Intervals.icu: synced %d activities", count)
        return count


def _float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _int(val) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
