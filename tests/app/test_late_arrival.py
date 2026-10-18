"""F5 late arrivals: preparation, PIN privacy and next-shift resolution."""

import json
from datetime import time, timedelta

from sqlalchemy import select

from kurort_app.config import get_settings
from kurort_app.defaults import ensure_defaults
from kurort_app.models import AuditEvent, EmailMessageRow, LateArrival, Reservation, SafeCompartment
from tests.app.conftest import BUSINESS_DATE
from tests.app.test_engine_adapter import make_stay


def stay(db, *, code="LATE-1", email=True):
    ensure_defaults(db)
    r = make_stay(db, [{"first": "Anna"}, {"first": "Peter"}], code=code)
    r.eta = time(21, 30)
    r.primary_guest.email = "anna@example.de" if email else None
    for rg in r.guests:
        rg.meldeschein_status = "gedruckt"
    db.commit()
    return r


def prepare(client, r, compartment=1):
    return client.post(
        f"/spaetanreise/{r.id}",
        data={"compartment_id": str(compartment), "key_in_safe": "on", "meldeschein_in_safe": "on"},
    )


def tomorrow(monkeypatch):
    monkeypatch.setenv("KURORT_TODAY", (BUSINESS_DATE + timedelta(days=1)).isoformat())
    get_settings.cache_clear()


def test_ac7_late_boundary_and_manual_entry(client, db):
    r = stay(db)
    r.eta = time(18)
    db.commit()
    assert "Spätanreise 18:00 · vorbereiten" in client.get("/").text
    r.eta = time(17, 59)
    db.commit()
    assert "Spätanreise 17:59" not in client.get("/").text
    r.eta = None
    db.commit()
    assert f'href="/spaetanreise/{r.id}"' in client.get(f"/reservierungen/{r.id}").text


def test_ac8_generated_pin_once_and_ac10_privacy(client, db):
    r = stay(db)
    page = prepare(client, r)
    assert page.status_code == 200
    late = db.scalar(select(LateArrival))
    assert late is not None and late.status == "vorbereitet"
    pin = late.pin
    assert len(pin) == 4 and pin.isdigit() and len(set(pin)) > 1
    assert pin not in "0123456789" and pin not in "9876543210"
    message = db.get(EmailMessageRow, late.email_message_id)
    assert pin in message.body and "Fach 1" in message.body and message.status == "logged"
    assert pin in page.text and "jetzt am Safe" in page.text
    for path in (
        f"/spaetanreise/{r.id}",
        "/e-mails",
        f"/e-mails/{message.id}",
        f"/reservierungen/{r.id}",
    ):
        assert pin not in client.get(path).text
    assert "••••" in client.get(f"/spaetanreise/{r.id}").text
    assert pin in client.post(f"/spaetanreise/{r.id}/pin").text
    events = db.scalars(select(AuditEvent)).all()
    assert pin not in json.dumps([{"summary": e.summary, "payload": e.payload} for e in events])
    assert any(e.action == "late_arrival_pin_viewed" for e in events)
    db.refresh(r)
    assert r.status == "reserved" and r.checked_in_at is None


def test_ac8_fixed_pin_not_copied(client, db):
    r = stay(db)
    c = db.get(SafeCompartment, 1)
    c.fixed_pin = "481792"
    db.commit()
    assert "Fester Code" in prepare(client, r).text
    late = db.scalar(select(LateArrival))
    assert late.pin is None and "481792" in late.email_message.body


def test_ac9_prerequisite_occupied_and_phone(client, db):
    r = stay(db, email=False)
    r.guests[1].meldeschein_status = "offen"
    db.commit()
    assert "Meldeschein erst in AVS drucken" in prepare(client, r).text
    assert db.scalar(select(LateArrival)) is None
    r.guests[1].meldeschein_status = "gedruckt"
    db.commit()
    assert "PIN telefonisch mitteilen" in prepare(client, r).text
    assert db.scalar(select(EmailMessageRow)) is None
    client.post(f"/spaetanreise/{r.id}/telefonisch")
    assert db.scalar(
        select(AuditEvent.id).where(AuditEvent.action == "late_arrival_phone_notified")
    )
    other = stay(db, code="LATE-2")
    assert '<option value="1"' not in client.get(f"/spaetanreise/{other.id}").text
    assert "belegt" in prepare(client, other).text
    assert len(db.scalars(select(LateArrival)).all()) == 1


def test_ac11_arrived_then_paper_completes(client, db, monkeypatch):
    from kurort_app.services import engine, today

    r = stay(db)
    prepare(client, r)
    late = db.scalar(select(LateArrival))
    pin = late.pin
    tomorrow(monkeypatch)
    assert r.code in client.get("/spaetanreisen").text
    assert "Meldeschein ausstehend" in client.get("/").text
    monkeypatch.setattr(
        today, "CHECKIN_BLOCKERS", [lambda s, r: [engine.Blocker("abschluss", "Nicht sauber")]]
    )
    client.post(f"/spaetanreise/{r.id}/angekommen")
    db.expire_all()
    assert r.status == "checked_in" and r.checked_in_at and r.kurtaxe
    assert late.status == "angereist" and late.pin is None
    assert pin not in late.email_message.body and "••••" in late.email_message.body
    assert r.code in client.get("/spaetanreisen").text
    client.post(f"/spaetanreise/{r.id}/meldeschein")
    db.expire_all()
    assert late.status == "abgeschlossen"
    assert all(g.meldeschein_status == "unterschrieben" for g in r.guests)
    assert r.code not in client.get("/spaetanreisen").text
    get_settings.cache_clear()


def test_ac12_no_show_cancel_and_paper_first(client, db, monkeypatch):
    r = stay(db)
    prepare(client, r)
    client.post(f"/spaetanreise/{r.id}/abbrechen")
    db.expire_all()
    late = db.scalar(select(LateArrival))
    assert late.status == "abgebrochen" and late.pin is None and r.status == "reserved"
    assert '<option value="1"' in client.get(f"/spaetanreise/{r.id}").text
    prepare(client, r)
    tomorrow(monkeypatch)
    client.post(f"/spaetanreise/{r.id}/nicht-angereist")
    db.expire_all()
    assert r.status == "no_show" and late.status == "nicht_angereist" and late.pin is None
    other = stay(db, code="LATE-2")
    # Move back to prepare the second stay, then hand in the paper before arrival.
    monkeypatch.setenv("KURORT_TODAY", BUSINESS_DATE.isoformat())
    get_settings.cache_clear()
    prepare(client, other)
    client.post(f"/spaetanreise/{other.id}/meldeschein")
    client.post(f"/spaetanreise/{other.id}/angekommen")
    db.expire_all()
    assert (
        db.scalar(select(LateArrival).where(LateArrival.reservation_id == other.id)).status
        == "abgeschlossen"
    )
    get_settings.cache_clear()


def test_ac13_seed_reset_is_deterministic(client, db):
    from kurort_app.seed import seed_demo_data

    def snapshot():
        late = db.scalar(select(LateArrival))
        today = db.scalar(select(Reservation).where(Reservation.code == "F5-HEUTE"))
        assert (
            today.arrival == BUSINESS_DATE
            and today.eta == time(21, 30)
            and today.primary_guest.email
        )
        assert all(g.meldeschein_status == "gedruckt" for g in today.guests)
        assert late.reservation.arrival == BUSINESS_DATE - timedelta(days=1)
        assert late.reservation.status == "reserved" and late.compartment.label == "Fach 2"
        assert late.email_message.status == "logged"
        return today.id, today.primary_guest.full_name, late.pin, late.email_message.body

    seed_demo_data(db, reset=True, anchor=BUSINESS_DATE)
    first = snapshot()
    db.expunge_all()
    seed_demo_data(db, reset=True, anchor=BUSINESS_DATE)
    assert snapshot() == first


def test_pin_generation_rejects_weak_sequences(monkeypatch):
    from kurort_app.services import late_arrival

    candidates = iter([1, 1, 1, 1, 1, 2, 3, 4, 9, 8, 7, 6, 4, 8, 1, 7])
    monkeypatch.setattr(late_arrival.secrets, "randbelow", lambda _: next(candidates))
    assert late_arrival.generate_pin() == "4817"


def test_preparation_hints_do_not_block_and_no_duplicate_send(client, db, monkeypatch):
    from kurort_app.services import engine, today

    r = stay(db)
    monkeypatch.setattr(
        today,
        "CHECKIN_BLOCKERS",
        [lambda s, r: [engine.Blocker("abschluss", "Zimmer noch nicht sauber")]],
    )
    assert "Zimmer noch nicht sauber" in client.get(f"/spaetanreise/{r.id}").text
    prepare(client, r)
    assert prepare(client, r).status_code == 200
    assert len(db.scalars(select(EmailMessageRow)).all()) == 1
    assert len(db.scalars(select(LateArrival)).all()) == 1


def test_cleared_fixed_pin_is_redacted_and_unavailable(client, db):
    r = stay(db)
    db.get(SafeCompartment, 1).fixed_pin = "481792"
    db.commit()
    prepare(client, r)
    client.post(f"/spaetanreise/{r.id}/abbrechen")
    db.expire_all()
    late = db.scalar(select(LateArrival))
    assert "481792" not in late.email_message.body and "••••" in late.email_message.body
    assert client.post(f"/spaetanreise/{r.id}/pin").status_code == 409
    assert '<option value="1"' in client.get(f"/spaetanreise/{r.id}").text


def test_late_arrival_roles(oidc_client, idp, db):
    from tests.app.auth_helpers import login

    r = stay(db)
    login(oidc_client)
    assert oidc_client.get(f"/spaetanreise/{r.id}").status_code == 200
    assert prepare(oidc_client, r).status_code == 200
    assert oidc_client.post(f"/spaetanreise/{r.id}/pin").status_code == 200
