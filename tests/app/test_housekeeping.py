"""F2 room cleaning status, front-desk integration and limited staff."""

import re
from datetime import time, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from kurort_app.models import AuditEvent, Reservation, Room
from tests.app.conftest import BUSINESS_DATE as D
from tests.app.test_engine_adapter import make_stay


def cards(html):
    return re.findall(r"<article\b.*?</article>", html, re.S)


def events(db):
    db.expire_all()
    return db.scalars(select(AuditEvent).where(AuditEvent.action == "room.status_changed")).all()


def test_list_shows_all_rooms_without_guest_names(client, seeded):
    response = client.get("/zimmerstatus")
    assert response.status_code == 200
    found = cards(response.text)
    rooms = seeded.scalars(select(Room)).all()
    assert len(found) == len(rooms) == 33
    for room in rooms:
        card = next(c for c in found if f'data-room-id="{room.id}"' in c)
        assert room.number in card and room.category in card
        assert 'data-status="' in card and 'class="hk-situation"' in card
    for stay in seeded.scalars(
        select(Reservation).where((Reservation.arrival == D) | (Reservation.departure == D))
    ):
        for rg in stay.guests:
            assert rg.guest.full_name not in response.text


def test_status_database_default_and_constraint(db):
    room = make_stay(db, [{}]).room
    assert getattr(room, "housekeeping_status", None) == "clean"
    with pytest.raises(IntegrityError):
        db.execute(text("UPDATE rooms SET housekeeping_status = 'unknown'"))
        db.commit()
    db.rollback()


def test_manual_status_prg_htmx_audit_and_noop(client, db):
    room = make_stay(db, [{}]).room
    assert client.post(f"/zimmerstatus/{room.id}/dirty", follow_redirects=False).status_code == 303
    response = client.post(f"/zimmerstatus/{room.id}/clean", follow_redirects=False)
    assert response.status_code == 303 and "notice=" in response.headers["location"]
    db.refresh(room)
    assert room.housekeeping_status == "clean"
    assert room.housekeeping_changed_at is not None and room.housekeeping_changed_by == "rezeption"
    event = events(db)[-1]
    assert event.entity == "room" and event.entity_id == str(room.id)
    assert event.payload == {"from": "dirty", "to": "clean", "reason": "manual", "note": None}
    assert event.summary == "Zimmer 204: schmutzig → sauber"
    count = len(events(db))
    stamp = room.housekeeping_changed_at
    fragment = client.post(f"/zimmerstatus/{room.id}/clean", headers={"HX-Request": "true"})
    assert fragment.status_code == 200 and len(cards(fragment.text)) == 1
    assert "<html" not in fragment.text and "Zuletzt" in fragment.text
    assert len(events(db)) == count
    db.refresh(room)
    assert room.housekeeping_changed_at == stamp
    assert (
        'hx-swap="outerHTML"' in fragment.text and f'hx-target="#room-{room.id}"' in fragment.text
    )


def test_note_and_return_path(client, db):
    room = make_stay(db, [{}]).room
    client.post(f"/zimmerstatus/{room.id}/out_of_order", data={"notiz": "Heizung defekt"})
    db.refresh(room)
    assert room.housekeeping_note == "Heizung defekt"
    assert "Heizung defekt" in client.get("/zimmerstatus").text
    response = client.post(
        f"/zimmerstatus/{room.id}/dirty", data={"zurueck": "//evil.example"}, follow_redirects=False
    )
    assert response.headers["location"].startswith("/zimmerstatus?")
    db.refresh(room)
    assert room.housekeeping_note is None
    assert events(db)[-1].payload["reason"] == "manual"


@pytest.mark.parametrize("suffix,code", [("unknown", 400), ("clean", 404)])
def test_unknown_status_or_room(client, db, suffix, code):
    response = client.post(f"/zimmerstatus/99999/{suffix}")
    assert response.status_code == code
    if code == 400:
        assert response.json()["detail"] == "Unbekannter Zimmerstatus."


def test_filters_counts_and_room_sort(client, seeded):
    rooms = seeded.scalars(select(Room).order_by(Room.number)).all()
    client.post(f"/zimmerstatus/{rooms[0].id}/dirty")
    for query, expected in [
        ("etage=2", [r for r in rooms if r.floor == 2]),
        ("status=dirty", [r for r in rooms if r.housekeeping_status == "dirty"]),
    ]:
        seeded.expire_all()
        expected = (
            [r for r in rooms if r.floor == 2]
            if query == "etage=2"
            else [r for r in rooms if r.housekeeping_status == "dirty"]
        )
        response = client.get(f"/zimmerstatus?{query}")
        assert {int(v) for v in re.findall(r'data-room-id="(\d+)"', response.text)} == {
            r.id for r in expected
        }
    html = client.get("/zimmerstatus?sort=zimmer").text
    assert re.findall(r'data-room-id="(\d+)"', html) == [str(r.id) for r in rooms]
    for status in ("dirty", "clean", "inspected", "out_of_order"):
        count = sum(r.housekeeping_status == status for r in rooms)
        assert f'data-status-count="{status}">{count}</span>' in html


def test_situations_urgency_and_bulk_stayover(client, db):
    stay = make_stay(db, [{}], arrival=D - timedelta(days=1), nights=3)
    stay.status = "checked_in"
    db.commit()
    html = client.get("/zimmerstatus").text
    assert "Bleibe" in html
    response = client.post("/zimmerstatus/bleibe", follow_redirects=False)
    assert response.status_code == 303
    assert "1+Bleibezimmer" in response.headers["location"]
    db.refresh(stay.room)
    assert stay.room.housekeeping_status == "dirty"
    assert events(db)[-1].payload["reason"] == "stayover"
    again = client.post("/zimmerstatus/bleibe")
    assert "Keine Bleibezimmer zu setzen." in again.text
    for status in ("dirty", "out_of_order", "clean", "inspected"):
        client.post(f"/zimmerstatus/{stay.room_id}/{status}")
        stay.departure = D
        db.commit()
        client.post("/zimmerstatus/bleibe")
        db.refresh(stay.room)
        assert stay.room.housekeeping_status == status
    assert "Abreise heute" in client.get("/zimmerstatus").text
    stay.status = "checked_out"
    db.commit()
    assert "Abgereist" in client.get("/zimmerstatus").text
    arrival = make_stay(db, [{}], code="ARRIVING")
    assert "Abreise · Anreise heute" in client.get("/zimmerstatus").text
    stay.departure = D - timedelta(days=1)
    stay.arrival = D - timedelta(days=3)
    arrival.eta = time(14, 0)
    db.commit()
    assert "Anreise heute · ca. 14:00" in client.get("/zimmerstatus").text


def test_bulk_only_ready_stayovers_and_urgency_groups(client, db):
    from decimal import Decimal

    rooms = []
    for number, status in [
        ("101", "clean"),
        ("102", "dirty"),
        ("103", "out_of_order"),
        ("104", "inspected"),
        ("105", "dirty"),
        ("106", "dirty"),
    ]:
        room = Room(
            number=number,
            category="Einzelzimmer",
            floor=1,
            max_occupancy=1,
            nightly_rate=Decimal("80"),
            housekeeping_status=status,
        )
        db.add(room)
        rooms.append(room)
    db.flush()
    for index in range(4):
        db.add(
            Reservation(
                code=f"BLEIBE-{index}",
                room=rooms[index],
                arrival=D - timedelta(days=2),
                departure=D + timedelta(days=2),
                status="checked_in",
            )
        )
    db.add(
        Reservation(
            code="LEAVING",
            room=rooms[4],
            arrival=D - timedelta(days=2),
            departure=D,
            status="checked_out",
        )
    )
    db.add(
        Reservation(
            code="ARRIVING",
            room=rooms[5],
            arrival=D,
            departure=D + timedelta(days=2),
            status="reserved",
        )
    )
    db.commit()
    html = client.get("/zimmerstatus").text
    assert re.findall(r'data-room-id="(\d+)"', html) == [
        str(rooms[i].id) for i in (5, 4, 1, 2, 0, 3)
    ]
    response = client.post("/zimmerstatus/bleibe")
    assert "2 Bleibezimmer auf schmutzig gesetzt." in response.text
    db.expire_all()
    assert [r.housekeeping_status for r in rooms] == [
        "dirty",
        "dirty",
        "out_of_order",
        "dirty",
        "dirty",
        "dirty",
    ]
    assert len(events(db)) == 2
