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
    assert "Zimmer 204 ist sauber." in client.get(response.headers["location"]).text
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
    assert "<html" not in fragment.text and "· Rezeption</p>" in fragment.text
    assert len(events(db)) == count
    db.refresh(room)
    assert room.housekeeping_changed_at == stamp
    assert (
        'hx-swap="outerHTML settle:600ms"' in fragment.text
        and f'hx-target="#room-{room.id}"' in fragment.text
    )
    assert ">Außer Betrieb</button>" in fragment.text


def test_status_tap_updates_counts_and_bulk_out_of_band(client, db):
    from decimal import Decimal

    stay = make_stay(db, [{}], arrival=D - timedelta(days=1), nights=3)
    stay.status = "checked_in"
    db.add(Room(number="301", category="Suite", floor=3, max_occupancy=2, nightly_rate=Decimal(1)))
    db.commit()
    page = client.get(f"/zimmerstatus?etage={stay.room.floor}").text
    assert 'id="hk-count-clean" data-status-count="clean">1</span>' in page
    assert "(1, alle Etagen)" in page and "auf allen Etagen wird" in page
    fragment = client.post(
        f"/zimmerstatus/{stay.room_id}/dirty",
        headers={
            "HX-Request": "true",
            "HX-Current-URL": f"http://testserver/zimmerstatus?etage={stay.room.floor}",
        },
    ).text
    assert len(cards(fragment)) == 1
    assert 'id="hk-count-dirty" hx-swap-oob="true" data-status-count="dirty">1</span>' in fragment
    assert 'id="hk-count-clean" hx-swap-oob="true" data-status-count="clean">0</span>' in fragment
    bulk = fragment.split('id="hk-bulk" hx-swap-oob="true"', 1)[1]
    assert "disabled><span>Bleibezimmer auf schmutzig setzen" in bulk and "(0)" in bulk


def test_invalid_floor_filter_shows_all_floors(client, db):
    make_stay(db, [{}])
    response = client.get("/zimmerstatus?etage=x")
    assert response.status_code == 200 and len(cards(response.text)) == 1


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


def test_a_guest_checked_in_today_is_not_shown_as_free(client, db):
    stay = make_stay(db, [{}], arrival=D, nights=2)
    stay.status = "checked_in"
    db.commit()
    assert '<p class="hk-situation">Angereist</p>' in client.get("/zimmerstatus").text


def test_situations_urgency_and_bulk_stayover(client, db):
    stay = make_stay(db, [{}], arrival=D - timedelta(days=1), nights=3)
    stay.status = "checked_in"
    db.commit()
    html = client.get("/zimmerstatus").text
    assert '<p class="hk-situation">Bleiber</p>' in html
    assert '<form class="card" method="post" action="/zimmerstatus/bleibe">' in html
    assert "Ja, 1 Zimmer auf schmutzig setzen" in html and "alle Etagen" not in html
    response = client.post("/zimmerstatus/bleibe", follow_redirects=False)
    assert response.status_code == 303
    assert "1+Bleibezimmer" in response.headers["location"]
    db.refresh(stay.room)
    assert stay.room.housekeeping_status == "dirty"
    assert events(db)[-1].payload["reason"] == "stayover"
    assert 'action="/zimmerstatus/bleibe"' not in client.get("/zimmerstatus").text
    again = client.post("/zimmerstatus/bleibe")
    assert '<div class="notice info flash"' in again.text
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
    arrival.eta = time(15, 30)
    db.commit()
    assert "Abreise · Anreise heute · ca. 15:30" in client.get("/zimmerstatus").text
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


def test_checkout_marks_room_dirty_with_audit(client, db):
    stay = make_stay(db, [{}])
    stay.status = "checked_in"
    db.commit()
    response = client.post(
        f"/check-out/{stay.id}", data={"offen_geklaert": "1"}, follow_redirects=False
    )
    assert response.status_code == 303
    db.refresh(stay.room)
    assert stay.room.housekeeping_status == "dirty"
    assert events(db)[-1].payload["reason"] == "checkout"


def test_arrival_flag_and_checkin_blocker_action(client, db):
    stay = make_stay(db, [{}])
    room = stay.room
    client.post(f"/check-in/{stay.id}/avs/alle")
    client.post(f"/zimmerstatus/{room.id}/dirty")
    html = client.get("/").text
    assert "Zimmer noch nicht sauber" in html
    assert f'href="/zimmerstatus?etage={room.floor}#room-{room.id}"' in html
    summary = client.get(f"/check-in/{stay.id}/abschluss").text
    # The dirty room shows once: in the checklist's Zimmer row, with its button.
    assert "Als sauber markieren" in summary and f"{room.number} · Schmutzig" in summary
    assert f"Zimmer {room.number} ist noch nicht sauber." not in summary
    assert f'action="/zimmerstatus/{room.id}/clean"' in summary
    client.post(f"/check-in/{stay.id}/abschluss")
    db.refresh(stay)
    assert stay.status == "reserved"
    response = client.post(
        f"/zimmerstatus/{room.id}/clean",
        data={"zurueck": f"/check-in/{stay.id}/abschluss"},
        follow_redirects=False,
    )
    assert response.headers["location"].startswith(f"/check-in/{stay.id}/abschluss?")
    assert events(db)[-1].payload["reason"] == "checkin_blocker"
    assert "Zimmer noch nicht sauber" not in client.get("/").text
    client.post(f"/check-in/{stay.id}/abschluss")
    db.refresh(stay)
    assert stay.status == "checked_in"
    db.refresh(room)
    assert room.housekeeping_status == "clean", "check-in does not reset status"


@pytest.mark.parametrize("status", ["clean", "inspected"])
def test_ready_rooms_do_not_block_or_flag(client, db, status):
    from kurort_app.services import today

    stay = make_stay(db, [{}])
    client.post(f"/zimmerstatus/{stay.room_id}/{status}")
    db.expire_all()
    assert not today.checkin_blockers(db, stay)
    assert not any("Zimmer" in f.text for f in today.flags_for(db, "anreise", stay))


def test_out_of_order_flag_blocker_and_plan(client, db):
    stay = make_stay(db, [{}])
    client.post(f"/zimmerstatus/{stay.room_id}/out_of_order", data={"notiz": "Heizung defekt"})
    html = client.get("/").text
    assert "Zimmer außer Betrieb" in html
    assert f'href="/reservierungen/{stay.id}/bearbeiten"' in html
    client.post(f"/check-in/{stay.id}/avs/alle")
    summary = client.get(f"/check-in/{stay.id}/abschluss").text
    assert "bitte ein anderes Zimmer zuweisen." in summary
    assert "Als sauber markieren" not in summary
    client.post(f"/check-in/{stay.id}/abschluss")
    db.refresh(stay)
    assert stay.status == "reserved"
    plan = client.get("/zimmerplan").text
    row = plan.split(f'data-room-row="{stay.room.number}"', 1)[1].split('<div class="plan-row', 1)[
        0
    ]
    assert "Außer Betrieb" in row and 'title="Heizung defekt"' in row
    assert "/reservierungen/neu?zimmer=" not in row
    client.post(f"/zimmerstatus/{stay.room_id}/inspected")
    assert "Geprüft" in client.get("/zimmerplan").text


def test_housekeeping_limited_staff_home_navigation_and_forbidden(oidc_client, idp, db):
    from tests.app.auth_helpers import login

    room = make_stay(db, [{}]).room
    idp.claims.update(roles=["housekeeping"], preferred_username="s.klein", name="Sandra Klein")
    login(oidc_client)
    home = oidc_client.get("/", follow_redirects=False)
    assert home.status_code == 303 and home.headers["location"] == "/zimmerstatus"
    page = oidc_client.get("/zimmerstatus")
    assert page.status_code == 200
    menu = page.text.split('<nav class="rail-nav">')[1].split("</nav>")[0]
    assert re.findall(r'href="([^"]+)"', menu) == ["/zimmerstatus"]
    assert "assistant-bar" not in page.text and "Neue Reservierung" not in page.text
    oidc_client.post(f"/zimmerstatus/{room.id}/dirty")
    db.refresh(room)
    assert room.housekeeping_changed_by == "s.klein" and events(db)[-1].actor == "s.klein"
    for path in (
        "/anreisen",
        "/abreisen",
        "/im-haus",
        "/reservierungen",
        "/zimmerplan",
        "/seminarraum",
        "/verwaltung/seminarraum",
        "/check-in/1/abschluss",
        "/zahlungen/offen",
        "/verwaltung/zahlungsarten",
        "/e-mails",
        "/reservierungen/1/e-mail",
        "/spaetanreisen",
        "/spaetanreise/1",
    ):
        response = oidc_client.get(path)
        assert response.status_code == 403, path
        assert 'href="/zimmerstatus"' in response.text and "Zu Ihrem Bereich" in response.text
    denied = oidc_client.post("/assistent/plan", json={"text": "Anreisen"})
    assert denied.status_code == 403 and denied.headers["content-type"].startswith(
        "application/json"
    )
    denied = oidc_client.get("/anreisen", headers={"Accept": "application/json"})
    assert denied.status_code == 403 and denied.headers["content-type"].startswith(
        "application/json"
    )


@pytest.mark.parametrize("roles", [["rezeption"], ["leitung"], ["housekeeping", "rezeption"]])
def test_front_desk_roles_keep_full_access(oidc_client, idp, db, roles):
    from tests.app.auth_helpers import login

    idp.claims["roles"] = roles
    login(oidc_client)
    for path in (
        "/",
        "/zimmerstatus",
        "/anreisen",
        "/abreisen",
        "/im-haus",
        "/reservierungen",
        "/zimmerplan",
        "/seminarraum",
    ):
        page = oidc_client.get(path)
        assert page.status_code == 200, path
        assert "Neue Reservierung" in page.text and 'href="/zimmerstatus"' in page.text


def test_no_role_still_has_no_access(oidc_client, idp):
    from tests.app.auth_helpers import login

    idp.claims["roles"] = []
    login(oidc_client)
    for path in ("/", "/zimmerstatus", "/anreisen"):
        response = oidc_client.get(path)
        assert response.status_code == 403 and "Kein Zugriff" in response.text


def test_seed_reset_plants_cleaning_statuses_without_changing_f1_flags(client, db):
    from kurort_app.seed import seed_demo_data

    snapshots = []
    for _ in range(2):
        db.expunge_all()
        seed_demo_data(db, reset=True, anchor=D)
        rooms = db.scalars(select(Room).order_by(Room.number)).all()
        assert sum(r.housekeeping_status == "dirty" for r in rooms) >= 3
        assert any(r.housekeeping_status == "inspected" for r in rooms)
        assert any(r.housekeeping_status == "out_of_order" and r.housekeeping_note for r in rooms)
        assert any(
            r.room.housekeeping_status == "dirty"
            for r in db.scalars(
                select(Reservation).where(
                    Reservation.arrival == D, Reservation.status == "reserved"
                )
            )
        )
        stays = db.scalars(select(Reservation)).all()
        departed = [s for s in stays if s.departure == D and s.status == "checked_out"]
        assert departed and all(s.room.housekeeping_status == "dirty" for s in departed)
        broken = next(r for r in rooms if r.housekeeping_status == "out_of_order")
        assert not any(
            s.room_id == broken.id
            and s.status not in ("cancelled", "no_show")
            and s.departure >= D
            and s.arrival <= D + timedelta(days=3)
            for s in stays
        )
        assert all(re.fullmatch(r"R-\d{4}-\d{4}", s.code) for s in stays)
        assert not any(
            g.email == "spaetanreise@example.de" for s in stays for g in (s.primary_guest,)
        )
        snapshots.append([(r.number, r.housekeeping_status, r.housekeeping_note) for r in rooms])
        html = client.get("/").text
        assert (
            "Gästedaten fehlen · Geburtsdatum" in html and "Kurtaxe klären · Nachweis fehlt" in html
        )
    assert snapshots[0] == snapshots[1]


@pytest.mark.parametrize("hour,status", [(6, "checked_in"), (12, "checked_out")])
def test_seed_keeps_todays_early_leavers_in_house_until_they_left(hour, status):
    import random
    from datetime import datetime

    from kurort_app.seed import HOTEL_TZ, _apply_lifecycle

    stay = Reservation(arrival=D - timedelta(days=3), departure=D)
    rng = random.Random(0)
    rng.random = lambda: 0.1  # one of the departures that leave early
    _apply_lifecycle(rng, stay, D, datetime.combine(D, time(hour), tzinfo=HOTEL_TZ))
    assert stay.status == status and stay.checked_in_at is not None
    if status == "checked_out":
        assert stay.checked_out_at.date() == D and stay.checked_out_at.hour == 7
    else:
        assert stay.checked_out_at is None
