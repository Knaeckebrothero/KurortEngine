"""German plain-text templates with an explicitly string-only, bounded context.

Public interface: ``context_for(reservation, safe={"fach": label, "pin": pin})``;
``render(subject, body, context)``; ``validate_template(..., allow_safe=False)``.
No ORM objects, settings or callables are ever passed to the Jinja sandbox.
"""

from __future__ import annotations

from collections.abc import Mapping

from jinja2 import StrictUndefined, TemplateError, nodes
from jinja2.sandbox import SandboxedEnvironment
from sqlalchemy import select
from sqlalchemy.orm import Session

from kurort_app.config import Settings, get_settings
from kurort_app.models import EmailTemplate, Reservation
from kurort_app.web import fmt_date, fmt_time

DEFAULT_EMAIL_TEMPLATES = (
    {
        "key": "buchungsbestaetigung",
        "name": "Buchungsbestätigung",
        "subject": "Ihre Buchung {{ reservierung.code }} im {{ hotel.name }}",
        "body": (
            "Guten Tag {{ gast.vorname }} {{ gast.nachname }},\n\n"
            "herzlichen Dank für Ihre Buchung. Wir freuen uns auf Sie!\n"
            "Anreise: {{ reservierung.anreise }}\n"
            "Abreise: {{ reservierung.abreise }}\n"
            "Ihr Zimmer: {{ reservierung.zimmer }} ({{ reservierung.kategorie }})\n"
            "Aufenthalt: {{ reservierung.naechte }} Nächte\n\n"
            "Bei Fragen sind wir gerne für Sie da.\n\n"
            "Herzliche Grüße aus {{ hotel.ort }}\nIhr Team vom {{ hotel.name }}"
        ),
        "system": False,
    },
    {
        "key": "anreiseinformationen",
        "name": "Anreiseinformationen",
        "subject": "Ihre Anreise am {{ reservierung.anreise }} – {{ hotel.name }}",
        "body": (
            "Guten Tag {{ gast.name }},\n\n"
            "bald begrüßen wir Sie im {{ hotel.name }} in {{ hotel.ort }}.\n"
            "Für Sie ist Zimmer {{ reservierung.zimmer }} reserviert.\n"
            "Ihre angekündigte Ankunftszeit: {{ reservierung.ankunftszeit }}.\n\n"
            "Falls Sie nach 18 Uhr anreisen, melden Sie sich bitte vorher bei uns. "
            "Wir besprechen dann gerne die Schlüsselübergabe mit Ihnen.\n\n"
            "Wir wünschen Ihnen eine gute Reise!\nIhr Team vom {{ hotel.name }}"
        ),
        "system": False,
    },
    {
        "key": "spaetanreise",
        "name": "Spätanreise",
        "subject": "Ihre späte Anreise – {{ hotel.name }}",
        "body": (
            "Guten Tag {{ gast.name }},\n\n"
            "für Ihre Anreise am {{ reservierung.anreise }} haben wir Ihren "
            "Zimmerschlüssel und Meldeschein im Safe hinterlegt.\n\n"
            "Safe-Fach: {{ safe.fach }}\nPIN: {{ safe.pin }}\n"
            "Ihr Zimmer: {{ reservierung.zimmer }}\n\n"
            "Bitte unterschreiben Sie den Meldeschein und werfen Sie ihn in die "
            "Box an der Rezeption oder lassen Sie ihn in Ihrem Zimmer liegen.\n\n"
            "Kommen Sie gut an und fühlen Sie sich bei uns wohl!\n"
            "Ihr Team vom {{ hotel.name }} in {{ hotel.ort }}"
        ),
        "system": True,
    },
    {
        "key": "nach_abreise",
        "name": "Nach der Abreise",
        "subject": "Vielen Dank für Ihren Besuch im {{ hotel.name }}",
        "body": (
            "Guten Tag {{ gast.name }},\n\n"
            "vielen Dank, dass Sie bei uns in {{ hotel.ort }} zu Gast waren. "
            "Wir hoffen, Sie hatten eine erholsame Zeit und eine gute Heimreise.\n\n"
            "Wir würden uns freuen, Sie wieder bei uns begrüßen zu dürfen.\n\n"
            "Alles Gute und herzliche Grüße\nIhr Team vom {{ hotel.name }}"
        ),
        "system": False,
    },
)

PLACEHOLDERS = {
    "gast": ("vorname", "nachname", "name"),
    "reservierung": (
        "code",
        "anreise",
        "abreise",
        "naechte",
        "zimmer",
        "kategorie",
        "ankunftszeit",
    ),
    "hotel": ("name", "ort"),
}
SAFE_PLACEHOLDERS = {"safe": ("fach", "pin")}


class TemplateValidationError(ValueError):
    """Safe, German error text suitable for the editor and compose preview."""


_ENV = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False, keep_trailing_newline=True)
_ENV.globals.clear()


def ensure_email_templates(session: Session) -> None:
    """Insert only absent keys; never overwrite a manager's edits or inactive row."""
    existing = set(session.scalars(select(EmailTemplate.key)))
    for values in DEFAULT_EMAIL_TEMPLATES:
        if values["key"] not in existing:
            session.add(EmailTemplate(**values, active=True, updated_by="system"))
    session.flush()


def context_for(
    reservation: Reservation,
    safe: Mapping[str, str] | None = None,
    *,
    settings: Settings | None = None,
) -> dict[str, dict[str, str]]:
    """Preformat a stay; safe is opt-in and must contain only ``fach`` and ``pin`` strings."""
    settings = settings or get_settings()
    guest = reservation.primary_guest
    room = reservation.room
    context = {
        "gast": {
            "vorname": guest.first_name if guest else "",
            "nachname": guest.last_name if guest else "",
            "name": guest.full_name if guest else "",
        },
        "reservierung": {
            "code": reservation.code,
            "anreise": fmt_date(reservation.arrival, "long"),
            "abreise": fmt_date(reservation.departure, "long"),
            "naechte": str(reservation.nights),
            "zimmer": room.number if room else "noch nicht zugeteilt",
            "kategorie": room.category if room else "noch nicht zugeteilt",
            "ankunftszeit": fmt_time(reservation.eta) if reservation.eta else "nicht angegeben",
        },
        "hotel": {"name": settings.hotel_name, "ort": settings.hotel_city},
    }
    if safe is not None:
        if set(safe) != {"fach", "pin"} or any(type(v) is not str for v in safe.values()):
            raise TemplateValidationError("Safe-Kontext muss Fach und PIN als Text enthalten.")
        context["safe"] = dict(safe)
    return context


def demo_context(*, allow_safe: bool = False) -> dict[str, dict[str, str]]:
    """Fictitious editor preview, deliberately independent of real stays and safe codes."""
    context = {
        "gast": {"vorname": "Anna", "nachname": "Weber", "name": "Anna Weber"},
        "reservierung": {
            "code": "R-2610-0042",
            "anreise": "Mittwoch, 14. Oktober 2026",
            "abreise": "Samstag, 17. Oktober 2026",
            "naechte": "3",
            "zimmer": "204",
            "kategorie": "Doppelzimmer",
            "ankunftszeit": "21:30",
        },
        "hotel": {"name": "Hotel Rheinland", "ort": "Bad Orb"},
    }
    if allow_safe:
        context["safe"] = {"fach": "Beispielfach", "pin": "••••"}
    return context


def placeholder_names(*, allow_safe: bool = False) -> list[str]:
    groups = PLACEHOLDERS | (SAFE_PLACEHOLDERS if allow_safe else {})
    return [f"{group}.{field}" for group, fields in groups.items() for field in fields]


def _placeholder(node: nodes.Node) -> str | None:
    if isinstance(node, nodes.Name):
        return node.name
    if isinstance(node, nodes.Getattr):
        parent = _placeholder(node.node)
        return f"{parent}.{node.attr}" if parent else None
    if isinstance(node, nodes.Getitem) and isinstance(node.arg, nodes.Const):
        parent = _placeholder(node.node)
        return f"{parent}.{node.arg.value}" if parent else None
    return None


def _check_source(source: str, *, allow_safe: bool) -> None:
    try:
        parsed = _ENV.parse(source)
    except TemplateError as exc:
        raise TemplateValidationError(
            f"Vorlage konnte nicht gelesen werden: {exc.message}"
        ) from None
    allowed = set(placeholder_names(allow_safe=allow_safe))
    # Templates are plain text with placeholders, not programs. Reject all control
    # structures, calls and filters, including unknown names in unexecuted branches.
    for output in parsed.body:
        if not isinstance(output, nodes.Output):
            raise TemplateValidationError(
                "Bitte nur Text und die aufgeführten Platzhalter verwenden."
            )
        for node in output.nodes:
            if isinstance(node, nodes.TemplateData):
                continue
            name = _placeholder(node)
            if name not in allowed:
                label = name or "Ausdruck nicht erlaubt"
                raise TemplateValidationError(f"Unbekannter Platzhalter: {label}")


def _subject(subject: str) -> None:
    if not subject.strip():
        raise TemplateValidationError("Bitte einen Betreff angeben.")
    if any(ord(c) < 32 or ord(c) == 127 for c in subject):
        raise TemplateValidationError("Der Betreff muss eine Zeile ohne Steuerzeichen sein.")
    if len(subject) > 200:
        raise TemplateValidationError("Der Betreff darf höchstens 200 Zeichen haben.")


def render(subject: str, body: str, context: Mapping[str, Mapping[str, str]]) -> tuple[str, str]:
    """Render once, preserving whitespace; reject any non-string/context object access."""
    allow_safe = "safe" in context
    groups = PLACEHOLDERS | (SAFE_PLACEHOLDERS if allow_safe else {})
    if any(
        group not in groups
        or not isinstance(values, Mapping)
        or any(
            field not in groups[group] or type(value) is not str for field, value in values.items()
        )
        for group, values in context.items()
    ):
        raise TemplateValidationError("Die Vorlage darf nur vorformatierte Textwerte verwenden.")
    _subject(subject)
    if not body.strip():
        raise TemplateValidationError("Bitte einen Nachrichtentext angeben.")
    _check_source(subject, allow_safe=allow_safe)
    _check_source(body, allow_safe=allow_safe)
    # Copy to plain dicts, even when callers supply a Mapping implementation.
    values = {key: dict(value) for key, value in context.items()}
    try:
        rendered_subject = _ENV.from_string(subject).render(values)
        rendered_body = _ENV.from_string(body).render(values)
    except TemplateError:
        # Never include values from the context (especially a PIN) in errors.
        raise TemplateValidationError(
            "Unbekannter Platzhalter: Textwert fehlt im Kontext."
        ) from None
    _subject(rendered_subject)
    return rendered_subject, rendered_body


def validate_template(subject: str, body: str, *, allow_safe: bool = False) -> tuple[str, str]:
    """Validate/editor preview. Only the system spaetanreise editor opts into safe fields."""
    return render(subject, body, demo_context(allow_safe=allow_safe))
