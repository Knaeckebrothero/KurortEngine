"""The single validation/audit path used by forms, plugins and demo hooks."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select

from kurort_app import audit
from kurort_app.apps import values
from kurort_app.apps.models import AppRecord
from kurort_app.apps.schema import RangeSource
from kurort_app.auth import current_actor
from kurort_app.config import HOTEL_TZ
from kurort_app.models import Room


class RecordValidationError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("; ".join(errors.values()))


def records(session, app, collection=None, where=None):
    query = select(AppRecord).where(AppRecord.app_slug == app.slug, AppRecord.deleted_at.is_(None))
    if collection:
        query = query.where(AppRecord.collection == collection)
    rows = list(session.scalars(query).all())
    if where:
        rows = [r for r in rows if all(r.data.get(k) == v for k, v in where.items())]
    return rows


def record(session, app, collection, id):
    return session.scalar(
        select(AppRecord).where(
            AppRecord.id == id,
            AppRecord.app_slug == app.slug,
            AppRecord.collection == collection,
            AppRecord.deleted_at.is_(None),
        )
    )


def title(session, app, row, seen=None):
    if row is None:
        return "Eintrag nicht vorhanden"
    seen = set(seen or ())
    if row.id in seen:
        return f"Eintrag {row.id}"
    seen.add(row.id)
    collection = app.collection(row.collection)
    field = collection.field(collection.title_field)
    value = row.data.get(field.key)
    if field.type == "reference":
        target = record(session, app, field.collection, value)
        return title(session, app, target, seen)
    return values.display(field, value)


def display(session, app, field, value, *, unit=True):
    return values.display(
        field,
        value,
        unit=unit,
        reference_title=lambda id: title(session, app, record(session, app, field.collection, id)),
    )


def _limit(field, value):
    """A schema min/max (stored as float) in the field's own display form, e.g. "100,0 °C"."""
    return values.display(field, int(value) if field.type == "integer" else Decimal(str(value)))


def bounds(session, app, collection, field, data):
    """The (low, high) range of ``field`` for one record; a bound can come from a reference."""
    result = []
    for bound in (field.range.min, field.range.max):
        if isinstance(bound, RangeSource):
            first, second = bound.from_.split(".")
            target = record(session, app, collection.field(first).collection, data.get(first))
            bound = target.data.get(second) if target else None
        result.append(Decimal(str(bound)) if bound is not None else None)
    return result


def interval(field, low, high):
    """A range as people read it: "0,0 bis 7,0 °C", "ab 63,0 °C" or "bis 7,0 °C"."""

    def show(value):
        return values.display(field, value, unit=False)

    if low is not None and high is not None:
        text = f"{show(low)} bis {show(high)}"
    elif low is not None or high is not None:
        text = f"ab {show(low)}" if low is not None else f"bis {show(high)}"
    else:
        return ""
    return f"{text} {field.unit}" if field.unit else text


def ranges(session, app, row):
    """Each ranged field's allowed interval for ``row``, by field label (detail page)."""
    collection = app.collection(row.collection)
    result = {}
    for field in collection.fields:
        if field.range and (
            text := interval(field, *bounds(session, app, collection, field, row.data))
        ):
            result[field.label] = text
    return result


def validate(session, app, collection, raw):
    data, errors = {}, {}
    for field in collection.fields:
        value = raw.get(field.key)
        try:
            parsed = values.typed(field, value)
        except ValueError as exc:
            errors[field.key] = str(exc)
            continue
        if parsed is None:
            if field.required:
                errors[field.key] = f"{field.label} ist Pflicht."
            continue
        if field.required and parsed == "":
            errors[field.key] = f"{field.label} ist Pflicht."
        elif field.max_length and len(str(parsed)) > field.max_length:
            errors[field.key] = f"Bitte höchstens {field.max_length} Zeichen eingeben."
        elif field.type in {"integer", "decimal"}:
            if field.min is not None and parsed < Decimal(str(field.min)):
                errors[field.key] = f"Wert muss mindestens {_limit(field, field.min)} sein."
            if field.max is not None and parsed > Decimal(str(field.max)):
                errors[field.key] = f"Wert darf höchstens {_limit(field, field.max)} sein."
        elif field.type in {"select", "multiselect"}:
            chosen = parsed if isinstance(parsed, list) else [parsed]
            if any(v not in {o.key for o in field.options} for v in chosen):
                errors[field.key] = "Bitte eine gültige Auswahl treffen."
        elif field.type == "reference":
            if record(session, app, field.collection, parsed) is None:
                errors[field.key] = "Eintrag nicht vorhanden."
        elif field.type == "room":
            if session.scalar(select(Room.id).where(Room.number == parsed)) is None:
                errors[field.key] = "Zimmer nicht vorhanden."
        data[field.key] = values.serialize(field, value)
    if errors:
        raise RecordValidationError(errors)
    deviation = False
    for field in collection.fields:
        if not field.range or field.key not in data:
            continue
        low, high = bounds(session, app, collection, field, data)
        number = Decimal(str(data[field.key]))
        above = high is not None and number > high
        if not above and not (low is not None and number < low):
            continue
        deviation = True
        if field.range.severity == "block":
            errors[field.key] = (
                f"Wert außerhalb des zulässigen Bereichs ({interval(field, low, high)})."
            )
            continue
        missing = [k for k in field.require_when_out_of_range if data.get(k) in (None, "", [])]
        if missing:
            limit = "über der Obergrenze" if above else "unter der Untergrenze"
            todo = ", ".join(f"„{collection.field(k).label}“" for k in missing)
            errors[field.key] = (
                f"{values.display(field, number)} liegt {limit} "
                f"{values.display(field, high if above else low)} – bitte {todo} eintragen."
            )
        for key in missing:
            errors[key] = f"Bei einer Abweichung ist „{collection.field(key).label}“ Pflicht."
    if errors:
        raise RecordValidationError(errors)
    return data, deviation


def _event(session, app, row, action, before, actor):
    keys = before.keys() | row.data.keys()
    changes = {
        key: [before.get(key), row.data.get(key)]
        for key in sorted(keys)
        if before.get(key) != row.data.get(key)
    }
    verb = {"created": "angelegt", "updated": "geändert", "deleted": "gelöscht"}[action]
    collection = app.collection(row.collection)
    label = title(session, app, row)
    extra = " (Abweichung)" if row.out_of_range else ""
    audit.record(
        session,
        action=f"app_record.{action}",
        entity="app_record",
        entity_id=row.id,
        actor=actor,
        summary=f"{app.title} · {collection.item} {verb}: {label}{extra}",
        payload={"app": app.slug, "collection": row.collection, "changes": changes},
    )


def create(session, app, collection, data, *, actor=None, created_at=None):
    collection = app.collection(collection) if isinstance(collection, str) else collection
    parsed, deviation = validate(session, app, collection, data)
    actor = actor or current_actor.get() or audit.DEFAULT_ACTOR
    row = AppRecord(
        app_slug=app.slug,
        collection=collection.key,
        data=parsed,
        out_of_range=deviation,
        definition_version=app.version,
        created_by=actor,
    )
    if created_at:
        row.created_at = created_at
    session.add(row)
    session.flush()
    _event(session, app, row, "created", {}, actor)
    session.flush()
    return row


def update(session, app, row, data, *, actor=None):
    if row.app_slug != app.slug or row.deleted_at:
        raise ValueError("Eintrag nicht vorhanden")
    collection = app.collection(row.collection)
    parsed, deviation = validate(session, app, collection, data)
    before = dict(row.data)
    known = {f.key for f in collection.fields}
    row.data = {**{k: v for k, v in before.items() if k not in known}, **parsed}
    row.out_of_range = deviation
    row.updated_at, row.updated_by = (
        datetime.now(UTC),
        actor or current_actor.get() or audit.DEFAULT_ACTOR,
    )
    row.definition_version = app.version
    _event(session, app, row, "updated", before, row.updated_by)
    session.flush()
    return row


def delete(session, app, row, *, actor=None):
    row.deleted_at, row.deleted_by = (
        datetime.now(UTC),
        actor or current_actor.get() or audit.DEFAULT_ACTOR,
    )
    _event(session, app, row, "deleted", dict(row.data), row.deleted_by)
    session.flush()


def record_date(collection, row):
    value = (
        row.created_at
        if collection.date_field == "created_at"
        else row.data.get(collection.date_field)
    )
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value) if "T" in value else date.fromisoformat(value)
    return value.astimezone(HOTEL_TZ).date() if isinstance(value, datetime) else value


def search_text(session, app, collection, row, titles):
    """What a list row shows (German numbers, referenced titles) plus its stored values.

    ``titles`` caches reference titles across the rows of one search.
    """

    def reference_title(field):
        def lookup(id):
            if (field.collection, id) not in titles:
                target = record(session, app, field.collection, id)
                titles[field.collection, id] = title(session, app, target)
            return titles[field.collection, id]

        return lookup

    shown = [
        values.display(f, row.data.get(f.key), reference_title=reference_title(f))
        for f in collection.fields
    ]
    return " ".join([*shown, json.dumps(row.data, ensure_ascii=False)]).casefold()


def changes(session, app, payload):
    """An audit payload's changes as (label, before, after), formatted like the detail view."""
    collection = next((c for c in app.collections if c.key == payload.get("collection")), None)
    changed = payload.get("changes") or {}
    fields = {f.key: f for f in collection.fields} if collection else {}
    result = []
    for key in [k for k in fields if k in changed] + [k for k in changed if k not in fields]:
        before, after = changed[key]
        if key in fields:
            field = fields[key]
            result.append(
                (
                    field.label,
                    display(session, app, field, before),
                    display(session, app, field, after),
                )
            )
        else:
            result.append((key, *("–" if v in (None, "", []) else str(v) for v in (before, after))))
    return result


def query(
    session, app, collection, *, q="", von=None, bis=None, deviations=False, page=None, where=None
):
    collection = app.collection(collection) if isinstance(collection, str) else collection
    rows = records(session, app, collection.key, where)
    start = date.fromisoformat(von) if isinstance(von, str) and von else von
    end = date.fromisoformat(bis) if isinstance(bis, str) and bis else bis
    if start or end:
        rows = [
            r
            for r in rows
            if (day := record_date(collection, r))
            and (not start or day >= start)
            and (not end or day <= end)
        ]
    if q:
        needle, titles = q.strip().casefold(), {}
        rows = [r for r in rows if needle in search_text(session, app, collection, r, titles)]
    if deviations:
        rows = [r for r in rows if r.out_of_range]
    key = collection.order_by.removeprefix("-")

    def sort_value(row):
        if key == "created_at":
            return (False, row.created_at, row.id)
        raw = row.data.get(key)
        try:
            parsed = values.typed(collection.field(key), raw)
        except ValueError:
            parsed = None
        return (parsed is None, parsed if parsed is not None else "", row.id)

    rows.sort(key=sort_value, reverse=collection.order_by.startswith("-"))
    return rows[(max(1, page) - 1) * 50 : max(1, page) * 50] if page is not None else rows
