"""Front desk: overview, arrivals, departures, in-house and check-out."""

from __future__ import annotations

import re
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from kurort_app.models import (
    CANCELLED,
    CHECKED_IN,
    CHECKED_OUT,
    MELDESCHEIN_SIGNED,
    NO_SHOW,
    RESERVED,
    AuditEvent,
    Reservation,
    ReservationGuest,
)
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


def _hints_section(html: str) -> str:
    start = html.index('id="hinweise"')
    return html[start : html.index("</section>", start)]


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


def test_dashboard_metrics_match_database(client, seeded):
    html = client.get("/").text
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
    in_house_guests = seeded.scalar(
        select(func.count())
        .select_from(ReservationGuest)
        .join(Reservation)
        .where(Reservation.status == CHECKED_IN)
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
    assert _metric(html, "in-house") == in_house_guests
    assert _metric(html, "occupancy") == round(100 * tonight / 33)


def test_dashboard_chart_has_fourteen_accessible_nights(client, seeded):
    html = client.get("/").text
    assert html.count('<g class="fd-bar') == 14
    assert '<title id="chart-svg-title">Belegte Zimmer pro Nacht</title>' in html
    # The visually-hidden data table mirrors the bars.
    table = html[html.index("<caption>Belegte Zimmer pro Nacht</caption>") :]
    assert table.count("<tr><td>") == 14
    assert "Mittwoch, 14. Oktober 2026" in table


def test_dashboard_queue_links_open_arrivals_to_check_in(client, seeded):
    html = client.get("/").text
    for r in _reservations(
        seeded, Reservation.arrival == BUSINESS_DATE, Reservation.status == RESERVED
    ):
        assert f'href="/check-in/{r.id}"' in html
        assert r.code in html


def test_dashboard_hints_list_planted_exceptions(client, seeded):
    hints = _hints_section(client.get("/").text)

    arrivals = _reservations(
        seeded, Reservation.arrival == BUSINESS_DATE, Reservation.status == RESERVED
    )
    missing_birth = [r for r in arrivals if any(rg.guest.birth_date is None for rg in r.guests)]
    assert missing_birth, "seed should plant a missing birth date"
    for r in missing_birth:
        assert f'data-code="{r.code}"' in hints
        assert f'href="/reservierungen/{r.id}"' in hints
    assert "Geburtsdatum fehlt" in hints

    no_proof = [
        r
        for r in arrivals
        if any(rg.exemption_category and not rg.exemption_evidence for rg in r.guests)
    ]
    assert no_proof, "seed should plant an exemption without proof"
    assert "Kurtaxe klären · Nachweis fehlt" in hints
    for r in no_proof:
        assert f'data-code="{r.code}"' in hints

    unsigned = [
        r
        for r in _reservations(seeded, Reservation.status == CHECKED_IN)
        if any(rg.meldeschein_status != MELDESCHEIN_SIGNED for rg in r.guests)
    ]
    assert unsigned, "seed should plant an unsigned Meldeschein"
    for r in unsigned:
        assert f'data-code="{r.code}"' in hints
    assert "PDF erzeugt · nicht unterschrieben" in hints

    for r in _reservations(
        seeded,
        Reservation.status == NO_SHOW,
        Reservation.arrival == BUSINESS_DATE - timedelta(days=1),
    ):
        assert f'data-code="{r.code}"' in hints
        assert "No-Show von gestern" in hints


def test_dashboard_on_empty_database(client, db):
    response = client.get("/")
    assert response.status_code == 200
    assert "Heute keine Anreisen" in response.text
    assert "Keine offenen Hinweise" in response.text


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
    assert "Check-in starten" not in html


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


def test_in_house_lists_every_checked_in_stay_and_sorts(client, seeded):
    rows = _reservations(seeded, Reservation.status == CHECKED_IN)
    html = client.get("/im-haus").text
    for r in rows:
        assert f'data-code="{r.code}"' in html
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


def test_checkout_happy_path_records_audit(client, seeded):
    r = _departing(seeded)
    response = client.post(f"/check-out/{r.id}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/abreisen?notice=")

    seeded.expire_all()
    stored = seeded.get(Reservation, r.id)
    assert stored.status == CHECKED_OUT
    assert stored.checked_out_at is not None
    event = seeded.scalar(select(AuditEvent).where(AuditEvent.entity_id == str(r.id)))
    assert event.action == "check_out"
    assert r.code in event.summary

    followed = client.get(response.headers["location"]).text
    assert "ausgecheckt" in followed


def test_checkout_rejects_wrong_state(client, seeded):
    r = _reservations(seeded, Reservation.arrival > BUSINESS_DATE, Reservation.status == RESERVED)[
        0
    ]
    response = client.post(f"/check-out/{r.id}", follow_redirects=False)
    assert response.status_code == 303
    assert "notice_kind=danger" in response.headers["location"]
    seeded.expire_all()
    assert seeded.get(Reservation, r.id).status == RESERVED
    assert seeded.scalar(select(func.count()).select_from(AuditEvent)) == 0


def test_checkout_unknown_reservation_is_404(client, seeded):
    assert client.get("/check-out/999999").status_code == 404
    assert client.post("/check-out/999999").status_code == 404
