"""App wiring: probes, migrations, seed and the shell render."""

from __future__ import annotations

import itertools

from sqlalchemy import func, select

from kurort_app.models import CHECKED_IN, CHECKED_OUT, RESERVED, Reservation, Room
from tests.app.conftest import BUSINESS_DATE


def test_healthz(client):
    assert client.get("/healthz").text == "ok\n"


def test_readyz_reports_database(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.text == "ok\n"


def test_seed_lays_out_a_consistent_hotel(seeded):
    assert seeded.scalar(select(func.count()).select_from(Room)) == 33
    reservations = seeded.scalars(select(Reservation)).all()
    assert len(reservations) > 150
    for r in reservations:
        if r.departure < BUSINESS_DATE:
            assert r.status in (CHECKED_OUT, "no_show", "cancelled"), r.code
        if r.arrival > BUSINESS_DATE:
            assert r.status in (RESERVED, "cancelled"), r.code
    assert any(r.arrival == BUSINESS_DATE and r.status == RESERVED for r in reservations)
    assert any(r.status == CHECKED_IN for r in reservations)


def test_seed_never_double_books_a_room(seeded):
    by_room: dict[int, list[Reservation]] = {}
    for r in seeded.scalars(select(Reservation).where(Reservation.status != "cancelled")):
        by_room.setdefault(r.room_id, []).append(r)
    for stays in by_room.values():
        stays.sort(key=lambda r: r.arrival)
        for a, b in itertools.pairwise(stays):
            assert a.departure <= b.arrival, (a.code, b.code)


def test_seed_if_empty_is_idempotent(seeded):
    from kurort_app.seed import seed_demo_data

    assert seed_demo_data(seeded, if_empty=True) == 0


def test_dashboard_renders_shell(client, seeded):
    response = client.get("/")
    assert response.status_code == 200
    assert "Hotel Rheinland" in response.text
    assert "Mittwoch, 14. Oktober 2026" in response.text


def test_business_date_is_the_hotels_local_date(monkeypatch):
    """At 23:30 UTC it is already the next day in Bad Orb."""
    from datetime import UTC, datetime

    import kurort_app.config as config

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 14, 23, 30, tzinfo=UTC).astimezone(tz)

    monkeypatch.setattr(config, "datetime", FrozenDatetime)
    monkeypatch.setattr(config.get_settings(), "today", None)
    assert config.today().isoformat() == "2026-10-15"
