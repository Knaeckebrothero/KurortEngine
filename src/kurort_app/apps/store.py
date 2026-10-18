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
                errors[field.key] = f"Wert muss mindestens {str(field.min).replace('.', ',')} sein."
            if field.max is not None and parsed > Decimal(str(field.max)):
                errors[field.key] = f"Wert darf höchstens {str(field.max).replace('.', ',')} sein."
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
        bounds = []
        for bound in (field.range.min, field.range.max):
            if isinstance(bound, RangeSource):
                first, second = bound.from_.split(".")
                ref_field = collection.field(first)
                target = record(session, app, ref_field.collection, data.get(first))
                bound = target.data.get(second) if target else None
            bounds.append(Decimal(str(bound)) if bound is not None else None)
        number = Decimal(str(data[field.key]))
        low, high = bounds
        outside = (low is not None and number < low) or (high is not None and number > high)
        if not outside:
            continue
        deviation = True
        if field.range.severity == "block":

            def bound_label(value, field=field):
                return values.display(field, value, unit=False) if value is not None else "offen"

            interval = f"{bound_label(low)} bis {bound_label(high)}" + (
                f" {field.unit}" if field.unit else ""
            )
            errors[field.key] = f"Wert außerhalb des zulässigen Bereichs ({interval})."
        else:
            for key in field.require_when_out_of_range:
                if data.get(key) in (None, "", []):
                    errors[key] = (
                        f'Bei einer Abweichung ist „{collection.field(key).label}" Pflicht.'
                    )
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
        rows = [
            r for r in rows if q.casefold() in json.dumps(r.data, ensure_ascii=False).casefold()
        ]
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
