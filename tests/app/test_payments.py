"""F4: received payments, desk balances and editable payment methods."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select

from kurort_app import defaults, models
from tests.app.conftest import BUSINESS_DATE


def test_ac1_default_methods_preserve_manager_changes(db):
    defaults.ensure_defaults(db)
    assert "payment_methods" in inspect(db.bind).get_table_names()
    methods = list(db.scalars(select(models.PaymentMethod).order_by(models.PaymentMethod.position)))
    assert [(m.code, m.label, m.deferred, m.active) for m in methods] == [
        ("bar", "Bar", False, True),
        ("ec", "EC-Karte", False, True),
        ("kreditkarte", "Kreditkarte", False, True),
        ("ueberweisung", "Überweisung", False, True),
        ("booking", "Booking.com (vorausbezahlt)", False, True),
        ("rechnung", "Auf Rechnung", True, True),
    ]
    methods[0].label, methods[0].active, methods[0].position = "Bargeld", False, 99
    db.commit()
    defaults.ensure_defaults(db)
    db.expire_all()
    assert db.get(models.PaymentMethod, methods[0].id).label == "Bargeld"
    assert not db.get(models.PaymentMethod, methods[0].id).active
    assert db.get(models.PaymentMethod, methods[0].id).position == 99
    assert len(list(db.scalars(select(models.PaymentMethod)))) == 6


@pytest.mark.parametrize(
    "amounts,tax,status,cancelled,expected",
    [
        ([], "20", "reserved", False, ("420", "0", "420", "offen")),
        (["120.50"], "20", "reserved", False, ("420", "120.50", "299.50", "offen")),
        (["420"], "20", "checked_in", False, ("420", "420", "0", "bezahlt")),
        (["440"], "20", "checked_out", False, ("420", "440", "-20", "guthaben")),
        ([], None, "reserved", False, ("400", "0", "400", "offen")),
        (["50"], "20", "cancelled", False, ("0", "50", "-50", "guthaben")),
        (["50"], "20", "no_show", False, ("0", "50", "-50", "guthaben")),
        (["420"], "20", "checked_in", True, ("420", "0", "420", "offen")),
    ],
)
def test_ac6_balance(amounts, tax, status, cancelled, expected):
    from kurort_app.services.payments import balance

    r = models.Reservation(rate_total=Decimal("400"), status=status)
    if tax is not None:
        r.kurtaxe = models.KurtaxeAssessment(amount=Decimal(tax))
    r.payments = [
        models.Payment(
            amount=Decimal(amount),
            paid_on=BUSINESS_DATE,
            received_on=BUSINESS_DATE,
            cancelled_at=datetime.now(UTC) if cancelled else None,
        )
        for amount in amounts
    ]
    b = balance(r)
    assert (b.due, b.paid, b.open, b.state) == (*(Decimal(v) for v in expected[:3]), expected[3])
    assert b.room == Decimal("400")
    assert b.kurtaxe == (Decimal(tax) if tax is not None else None)
    assert b.awaiting == 0


def test_ac6_deferred_awaiting_is_independent_of_later_method_edits():
    from kurort_app.services.payments import balance

    r = models.Reservation(rate_total=Decimal("400"), status="checked_in")
    r.payments = [models.Payment(amount=Decimal("400"), received_on=None)]
    assert balance(r).state == "bezahlt"
    assert balance(r).awaiting == Decimal("400")
    r.payments[0].received_on = BUSINESS_DATE
    assert balance(r).awaiting == 0


@pytest.fixture
def stay(db):
    from datetime import timedelta

    defaults.ensure_defaults(db)
    r = models.Reservation(
        code="PAY-1",
        arrival=BUSINESS_DATE - timedelta(days=2),
        departure=BUSINESS_DATE,
        status="checked_in",
        channel="direct",
        rate_total=Decimal("400"),
    )
    db.add(r)
    db.commit()
    return r


def _method(db, code="bar"):
    return db.scalar(select(models.PaymentMethod).where(models.PaymentMethod.code == code))


def _post(client, db, r, **changes):
    data = {
        "amount": "120,50",
        "method_id": str(_method(db).id),
        "paid_on": BUSINESS_DATE.isoformat(),
    }
    data.update(changes)
    return client.post(f"/reservierungen/{r.id}/zahlungen", data=data, follow_redirects=False)


def _payments(db):
    db.expire_all()
    return list(db.scalars(select(models.Payment).order_by(models.Payment.id)))


def _audit(db, action):
    db.expire_all()
    return db.scalar(
        select(models.AuditEvent)
        .where(models.AuditEvent.action == action)
        .order_by(models.AuditEvent.id.desc())
    )


def test_ac2_record_payment_and_audit(client, db, stay):
    response = _post(client, db, stay, payer="Firma Müller GmbH", note="Anzahlung")
    assert response.status_code == 303
    assert response.headers["location"].startswith(f"/reservierungen/{stay.id}?")
    assert response.headers["location"].endswith("#zahlung")
    p = _payments(db)[0]
    assert p.amount == Decimal("120.50") and p.received_on == BUSINESS_DATE
    assert p.recorded_by == "rezeption" and p.recorded_at is not None
    assert p.payer == "Firma Müller GmbH" and p.note == "Anzahlung"
    event = _audit(db, "payment_recorded")
    assert event.entity == "reservation" and event.entity_id == str(stay.id)
    assert event.payload == {"payment_id": p.id, "amount": "120.50", "method": "bar"}
    html = client.get(f"/reservierungen/{stay.id}").text
    assert "Offen 279,50 €" in html
    assert "Firma Müller GmbH" in html and "rezeption" in html


@pytest.mark.parametrize(
    "changes,message",
    [
        ({"amount": ""}, "Betrag fehlt"),
        ({"amount": "0"}, "Betrag muss größer als 0 sein"),
        ({"amount": "12,345"}, "Höchstens zwei Nachkommastellen"),
        ({"amount": "100.000,01"}, "Höchstens 100.000,00 €"),
        ({"amount": "NaN"}, "Betrag ungültig"),
        ({"amount": "1e2"}, "Betrag ungültig"),
        ({"method_id": "9999"}, "Zahlungsart wählen"),
        ({"paid_on": "2026-10-15"}, "Datum liegt in der Zukunft"),
        ({"paid_on": "falsch"}, "Datum ungültig"),
        ({"payer": "x" * 121}, "Höchstens 120 Zeichen"),
        ({"note": "x" * 201}, "Höchstens 200 Zeichen"),
    ],
)
def test_ac3_invalid_payment_writes_nothing(client, db, stay, changes, message):
    response = _post(client, db, stay, **changes)
    assert response.status_code == 200 and message in response.text
    assert 'aria-invalid="true"' in response.text
    assert not _payments(db) and _audit(db, "payment_recorded") is None


def test_ac3_inactive_method(client, db, stay):
    method = _method(db)
    method.active = False
    db.commit()
    response = _post(client, db, stay)
    assert response.status_code == 200 and "Zahlungsart wählen" in response.text
    assert not _payments(db)


@pytest.mark.parametrize(
    "amount,expected", [("1.234,50", "1234.50"), ("120.50", "120.50"), ("100.000,00", "100000.00")]
)
def test_german_amounts_and_warning_before_overpayment(client, db, stay, amount, expected):
    response = _post(client, db, stay, amount=amount)
    if Decimal(expected) > 400:
        assert response.status_code == 200 and "Mehr als offen – Guthaben" in response.text
        assert not _payments(db)
        response = _post(client, db, stay, amount=amount, confirm_overpayment="1")
    assert response.status_code == 303
    assert _payments(db)[0].amount == Decimal(expected)
    if Decimal(expected) > 400:
        assert "Guthaben" in client.get(f"/reservierungen/{stay.id}").text


def test_ac4_cancel_requires_reason_and_cannot_be_repeated(client, db, stay):
    _post(client, db, stay)
    p = _payments(db)[0]
    url = f"/reservierungen/{stay.id}/zahlungen/{p.id}/stornieren"
    invalid = client.post(url, data={"reason": " "})
    assert invalid.status_code == 200 and "Grund fehlt" in invalid.text
    assert _payments(db)[0].cancelled_at is None
    assert (
        client.post(url, data={"reason": "Doppelt erfasst"}, follow_redirects=False).status_code
        == 303
    )
    p = _payments(db)[0]
    assert p.cancel_reason == "Doppelt erfasst" and p.cancelled_by == "rezeption"
    assert _audit(db, "payment_cancelled").payload["reason"] == "Doppelt erfasst"
    html = client.get(f"/reservierungen/{stay.id}").text
    assert "Offen 400,00 €" in html and "<s>" in html and "Doppelt erfasst" in html
    assert (
        client.post(url, data={"reason": "Noch einmal"}, follow_redirects=False).status_code == 409
    )


def test_ac5_deferred_receipt_and_validation(client, db, stay):
    _post(
        client,
        db,
        stay,
        amount="400",
        method_id=str(_method(db, "rechnung").id),
        payer="Firma Müller GmbH",
    )
    p = _payments(db)[0]
    assert p.received_on is None
    assert "Bezahlt · Rechnung offen 400,00 €" in client.get(f"/reservierungen/{stay.id}").text
    assert f'data-payment-id="{p.id}"' in client.get("/zahlungen/offen?ansicht=rechnung").text
    url = f"/zahlungen/{p.id}/eingang"
    for value in ("2026-10-15", "2026-10-13", "falsch"):
        response = client.post(url, data={"received_on": value})
        assert response.status_code == 200
        assert _payments(db)[0].received_on is None
    assert (
        client.post(
            url, data={"received_on": BUSINESS_DATE.isoformat()}, follow_redirects=False
        ).status_code
        == 303
    )
    assert _payments(db)[0].received_on == BUSINESS_DATE
    assert f'data-payment-id="{p.id}"' not in client.get("/zahlungen/offen?ansicht=rechnung").text
    assert _audit(db, "payment_received").payload["method"] == "rechnung"
    assert (
        client.post(
            url, data={"received_on": BUSINESS_DATE.isoformat()}, follow_redirects=False
        ).status_code
        == 409
    )


def test_ac7_today_departures_only_and_dashboard_notice(client, db, stay):
    from datetime import timedelta

    arrival = models.Reservation(
        code="PAY-ARR",
        arrival=BUSINESS_DATE,
        departure=BUSINESS_DATE + timedelta(days=1),
        status="reserved",
        channel="direct",
        rate_total=Decimal("400"),
    )
    db.add(arrival)
    db.commit()
    html = client.get("/").text
    assert f'href="/reservierungen/{stay.id}#zahlung"' in html
    assert "Offen 400,00 €" in html and "1 offene Beträge" in html
    row = html.split(f'data-reservation-id="{arrival.id}"', 1)[1].split("</tr>", 1)[0]
    assert "Offen 400,00 €" not in row and "Bezahlt" not in row
    _post(client, db, stay, amount="400")
    assert "Bezahlt" in client.get("/").text
    assert "offene Beträge</a>" not in client.get("/").text


def test_ac8_checkout_payment_and_unpaid_checkout_audit(client, db, stay):
    html = client.get(f"/check-out/{stay.id}").text
    assert "Offener Betrag 400,00 € – bitte vor dem Check-out kassieren" in html
    assert f'action="/reservierungen/{stay.id}/zahlungen"' in html
    response = _post(client, db, stay, next=f"/check-out/{stay.id}")
    assert response.status_code == 303 and response.headers["location"].startswith(
        f"/check-out/{stay.id}?"
    )
    html = client.get(f"/check-out/{stay.id}").text
    assert "279,50 €" in html and "Bar" in html
    response = client.post(f"/check-out/{stay.id}", follow_redirects=False)
    assert response.status_code == 303
    assert _audit(db, "check_out").payload["open"] == "279.50"


def test_ac9_open_list_filters_and_sorts(client, db, stay):
    from datetime import timedelta

    for idx, (status, departure) in enumerate(
        [
            ("checked_out", -2),
            ("checked_out", -1),
            ("reserved", 1),
            ("cancelled", 1),
            ("no_show", 1),
        ]
    ):
        db.add(
            models.Reservation(
                code=f"FILTER-{idx}",
                arrival=BUSINESS_DATE - timedelta(days=4),
                departure=BUSINESS_DATE + timedelta(days=departure),
                status=status,
                channel="direct",
                rate_total=Decimal("200"),
            )
        )
    db.commit()
    html = client.get("/zahlungen/offen").text
    assert html.index("FILTER-0") < html.index("FILTER-1") < html.index(stay.code)
    assert all(f"FILTER-{i}" not in html for i in (2, 3, 4))
    _post(client, db, stay, amount="400")
    assert f'data-reservation-id="{stay.id}"' not in client.get("/zahlungen/offen").text
    assert 'href="/zahlungen/offen"' in client.get("/abreisen").text


def test_ac10_method_management_keeps_history_and_code(client, db, stay):
    _post(client, db, stay)
    bar, ec = _method(db), _method(db, "ec")
    response = client.post(
        "/verwaltung/zahlungsarten",
        data={"code": "gutschein", "label": "Gutschein", "active": "1", "deferred": "1"},
        follow_redirects=False,
    )
    assert response.status_code == 303 and _method(db, "gutschein").deferred
    assert _audit(db, "payment_method_created") is not None
    url = f"/verwaltung/zahlungsarten/{bar.id}"
    response = client.post(
        url, data={"code": "changed", "label": "Bargeld", "deferred": "1"}, follow_redirects=False
    )
    assert response.status_code == 303
    db.expire_all()
    assert _method(db).label == "Bargeld" and not _method(db).active
    assert _payments(db)[0].received_on == BUSINESS_DATE
    html = client.get(f"/reservierungen/{stay.id}").text
    assert "Bargeld" in html
    assert f'<option value="{bar.id}"' not in html
    assert _audit(db, "payment_method_updated") is not None
    assert (
        client.post(
            f"/verwaltung/zahlungsarten/{ec.id}", data={"move": "up"}, follow_redirects=False
        ).status_code
        == 303
    )
    db.expire_all()
    assert _method(db, "ec").position < _method(db).position


def test_ac10_oidc_roles_and_actor(oidc_client, idp, db, stay):
    from tests.app.auth_helpers import login

    idp.claims["roles"] = ["rezeption"]
    login(oidc_client)
    assert oidc_client.get("/verwaltung/zahlungsarten").status_code == 403
    assert (
        oidc_client.post("/verwaltung/zahlungsarten", data={"code": "x", "label": "X"}).status_code
        == 403
    )
    assert (
        oidc_client.post(
            f"/verwaltung/zahlungsarten/{_method(db).id}", data={"label": "X"}
        ).status_code
        == 403
    )
    assert _post(oidc_client, db, stay).status_code == 303
    assert _payments(db)[0].recorded_by == _audit(db, "payment_recorded").actor
    assert _payments(db)[0].recorded_by != "rezeption"
    assert oidc_client.post("/auth/logout", follow_redirects=False).status_code == 303
    idp.claims["roles"] = ["leitung"]
    login(oidc_client)
    assert oidc_client.get("/verwaltung/zahlungsarten").status_code == 200
    assert (
        oidc_client.post(
            "/verwaltung/zahlungsarten",
            data={"code": "neu", "label": "Neu"},
            follow_redirects=False,
        ).status_code
        == 303
    )


def test_ac11_amount_screens_disclaim_invoice(client, db, stay):
    for url in (
        f"/reservierungen/{stay.id}",
        f"/check-out/{stay.id}",
        "/zahlungen/offen",
        "/zahlungen/offen?ansicht=rechnung",
        "/abreisen",
        "/",
    ):
        assert "Zahlungsübersicht – keine Rechnung." in client.get(url).text


@pytest.mark.parametrize(
    "target",
    ["https://evil.test/", "//evil.test", "/\\evil.test", "/%2f%2fevil.test", "/\n/evil.test"],
)
def test_payment_next_cannot_redirect_off_site(client, db, stay, target):
    response = _post(client, db, stay, next=target)
    assert response.status_code == 303
    assert response.headers["location"].startswith(f"/reservierungen/{stay.id}?")


def test_cancelled_stay_rejects_payment_and_cross_stay_cancel(client, db, stay):
    _post(client, db, stay)
    p = _payments(db)[0]
    stay.status = "cancelled"
    db.commit()
    assert _post(client, db, stay).status_code == 200
    assert len(_payments(db)) == 1
    assert "Guthaben – Erstattung klären" in client.get(f"/reservierungen/{stay.id}").text
    assert (
        client.post(
            f"/reservierungen/9999/zahlungen/{p.id}/stornieren", data={"reason": "X"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/reservierungen/{stay.id}/zahlungen/{p.id}/stornieren",
            data={"reason": "Korrektur"},
            follow_redirects=False,
        ).status_code
        == 303
    )


def test_ac12_seed_payments_and_deterministic_reset(seeded):
    from kurort_app.seed import seed_demo_data
    from kurort_app.services.payments import balance

    def snapshot():
        seeded.expire_all()
        stays = list(seeded.scalars(select(models.Reservation).order_by(models.Reservation.id)))
        records = list(seeded.scalars(select(models.Payment).order_by(models.Payment.id)))
        assert records
        assert any(
            r.departure == BUSINESS_DATE and r.status == "checked_in" and balance(r).open > 0
            for r in stays
        )
        assert any(r.status == "checked_in" and 0 < balance(r).paid < balance(r).due for r in stays)
        assert any(
            r.channel == "booking.com"
            and balance(r).due > 0
            and balance(r).open == 0
            and any(p.method.code == "booking" for p in r.payments)
            for r in stays
        )
        assert any(p.method.code == "rechnung" and p.received_on is None for p in records)
        departed = [r for r in stays if r.status == "checked_out"]
        assert sum(balance(r).state == "bezahlt" for r in departed) > len(departed) / 2
        assert all(p.paid_on <= BUSINESS_DATE and p.recorded_at is not None for p in records)
        return (
            [
                (
                    r.code,
                    r.arrival,
                    r.departure,
                    r.status,
                    r.channel,
                    r.rate_total,
                    [(g.guest.full_name, g.guest.birth_date) for g in r.guests],
                )
                for r in stays
            ],
            [
                (
                    p.reservation_id,
                    p.method.code,
                    p.amount,
                    p.paid_on,
                    p.received_on,
                    p.payer,
                    p.recorded_at,
                )
                for p in records
            ],
        )

    first = snapshot()
    seeded.expunge_all()
    seed_demo_data(seeded, reset=True, anchor=BUSINESS_DATE)
    assert snapshot() == first
