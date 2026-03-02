import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class SyncLog(Base):
    """Tracks the last sync status per data source."""

    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), index=True)  # "garmin", "intervals_icu"
    status: Mapped[str] = mapped_column(String(20))  # "success", "error"
    message: Mapped[str | None] = mapped_column(Text)
    rows_synced: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    finished_at: Mapped[datetime.datetime | None] = mapped_column(DateTime)

    def __repr__(self) -> str:
        return f"<SyncLog {self.source} {self.status} @ {self.started_at}>"
