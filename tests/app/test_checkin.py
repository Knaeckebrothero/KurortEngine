"""The three-step check-in flow over HTTP."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select

from kurort_app.config import get_settings
from kurort_app.models import CHECKED_IN, RESERVED, AuditEvent, Reservation, ReservationGuest
from tests.app.conftest import BUSINESS_DATE
from tests.app.test_engine_adapter import make_stay


def _notice(response) -> str:
    return parse_qs(urlparse(response.headers["location"]).query).get("notice", [""])[0]


def _path(response) -> str:
    return urlparse(response.headers["location"]).path


def _reload(db, res) -> Reservation:
    db.expire_all()
    return db.get(Reservation, res.id)


def _guest_form(rg: ReservationGuest, **overrides) -> dict[str, str]:
    g = rg.guest
    values = {
        "first_name": g.first_name,
        "last_name": g.last_name,
        "birth_date": g.birth_date.isoformat() if g.birth_date else "",
        "nationality": g.nationality,
        "street": g.street or "",
        "postal_code": g.postal_code or "",
        "city": g.city or "",
        "country": g.country,
        "id_document_number": g.id_document_number or "",
        "disability_pct": "" if g.disability_pct is None else str(g.disability_pct),
    }
    values.update(overrides)
    return {f"g{rg.id}_{k}": v for k, v in values.items()}


def test_happy_path_checks_the_guest_in(client, db):
    res = make_stay(db, [{"first": "Claudia", "last": "Wolf"}, {"first": "Klaus", "last": "Wolf"}])
    rid = res.id
    ids = [rg.id for rg in res.guests]
    assert _path(client.get(f"/check-in/{rid}", follow_redirects=False)) == f"/check-in/{rid}/avs"
    assert client.post(f"/check-in/{rid}/avs/alle", follow_redirects=False).status_code == 303
    summary = client.get(f"/check-in/{rid}/abschluss")
    assert "Check-in abschließen · Zimmer 204" in summary.text
    assert summary.text.count('name="unterschrieben"') == 2
    response = client.post(
        f"/check-in/{rid}/abschluss", data={"unterschrieben": str(ids[0])}, follow_redirects=False
    )
    assert _path(response) == "/"
    assert _notice(response) == "Claudia Wolf ist eingecheckt · Zimmer 204"
    res = _reload(db, res)
    assert res.status == CHECKED_IN and res.checked_in_at
    assert res.kurtaxe.amount == Decimal("35.00")
    assert [rg.meldeschein_status for rg in res.guests] == ["unterschrieben", "gedruckt"]
    events = db.scalars(select(AuditEvent).order_by(AuditEvent.id)).all()
    actions = [event.action for event in events]
    assert actions.count("meldeschein.printed") == 2
    assert actions.count("meldeschein.signed") == 1
    assert "meldeschein.generated" not in actions and "kurkarte.issued" not in actions
    assert actions[-1] == "reservation.checked_in"
    assert all(e.payload["auto"] is True for e in events if e.action == "kurtaxe.assessed")


def test_missing_birth_date_starts_on_guest_step_and_save_fixes_it(client, db):
    res = make_stay(db, [{"first": "Christa", "last": "Herrmann", "birth": None}])
    rg = res.guests[0]
    r = client.get(f"/check-in/{res.id}", follow_redirects=False)
    assert _path(r) == f"/check-in/{res.id}/gaeste"

    page = client.get(f"/check-in/{res.id}/gaeste")
    assert "Geburtsdatum fehlt." in page.text and 'aria-invalid="true"' in page.text

    bad = client.post(f"/check-in/{res.id}/gaeste", data=_guest_form(rg, birth_date="31.02.1960"))
    assert bad.status_code == 200
    assert "Geburtsdatum im Format" in bad.text

    ok = client.post(
        f"/check-in/{res.id}/gaeste",
        data=_guest_form(rg, birth_date="1958-05-17"),
        follow_redirects=False,
    )
    assert ok.status_code == 303 and _path(ok) == f"/check-in/{res.id}/avs"
    assert _reload(db, res).guests[0].guest.birth_date.isoformat() == "1958-05-17"


def test_changing_data_after_printing_resets_the_meldeschein(client, db):
    res = make_stay(db, [{"first": "Ada"}])
    rg = res.guests[0]
    client.post(f"/check-in/{res.id}/avs/{rg.id}/gedruckt")
    client.post(f"/meldeschein/{rg.id}/unterschrieben")
    response = client.post(
        f"/check-in/{res.id}/gaeste",
        data=_guest_form(rg, birth_date="1955-01-01"),
        follow_redirects=False,
    )
    assert "Daten geändert – in AVS neu drucken: Ada Weber." in _notice(response)
    rg = _reload(db, res).guests[0]
    assert rg.meldeschein_status == "offen"
    assert rg.meldeschein_printed_at is None and rg.meldeschein_signed_at is None


def test_htmx_printing_returns_only_the_guest_card_and_can_be_undone(client, db):
    res = make_stay(db, [{}])
    rg = res.guests[0]
    response = client.post(
        f"/check-in/{res.id}/avs/{rg.id}/gedruckt", headers={"HX-Request": "true"}
    )
    assert response.status_code == 200 and "<html" not in response.text
    assert f'id="avs-guest-{rg.id}"' in response.text
    assert "Gedruckt" in response.text and "rezeption" in response.text
    rg = _reload(db, res).guests[0]
    assert rg.meldeschein_status == "gedruckt" and rg.meldeschein_printed_at
    assert (
        db.scalar(select(AuditEvent).where(AuditEvent.action == "meldeschein.printed")).entity
        == "reservation_guest"
    )
    response = client.post(f"/check-in/{res.id}/avs/{rg.id}/offen", follow_redirects=False)
    assert response.status_code == 303
    assert _reload(db, res).guests[0].meldeschein_status == "offen"
    assert db.scalar(select(AuditEvent).where(AuditEvent.action == "meldeschein.print_undone"))


def test_old_steps_redirect_and_local_papers_are_removed(client, db):
    res = make_stay(db, [{}])
    rg = res.guests[0]
    for old, new in (
        ("meldeschein", "avs"),
        ("kurtaxe", "abschluss#kurtaxe"),
        ("kurkarte", "abschluss"),
    ):
        response = client.get(f"/check-in/{res.id}/{old}", follow_redirects=False)
        assert (
            response.status_code == 303
            and response.headers["location"] == f"/check-in/{res.id}/{new}"
        )
    assert client.get(f"/meldeschein/{rg.id}.pdf").status_code == 404
    for removed in (
        f"meldeschein/{rg.id}/erzeugen",
        "meldeschein/alle",
        f"meldeschein/{rg.id}/unterschreiben",
        "kurkarte",
    ):
        assert client.post(f"/check-in/{res.id}/{removed}").status_code in (404, 405)
    for path in (
        f"/reservierungen/{res.id}",
        f"/check-out/{res.id}",
        *(f"/check-in/{res.id}/{step}" for step in ("gaeste", "avs", "abschluss")),
    ):
        page = client.get(path)
        assert page.status_code == 200
        assert ".pdf" not in page.text and "Kurkarte" not in page.text


def test_kurtaxe_exemption_needs_evidence(client, db):
    res = make_stay(db, [{"exemption": "geschaeftsreisender"}])
    rg = res.guests[0]
    client.post(f"/check-in/{res.id}/avs/alle")
    preview = client.post(
        f"/check-in/{res.id}/kurtaxe/vorschau", data={f"ex{rg.id}_category": "geschaeftsreisender"}
    )
    assert "Nachweis fehlt" in preview.text and "<html" not in preview.text
    page = client.get(f"/check-in/{res.id}/abschluss").text
    assert 'id="kurtaxe" open' in page and "Befreiungsnachweis fehlt" in page
    blocked = client.post(f"/check-in/{res.id}/abschluss", follow_redirects=False)
    assert "noch nicht möglich" in _notice(blocked)
    assert _reload(db, res).status == RESERVED
    ok = client.post(
        f"/check-in/{res.id}/kurtaxe",
        data={
            f"ex{rg.id}_category": "geschaeftsreisender",
            f"ex{rg.id}_evidence": "Bescheinigung Weber GmbH",
        },
        follow_redirects=False,
    )
    assert ok.status_code == 303 and ok.headers["location"].split("?")[0].endswith(
        "/abschluss#kurtaxe"
    )
    assert _reload(db, res).kurtaxe.amount == Decimal("0.00")
    client.post(f"/check-in/{res.id}/abschluss", data={"unterschrieben": str(rg.id)})
    assert _reload(db, res).status == CHECKED_IN


def test_normal_kurtaxe_is_automatic_after_guest_save(client, db):
    res = make_stay(db, [{}])
    response = client.post(
        f"/check-in/{res.id}/gaeste", data=_guest_form(res.guests[0]), follow_redirects=False
    )
    assert _path(response) == f"/check-in/{res.id}/avs"
    assert _reload(db, res).kurtaxe.amount == Decimal("17.50")
    page = client.get(f"/check-in/{res.id}/abschluss").text
    assert "17,50 € · normaler Satz" in page and "Kurtaxe bearbeiten" in page


def test_completion_is_refused_while_items_are_open(client, db):
    res = make_stay(db, [{}])
    response = client.post(f"/check-in/{res.id}/abschluss", follow_redirects=False)
    assert _path(response) == f"/check-in/{res.id}/avs"
    assert "noch nicht möglich" in _notice(response)
    assert _reload(db, res).status == RESERVED


def test_avs_values_order_and_incomplete_guest(client, db):
    from html import escape

    res = make_stay(db, [{"first": "Ada"}, {"first": "No", "birth": None}])
    page = client.get(f"/check-in/{res.id}/avs").text
    labels = [
        "Familienname",
        "Vorname",
        "Geburtsdatum",
        "Staatsangehörigkeit",
        "Straße und Hausnummer",
        "PLZ",
        "Ort",
        "Land",
        "Anreise",
        "Abreise",
        "Kurtaxe-Gruppe",
    ]
    positions = [page.index(f'aria-label="{escape(label)} kopieren"') for label in labels]
    assert positions == sorted(positions)
    assert 'data-copy="Deutschland"' in page and "Alle Angaben kopieren" in page
    assert "Daten unvollständig" in page
    assert f"/avs/{res.guests[1].id}/gedruckt" not in page
    client.post(f"/check-in/{res.id}/avs/alle")
    assert [rg.meldeschein_status for rg in _reload(db, res).guests] == ["gedruckt", "offen"]


def test_signature_later_and_safe_return(client, db):
    res = make_stay(db, [{}])
    rg = res.guests[0]
    response = client.post(f"/meldeschein/{rg.id}/unterschrieben", follow_redirects=False)
    assert "Erst in AVS drucken." in _notice(response)
    client.post(f"/check-in/{res.id}/avs/alle")
    res = _reload(db, res)
    res.status = CHECKED_IN
    db.commit()
    assert "Unterschrift fehlt" in client.get("/im-haus").text
    response = client.post(
        f"/meldeschein/{rg.id}/unterschrieben",
        data={"zurueck": "https://evil.invalid"},
        follow_redirects=False,
    )
    assert _path(response) == "/"
    assert _reload(db, res).guests[0].meldeschein_status == "unterschrieben"
    assert db.scalar(select(AuditEvent).where(AuditEvent.action == "meldeschein.signed"))


def test_only_reserved_arrivals_from_today_can_check_in(client, db):
    in_house = make_stay(db, [{}], code="R-TEST-0002")
    in_house.status = CHECKED_IN
    future = make_stay(db, [{}], code="R-TEST-0003", arrival=BUSINESS_DATE + timedelta(days=2))
    db.commit()

    r = client.get(f"/check-in/{in_house.id}/gaeste", follow_redirects=False)
    assert _path(r) == f"/reservierungen/{in_house.id}" and "Im Haus" in _notice(r)

    r = client.get(f"/check-in/{future.id}", follow_redirects=False)
    assert _path(r) == f"/reservierungen/{future.id}" and "frühestens am Anreisetag" in _notice(r)

    late = make_stay(db, [{}], code="R-TEST-0004", arrival=BUSINESS_DATE - timedelta(days=1))
    page = client.get(f"/check-in/{late.id}/avs")
    assert page.status_code == 200 and "Verspätete Anreise" in page.text


def test_add_and_remove_a_co_traveller(client, db):
    res = make_stay(db, [{"first": "Anja", "last": "König"}])
    r = client.post(
        f"/check-in/{res.id}/gaeste/hinzufuegen",
        data={"first_name": "Dieter", "last_name": "König", "birth_date": "1953-02-11"},
        follow_redirects=False,
    )
    assert "Dieter König ergänzt" in _notice(r)
    res = _reload(db, res)
    assert [rg.guest.full_name for rg in res.guests] == ["Anja König", "Dieter König"]
    assert res.guests[1].guest.city == res.guests[0].guest.city

    r = client.post(
        f"/check-in/{res.id}/gaeste/{res.guests[0].id}/entfernen", follow_redirects=False
    )
    assert "Hauptgast" in _notice(r)
    r = client.post(
        f"/check-in/{res.id}/gaeste/{res.guests[1].id}/entfernen", follow_redirects=False
    )
    assert "entfernt" in _notice(r)
    assert len(_reload(db, res).guests) == 1


def test_seeded_arrivals_surface_their_blockers(client, seeded):
    arrivals = seeded.scalars(
        select(Reservation)
        .where(Reservation.arrival == BUSINESS_DATE, Reservation.status == RESERVED)
        .order_by(Reservation.id)
    ).all()
    no_birth = next(r for r in arrivals if any(rg.guest.birth_date is None for rg in r.guests))
    assert (
        _path(client.get(f"/check-in/{no_birth.id}", follow_redirects=False))
        == f"/check-in/{no_birth.id}/gaeste"
    )
    missing_proof = next(
        r
        for r in arrivals
        if any(rg.exemption_category and not rg.exemption_evidence for rg in r.guests)
    )
    page = client.get(f"/check-in/{missing_proof.id}/abschluss")
    assert "Befreiungsnachweis fehlt" in page.text
    # the seed assessed every stay that is or was in house
    in_house = seeded.scalars(select(Reservation).where(Reservation.status == CHECKED_IN)).all()
    assert in_house and all(r.kurtaxe is not None for r in in_house)


def test_three_step_entry_and_stepper(client, db):
    """AC-1: complete data goes directly to AVS, with exactly three steps."""
    import re

    from kurort_app.services import engine

    assert engine.STEP_KEYS == ("gaeste", "avs", "abschluss")
    res = make_stay(db, [{}])
    response = client.get(f"/check-in/{res.id}", follow_redirects=False)
    assert response.status_code == 303
    assert _path(response) == f"/check-in/{res.id}/avs"
    page = client.get(f"/check-in/{res.id}/gaeste").text
    assert re.findall(r'<span class="ci-step-label">(.*?)</span>', page) == [
        "Gäste &amp; Daten",
        "AVS",
        "Abschluss",
    ]


def test_avs_link_is_optional_and_foreign_id_is_in_order(client, db, monkeypatch):
    res = make_stay(db, [{}])
    guest = res.guests[0].guest
    guest.nationality = "AT"
    guest.id_document_number = "P123456"
    db.commit()
    page = client.get(f"/check-in/{res.id}/avs").text
    assert "AVS öffnen" not in page
    assert (
        page.index("Land kopieren")
        < page.index("Ausweisnummer kopieren")
        < page.index("Anreise kopieren")
    )
    assert 'data-copy="P123456"' in page and 'data-copy="Österreich"' in page
    monkeypatch.setattr(get_settings(), "avs_url", "https://avs.example.invalid/login")
    page = client.get(f"/check-in/{res.id}/avs").text
    assert 'href="https://avs.example.invalid/login"' in page and 'target="_blank"' in page
    assert "AVS öffnen" in page
