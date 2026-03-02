import datetime

from sqlalchemy import Date, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class UserSettings(Base):
    """Single-row user configuration."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    plan_start_date: Mapped[datetime.date | None] = mapped_column(Date)
    plan_name: Mapped[str | None] = mapped_column(String(256))
    location_lat: Mapped[float | None] = mapped_column(Float)
    location_lon: Mapped[float | None] = mapped_column(Float)
    sleep_target_hours: Mapped[float | None] = mapped_column(Float, default=8.0)

    def __repr__(self) -> str:
        return f"<UserSettings plan={self.plan_name}>"
