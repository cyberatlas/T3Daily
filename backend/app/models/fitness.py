import datetime

from sqlalchemy import Date, Float
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class FitnessMetrics(Base):
    """Daily fitness metrics from Intervals.icu."""

    __tablename__ = "fitness_metrics"

    date: Mapped[datetime.date] = mapped_column(Date, primary_key=True)

    ctl: Mapped[float | None] = mapped_column(Float)  # Chronic Training Load
    atl: Mapped[float | None] = mapped_column(Float)  # Acute Training Load
    tsb: Mapped[float | None] = mapped_column(Float)  # Training Stress Balance
    ramp_rate: Mapped[float | None] = mapped_column(Float)
    vo2max: Mapped[float | None] = mapped_column(Float)

    def __repr__(self) -> str:
        return f"<FitnessMetrics date={self.date} ctl={self.ctl}>"
