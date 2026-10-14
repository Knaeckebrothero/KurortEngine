"""Runtime configuration, read from ``KURORT_*`` environment variables."""

from __future__ import annotations

from datetime import date
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KURORT_", env_file=".env", extra="ignore", env_ignore_empty=True
    )

    database_url: str = "postgresql+psycopg://kurort:kurort@localhost:5432/kurort"
    hotel_name: str = "Hotel Rheinland"
    hotel_city: str = "Bad Orb"
    # Pin "today" for demos and tests (ISO date). Unset = the real date.
    today: date | None = None
    # Tourist-tax statute profile loaded via kurort_engine.rates.load_profile.
    kurtaxe_bundesland: str = "hessen"
    kurtaxe_kurort: str = "bad_orb"

    @field_validator("database_url")
    @classmethod
    def _psycopg_driver(cls, url: str) -> str:
        """Accept plain postgres:// URLs (CNPG/Heroku style) and pin the psycopg 3 driver."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix) :]
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


def today() -> date:
    """The business date the front desk works on."""
    return get_settings().today or date.today()
