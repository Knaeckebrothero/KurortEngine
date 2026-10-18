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


def test_meldeschein_avs_data_round_trip(scratch_url: str):
    """AC-10: migrate existing printed forms, not just an empty schema."""
    from alembic import command
    from sqlalchemy.exc import IntegrityError

    cfg = alembic_config(scratch_url)
    command.upgrade(cfg, "0001")
    engine = create_engine(scratch_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO guests (id, first_name, last_name, nationality, country) VALUES (1, 'Ada', 'Weber', 'DE', 'DE')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO reservations (id, code, arrival, departure, status, channel, rate_total) VALUES (1, 'MIG-1', '2026-10-14', '2026-10-15', 'reserved', 'direct', 89)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO reservation_guests (id, reservation_id, guest_id, is_primary, position, meldeschein_status, meldeschein_generated_at) VALUES (1, 1, 1, true, 0, 'erzeugt', '2026-10-14 10:00:00+00')"
            )
        )
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT meldeschein_status FROM reservation_guests")) == "gedruckt"
        assert (
            conn.scalar(text("SELECT meldeschein_printed_at FROM reservation_guests")) is not None
        )
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(text("UPDATE reservation_guests SET meldeschein_status = 'erzeugt'"))
    columns = _schema(scratch_url)["reservation_guests"]
    assert not {
        "meldeschein_pdf",
        "meldeschein_form_id",
        "kurkarte_code",
        "kurkarte_qr_payload",
        "kurkarte_issued_at",
    }.intersection(columns)
    command.downgrade(cfg, "0001")
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT meldeschein_status FROM reservation_guests")) == "erzeugt"
        assert (
            conn.scalar(text("SELECT meldeschein_generated_at FROM reservation_guests")) is not None
        )
    engine.dispose()
