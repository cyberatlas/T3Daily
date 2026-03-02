import datetime
import logging
from pathlib import Path

from garminconnect import Garmin
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.wellness import Wellness
from backend.app.models.sync_log import SyncLog

logger = logging.getLogger(__name__)


class GarminSyncService:
    def __init__(self):
        self.token_dir = Path(settings.garmin_token_dir)
        self.token_dir.mkdir(parents=True, exist_ok=True)
        self.client: Garmin | None = None

    def _connect(self) -> Garmin:
        """Authenticate with Garmin Connect, reusing saved tokens if possible."""
        client = Garmin(email=settings.garmin_email, password=settings.garmin_password)

        token_path = str(self.token_dir)
        try:
            client.login(tokenstore=token_path)
            logger.info("Garmin: authenticated via saved tokens")
        except Exception:
            logger.info("Garmin: saved tokens invalid, performing full login")
            client.login()

        # Save/refresh tokens for next time
        client.garth.dump(token_path)
        self.client = client
        return client

    def sync(self, db: Session, days_back: int = 2) -> dict:
        """Sync Garmin wellness data for today and previous N days.

        Returns a summary dict with counts and any errors.
        """
        sync_log = SyncLog(source="garmin", status="in_progress")
        db.add(sync_log)
        db.commit()

        try:
            client = self._connect()
        except Exception as e:
            logger.error("Garmin: authentication failed: %s", e)
            sync_log.status = "error"
            sync_log.message = f"Authentication failed: {e}"
            sync_log.finished_at = datetime.datetime.now(datetime.UTC)
            db.commit()
            return {"source": "garmin", "status": "error", "message": str(e)}

        today = datetime.date.today()
        dates = [today - datetime.timedelta(days=i) for i in range(days_back + 1)]

        rows_synced = 0
        errors = []

        for date in dates:
            try:
                self._sync_date(client, db, date)
                rows_synced += 1
            except Exception as e:
                logger.warning("Garmin: failed to sync %s: %s", date, e)
                errors.append(f"{date}: {e}")

        db.commit()

        sync_log.status = "success" if not errors else "partial"
        sync_log.rows_synced = rows_synced
        sync_log.message = "; ".join(errors) if errors else None
        sync_log.finished_at = datetime.datetime.now(datetime.UTC)
        db.commit()

        return {
            "source": "garmin",
            "status": sync_log.status,
            "rows_synced": rows_synced,
            "errors": errors,
        }

    def _sync_date(self, client: Garmin, db: Session, date: datetime.date) -> None:
        """Pull all wellness data for a single date and upsert into DB."""
        date_str = date.isoformat()

        # Fetch each metric independently so one failure doesn't block others
        hrv_data = self._safe_call(client.get_hrv_data, date_str)
        sleep_data = self._safe_call(client.get_sleep_data, date_str)
        body_battery = self._safe_call(client.get_body_battery, date_str, date_str)
        training_readiness = self._safe_call(client.get_training_readiness, date_str)
        training_status = self._safe_call(client.get_training_status, date_str)
        endurance = self._safe_call(client.get_endurance_score, date_str, date_str)
        heart_rates = self._safe_call(client.get_heart_rates, date_str)
        stress = self._safe_call(client.get_all_day_stress, date_str)

        # Parse each response defensively
        values = {
            "hrv_rmssd": self._parse_hrv(hrv_data),
            "hrv_status": self._parse_hrv_status(hrv_data),
            "sleep_score": self._parse_sleep_score(sleep_data),
            "sleep_duration_seconds": self._parse_sleep_duration(sleep_data),
            "sleep_start": self._parse_sleep_time(sleep_data, "sleepStartTimestampLocal"),
            "sleep_end": self._parse_sleep_time(sleep_data, "sleepEndTimestampLocal"),
            "body_battery_high": self._parse_body_battery(body_battery, "charged"),
            "body_battery_low": self._parse_body_battery(body_battery, "drained"),
            "body_battery_most_recent": self._parse_body_battery(body_battery, "mostRecentValue"),
            "training_readiness": self._parse_training_readiness(training_readiness),
            "training_status": self._parse_training_status(training_status),
            "endurance_score": self._parse_endurance_score(endurance),
            "resting_hr": self._parse_resting_hr(heart_rates),
            "avg_stress": self._parse_avg_stress(stress),
        }

        # Upsert: update if exists, insert if not
        existing = db.get(Wellness, date)
        if existing:
            for key, value in values.items():
                if value is not None:
                    setattr(existing, key, value)
        else:
            db.add(Wellness(date=date, **values))

    def _safe_call(self, func, *args):
        """Call a Garmin API method, returning None on any error."""
        try:
            return func(*args)
        except Exception as e:
            logger.debug("Garmin API call %s failed: %s", func.__name__, e)
            return None

    # --- Parsers: each returns a value or None ---

    def _parse_hrv(self, data) -> float | None:
        if not data:
            return None
        try:
            summary = data.get("hrvSummary", {})
            # Try weekly average first, then last night
            val = summary.get("weeklyAvg") or summary.get("lastNight")
            return float(val) if val is not None else None
        except (TypeError, ValueError, KeyError):
            return None

    def _parse_hrv_status(self, data) -> str | None:
        if not data:
            return None
        try:
            return data.get("hrvSummary", {}).get("status")
        except (TypeError, KeyError):
            return None

    def _parse_sleep_score(self, data) -> int | None:
        if not data:
            return None
        try:
            score = data.get("dailySleepDTO", {}).get("sleepScores", {}).get("overall", {}).get("value")
            return int(score) if score is not None else None
        except (TypeError, ValueError, KeyError):
            return None

    def _parse_sleep_duration(self, data) -> int | None:
        if not data:
            return None
        try:
            val = data.get("dailySleepDTO", {}).get("sleepTimeSeconds")
            return int(val) if val is not None else None
        except (TypeError, ValueError, KeyError):
            return None

    def _parse_sleep_time(self, data, field: str) -> str | None:
        if not data:
            return None
        try:
            val = data.get("dailySleepDTO", {}).get(field)
            return str(val) if val is not None else None
        except (TypeError, KeyError):
            return None

    def _parse_body_battery(self, data, field: str) -> int | None:
        if not data:
            return None
        try:
            # body_battery returns a list; take first entry
            if isinstance(data, list) and data:
                val = data[0].get(field)
            elif isinstance(data, dict):
                val = data.get(field)
            else:
                return None
            return int(val) if val is not None else None
        except (TypeError, ValueError, KeyError, IndexError):
            return None

    def _parse_training_readiness(self, data) -> int | None:
        if not data:
            return None
        try:
            val = data.get("score") or data.get("trainingSummary", {}).get("score")
            return int(val) if val is not None else None
        except (TypeError, ValueError, KeyError):
            return None

    def _parse_training_status(self, data) -> str | None:
        if not data:
            return None
        try:
            return data.get("trainingStatus") or data.get("currentTrainingStatus")
        except (TypeError, KeyError):
            return None

    def _parse_endurance_score(self, data) -> float | None:
        if not data:
            return None
        try:
            if isinstance(data, list) and data:
                val = data[0].get("enduranceScore") or data[0].get("overallScore")
            elif isinstance(data, dict):
                val = data.get("enduranceScore") or data.get("overallScore")
            else:
                return None
            return float(val) if val is not None else None
        except (TypeError, ValueError, KeyError, IndexError):
            return None

    def _parse_resting_hr(self, data) -> int | None:
        if not data:
            return None
        try:
            val = data.get("restingHeartRate")
            return int(val) if val is not None else None
        except (TypeError, ValueError, KeyError):
            return None

    def _parse_avg_stress(self, data) -> int | None:
        if not data:
            return None
        try:
            val = data.get("overallStressLevel") or data.get("avgStressLevel")
            return int(val) if val is not None else None
        except (TypeError, ValueError, KeyError):
            return None
