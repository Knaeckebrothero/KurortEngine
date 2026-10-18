"""Convert field values between forms, exact JSON storage and German display."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from kurort_app.config import HOTEL_TZ
from kurort_app.config import today as business_today


def typed(field, value):
    if value is None or value == "" or value == []:
        return None
    kind = field.type
    try:
        if kind in {"integer", "reference"}:
            if isinstance(value, bool) or str(value).strip() != str(int(value)):
                raise ValueError
            return int(value)
        if kind == "decimal":
            number = Decimal(str(value).replace(",", "."))
            if not number.is_finite():
                raise ValueError
            return number
        if kind == "date":
            return (
                value
                if isinstance(value, date) and not isinstance(value, datetime)
                else date.fromisoformat(str(value))
            )
        if kind == "datetime":
            result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
            if result.tzinfo is None:
                result = result.replace(tzinfo=HOTEL_TZ)
            return result.astimezone(UTC)
        if kind == "time":
            return value if isinstance(value, time) else time.fromisoformat(str(value))
        if kind == "boolean":
            if value in (True, "on", "true", "1", 1):
                return True
            if value in (False, "off", "false", "0", 0):
                return False
            raise ValueError
        if kind == "multiselect":
            return list(value) if isinstance(value, (list, tuple)) else [str(value)]
        return str(value).strip() or None
    except (ValueError, TypeError, InvalidOperation, OverflowError) as exc:
        messages = {
            "integer": "Bitte eine ganze Zahl eingeben.",
            "reference": "Eintrag nicht vorhanden.",
            "decimal": "Bitte eine gültige Zahl eingeben.",
            "date": "Bitte ein gültiges Datum eingeben.",
            "datetime": "Bitte einen gültigen Zeitpunkt eingeben.",
            "time": "Bitte eine gültige Uhrzeit eingeben.",
            "boolean": "Bitte ja oder nein auswählen.",
        }
        raise ValueError(messages.get(kind, "Bitte den Wert prüfen.")) from exc


def serialize(field, value):
    value = typed(field, value)
    if value is None:
        return None
    if field.type == "decimal":
        return str(value)
    if field.type in {"date", "datetime"}:
        return value.isoformat()
    if field.type == "time":
        return value.strftime("%H:%M")
    return value


def form_value(field, value):
    try:
        parsed = typed(field, value)
    except ValueError:
        return value
    if parsed is None:
        return ""
    if field.type == "datetime":
        return parsed.astimezone(HOTEL_TZ).strftime("%Y-%m-%dT%H:%M")
    if field.type == "decimal":
        return str(parsed).replace(".", ",")
    return serialize(field, value)


def defaults(collection, username="rezeption", *, today=None, now=None):
    today = today or business_today()
    now = (now or datetime.now(UTC)).astimezone(HOTEL_TZ)
    result = {}
    for field in collection.fields:
        value = field.default
        if value == "today":
            value = today.isoformat()
        elif isinstance(value, str) and value.startswith("today+"):
            value = (today + timedelta(days=int(value[6:]))).isoformat()
        elif value == "now":
            value = datetime.combine(today, now.timetz()).isoformat()
        elif value == "current_user" or (value is None and field.type == "staff"):
            value = username
        if value is not None:
            result[field.key] = form_value(field, value)
    return result


def display(field, value, *, reference_title=None, unit=True):
    try:
        parsed = typed(field, value)
    except ValueError:
        return str(value)
    if parsed is None:
        return "–"
    if field.type == "date":
        result = parsed.strftime("%d.%m.%Y")
    elif field.type == "datetime":
        result = parsed.astimezone(HOTEL_TZ).strftime("%d.%m.%Y %H:%M")
    elif field.type == "time":
        result = parsed.strftime("%H:%M")
    elif field.type == "boolean":
        result = "ja" if parsed else "nein"
    elif field.type == "decimal":
        result = (
            f"{parsed:.{field.decimals}f}" if field.decimals is not None else str(parsed)
        ).replace(".", ",")
    elif field.type in {"select", "multiselect"}:
        labels = {o.key: o.label for o in field.options}
        result = (
            ", ".join(labels.get(v, v) for v in parsed)
            if isinstance(parsed, list)
            else labels.get(parsed, parsed)
        )
    elif field.type == "reference" and reference_title:
        result = reference_title(parsed)
    else:
        result = str(parsed)
    return f"{result} {field.unit}" if unit and field.unit else result
