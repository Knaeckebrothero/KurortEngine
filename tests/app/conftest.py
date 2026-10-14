"""Fixtures for the web app: a real Postgres, migrated once per session.

Point KURORT_TEST_DATABASE_URL at a server you can create databases on
(default: the podman container from docs/ops/local-development.md). The
database named in the URL is dropped and recreated per test session. Every
test starts from empty tables; use the ``seeded`` fixture for demo data.
Without a reachable server the app tests are skipped, not failed.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

# The suite exercises the screens without a login; tests/app/test_auth.py
# builds its own app with KURORT_AUTH=oidc against a fake provider.
os.environ["KURORT_AUTH"] = "off"

TEST_DB_URL = os.environ.get(
    "KURORT_TEST_DATABASE_URL", "postgresql+psycopg://kurort:kurort@127.0.0.1:55432/kurort_test"
)
BUSINESS_DATE = date(2026, 10, 14)  # a Wednesday; seed data is laid out around it
TABLES = (
    "audit_events",
    "kurtaxe_assessments",
    "reservation_guests",
    "reservations",
    "guests",
    "rooms",
)


def _reset_caches() -> None:
    from kurort_app.config import get_settings
    from kurort_app.db import get_engine, get_sessionmaker

    for fn in (get_settings, get_engine, get_sessionmaker):
        fn.cache_clear()


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    url = make_url(TEST_DB_URL)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"no test Postgres at {url.render_as_string(hide_password=True)}: {exc}")
    finally:
        admin.dispose()

    rendered = url.render_as_string(hide_password=False)
    os.environ["KURORT_DATABASE_URL"] = rendered
    os.environ["KURORT_TODAY"] = BUSINESS_DATE.isoformat()
    _reset_caches()
    from kurort_app.migrate import upgrade

    upgrade(rendered)
    yield rendered
    from kurort_app.db import get_engine

    get_engine().dispose()


@pytest.fixture
def db(database_url: str) -> Iterator[Session]:
    from kurort_app.db import get_engine, get_sessionmaker

    with get_engine().begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seeded(db: Session) -> Session:
    from kurort_app.seed import seed_demo_data

    seed_demo_data(db, anchor=BUSINESS_DATE)
    return db


@pytest.fixture
def client(db: Session):
    from fastapi.testclient import TestClient

    from kurort_app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
