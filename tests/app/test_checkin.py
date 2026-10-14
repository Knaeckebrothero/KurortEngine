"""The five-step check-in flow over HTTP."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select

from kurort_app.models import CHECKED_IN, RESERVED, AuditEvent, Reservation, ReservationGuest
from tests.app.conftest import BUSINESS_DATE
from tests.app.test_engine_adapter import _age, make_stay


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
    res = make_stay(
        db,
        [
            {"first": "Claudia", "last": "Wolf", "birth": _age(55)},
            {"first": "Klaus", "last": "Wolf", "birth": _age(58)},
        ],
    )
    rid = res.id
    rgs = [rg.id for rg in res.guests]

    r = client.get(f"/check-in/{rid}", follow_redirects=False)
    assert _path(r) == f"/check-in/{rid}/meldeschein"

    page = client.get(f"/check-in/{rid}/meldeschein")
    assert page.status_code == 200 and "Weiter zur Kurtaxe" in page.text

    r = client.post(f"/check-in/{rid}/meldeschein/alle", follow_redirects=False)
    assert r.status_code == 303
    for rg_id in rgs:
        assert (
            client.post(
                f"/check-in/{rid}/meldeschein/{rg_id}/unterschreiben", follow_redirects=False
            ).status_code
            == 303
        )

    r = client.post(f"/check-in/{rid}/kurtaxe", data={}, follow_redirects=False)
    assert _path(r) == f"/check-in/{rid}/kurkarte"
    assert "35,00 €" in _notice(r)

    r = client.post(f"/check-in/{rid}/kurkarte", follow_redirects=False)
    assert _path(r) == f"/check-in/{rid}/kurkarte"
    page = client.get(f"/check-in/{rid}/kurkarte")
    assert page.text.count("<svg xmlns") == 2  # one QR per guest

    summary = client.get(f"/check-in/{rid}/abschluss")
    assert "Check-in abschließen · Zimmer 204" in summary.text

    r = client.post(f"/check-in/{rid}/abschluss", follow_redirects=False)
    assert _path(r) == "/anreisen"
    assert _notice(r) == "Claudia Wolf ist eingecheckt · Zimmer 204"

    res = _reload(db, res)
    assert res.status == CHECKED_IN and res.checked_in_at is not None
    assert res.kurtaxe.amount == Decimal("35.00")
    actions = db.scalars(select(AuditEvent.action).order_by(AuditEvent.id)).all()
    assert actions.count("meldeschein.generated") == 2
    assert actions.count("meldeschein.signed") == 2
    assert actions.count("kurkarte.issued") == 2
    assert actions[-1] == "reservation.checked_in"
    assert "kurtaxe.assessed" in actions


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
    assert ok.status_code == 303 and _path(ok) == f"/check-in/{res.id}/meldeschein"
    assert _reload(db, res).guests[0].guest.birth_date.isoformat() == "1958-05-17"


def test_changing_data_after_generation_resets_the_meldeschein(client, db):
    res = make_stay(db, [{}])
    rg = res.guests[0]
    client.post(f"/check-in/{res.id}/meldeschein/{rg.id}/erzeugen")
    client.post(f"/check-in/{res.id}/meldeschein/{rg.id}/unterschreiben")
    r = client.post(
        f"/check-in/{res.id}/gaeste",
        data=_guest_form(rg, street="Am Kurpark 9"),
        follow_redirects=False,
    )
    assert "Meldeschein neu erzeugen" in _notice(r)
    assert _reload(db, res).guests[0].meldeschein_status == "offen"


def test_htmx_generation_returns_only_the_panel(client, db):
    res = make_stay(db, [{}])
    rg = res.guests[0]
    r = client.post(
        f"/check-in/{res.id}/meldeschein/{rg.id}/erzeugen", headers={"HX-Request": "true"}
    )
    assert r.status_code == 200
    assert 'id="meldeschein-panel"' in r.text and "<html" not in r.text
    assert "Unterschrift bestätigen" in r.text


def test_pdf_endpoint(client, db):
    res = make_stay(db, [{"last": "Müller"}])
    rg = res.guests[0]
    assert client.get(f"/meldeschein/{rg.id}.pdf").status_code == 404
    client.post(f"/check-in/{res.id}/meldeschein/{rg.id}/erzeugen")
    r = client.get(f"/meldeschein/{rg.id}.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF-")
    assert 'filename="Meldeschein-R-TEST-0001-M-ller.pdf"' in r.headers["content-disposition"]


def test_kurtaxe_exemption_needs_evidence(client, db):
    res = make_stay(db, [{"birth": _age(50)}])
    rg = res.guests[0]
    preview = client.post(
        f"/check-in/{res.id}/kurtaxe/vorschau",
        data={f"ex{rg.id}_category": "geschaeftsreisender", f"ex{rg.id}_evidence": ""},
    )
    assert "Nachweis fehlt" in preview.text and "<html" not in preview.text

    blocked = client.post(
        f"/check-in/{res.id}/kurtaxe",
        data={f"ex{rg.id}_category": "geschaeftsreisender", f"ex{rg.id}_evidence": ""},
    )
    assert blocked.status_code == 200 and "Kurtaxe nicht bestätigt" in blocked.text
    assert _reload(db, res).kurtaxe is None

    ok = client.post(
        f"/check-in/{res.id}/kurtaxe",
        data={
            f"ex{rg.id}_category": "geschaeftsreisender",
            f"ex{rg.id}_evidence": "Bescheinigung Weber GmbH",
        },
        follow_redirects=False,
    )
    assert ok.status_code == 303 and "0,00 €" in _notice(ok)
    res = _reload(db, res)
    assert res.kurtaxe.amount == Decimal("0.00")
    assert res.guests[0].exemption_evidence == "Bescheinigung Weber GmbH"


def test_kurkarte_waits_for_the_kurtaxe(client, db):
    res = make_stay(db, [{}])
    r = client.post(f"/check-in/{res.id}/kurkarte", follow_redirects=False)
    assert _path(r) == f"/check-in/{res.id}/kurtaxe"
    assert _reload(db, res).guests[0].kurkarte_code is None


def test_completion_is_refused_while_items_are_open(client, db):
    res = make_stay(db, [{}])
    r = client.post(f"/check-in/{res.id}/abschluss", follow_redirects=False)
    assert _path(r) == f"/check-in/{res.id}/meldeschein"
    assert "noch nicht möglich" in _notice(r)
    assert _reload(db, res).status == RESERVED


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
    page = client.get(f"/check-in/{late.id}/meldeschein")
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
    page = client.get(f"/check-in/{missing_proof.id}/kurtaxe")
    assert "Befreiungsnachweis fehlt" in page.text
    # the seed assessed every stay that is or was in house
    in_house = seeded.scalars(select(Reservation).where(Reservation.status == CHECKED_IN)).all()
    assert in_house and all(r.kurtaxe is not None for r in in_house)
