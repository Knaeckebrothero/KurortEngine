"""Runtime configuration, read from ``KURORT_*`` environment variables."""

from __future__ import annotations

from datetime import date, datetime, time
from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KURORT_", env_file=".env", extra="ignore", env_ignore_empty=True
    )

    database_url: str = "postgresql+psycopg://kurort:kurort@localhost:5432/kurort"
    hotel_name: str = "Hotel Rheinland"
    hotel_city: str = "Bad Orb"
    avs_url: str | None = None
    # Pin "today" for demos and tests (ISO date). Unset = the real date.
    today: date | None = None
    # Tourist-tax statute profile loaded via kurort_engine.rates.load_profile.
    kurtaxe_bundesland: str = "hessen"
    kurtaxe_kurort: str = "bad_orb"

    # Outbound guest mail. No SMTP connection is made for the default log transport.
    mail_transport: Literal["log", "smtp"] = "log"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_security: Literal["starttls", "ssl", "none"] = "starttls"
    late_arrival_from: time = time(18, 0)

    # Staff login. "oidc" (default) requires the OIDC/session settings below and
    # refuses to start without them; "off" serves every page without a login.
    auth: Literal["oidc", "off"] = "oidc"
    # Public issuer the browser is sent to and that tokens name in `iss`.
    oidc_issuer: str | None = None
    # Base URL the server uses for discovery/token/JWKS/userinfo (default: issuer).
    oidc_internal_url: str | None = None
    oidc_client_id: str = "kurort-app"
    oidc_client_secret: str | None = None
    # Signs the session cookie; at least 32 characters.
    session_secret: str | None = None
    # External base URL of this app (redirect URIs); default: derived from the request.
    public_url: str | None = None

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


HOTEL_TZ = ZoneInfo("Europe/Berlin")


def today() -> date:
    """The business date the front desk works on: the hotel's local date, not the server's.

    Containers run on UTC, so date.today() would still be yesterday between
    midnight and 02:00 in Bad Orb.
    """
    return get_settings().today or datetime.now(HOTEL_TZ).date()
