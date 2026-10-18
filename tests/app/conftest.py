"""Fixtures for the web app: a real Postgres, migrated once per session.

Point KURORT_TEST_DATABASE_URL at a server you can create databases on
(default: the podman container from docs/ops/local-development.md). When that
variable is unset and the default server does not answer, an embedded Postgres
from the ``pgserver`` package is started instead, if installed
(``pip install -e ".[web,dev,test-pg]"``). The database named in the URL is
dropped and recreated per test session. Every test starts from empty tables;
use the ``seeded`` fixture for demo data. Without a reachable server the app
tests are skipped, or fail when KURORT_TEST_REQUIRE_DB=1.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

# The suite exercises the screens without a login; tests/app/test_auth.py
# builds its own app with KURORT_AUTH=oidc against a fake provider.
os.environ["KURORT_AUTH"] = "off"

DEFAULT_TEST_DB_URL = "postgresql+psycopg://kurort:kurort@127.0.0.1:55432/kurort_test"
BUSINESS_DATE = date(2026, 10, 14)  # a Wednesday; seed data is laid out around it
REQUIRE_DB = os.environ.get("KURORT_TEST_REQUIRE_DB") == "1"


def _answers(url) -> bool:
    engine = create_engine(url.set(database="postgres"), connect_args={"connect_timeout": 3})
    try:
        with engine.connect():
            return True
    except Exception:  # noqa: BLE001 - any failure means "not this server"
        return False
    finally:
        engine.dispose()


def _test_db_url() -> str:
    explicit = os.environ.get("KURORT_TEST_DATABASE_URL")
    if explicit or _answers(make_url(DEFAULT_TEST_DB_URL)):
        return explicit or DEFAULT_TEST_DB_URL
    try:
        import pgserver
    except ImportError:
        return DEFAULT_TEST_DB_URL
    # Workspaces without podman or a system Postgres: a throwaway embedded
    # server, stopped and deleted when the test process exits.
    server = pgserver.get_server(tempfile.mkdtemp(prefix="kurort-pg-"), cleanup_mode="delete")
    socket_dir = make_url(server.get_uri()).query["host"]
    return f"postgresql+psycopg://postgres@/kurort_test?host={socket_dir}"


def _reset_caches() -> None:
    from kurort_app.config import get_settings
    from kurort_app.db import get_engine, get_sessionmaker

    for fn in (get_settings, get_engine, get_sessionmaker):
        fn.cache_clear()


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    url = make_url(_test_db_url())
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)'))
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    except Exception as exc:  # noqa: BLE001
        reason = f"no test Postgres at {url.render_as_string(hide_password=True)}: {exc}"
        if REQUIRE_DB:
            pytest.fail(reason)
        pytest.skip(reason)
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

    # Every table the migrations created, so new features need no list here.
    with get_engine().begin() as conn:
        tables = conn.scalars(
            text(
                "SELECT quote_ident(tablename) FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
            )
        ).all()
        conn.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
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
