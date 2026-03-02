import datetime

from sqlalchemy import Date, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class Activity(Base):
    """Completed workouts from Intervals.icu."""

    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # Intervals.icu activity id
    external_id: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)

    date: Mapped[datetime.date] = mapped_column(Date, index=True)
    name: Mapped[str | None] = mapped_column(String(256))
    activity_type: Mapped[str | None] = mapped_column(String(50))

    # Duration and distance
    moving_time_seconds: Mapped[int | None] = mapped_column(Integer)
    elapsed_time_seconds: Mapped[int | None] = mapped_column(Integer)
    distance_meters: Mapped[float | None] = mapped_column(Float)

    # Training load
    load: Mapped[float | None] = mapped_column(Float)  # training load / stress score
    intensity: Mapped[float | None] = mapped_column(Float)

    # Heart rate
    avg_hr: Mapped[int | None] = mapped_column(Integer)
    max_hr: Mapped[int | None] = mapped_column(Integer)

    # Power (cycling)
    avg_power: Mapped[float | None] = mapped_column(Float)
    normalized_power: Mapped[float | None] = mapped_column(Float)

    # Pace (running/swimming)
    avg_pace: Mapped[float | None] = mapped_column(Float)  # seconds per km

    source: Mapped[str | None] = mapped_column(String(50))  # e.g. "intervals.icu"
    raw_json: Mapped[str | None] = mapped_column(Text)  # full API response for debugging

    def __repr__(self) -> str:
        return f"<Activity {self.date} {self.activity_type}: {self.name}>"
