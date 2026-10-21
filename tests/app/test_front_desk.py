"""Front desk: overview, arrivals, departures, in-house and check-out."""

from __future__ import annotations

import re
from datetime import timedelta
from urllib.parse import unquote_plus

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from kurort_app.models import (
    CANCELLED,
    CHECKED_IN,
    CHECKED_OUT,
    NO_SHOW,
    RESERVED,
    AuditEvent,
    Payment,
    PaymentMethod,
    Reservation,
    ReservationGuest,
)
from kurort_app.services import payments
from kurort_app.web import fmt_money
from tests.app.conftest import BUSINESS_DATE


def _metric(html: str, name: str) -> int:
    match = re.search(rf'data-metric="{name}" data-value="(\d+)"', html)
    assert match, f"metric {name} missing"
    return int(match.group(1))


def _reservations(session, *where):
    stmt = (
        select(Reservation)
        .where(*where)
        .options(selectinload(Reservation.guests).selectinload(ReservationGuest.guest))
    )
    return list(session.scalars(stmt))


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


def test_dashboard_metrics_match_database(client, seeded):
    html = client.get("/").text
    assert 'class="grid grid-3 fd-metrics"' in html  # a row of three, not stacked
    arrivals = seeded.scalar(
        select(func.count())
        .select_from(Reservation)
        .where(Reservation.arrival == BUSINESS_DATE, Reservation.status != CANCELLED)
    )
    departures = seeded.scalar(
        select(func.count())
        .select_from(Reservation)
        .where(
            Reservation.departure == BUSINESS_DATE,
            Reservation.status.in_((CHECKED_IN, CHECKED_OUT)),
        )
    )
    tonight = seeded.scalar(
        select(func.count())
        .select_from(Reservation)
        .where(
            Reservation.arrival <= BUSINESS_DATE,
            Reservation.departure > BUSINESS_DATE,
            Reservation.status.in_((RESERVED, CHECKED_IN, CHECKED_OUT)),
        )
    )
    assert _metric(html, "arrivals") == arrivals
    assert _metric(html, "departures") == departures
    assert html.count('data-metric="') == 3
    assert _metric(html, "occupancy") == round(100 * tonight / 33)


def test_dashboard_chart_has_fourteen_accessible_nights(client, seeded):
    html = client.get("/").text
    assert html.count('<g class="fd-bar') == 14
    assert '<title id="chart-svg-title">Belegte Zimmer pro Nacht</title>' in html
    # The visually-hidden data table mirrors the bars.
    table = html[html.index("<caption>Belegte Zimmer pro Nacht</caption>") :]
    assert table.count("<tr><td>") == 14
    assert "Mittwoch, 14. Oktober 2026" in table


def test_dashboard_today_combines_filters_and_finished_rows(client, seeded):
    html = client.get("/").text
    assert '<h2 id="today-title">Heute</h2>' in html
    assert '<h2 id="hints-title">' not in html
    arrivals = _reservations(
        seeded, Reservation.arrival == BUSINESS_DATE, Reservation.status != CANCELLED
    )
    departures = _reservations(
        seeded,
        Reservation.departure == BUSINESS_DATE,
        Reservation.status.in_((CHECKED_IN, CHECKED_OUT)),
    )
    for row in arrivals + departures:
        assert f'data-reservation-id="{row.id}"' in html
    assert f'Anreisen <span class="count">{len(arrivals)}</span>' in html
    assert f'Abreisen <span class="count">{len(departures)}</span>' in html
    for kind, rows in (("anreisen", arrivals), ("abreisen", departures)):
        page = client.get(f"/?zeigen={kind}").text
        found = re.findall(r'data-reservation-id="(\d+)"', page)
        assert set(map(int, found)) == {r.id for r in rows}
        # A link without JavaScript; with htmx it swaps only the Heute card.
        chip = re.search(rf'<a class="chip" href="/\?zeigen={kind}"[^>]*>', html).group(0)
        assert 'hx-select="#heute"' in chip and 'hx-target="#heute"' in chip
        assert 'hx-push-url="true"' in chip
    assert 'id="heute"' in html
    for row in arrivals:
        if row.status == RESERVED:
            assert f'href="/check-in/{row.id}"' in html
    completed = html.split('<details class="fd-finished">', 1)[1]
    for row in departures:
        if row.status == CHECKED_OUT:
            assert f'data-reservation-id="{row.id}"' in completed
    for match in re.findall(r"<tr[^>]*data-reservation-id=.*?</tr>", html, re.S):
        assert len(re.findall(r'class="btn[^"]*"', match)) == 1


def test_dashboard_flags_link_planted_exceptions_to_fixes(client, seeded):
    html = client.get("/").text
    arrivals = _reservations(
        seeded, Reservation.arrival == BUSINESS_DATE, Reservation.status == RESERVED
    )
    missing = next(r for r in arrivals if any(rg.guest.birth_date is None for rg in r.guests))
    proof = next(
        r
        for r in arrivals
        if any(rg.exemption_category and not rg.exemption_evidence for rg in r.guests)
    )
    assert "Gästedaten fehlen · Geburtsdatum" in html
    assert f'href="/check-in/{missing.id}/gaeste"' in html
    assert "Kurtaxe klären · Nachweis fehlt" in html
    assert f'href="/check-in/{proof.id}/abschluss#kurtaxe"' in html
    for r in _reservations(
        seeded,
        Reservation.status == NO_SHOW,
        Reservation.arrival == BUSINESS_DATE - timedelta(days=1),
    ):
        assert f'data-reservation-id="{r.id}"' not in html


def test_dashboard_on_empty_database(client, db):
    response = client.get("/")
    assert response.status_code == 200 and "Heute nichts offen" in response.text
    assert "Keine offenen Hinweise" not in response.text


# ---------------------------------------------------------------------------
# Arrivals / departures / in-house
# ---------------------------------------------------------------------------


def test_arrivals_lists_todays_arrivals_with_filters(client, seeded):
    today = _reservations(
        seeded, Reservation.arrival == BUSINESS_DATE, Reservation.status != CANCELLED
    )
    html = client.get("/anreisen").text
    assert "Mittwoch, 14. Oktober 2026" in html
    for r in today:
        assert f'data-code="{r.code}"' in html

    offen = client.get("/anreisen?filter=offen").text
    for r in today:
        assert (f'data-code="{r.code}"' in offen) == (r.status == RESERVED)
    assert 'aria-current="true"' in offen


def test_arrivals_for_another_day(client, seeded):
    tomorrow = BUSINESS_DATE + timedelta(days=1)
    rows = _reservations(seeded, Reservation.arrival == tomorrow, Reservation.status != CANCELLED)
    html = client.get(f"/anreisen?tag={tomorrow.isoformat()}").text
    assert "Donnerstag, 15. Oktober 2026" in html
    for r in rows:
        assert f'data-code="{r.code}"' in html
    # Future arrivals cannot be checked in yet.
    assert 'href="/check-in/' not in html


def test_lists_use_the_same_action_labels_and_styles(client, seeded):
    pages = [client.get(path).text for path in ("/", "/anreisen", "/abreisen", "/im-haus")]
    assert all("Check-in starten" not in page for page in pages)
    for page in pages:
        for label in ("Check-in", "Check-out"):
            for cls in re.findall(
                rf'<a class="([^"]*)" href="/check-[a-z]+/\d+">{label}</a>', page
            ):
                assert cls == "btn sm primary", (label, cls)
    assert re.search(r'<a class="btn sm primary" href="/check-in/\d+">Check-in</a>', pages[1])


def test_dashboard_notices_are_warning_notices(client, seeded):
    html = client.get("/").text
    notices = re.findall(r'<div class="notice warning fd-notice"><p><a href="([^"]+)">', html)
    assert "/zahlungen/offen" in notices
    assert "Wochenende" in html  # the darker bars are explained in the legend


def test_departures_lists_open_and_finished_checkouts(client, seeded):
    rows = _reservations(
        seeded,
        Reservation.departure == BUSINESS_DATE,
        Reservation.status.in_((CHECKED_IN, CHECKED_OUT)),
    )
    assert rows
    html = client.get("/abreisen").text
    for r in rows:
        assert f'data-code="{r.code}"' in html
        if r.status == CHECKED_IN:
            assert f'href="/check-out/{r.id}"' in html
    assert "inkl." not in html
    for r in rows:
        row = re.search(rf'data-code="{r.code}".*?</tr>', html, re.S).group(0)
        b = payments.balance(r)
        # The Saldo column carries the open amount; the status column does not repeat it.
        assert f"Offen {fmt_money(b.open)}" not in row
        if b.open > 0 and b.kurtaxe:
            assert f"davon Kurtaxe {fmt_money(b.kurtaxe)}" in row
        elif b.open <= 0:
            assert "davon Kurtaxe" not in row


def test_in_house_lists_every_checked_in_stay_and_sorts(client, seeded):
    rows = _reservations(seeded, Reservation.status == CHECKED_IN)
    html = client.get("/im-haus").text
    assert '<th scope="col">Saldo</th>' in html
    for r in rows:
        assert f'data-code="{r.code}"' in html
        row = re.search(rf'data-code="{r.code}".*?</tr>', html, re.S).group(0)
        cells = re.findall(r"<td[^>]*>.*?</td>", row, re.S)
        saldo, meldeschein = cells[-2], cells[-3]
        assert "Offen " not in meldeschein and "Bezahlt" not in meldeschein
        assert "Offen " in saldo or "Bezahlt" in saldo or "Guthaben" in saldo
        # Each guest's status says what is unsigned; no second "Unterschrift fehlt".
        assert row.count("Unterschrift fehlt") == sum(
            rg.meldeschein_status == "gedruckt" for rg in r.guests
        )
    by_departure = client.get("/im-haus?sort=abreise").text
    codes = re.findall(r'<tr data-code="([^"]+)"', by_departure)
    expected = [r.code for r in sorted(rows, key=lambda r: (r.departure, int(r.room.number)))]
    assert codes == expected


# ---------------------------------------------------------------------------
# Check-out
# ---------------------------------------------------------------------------


def _departing(session) -> Reservation:
    return _reservations(
        session, Reservation.departure == BUSINESS_DATE, Reservation.status == CHECKED_IN
    )[0]


def test_checkout_summary_shows_bill(client, seeded):
    r = _departing(seeded)
    assert r.kurtaxe is not None, "seeded in-house stays carry an engine assessment"
    html = client.get(f"/check-out/{r.id}").text
    assert r.code in html
    assert "Abrechnung (Vorschau)" in html
    assert fmt_money(r.kurtaxe.amount) in html
    assert fmt_money(r.rate_total + r.kurtaxe.amount) in html
    assert "Kurtaxe noch nicht berechnet" not in html
    assert 'action="/check-out/' in html


def test_checkout_summary_flags_missing_kurtaxe(client, seeded):
    r = _departing(seeded)
    seeded.delete(r.kurtaxe)
    seeded.commit()
    html = client.get(f"/check-out/{r.id}").text
    assert "Kurtaxe noch nicht berechnet" in html


def test_checkout_bill_lists_payments_after_the_total(client, seeded):
    r = next(r for r in _reservations(seeded, Reservation.status == CHECKED_IN) if r.payments)
    html = client.get(f"/check-out/{r.id}").text
    bill = html[html.index('class="table fd-bill"') :]
    order = [bill.index(">Logis<"), bill.index(">Kurtaxe<"), bill.index(">Gesamt<")]
    order += [bill.index(r.payments[0].method.label), bill.index(">Offen<")]
    assert order == sorted(order)


def test_checkout_with_money_open_needs_a_confirmation(client, seeded):
    r = next(
        r
        for r in _reservations(seeded, Reservation.status == CHECKED_IN)
        if payments.balance(r).open > 0
    )
    b = payments.balance(r)
    html = client.get(f"/check-out/{r.id}").text
    assert f"Trotz offenem Betrag ({fmt_money(b.open)}) auschecken" in html
    assert 'name="offen_geklaert"' in html and "Offener Betrag ist geklärt" in html
    assert "Check-out abschließen" not in html and "confirm(" not in html
    response = client.post(f"/check-out/{r.id}", follow_redirects=False)
    assert response.headers["location"].startswith(f"/check-out/{r.id}?notice=")
    assert "notice_kind=danger" in response.headers["location"]
    seeded.expire_all()
    assert seeded.get(Reservation, r.id).status == CHECKED_IN


def test_checkout_without_money_open_is_one_step(client, seeded):
    r = _departing(seeded)
    b = payments.balance(r)
    payments.ensure_payment_methods(seeded)
    method = seeded.scalars(select(PaymentMethod).where(PaymentMethod.code == "bar")).one()
    seeded.add(
        Payment(
            reservation_id=r.id,
            method_id=method.id,
            amount=b.open,
            paid_on=BUSINESS_DATE,
            received_on=BUSINESS_DATE,
            recorded_by="rezeption",
        )
    )
    seeded.commit()
    html = client.get(f"/check-out/{r.id}").text
    assert "Check-out abschließen" in html and "Trotz offenem Betrag" not in html
    assert '<details class="card fd-pay"><summary>Zahlung erfassen</summary>' in html
    response = client.post(f"/check-out/{r.id}", follow_redirects=False)
    assert response.headers["location"].startswith("/abreisen?notice=")
    seeded.expire_all()
    assert seeded.get(Reservation, r.id).status == CHECKED_OUT


def test_checkout_happy_path_records_audit(client, seeded):
    r = _departing(seeded)
    response = client.post(
        f"/check-out/{r.id}", data={"offen_geklaert": "1"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/abreisen?notice=")
    room = r.room.number
    assert f"Zimmer {room} zur Reinigung freigegeben" in unquote_plus(response.headers["location"])

    seeded.expire_all()
    stored = seeded.get(Reservation, r.id)
    assert stored.status == CHECKED_OUT
    assert stored.checked_out_at is not None
    event = seeded.scalars(
        select(AuditEvent).where(
            AuditEvent.entity == "reservation", AuditEvent.entity_id == str(r.id)
        )
    ).one()
    assert event.action == "check_out"
    assert r.code in event.summary

    followed = client.get(response.headers["location"]).text
    assert "ausgecheckt" in followed


def test_checkout_rejects_wrong_state(client, seeded):
    before = list(seeded.scalars(select(AuditEvent.id).order_by(AuditEvent.id)))
    r = _reservations(seeded, Reservation.arrival > BUSINESS_DATE, Reservation.status == RESERVED)[
        0
    ]
    response = client.post(f"/check-out/{r.id}", follow_redirects=False)
    assert response.status_code == 303
    assert "notice_kind=danger" in response.headers["location"]
    seeded.expire_all()
    assert seeded.get(Reservation, r.id).status == RESERVED
    assert list(seeded.scalars(select(AuditEvent.id).order_by(AuditEvent.id))) == before


def test_checkout_unknown_reservation_is_404(client, seeded):
    assert client.get("/check-out/999999").status_code == 404
    assert client.post("/check-out/999999").status_code == 404


# ---------------------------------------------------------------------------
# Chart range (`tage`) and the hooks the assistant drives
# ---------------------------------------------------------------------------


def _chart_nights(html: str) -> int:
    match = re.search(r'data-occupancy-days="(\d+)"', html)
    assert match, "chart card carries no data-occupancy-days"
    return int(match.group(1))


def test_dashboard_chart_range_follows_tage(client, seeded):
    html = client.get("/?tage=30").text
    assert _chart_nights(html) == 30
    assert "nächste 30 Nächte" in html
    assert html.count('<g class="fd-bar') == 30


def test_dashboard_chart_range_is_clamped(client, seeded):
    assert _chart_nights(client.get("/?tage=500").text) == 60
    assert _chart_nights(client.get("/?tage=3").text) == 7
    assert _chart_nights(client.get("/?tage=viele").text) == 14
    assert _chart_nights(client.get("/").text) == 14


def test_dense_chart_labels_only_today_and_mondays(client, seeded):
    html = client.get("/?tage=30").text
    day_labels = re.findall(r'class="fd-axis fd-axis-day"[^>]*>([^<]+)<', html)
    assert day_labels[0] == "Heute"
    assert set(day_labels[1:]) == {"Mo"}
    assert 'class="fd-bar-value"' not in html  # per-bar counts would collide


def test_dashboard_chart_range_cookie_and_param_precedence(client, seeded):
    client.cookies.set("kurort_tage", "21")
    try:
        assert _chart_nights(client.get("/").text) == 21
        assert _chart_nights(client.get("/?tage=10").text) == 10
    finally:
        client.cookies.clear()


def test_pages_expose_assistant_hooks(client, seeded):
    dashboard = client.get("/").text
    for widget in ("metrics", "today", "occupancy"):
        assert f'data-widget="{widget}"' in dashboard
    assert 'id="ai-input"' in dashboard and "data-ai-drawer" in dashboard
    assert 'data-user=""' in dashboard  # auth is off in the test suite

    arrival = _reservations(
        seeded, Reservation.arrival == BUSINESS_DATE, Reservation.status == RESERVED
    )[0]
    assert f'data-reservation-id="{arrival.id}"' in client.get("/anreisen").text
    plan = client.get("/zimmerplan").text
    assert 'data-room-row="101"' in plan and 'data-room-row="311"' in plan
