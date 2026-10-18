"""F6 seminar room: independent day bookings, prices, availability and staff screens."""

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from tests.app.conftest import BUSINESS_DATE as D


def test_defaults_preserve_staff_changes(db):
    from kurort_app.defaults import ensure_defaults
    from kurort_app.models import FunctionSpace

    ensure_defaults(db)
    room = db.scalar(select(FunctionSpace))
    assert room.name == "Seminarraum"
    assert room.capacity == 20
    assert room.price_half_day == Decimal("190.00")
    assert room.price_full_day == Decimal("340.00")
    room.name = "Tagungsraum"
    room.price_half_day = Decimal("220.00")
    room.active = False
    db.commit()
    ensure_defaults(db)
    db.refresh(room)
    assert db.scalar(select(func.count()).select_from(FunctionSpace)) == 1
    assert room.name == "Tagungsraum"
    assert room.price_half_day == Decimal("220.00")
    assert not room.active


def test_ac3_ac4_direct_price_and_clashes(db):
    from kurort_app.defaults import ensure_defaults
    from kurort_app.models import FunctionSpace, SpaceBooking
    from kurort_app.services import seminar

    ensure_defaults(db)
    room = db.scalar(select(FunctionSpace))
    assert seminar.calculate_price(room, D, D + timedelta(days=1), "ganztags") == Decimal("680")
    assert seminar.calculate_price(room, D, D, "vormittag") == Decimal("190")
    booking = SpaceBooking(
        space=room,
        start_date=D,
        end_date=D + timedelta(days=1),
        slot="vormittag",
        organizer_name="Test",
        attendees=4,
        price=Decimal("380"),
    )
    db.add(booking)
    db.commit()
    assert (
        seminar.find_clash(db, room.id, D + timedelta(days=1), D + timedelta(days=2), "ganztags").id
        == booking.id
    )
    assert seminar.find_clash(db, room.id, D, D, "nachmittag") is None
    assert (
        seminar.find_clash(db, room.id, D + timedelta(days=2), D + timedelta(days=2), "vormittag")
        is None
    )
    assert seminar.find_clash(db, room.id, D, D, "vormittag", exclude_booking_id=booking.id) is None
    booking.status = "storniert"
    db.commit()
    assert seminar.find_clash(db, room.id, D, D, "vormittag") is None


def test_ac11_seed_reset_is_exact_and_linked(db):
    from kurort_app.models import FunctionSpace, Reservation, SpaceBooking
    from kurort_app.seed import seed_demo_data

    for _ in range(2):
        db.expunge_all()
        seed_demo_data(db, reset=True, anchor=D)
        assert db.scalar(select(func.count()).select_from(FunctionSpace)) == 1
        bookings = db.scalars(select(SpaceBooking).order_by(SpaceBooking.id)).all()
        assert len(bookings) == 5
        assert [(b.start_date - D).days for b in bookings] == [1, 3, 2, 6, -5]
        assert [b.status for b in bookings] == [
            "bestaetigt",
            "bestaetigt",
            "storniert",
            "angefragt",
            "bestaetigt",
        ]
        assert bookings[0].company == "Spessart Physio GmbH"
        assert (
            bookings[0].attendees == 14
            and bookings[0].catering_coffee
            and bookings[0].catering_lunch
        )
        assert bookings[2].cancel_reason == "Kurs abgesagt" and bookings[2].cancelled_at
        assert bookings[3].company == "Volkshochschule Bad Orb" and bookings[3].catering_drinks
        assert bookings[3].end_date == D + timedelta(days=7)
        expected = db.scalar(
            select(Reservation)
            .where(
                Reservation.status != "cancelled",
                Reservation.arrival <= D + timedelta(days=3),
                Reservation.departure > D + timedelta(days=3),
            )
            .order_by(Reservation.id)
        )
        assert bookings[1].reservation_id == expected.id
        assert sum(b.reservation_id is not None for b in bookings) == 1


def _form(space_id=1, **changes):
    values = dict(
        raum=str(space_id),
        von=(D + timedelta(days=30)).isoformat(),
        bis=(D + timedelta(days=30)).isoformat(),
        zeit="ganztags",
        veranstalter="Clara Sommer",
        firma="Testfirma",
        email="clara@example.de",
        telefon="",
        personen="10",
        preis="",
        reservierung="",
        status="angefragt",
    )
    return values | changes


def _created(client, form):
    response = client.post("/seminarraum/neu", data=form, follow_redirects=False)
    assert response.status_code == 303, response.text
    return int(response.headers["location"].split("?")[0].rsplit("/", 1)[1])


def test_ac2_independent_booking_and_audit(client, seeded):
    from kurort_app.models import AuditEvent, Guest, Reservation, SpaceBooking

    counts = [seeded.scalar(select(func.count()).select_from(m)) for m in (Reservation, Guest)]
    before = seeded.scalar(select(func.count()).select_from(SpaceBooking))
    booking_id = _created(client, _form())
    seeded.expire_all()
    booking = seeded.get(SpaceBooking, booking_id)
    assert booking.status == "angefragt" and booking.reservation_id is None
    assert seeded.scalar(select(func.count()).select_from(SpaceBooking)) == before + 1
    assert counts == [
        seeded.scalar(select(func.count()).select_from(m)) for m in (Reservation, Guest)
    ]
    events = seeded.scalars(
        select(AuditEvent).where(AuditEvent.action == "space_booking.created")
    ).all()
    assert len(events) == 1 and events[0].entity_id == str(booking_id)
    assert "Testfirma" in events[0].summary
    detail = client.get(f"/seminarraum/{booking_id}")
    assert detail.status_code == 200 and "Clara Sommer" in detail.text
    assert events[0].summary in detail.text and "berechnet" in detail.text


def test_ac1_list_weeks_cancelled_and_history(client, seeded):
    from kurort_app.models import SpaceBooking

    response = client.get("/seminarraum")
    assert response.status_code == 200
    html = response.text
    assert "KW 42" in html and "KW 43" in html
    assert "Spessart Physio GmbH" in html and "Volkshochschule Bad Orb" in html
    cancelled = html.split('id="cancelled-bookings"')[1].split("</details>")[0]
    assert "Storniert (1)" in cancelled and "Physiokurs" in cancelled
    assert "Physiokurs" not in html.split('id="cancelled-bookings"')[0]
    history = seeded.scalar(select(SpaceBooking).where(SpaceBooking.start_date < D))
    assert history.display_name not in html
    assert history.display_name in client.get("/seminarraum?vergangene=1").text


def test_ac3_price_edit_and_manual_clear(client, seeded):
    from kurort_app.models import FunctionSpace, SpaceBooking

    start = D + timedelta(days=30)
    end = start + timedelta(days=1)
    booking_id = _created(client, _form(bis=end.isoformat()))
    seeded.expire_all()
    assert seeded.get(SpaceBooking, booking_id).price == Decimal("680")
    end += timedelta(days=1)
    response = client.post(
        f"/seminarraum/{booking_id}/bearbeiten",
        data=_form(bis=end.isoformat()),
        follow_redirects=False,
    )
    assert response.status_code == 303
    seeded.expire_all()
    assert seeded.get(SpaceBooking, booking_id).price == Decimal("1020")
    half = _created(
        client, _form(zeit="vormittag", von=(start + timedelta(days=4)).isoformat(), bis="")
    )
    seeded.expire_all()
    assert seeded.get(SpaceBooking, half).price == Decimal("190")
    manual_form = _form(
        von=(start + timedelta(days=7)).isoformat(),
        bis=(start + timedelta(days=7)).isoformat(),
        preis="125,50",
    )
    manual_id = _created(client, manual_form)
    manual_form["bis"] = (start + timedelta(days=8)).isoformat()
    client.post(f"/seminarraum/{manual_id}/bearbeiten", data=manual_form)
    seeded.expire_all()
    manual = seeded.get(SpaceBooking, manual_id)
    assert manual.price == Decimal("125.50") and manual.price_manual
    assert 'value="125.50"' in client.get(f"/seminarraum/{manual_id}/bearbeiten").text
    assert "manuell" in client.get(f"/seminarraum/{manual_id}").text
    manual_form["preis"] = ""
    client.post(f"/seminarraum/{manual_id}/bearbeiten", data=manual_form)
    seeded.expire_all()
    assert manual.price == Decimal("680") and not manual.price_manual
    room = seeded.get(FunctionSpace, 1)
    room.price_full_day = Decimal("400")
    seeded.commit()
    seeded.refresh(manual)
    assert manual.price == Decimal("680")


def test_ac4_http_clashes_and_exclusions(client, seeded):
    from kurort_app.models import FunctionSpace

    first = _created(client, _form(zeit="vormittag"))
    clash = client.post("/seminarraum/neu", data=_form(), follow_redirects=False)
    assert clash.status_code == 422
    assert (
        "Seminarraum ist am 13.11.2026 vormittags bereits gebucht (Testfirma, angefragt)."
        in clash.text
    )
    _created(client, _form(zeit="nachmittag"))
    later = (D + timedelta(days=31)).isoformat()
    _created(client, _form(von=later, bis=later))
    assert (
        client.post(
            f"/seminarraum/{first}/bearbeiten", data=_form(zeit="vormittag"), follow_redirects=False
        ).status_code
        == 303
    )
    room = FunctionSpace(
        name="Kleiner Saal",
        capacity=12,
        price_half_day=Decimal("100"),
        price_full_day=Decimal("180"),
    )
    seeded.add(room)
    seeded.commit()
    _created(client, _form(space_id=room.id))


@pytest.mark.parametrize(
    "changes,message",
    [
        ({"veranstalter": ""}, "Veranstalter fehlt."),
        ({"email": "", "telefon": ""}, "Bitte E-Mail oder Telefon angeben."),
        ({"bis": (D + timedelta(days=29)).isoformat()}, "Bis muss am oder nach Von liegen."),
        (
            {"bis": (D + timedelta(days=44)).isoformat()},
            "Eine Buchung darf höchstens 14 Tage dauern.",
        ),
        ({"von": (D - timedelta(days=1)).isoformat()}, "Beginn liegt in der Vergangenheit."),
        ({"personen": ""}, "Bitte mindestens eine Person angeben."),
        ({"personen": "0"}, "Bitte mindestens eine Person angeben."),
        ({"personen": "21"}, "Der Seminarraum ist für höchstens 20 Personen ausgelegt."),
        ({"reservierung": "UNBEKANNT"}, "Reservierung wurde nicht gefunden."),
        ({"preis": "-1"}, "Preis darf nicht negativ sein."),
        ({"preis": "NaN"}, "Bitte einen gültigen Preis angeben."),
        ({"zeit": "abends"}, "Bitte Vormittag, Nachmittag oder Ganztags wählen."),
        ({"status": "storniert"}, "Bitte Angefragt oder Bestätigt wählen."),
    ],
)
def test_ac5_validation_saves_nothing(client, seeded, changes, message):
    from kurort_app.models import AuditEvent, SpaceBooking

    counts = [
        seeded.scalar(select(func.count()).select_from(m)) for m in (SpaceBooking, AuditEvent)
    ]
    response = client.post("/seminarraum/neu", data=_form(**changes))
    assert response.status_code == 422
    assert response.text.count(message) >= 2  # summary and field
    assert counts == [
        seeded.scalar(select(func.count()).select_from(m)) for m in (SpaceBooking, AuditEvent)
    ]


def test_ac5_inactive_room_and_unchanged_past_edit(client, seeded):
    from kurort_app.models import FunctionSpace, SpaceBooking

    room = seeded.get(FunctionSpace, 1)
    room.active = False
    seeded.commit()
    response = client.post("/seminarraum/neu", data=_form())
    assert response.status_code == 422 and "Dieser Raum ist nicht aktiv." in response.text
    room.active = True
    seeded.commit()
    past = seeded.scalar(select(SpaceBooking).where(SpaceBooking.start_date < D))
    form = _form(von=past.start_date.isoformat(), bis=past.end_date.isoformat())
    assert (
        client.post(
            f"/seminarraum/{past.id}/bearbeiten", data=form, follow_redirects=False
        ).status_code
        == 303
    )


def test_ac6_status_lifecycle_and_cancelled_guards(client, seeded):
    from kurort_app.models import AuditEvent, SpaceBooking

    booking_id = _created(client, _form())
    assert (
        client.post(f"/seminarraum/{booking_id}/bestaetigen", follow_redirects=False).status_code
        == 303
    )
    seeded.expire_all()
    assert seeded.get(SpaceBooking, booking_id).status == "bestaetigt"
    client.post(f"/seminarraum/{booking_id}/stornieren", data={"grund": "Termin entfällt"})
    seeded.expire_all()
    booking = seeded.get(SpaceBooking, booking_id)
    assert (
        booking.status == "storniert"
        and booking.cancelled_at
        and booking.cancel_reason == "Termin entfällt"
    )
    events_before = seeded.scalar(select(func.count()).select_from(AuditEvent))
    for method, path in [
        ("get", "bearbeiten"),
        ("post", "bearbeiten"),
        ("post", "bestaetigen"),
        ("post", "stornieren"),
    ]:
        response = getattr(client, method)(
            f"/seminarraum/{booking_id}/{path}", follow_redirects=False
        )
        assert response.status_code == 303 and "notice_kind=warning" in response.headers["location"]
    assert seeded.scalar(select(func.count()).select_from(AuditEvent)) == events_before
    _created(client, _form())
    assert (
        seeded.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.action == "space_booking.confirmed")
        )
        == 1
    )
    assert (
        seeded.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.action == "space_booking.cancelled")
        )
        == 1
    )


def test_ac7_reservation_link_and_cancelled_refused(client, seeded):
    from kurort_app.models import Reservation, SpaceBooking

    res = seeded.scalar(
        select(Reservation).where(Reservation.status != "cancelled").order_by(Reservation.id)
    )
    booking_id = _created(client, _form(reservierung=res.code))
    seeded.expire_all()
    assert seeded.get(SpaceBooking, booking_id).reservation_id == res.id
    assert f'href="/reservierungen/{res.id}"' in client.get(f"/seminarraum/{booking_id}").text
    res.status = "cancelled"
    seeded.commit()
    response = client.post("/seminarraum/neu", data=_form(reservierung=res.code))
    assert response.status_code == 422 and "Diese Reservierung ist storniert." in response.text


def test_ac8_week_strip_and_prefill(client, seeded):
    html = client.get("/seminarraum?von=2026-10-15").text
    assert "Mo 12.10." in html and "So 18.10." in html
    assert 'href="/seminarraum/neu?raum=1&amp;von=2026-10-16&amp;zeit=vormittag"' in html
    assert 'href="/seminarraum/neu?raum=1&amp;von=2026-10-12' not in html
    assert html.count('data-booking="1"') == 2  # full day occupies both halves
    form = client.get("/seminarraum/neu?raum=1&von=2026-10-16&zeit=vormittag").text
    assert 'value="2026-10-16"' in form
    assert 'value="vormittag" checked' in form
    assert "1 × Halbtag à 190,00 €" in form


def test_ac9_settings_audit_prices_and_placeholder(client, seeded):
    from kurort_app.models import AuditEvent, FunctionSpace, SpaceBooking

    assert "Platzhalterpreise – bitte prüfen" in client.get("/verwaltung/seminarraum").text
    before = [b.price for b in seeded.scalars(select(SpaceBooking).order_by(SpaceBooking.id))]
    response = client.post(
        "/verwaltung/seminarraum/1",
        data={
            "name": "Seminarraum",
            "kapazitaet": "20",
            "halbtag": "210,00",
            "ganztag": "390",
            "aktiv": "on",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    seeded.expire_all()
    assert seeded.get(FunctionSpace, 1).price_full_day == Decimal("390")
    assert before == [
        b.price for b in seeded.scalars(select(SpaceBooking).order_by(SpaceBooking.id))
    ]
    assert "Platzhalterpreise – bitte prüfen" not in client.get("/verwaltung/seminarraum").text
    response = client.post(
        "/verwaltung/seminarraum/neu",
        data={
            "name": "Saal",
            "kapazitaet": "40",
            "halbtag": "250",
            "ganztag": "440",
            "aktiv": "on",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert seeded.scalar(select(func.count()).select_from(FunctionSpace)) == 2
    for action in ("function_space.created", "function_space.updated"):
        assert (
            seeded.scalar(
                select(func.count()).select_from(AuditEvent).where(AuditEvent.action == action)
            )
            == 1
        )


@pytest.mark.parametrize("roles,allowed", [(["rezeption"], False), (["leitung"], True)])
def test_ac9_ac12_settings_roles_and_sidebar(oidc_client, idp, seeded, roles, allowed):
    from tests.app.auth_helpers import login

    idp.claims["roles"] = roles
    login(oidc_client)
    html = oidc_client.get("/seminarraum").text
    assert 'href="/seminarraum"' in html
    assert ('href="/verwaltung/seminarraum"' in html) == allowed
    assert html.index("Planung") < html.index('href="/seminarraum"')
    assert oidc_client.get("/verwaltung/seminarraum").status_code == (200 if allowed else 403)
    if not allowed:
        for path in ("neu", "1"):
            assert oidc_client.post(f"/verwaltung/seminarraum/{path}", data={}).status_code == 403


def test_ac10_room_plan_bars_ignore_occupancy(client, seeded):
    from kurort_app.models import SpaceBooking

    before = client.get("/zimmerplan")
    assert before.status_code == 200 and "Seminarräume" in before.text
    assert (
        len(before.context["seminar_rows"][0]["bars"]) == 4
    )  # two mornings and two whole/half bookings
    for booking in seeded.scalars(
        select(SpaceBooking).where(SpaceBooking.status != "storniert", SpaceBooking.end_date >= D)
    ):
        assert f'href="/seminarraum/{booking.id}"' in before.text
    assert 'href="/seminarraum/3"' not in before.text
    seeded.query(SpaceBooking).delete()
    seeded.commit()
    after = client.get("/zimmerplan")
    assert before.context["room_count"] == after.context["room_count"] == 33
    assert before.context["today_info"] == after.context["today_info"]
    assert before.context["days"] == after.context["days"]


def test_ac12_sidebar_login_off(client, seeded):
    html = client.get("/").text
    assert 'href="/seminarraum"' in html and 'href="/verwaltung/seminarraum"' in html
    assert html.index("Verwaltung") < html.index('href="/verwaltung/seminarraum"')


def test_ac8_ac10_service_geometry_and_clipping(seeded):
    from kurort_app.services.seminar import plan_rows, week_rows

    rows = week_rows(seeded, D - timedelta(days=2))
    assert len(rows) == 1
    days = rows[0]["days"]
    assert days[0]["halves"] == {"vormittag": None, "nachmittag": None}
    assert days[3]["halves"]["vormittag"].id == 1
    assert days[3]["halves"]["nachmittag"].id == 1
    assert days[4]["halves"]["vormittag"] is None  # cancelled
    assert days[5]["halves"]["vormittag"] is None
    assert days[5]["halves"]["nachmittag"].id == 2
    bars = plan_rows(seeded, D + timedelta(days=1), D + timedelta(days=7))[0]["bars"]
    assert [(b["booking"].id, b["start"], b["end"]) for b in bars] == [
        (1, 2, 4),
        (2, 7, 8),
        (4, 12, 13),
    ]


def test_booking_fields_confirmed_create_and_edit_audit(client, seeded):
    from kurort_app.models import AuditEvent, SpaceBooking

    form = _form(
        status="bestaetigt",
        kaffee="on",
        mittagessen="on",
        getraenke="on",
        verpflegung_notiz="Vegetarisch für 3",
        notizen="Beginn 09:00",
    )
    booking_id = _created(client, form)
    seeded.expire_all()
    booking = seeded.get(SpaceBooking, booking_id)
    assert booking.status == "bestaetigt"
    assert booking.catering_coffee and booking.catering_lunch and booking.catering_drinks
    assert booking.catering_note == "Vegetarisch für 3" and booking.notes == "Beginn 09:00"
    detail = client.get(f"/seminarraum/{booking_id}").text
    assert "Vegetarisch für 3" in detail and "Beginn 09:00" in detail
    form.update(personen="5", status="angefragt", veranstalter="Eva Berg")
    assert (
        client.post(
            f"/seminarraum/{booking_id}/bearbeiten", data=form, follow_redirects=False
        ).status_code
        == 303
    )
    seeded.expire_all()
    assert booking.attendees == 5 and booking.organizer_name == "Eva Berg"
    assert booking.status == "bestaetigt"  # only explicit confirm/cancel may change status
    event = seeded.scalar(select(AuditEvent).where(AuditEvent.action == "space_booking.updated"))
    assert event.entity == "space_booking" and event.entity_id == str(booking_id)


@pytest.mark.parametrize(
    "changes,message",
    [
        ({"name": ""}, "Bitte einen Raumnamen"),
        ({"kapazitaet": "0"}, "Bitte eine gültige Kapazität"),
        ({"halbtag": "-1"}, "Bitte einen gültigen Preis ab 0"),
        ({"ganztag": "NaN"}, "Bitte einen gültigen Preis ab 0"),
    ],
)
def test_settings_invalid_saves_nothing(client, seeded, changes, message):
    from kurort_app.models import AuditEvent, FunctionSpace

    form = {
        "name": "Saal",
        "kapazitaet": "20",
        "halbtag": "100",
        "ganztag": "200",
        "aktiv": "on",
    } | changes
    for path in ("neu", "1"):
        response = client.post(f"/verwaltung/seminarraum/{path}", data=form)
        assert response.status_code == 422 and message in response.text
    seeded.expire_all()
    assert seeded.get(FunctionSpace, 1).name == "Seminarraum"
    assert seeded.scalar(select(func.count()).select_from(FunctionSpace)) == 1
    assert (
        seeded.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.entity == "function_space")
        )
        == 0
    )


def test_unknown_booking_routes_return_404(client):
    for method, suffix in (
        ("get", ""),
        ("get", "/bearbeiten"),
        ("post", "/bearbeiten"),
        ("post", "/bestaetigen"),
        ("post", "/stornieren"),
    ):
        assert getattr(client, method)(f"/seminarraum/99999{suffix}").status_code == 404
