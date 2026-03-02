import datetime

from sqlalchemy import Date, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class Wellness(Base):
    """Daily wellness data from Garmin Connect."""

    __tablename__ = "wellness"

    date: Mapped[datetime.date] = mapped_column(Date, primary_key=True)

    # HRV
    hrv_rmssd: Mapped[float | None] = mapped_column(Float)
    hrv_status: Mapped[str | None] = mapped_column(String(20))

    # Sleep
    sleep_score: Mapped[int | None] = mapped_column(Integer)
    sleep_duration_seconds: Mapped[int | None] = mapped_column(Integer)
    sleep_start: Mapped[str | None] = mapped_column(String(30))
    sleep_end: Mapped[str | None] = mapped_column(String(30))

    # Body Battery
    body_battery_high: Mapped[int | None] = mapped_column(Integer)
    body_battery_low: Mapped[int | None] = mapped_column(Integer)
    body_battery_most_recent: Mapped[int | None] = mapped_column(Integer)

    # Training metrics
    training_readiness: Mapped[int | None] = mapped_column(Integer)
    training_status: Mapped[str | None] = mapped_column(String(30))
    endurance_score: Mapped[float | None] = mapped_column(Float)

    # Resting heart rate
    resting_hr: Mapped[int | None] = mapped_column(Integer)

    # Stress
    avg_stress: Mapped[int | None] = mapped_column(Integer)

    def __repr__(self) -> str:
        return f"<Wellness date={self.date}>"
