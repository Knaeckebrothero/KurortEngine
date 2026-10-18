"""Reservations area: search, detail, create/edit/cancel, availability, room plan."""

from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kurort_app.models import (
    CANCELLED,
    CHECKED_IN,
    CHECKED_OUT,
    NO_SHOW,
    RESERVED,
    AuditEvent,
    Guest,
    Reservation,
    ReservationGuest,
    Room,
)
from kurort_app.services.availability import free_rooms, is_room_free, overlaps
from tests.app.conftest import BUSINESS_DATE

D = BUSINESS_DATE


def _room(session: Session, number: str) -> Room:
    return session.scalar(select(Room).where(Room.number == number))


def _first(session: Session, *where) -> Reservation:
    return session.scalars(select(Reservation).where(*where).order_by(Reservation.id)).first()


def _book(
    session: Session,
    room: Room,
    arrival: date,
    departure: date,
    *,
    status: str = RESERVED,
    last_name: str = "Testgast",
    code: str | None = None,
) -> Reservation:
    guest = Guest(first_name="Tina", last_name=last_name, birth_date=date(1960, 5, 1))
    reservation = Reservation(
        code=code or f"T-{room.number}-{arrival:%m%d}-{status[:3]}",
        room=room,
        arrival=arrival,
        departure=departure,
        status=status,
        rate_total=room.nightly_rate * (departure - arrival).days,
    )
    reservation.guests.append(ReservationGuest(guest=guest, is_primary=True, position=0))
    session.add(reservation)
    session.commit()
    return reservation


def _free_room_for(session: Session, arrival: date, departure: date, capacity: int = 2) -> Room:
    return next(r for r in free_rooms(session, arrival, departure) if r.max_occupancy >= capacity)


def _new_form(**overrides: str) -> dict[str, str]:
    form = {
        "anreise": (D + timedelta(days=60)).isoformat(),
        "abreise": (D + timedelta(days=67)).isoformat(),
        "zimmer": "",
        "kanal": "phone",
        "eta": "15:30",
        "paket": "B",
        "notizen": "Ruhiges Zimmer gewünscht.",
        "vorname": "Marianne",
        "nachname": "von der Lindenberg-Steinberg",
        "geburtsdatum": "1951-03-09",
        "nationalitaet": "DE",
        "strasse": "Am Kurpark 3",
        "plz": "63619",
        "ort": "Bad Orb",
        "land": "DE",
        "email": "marianne@example.de",
        "telefon": "+49 6052 123",
    }
    form.update(overrides)
    return form


# ---------------------------------------------------------------------------
# Availability service
# ---------------------------------------------------------------------------


def test_overlaps_treats_back_to_back_as_free():
    assert not overlaps(D, D + timedelta(days=3), D + timedelta(days=3), D + timedelta(days=5))
    assert not overlaps(D + timedelta(days=3), D + timedelta(days=5), D, D + timedelta(days=3))
    assert overlaps(D, D + timedelta(days=3), D + timedelta(days=2), D + timedelta(days=4))
    assert overlaps(D, D + timedelta(days=10), D + timedelta(days=2), D + timedelta(days=4))


def test_room_availability_rules(db):
    room = Room(
        number="901", category="Doppelzimmer", floor=9, max_occupancy=2, nightly_rate=Decimal("100")
    )
    db.add(room)
    db.commit()
    stay = _book(db, room, D + timedelta(days=2), D + timedelta(days=5))

    assert not is_room_free(db, room.id, D + timedelta(days=4), D + timedelta(days=6))
    assert is_room_free(db, room.id, D, D + timedelta(days=2)), "departure-day arrival is allowed"
    assert is_room_free(db, room.id, D + timedelta(days=5), D + timedelta(days=7))
    assert is_room_free(
        db, room.id, D + timedelta(days=3), D + timedelta(days=4), exclude_reservation_id=stay.id
    ), "editing a stay must not collide with itself"

    for status in (CANCELLED, NO_SHOW):
        stay.status = status
        db.commit()
        assert is_room_free(db, room.id, D + timedelta(days=3), D + timedelta(days=4)), status
    stay.status = CHECKED_IN
    db.commit()
    assert room not in free_rooms(db, D + timedelta(days=3), D + timedelta(days=4))


# ---------------------------------------------------------------------------
# List / search
# ---------------------------------------------------------------------------


def test_list_defaults_to_current_and_upcoming(client, seeded):
    past = _first(seeded, Reservation.departure < D - timedelta(days=3))
    arriving = _first(seeded, Reservation.arrival == D, Reservation.status == RESERVED)
    html = client.get("/reservierungen").text
    assert arriving.code in html
    assert past.code not in html
    assert "Aktuelle und kommende Aufenthalte" in html
    assert f'href="/check-in/{arriving.id}"' in html


def test_search_by_guest_name_is_case_insensitive_and_includes_past(client, seeded):
    past = _first(seeded, Reservation.departure < D - timedelta(days=3))
    last_name = past.primary_guest.last_name
    html = client.get("/reservierungen", params={"q": last_name.lower()}).text
    assert past.code in html


def test_search_by_full_name(client, seeded):
    target = _first(seeded, Reservation.status == CHECKED_IN)
    guest = target.primary_guest
    html = client.get("/reservierungen", params={"q": f"{guest.first_name} {guest.last_name}"}).text
    assert target.code in html


def test_search_by_code(client, seeded):
    target = _first(seeded, Reservation.status == CHECKED_OUT)
    html = client.get("/reservierungen", params={"q": target.code}).text
    assert target.code in html
    assert 'muted">1 Treffer' in html


def test_search_by_room_number(client, seeded):
    room = _room(seeded, "203")
    in_room = seeded.scalars(select(Reservation).where(Reservation.room_id == room.id)).all()
    code_hits = seeded.scalars(
        select(Reservation).where(Reservation.code.contains("203"), Reservation.room_id != room.id)
    ).all()
    html = client.get("/reservierungen", params={"q": "203"}).text
    assert f'muted">{len(in_room) + len(code_hits)} Treffer' in html
    assert html.count("<strong>203</strong>") == len(in_room)
    for r in in_room:
        assert r.code in html


def test_search_escapes_like_wildcards(client, seeded):
    html = client.get("/reservierungen", params={"q": "%"}).text
    assert "Keine Reservierung gefunden" in html


def test_status_filter_and_counts(client, seeded):
    cancelled = seeded.scalars(select(Reservation).where(Reservation.status == CANCELLED)).all()
    html = client.get("/reservierungen", params={"status": CANCELLED, "alle": "1"}).text
    for r in cancelled:
        assert r.code in html
    rows = re.findall(r'<span class="badge [a-z]*">([^<]+)</span>', html)
    assert rows and set(rows) == {"Storniert"}


def test_htmx_request_returns_results_fragment(client, seeded):
    response = client.get("/reservierungen", params={"q": "müller"}, headers={"HX-Request": "true"})
    assert response.status_code == 200
    assert "<html" not in response.text
    assert 'id="results"' in response.text


def test_pagination(client, seeded):
    html = client.get("/reservierungen", params={"alle": "1"}).text
    assert "Seite 1 von" in html
    page2 = client.get("/reservierungen", params={"alle": "1", "seite": "2"}).text
    assert "Seite 2 von" in page2
    assert client.get("/reservierungen", params={"seite": "abc"}).status_code == 200


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------


def test_detail_for_arrival_offers_check_in(client, seeded):
    target = _first(seeded, Reservation.arrival == D, Reservation.status == RESERVED)
    html = client.get(f"/reservierungen/{target.id}").text
    assert target.code in html
    assert f'href="/check-in/{target.id}"' in html
    assert f'href="/reservierungen/{target.id}/bearbeiten"' in html
    assert "stornieren" in html


def test_detail_shows_blockers(client, seeded):
    missing_birth = seeded.scalars(
        select(Reservation)
        .join(ReservationGuest)
        .join(Guest)
        .where(Reservation.arrival == D, Guest.birth_date.is_(None))
    ).first()
    html = client.get(f"/reservierungen/{missing_birth.id}").text
    assert "Geburtsdatum fehlt" in html


def test_detail_history_includes_check_in_trail(client, seeded):
    """Meldeschein events are recorded per stay guest; the stay's history must show them."""
    target = _first(seeded, Reservation.arrival == D, Reservation.status == RESERVED)
    if any(not rg.guest.birth_date for rg in target.guests):
        target = seeded.scalars(
            select(Reservation)
            .where(Reservation.arrival == D, Reservation.status == RESERVED)
            .order_by(Reservation.id.desc())
        ).first()
    client.post(f"/check-in/{target.id}/avs/alle", follow_redirects=False)
    html = client.get(f"/reservierungen/{target.id}").text
    assert "In AVS gedruckt:" in html
    assert "Noch keine Einträge" not in html


def test_detail_for_in_house_offers_check_out_and_signature(client, seeded):
    target = seeded.scalars(
        select(Reservation)
        .join(ReservationGuest)
        .where(
            Reservation.status == CHECKED_IN,
            ReservationGuest.meldeschein_status == "gedruckt",
        )
        .order_by(Reservation.id)
    ).first()
    html = client.get(f"/reservierungen/{target.id}").text
    assert f'href="/check-out/{target.id}"' in html
    assert "Unterschrift erfassen" in html
    assert ".pdf" not in html and "Kurkarte" not in html
    assert "/bearbeiten" not in html


def test_detail_unknown_id_is_404(client, seeded):
    response = client.get("/reservierungen/999999")
    assert response.status_code == 404
    assert "nicht gefunden" in response.text


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_reservation(client, seeded):
    arrival, departure = D + timedelta(days=60), D + timedelta(days=67)
    room = _free_room_for(seeded, arrival, departure, capacity=2)
    form = _new_form(
        zimmer=room.number, mitreisende_1_vorname="Klaus", mitreisende_1_geburtsdatum="1949-11-02"
    )
    response = client.post("/reservierungen/neu", data=form, follow_redirects=False)
    assert response.status_code == 303, response.text
    location = response.headers["location"]
    new_id = int(re.match(r"/reservierungen/(\d+)\?", location).group(1))

    seeded.expire_all()
    created = seeded.get(Reservation, new_id)
    assert created.status == RESERVED
    assert created.room_id == room.id
    assert created.rate_total == room.nightly_rate * 7
    assert created.package_code == "B"
    assert created.channel == "phone"
    assert re.fullmatch(rf"R-{arrival:%y%m}-\d{{4}}", created.code)
    assert [g.guest.first_name for g in created.guests] == ["Marianne", "Klaus"]
    assert created.guests[1].guest.last_name == "von der Lindenberg-Steinberg"
    assert created.guests[0].is_primary
    event = seeded.scalar(select(AuditEvent).where(AuditEvent.entity_id == str(new_id)))
    assert event.action == "reservation.created"

    page = client.get(location)
    assert "angelegt" in page.text
    assert created.code in page.text


def test_create_rejects_occupied_room(client, seeded):
    occupied = _first(
        seeded, Reservation.status == CHECKED_IN, Reservation.departure > D + timedelta(days=2)
    )
    form = _new_form(
        anreise=D.isoformat(),
        abreise=(D + timedelta(days=2)).isoformat(),
        zimmer=occupied.room.number,
        vorname="Peter",
        nachname="Konflikt",
    )
    before = seeded.scalar(select(func.count()).select_from(Reservation))
    response = client.post("/reservierungen/neu", data=form)
    assert response.status_code == 422
    assert "bereits belegt" in response.text
    assert seeded.scalar(select(func.count()).select_from(Reservation)) == before


def test_create_validation_errors_are_reported_in_german(client, seeded):
    form = _new_form(
        vorname="",
        nachname="",
        anreise=(D + timedelta(days=10)).isoformat(),
        abreise=(D + timedelta(days=10)).isoformat(),
        email="kein-at",
        geburtsdatum="2099-01-01",
    )
    response = client.post("/reservierungen/neu", data=form)
    assert response.status_code == 422
    text = response.text
    for message in (
        "Vorname fehlt.",
        "Nachname fehlt.",
        "Abreise muss nach der Anreise liegen.",
        "E-Mail-Adresse ist ungültig.",
        "Geburtsdatum liegt in der Zukunft.",
        "Bitte ein Zimmer wählen.",
    ):
        assert message in text
    assert 'id="vorname"' in text and 'aria-invalid="true"' in text
    assert 'value="kein-at"' in text, "entered data is preserved"


def test_create_rejects_past_arrival_and_overfull_room(client, seeded):
    single = seeded.scalar(select(Room).where(Room.max_occupancy == 1).order_by(Room.number))
    form = _new_form(
        anreise=(D - timedelta(days=2)).isoformat(),
        zimmer=single.number,
        mitreisende_1_vorname="Zweite",
    )
    response = client.post("/reservierungen/neu", data=form)
    assert response.status_code == 422
    assert "Anreise liegt in der Vergangenheit." in response.text
    assert "höchstens 1 Person" in response.text


def test_walk_in_prefill(client, seeded):
    html = client.get("/reservierungen/neu", params={"walkin": "1"}).text
    assert f'name="anreise" type="date" value="{D.isoformat()}"' in html
    assert f'name="abreise" type="date" value="{(D + timedelta(days=1)).isoformat()}"' in html
    assert '<option value="walk-in" selected>' in html
    assert "Walk-in aufnehmen" in html


def test_walk_in_creates_today_arrival(client, seeded):
    room = _free_room_for(seeded, D, D + timedelta(days=1), capacity=1)
    form = _new_form(
        anreise=D.isoformat(),
        abreise=(D + timedelta(days=1)).isoformat(),
        zimmer=room.number,
        kanal="walk-in",
        paket="",
        eta="",
    )
    response = client.post("/reservierungen/neu", data=form, follow_redirects=False)
    assert response.status_code == 303, response.text
    created = seeded.scalars(select(Reservation).where(Reservation.channel == "walk-in")).one()
    assert created.arrival == D and created.status == RESERVED and created.package_code is None


def test_prefill_from_room_plan(client, seeded):
    html = client.get("/reservierungen/neu", params={"zimmer": "305", "anreise": "2026-11-20"}).text
    assert 'value="2026-11-20"' in html
    assert 'value="2026-11-21"' in html
    assert '<option value="305" selected>' in html


def test_room_options_partial_lists_only_free_rooms(client, seeded):
    arrival, departure = D, D + timedelta(days=2)
    free = {r.number for r in free_rooms(seeded, arrival, departure)}
    html = client.get(
        "/reservierungen/verfuegbare-zimmer",
        params={"anreise": arrival.isoformat(), "abreise": departure.isoformat()},
    ).text
    offered = set(re.findall(r'<option value="(\d{3})"', html))
    assert offered == free
    assert f'<span class="num">{len(free)}</span> von 33 Zimmern frei' in html


def test_room_options_partial_flags_taken_selection(client, seeded):
    occupied = _first(
        seeded, Reservation.status == CHECKED_IN, Reservation.departure > D + timedelta(days=2)
    )
    html = client.get(
        "/reservierungen/verfuegbare-zimmer",
        params={
            "anreise": D.isoformat(),
            "abreise": (D + timedelta(days=2)).isoformat(),
            "zimmer": occupied.room.number,
        },
    ).text
    assert "nicht frei" in html
    assert "– belegt" in html


# ---------------------------------------------------------------------------
# Edit / cancel
# ---------------------------------------------------------------------------


def _future_reserved(session: Session) -> Reservation:
    return _first(
        session, Reservation.status == RESERVED, Reservation.arrival > D + timedelta(days=5)
    )


def test_edit_moves_stay_and_records_changes(client, seeded):
    target = _future_reserved(seeded)
    arrival, departure = D + timedelta(days=80), D + timedelta(days=83)
    room = _free_room_for(seeded, arrival, departure, capacity=len(target.guests))
    form = {
        "anreise": arrival.isoformat(),
        "abreise": departure.isoformat(),
        "zimmer": room.number,
        "kanal": "phone" if target.channel == "email" else "email",
        "eta": "17:00",
        "paket": "",
        "notizen": "Umgebucht auf Wunsch.",
        "reservierung": str(target.id),
    }
    response = client.post(
        f"/reservierungen/{target.id}/bearbeiten", data=form, follow_redirects=False
    )
    assert response.status_code == 303, response.text
    seeded.expire_all()
    updated = seeded.get(Reservation, target.id)
    assert (updated.arrival, updated.departure, updated.room_id) == (arrival, departure, room.id)
    assert updated.rate_total == room.nightly_rate * 3
    assert updated.notes == "Umgebucht auf Wunsch."
    event = seeded.scalar(select(AuditEvent).where(AuditEvent.action == "reservation.updated"))
    assert "Zeitraum" in event.summary and "Kanal" in event.summary


def test_edit_keeps_own_room_without_self_conflict(client, seeded):
    target = _future_reserved(seeded)
    form = {
        "anreise": target.arrival.isoformat(),
        "abreise": target.departure.isoformat(),
        "zimmer": target.room.number,
        "kanal": target.channel,
        "eta": "",
        "paket": target.package_code or "",
        "notizen": "Nur eine Notiz.",
    }
    response = client.post(
        f"/reservierungen/{target.id}/bearbeiten", data=form, follow_redirects=False
    )
    assert response.status_code == 303, response.text
    seeded.expire_all()
    assert seeded.get(Reservation, target.id).notes == "Nur eine Notiz."


def test_edit_rejects_conflicting_room(client, seeded):
    target = _future_reserved(seeded)
    other = next(
        r
        for r in seeded.scalars(
            select(Reservation)
            .where(Reservation.status == RESERVED, Reservation.arrival > D + timedelta(days=5))
            .order_by(Reservation.id)
        )
        if r.room_id != target.room_id and r.room.max_occupancy >= len(target.guests)
    )
    form = {
        "anreise": other.arrival.isoformat(),
        "abreise": other.departure.isoformat(),
        "zimmer": other.room.number,
        "kanal": "direct",
    }
    response = client.post(f"/reservierungen/{target.id}/bearbeiten", data=form)
    assert response.status_code == 422
    assert "bereits belegt" in response.text


@pytest.mark.parametrize("status", [CHECKED_IN, CHECKED_OUT])
def test_edit_and_cancel_only_for_reserved(client, seeded, status):
    target = _first(seeded, Reservation.status == status)
    edit = client.get(f"/reservierungen/{target.id}/bearbeiten", follow_redirects=False)
    assert edit.status_code == 303
    cancel = client.post(f"/reservierungen/{target.id}/stornieren", follow_redirects=False)
    assert cancel.status_code == 303
    seeded.expire_all()
    assert seeded.get(Reservation, target.id).status == status


def test_cancel_frees_the_room(client, seeded):
    target = _future_reserved(seeded)
    assert not is_room_free(seeded, target.room_id, target.arrival, target.departure)
    response = client.post(
        f"/reservierungen/{target.id}/stornieren",
        data={"grund": "Krankheit"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    seeded.expire_all()
    assert seeded.get(Reservation, target.id).status == CANCELLED
    assert is_room_free(seeded, target.room_id, target.arrival, target.departure)
    event = seeded.scalar(select(AuditEvent).where(AuditEvent.action == "reservation.cancelled"))
    assert "Krankheit" in event.summary
    detail = client.get(response.headers["location"]).text
    assert "storniert" in detail and "Krankheit" in detail


# ---------------------------------------------------------------------------
# Room plan
# ---------------------------------------------------------------------------


def test_room_plan_renders_all_rooms_and_today(client, seeded):
    html = client.get("/zimmerplan").text
    rooms = seeded.scalars(select(Room)).all()
    for room in rooms:
        assert f'<strong class="num">{room.number}</strong>' in html
    assert html.count('aria-current="date"') >= 1
    assert "Di 13.10. – Mo 26.10.2026" in html
    in_house = _first(seeded, Reservation.status == CHECKED_IN)
    assert f'href="/reservierungen/{in_house.id}"' in html
    assert "s-checked_in" in html and "s-reserved" in html


def test_room_plan_bar_geometry(client, db):
    room = Room(
        number="901", category="Doppelzimmer", floor=9, max_occupancy=2, nightly_rate=Decimal("100")
    )
    db.add(room)
    db.commit()
    start = D - timedelta(days=1)
    stay = _book(db, room, start + timedelta(days=2), start + timedelta(days=5), last_name="Balken")
    early = _book(
        db,
        room,
        start - timedelta(days=3),
        start + timedelta(days=1),
        status=CHECKED_IN,
        last_name="Links",
    )
    late = _book(
        db, room, start + timedelta(days=12), start + timedelta(days=20), last_name="Rechts"
    )
    cancelled = _book(
        db,
        room,
        start + timedelta(days=6),
        start + timedelta(days=8),
        status=CANCELLED,
        last_name="Weg",
    )

    html = client.get("/zimmerplan").text

    def bar(reservation: Reservation) -> str:
        match = re.search(
            rf'<a class="(plan-bar[^"]*)"\s+style="grid-column: (\d+) / (\d+)"\s+href="/reservierungen/{reservation.id}"',
            html,
        )
        assert match, reservation.code
        return match.group(1), int(match.group(2)), int(match.group(3))

    # arrival day index 2 → second half (half 5) → line 7; departure day 5 → line 2 + 11 = 13
    assert bar(stay)[1:] == (7, 13)
    cls, start_line, end_line = bar(early)
    assert "clip-left" in cls and start_line == 2 and end_line == 5
    cls, start_line, end_line = bar(late)
    assert "clip-right" in cls and end_line == 30
    assert f"/reservierungen/{cancelled.id}" not in html
    # free day cells link to a prefilled new reservation (cancelled stay does not block)
    assert (
        f"/reservierungen/neu?zimmer=901&amp;anreise={(start + timedelta(days=6)).isoformat()}"
        in html
    )


def test_room_plan_navigation(client, seeded):
    html = client.get("/zimmerplan", params={"von": "2026-11-01"}).text
    assert "So 01.11. – Sa 14.11.2026" in html
    assert 'href="/zimmerplan?von=2026-10-25"' in html
    assert 'href="/zimmerplan?von=2026-11-08"' in html
    assert client.get("/zimmerplan", params={"von": "kaputt"}).status_code == 200
