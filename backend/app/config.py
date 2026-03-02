from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Garmin
    garmin_email: str = ""
    garmin_password: str = ""
    garmin_token_dir: str = "data/garmin_tokens"

    # Intervals.icu
    intervals_api_key: str = ""
    intervals_athlete_id: str = ""

    # Database
    database_url: str = "sqlite:///data/db/t3daily.db"

    # Scheduler
    sync_hour: int = 5
    sync_minute: int = 0
    tz: str = "America/Denver"

    @property
    def db_path(self) -> Path:
        """Extract the file path from the SQLite URL."""
        return Path(self.database_url.replace("sqlite:///", ""))


settings = Settings()
