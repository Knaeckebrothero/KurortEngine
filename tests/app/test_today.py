"""F1 shared front-desk registries, mobile navigation and seeded states."""

from datetime import timedelta

from sqlalchemy import select

from kurort_app import web
from kurort_app.models import CHECKED_IN, CHECKED_OUT, Reservation, ReservationGuest
from kurort_app.services import engine, today
from tests.app.conftest import BUSINESS_DATE
from tests.app.test_engine_adapter import make_stay


def test_today_hooks_render_and_block_only_checkin(client, db, monkeypatch):
    res = make_stay(db, [{}])
    monkeypatch.setattr(
        today,
        "FLAG_PROVIDERS",
        [*today.FLAG_PROVIDERS, lambda session, row: [today.Flag("Testflag", "info", "/fix")]],
    )
    monkeypatch.setattr(
        today,
        "DASHBOARD_NOTICES",
        [lambda session, day: [today.Flag("Testzeile", "warning", "/notice")]],
    )
    monkeypatch.setattr(
        today,
        "CHECKIN_BLOCKERS",
        [
            lambda session, r: [
                engine.Blocker(
                    "abschluss", "Testblocker", action_label="Beheben", action_url="/repair"
                )
            ]
        ],
    )
    html = client.get("/").text
    assert 'href="/fix"' in html and "Testflag" in html
    assert html.index("Testzeile") < html.index('data-widget="today"')
    client.post(f"/check-in/{res.id}/avs/alle")
    html = client.get(f"/check-in/{res.id}/abschluss").text
    assert 'method="post" action="/repair"' in html
    assert f'name="zurueck" value="/check-in/{res.id}/abschluss"' in html
    assert "Beheben" in html
    client.post(f"/check-in/{res.id}/abschluss")
    db.expire_all()
    assert db.get(Reservation, res.id).status == "reserved"
    res.status = CHECKED_IN
    db.commit()
    monkeypatch.setattr(
        today,
        "CHECKOUT_WARNINGS",
        [*today.CHECKOUT_WARNINGS, lambda session, r: [today.Flag("Testwarnung", "warning")]],
    )
    html = client.get(f"/check-out/{res.id}").text
    assert html.index("Testwarnung") < html.index('id="bill-title"')
    assert client.post(f"/check-out/{res.id}", follow_redirects=False).status_code == 303
    db.expire_all()
    assert db.get(Reservation, res.id).status == CHECKED_OUT


def test_flag_providers_shared_on_all_lists(client, db, monkeypatch):
    res = make_stay(db, [{}])
    res.status = CHECKED_IN
    res.departure = BUSINESS_DATE
    res.arrival = BUSINESS_DATE - timedelta(days=2)
    res.guests[0].meldeschein_status = "gedruckt"
    db.commit()
    monkeypatch.setattr(
        today,
        "FLAG_PROVIDERS",
        [
            *today.FLAG_PROVIDERS,
            lambda session, row: [today.Flag("Gemeinsamer Hinweis", "info", "/fix")],
        ],
    )
    for path in ("/", "/abreisen", "/im-haus"):
        page = client.get(path).text
        assert "Gemeinsamer Hinweis" in page and "Unterschrift fehlt" in page
    assert "Unterschrift erfassen" in client.get("/im-haus").text
    client.post(f"/meldeschein/{res.guests[0].id}/unterschrieben", data={"zurueck": "/im-haus"})
    assert "Unterschrift fehlt" not in client.get("/abreisen").text
    other = make_stay(db, [{}], code="ARRIVAL")
    assert "Gemeinsamer Hinweis" in client.get("/anreisen").text
    flags = next(
        row for row in today.arrival_rows(db, BUSINESS_DATE) if row.reservation.id == other.id
    ).flags
    assert all(flag.text != "Anreisebereit" for flag in flags)


def test_phone_menu_contains_all_sidebar_links(client, db):
    html = client.get("/").text
    menu = html.split('<details class="rail-menu">', 1)[1].split("</details>", 1)[0]
    for item in web.NAV:
        assert f'href="{item.href}"' in menu
    assert "Menü" in menu and "Neue Reservierung" in menu


def test_seed_reset_leaves_one_printed_in_house_guest(db):
    from kurort_app.seed import seed_demo_data

    seed_demo_data(db, reset=True, anchor=BUSINESS_DATE)
    db.expunge_all()
    seed_demo_data(db, reset=True, anchor=BUSINESS_DATE)
    printed = db.scalars(
        select(ReservationGuest)
        .join(Reservation)
        .where(Reservation.status == CHECKED_IN, ReservationGuest.meldeschein_status == "gedruckt")
    ).all()
    assert len(printed) == 1 and printed[0].meldeschein_printed_at is not None
    assert not db.scalars(
        select(ReservationGuest).where(ReservationGuest.meldeschein_status == "erzeugt")
    ).all()


def test_arrival_flags_include_occupied_room_and_no_room(client, db):
    leaving = make_stay(
        db, [{}], code="LEAVING", arrival=BUSINESS_DATE - timedelta(days=1), nights=1
    )
    leaving.status = CHECKED_IN
    arriving = make_stay(db, [{}], code="ARRIVING")
    db.commit()
    rows = today.arrival_rows(db, BUSINESS_DATE)
    assert [f.text for f in rows[0].flags] == ["Zimmer noch belegt"]
    arriving.room = None
    db.commit()
    flags = today.flags_for(db, "anreise", arriving)
    assert any(
        f.text == "Kein Zimmer" and f.href == f"/reservierungen/{arriving.id}/bearbeiten"
        for f in flags
    )
