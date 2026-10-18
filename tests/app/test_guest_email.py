"""F5 guest mail: editable templates, safe rendering and synchronous transports."""

from sqlalchemy import text

from tests.app.test_engine_adapter import make_stay


def test_ac1_defaults_are_idempotent(db):
    from kurort_app.defaults import ensure_defaults

    ensure_defaults(db)
    tables = set(
        db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).scalars()
    )
    assert "email_templates" in tables
    assert db.scalar(text("SELECT count(*) FROM email_templates")) == 4
    assert db.scalar(text("SELECT system FROM email_templates WHERE key='spaetanreise'"))
    assert db.scalar(text("SELECT count(*) FROM safe_compartments")) == 3
    db.execute(
        text("UPDATE email_templates SET body='Vom Hotel angepasst' WHERE key='nach_abreise'")
    )
    db.commit()
    ensure_defaults(db)
    assert (
        db.scalar(text("SELECT body FROM email_templates WHERE key='nach_abreise'"))
        == "Vom Hotel angepasst"
    )


def test_ac3_compose_logs_exact_message_and_history(client, db):
    from kurort_app.defaults import ensure_defaults

    ensure_defaults(db)
    res = make_stay(db, [{"first": "Anna"}])
    res.primary_guest.email = "anna@example.de"
    db.commit()
    response = client.get(f"/reservierungen/{res.id}/e-mail")
    assert response.status_code == 200
    assert "spaetanreise" not in response.text
    response = client.post(
        f"/reservierungen/{res.id}/e-mail",
        data={
            "template_key": "buchungsbestaetigung",
            "to_address": "anna@example.de",
            "subject": "Ihre Buchung {{ reservierung.code }}",
            "body": "Guten Tag {{ gast.vorname }} – schön, dass Sie kommen!",
        },
    )
    assert response.status_code == 200
    assert "protokolliert – nicht versendet" in response.text
    row = db.execute(text("SELECT * FROM email_messages")).mappings().one()
    assert row["subject"] == f"Ihre Buchung {res.code}"
    assert row["body"] == "Guten Tag Anna – schön, dass Sie kommen!"
    assert row["status"] == "logged" and row["attempts"] == 1 and row["sent_at"]
    assert db.scalar(text("SELECT count(*) FROM audit_events WHERE action='email_logged'")) == 1


def test_ac2_rendering_and_invalid_placeholders_block_writes(client, seeded):
    from sqlalchemy import select

    from kurort_app.models import EmailTemplate, Reservation
    from kurort_app.services import mail_templates

    r = seeded.scalar(select(Reservation).where(Reservation.room_id.is_not(None)))
    t = seeded.scalar(select(EmailTemplate).where(EmailTemplate.key == "buchungsbestaetigung"))
    subject, body = mail_templates.render(t.subject, t.body, mail_templates.context_for(r))
    assert r.primary_guest.first_name in body
    assert "2026" in body and r.room.number in body and r.code in subject
    form = dict(key=t.key, name=t.name, subject=t.subject, body="{{ gast.vornamee }}", active="on")
    response = client.post(f"/verwaltung/e-mail/vorlagen/{t.key}", data=form)
    assert response.status_code == 422 and "Unbekannter Platzhalter: gast.vornamee" in response.text
    response = client.post(
        f"/reservierungen/{r.id}/e-mail",
        data=dict(
            template_key=t.key,
            to_address="anna@example.de",
            subject="Test",
            body="{{ gast.vornamee }}",
        ),
    )
    assert response.status_code == 422 and "Unbekannter Platzhalter" in response.text
    assert (
        seeded.scalar(
            text("SELECT count(*) FROM email_messages WHERE reservation_id=:rid").bindparams(
                rid=r.id
            )
        )
        == 0
    )
    for subject, body in [
        ("Test\nBcc: böse@example.de", "Hallo"),
        ("Test", "{{ gast.__class__ }}"),
        ("Test", "{% for x in range(100) %}x{% endfor %}"),
        ("Test", "{{ safe.pin }}"),
    ]:
        response = client.post(
            f"/reservierungen/{r.id}/e-mail/vorschau", data=dict(subject=subject, body=body)
        )
        assert 'role="alert"' in response.text


def test_ac4_smtp_failure_retry_and_queued_commit(client, db, monkeypatch):
    import smtplib

    from sqlalchemy import select

    from kurort_app.config import Settings
    from kurort_app.defaults import ensure_defaults
    from kurort_app.models import EmailMessageRow
    from kurort_app.services import mail

    ensure_defaults(db)
    r = make_stay(db, [{}])
    seen = []

    class FakeSMTP:
        fail = False

        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("mail.test", 587, 10)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def starttls(self, context):
            assert context is not None

        def login(self, user, password):
            assert (user, password) == ("hotel", "secret")

        def send_message(self, wire):
            from kurort_app.db import get_sessionmaker

            with get_sessionmaker()() as other:
                assert (
                    other.scalar(select(EmailMessageRow.status).where(EmailMessageRow.id == row.id))
                    == "queued"
                )
            if self.fail:
                raise smtplib.SMTPException("Mailserver nicht erreichbar")
            seen.append(wire)

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    settings = Settings(
        auth="off",
        mail_transport="smtp",
        smtp_host="mail.test",
        smtp_from="Hotel Rheinland <hotel@example.de>",
        smtp_user="hotel",
        smtp_password="secret",
    )
    row = EmailMessageRow(
        reservation_id=r.id,
        to_address="gast@example.de",
        subject="Grüße",
        body="Schön, dass Sie kommen!",
        template_key="buchungsbestaetigung",
    )
    FakeSMTP.fail = True
    mail.send(db, row, settings=settings)
    assert row.status == "failed" and "Mailserver nicht erreichbar" in row.error
    page = client.get(f"/e-mails/{row.id}").text
    assert "fehlgeschlagen" in page and "Erneut senden" in page
    FakeSMTP.fail = False
    client.app.state.settings = settings
    assert client.post(f"/e-mails/{row.id}/erneut").status_code == 200
    db.expire_all()
    assert row.status == "sent" and row.attempts == 2 and len(seen) == 1
    wire = seen[0]
    assert (
        wire["From"] == settings.smtp_from
        and wire["To"] == "gast@example.de"
        and wire["Subject"] == "Grüße"
    )
    assert wire["Date"] and wire["Message-ID"] and wire.get_content_charset() == "utf-8"
    assert wire.get_content() == "Schön, dass Sie kommen!\n"
    assert db.scalar(text("SELECT count(*) FROM audit_events WHERE action='email_retried'")) == 1


def test_ac5_smtp_configuration_refuses_startup():
    import pytest

    from kurort_app.config import Settings
    from kurort_app.main import create_app

    with pytest.raises(ValueError, match="KURORT_SMTP_HOST.*KURORT_SMTP_FROM"):
        create_app(Settings(auth="off", mail_transport="smtp", smtp_host=None, smtp_from=None))


def test_ac6_manager_edits_and_system_cannot_deactivate(client, db):
    from kurort_app.defaults import ensure_defaults

    ensure_defaults(db)
    r = make_stay(db, [{}])
    form = dict(
        key="buchungsbestaetigung",
        name="Bestätigung",
        subject="Willkommen",
        body="Guten Tag {{ gast.name }}",
        active="on",
    )
    assert (
        client.post("/verwaltung/e-mail/vorlagen/buchungsbestaetigung", data=form).status_code
        == 200
    )
    assert "Guten Tag {{ gast.name }}" in client.get(f"/reservierungen/{r.id}/e-mail").text
    form.update(key="spaetanreise", name="Spätanreise", active="")
    response = client.post("/verwaltung/e-mail/vorlagen/spaetanreise", data=form)
    assert response.status_code == 422 and "Systemvorlagen" in response.text
    assert db.scalar(text("SELECT active FROM email_templates WHERE key='spaetanreise'"))


def test_ac6_reception_cannot_edit_settings(oidc_client, idp, db):
    from kurort_app.defaults import ensure_defaults
    from tests.app.auth_helpers import login

    ensure_defaults(db)
    idp.claims["roles"] = ["rezeption"]
    login(oidc_client)
    for path in ("/verwaltung/e-mail", "/verwaltung/e-mail/vorlagen/buchungsbestaetigung"):
        assert oidc_client.get(path).status_code == 403
    assert oidc_client.post("/verwaltung/safe-faecher", data={"label": "Fach X"}).status_code == 403
    assert oidc_client.get("/e-mails").status_code == 200


def test_manager_oidc_edit_and_safe_settings(oidc_client, idp, db):
    from kurort_app.defaults import ensure_defaults

    ensure_defaults(db)
    from tests.app.auth_helpers import login

    idp.claims["roles"] = ["leitung"]
    login(oidc_client)
    assert oidc_client.get("/verwaltung/e-mail").status_code == 200
    form = dict(
        key="nach_abreise",
        name="Dankeschön",
        subject="Danke",
        body="Auf Wiedersehen {{ gast.name }}",
        active="on",
    )
    assert (
        oidc_client.post("/verwaltung/e-mail/vorlagen/nach_abreise", data=form).status_code == 200
    )
    assert (
        oidc_client.post(
            "/verwaltung/safe-faecher/1",
            data=dict(label="Fach 1", fixed_pin="481792", position="1", active="on"),
        ).status_code
        == 200
    )
    assert "481792" not in oidc_client.get("/verwaltung/e-mail").text
    assert db.scalar(text("SELECT fixed_pin FROM safe_compartments WHERE id=1")) == "481792"
    form.update(key="eigene_vorlage", name="Eigene Vorlage")
    assert oidc_client.post("/verwaltung/e-mail/vorlagen", data=form).status_code == 200
    assert db.scalar(text("SELECT count(*) FROM email_templates WHERE key='eigene_vorlage'")) == 1
