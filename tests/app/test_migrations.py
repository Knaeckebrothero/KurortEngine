"""Every migration applies, rolls back and applies again, as one linear chain.

Runs on its own database next to the test database, so a feature's new
migration is covered here without adding anything to this file.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from kurort_app.migrate import alembic_config

ROUND_TRIP_DB = "kurort_test_migrations"


def test_migrations_form_one_linear_chain():
    heads = ScriptDirectory.from_config(alembic_config()).get_heads()
    assert len(heads) == 1, f"several heads {heads}: re-point down_revision onto main's newest"


@pytest.fixture
def scratch_url(database_url: str) -> Iterator[str]:
    url = make_url(database_url).set(database=ROUND_TRIP_DB)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{ROUND_TRIP_DB}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{ROUND_TRIP_DB}"'))
    rendered = url.render_as_string(hide_password=False)
    yield rendered
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{ROUND_TRIP_DB}" WITH (FORCE)'))
    admin.dispose()


def _schema(url: str) -> dict[str, list[str]]:
    engine = create_engine(url)
    try:
        insp = inspect(engine)
        return {
            table: sorted(col["name"] for col in insp.get_columns(table))
            for table in insp.get_table_names()
            if table != "alembic_version"
        }
    finally:
        engine.dispose()


def test_upgrade_downgrade_upgrade(scratch_url: str):
    from alembic import command

    cfg = alembic_config(scratch_url)
    command.upgrade(cfg, "head")
    migrated = _schema(scratch_url)
    assert migrated

    command.downgrade(cfg, "base")
    assert _schema(scratch_url) == {}

    command.upgrade(cfg, "head")
    assert _schema(scratch_url) == migrated
