"""Clock-injected schedule, deadline and recent-deviation calculations."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from urllib.parse import urlencode

from kurort_app.config import HOTEL_TZ


@dataclass(frozen=True)
class StatusItem:
    title: str
    record: object
    status: str
    href: str
    note: str = ""


def _timestamp(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value) if "T" in value else date.fromisoformat(value)
    if isinstance(value, datetime):
        return value.replace(tzinfo=HOTEL_TZ) if value.tzinfo is None else value
    return datetime.combine(value, time(), HOTEL_TZ)


def schedules(app, records, *, today, now):
    rows = [r for r in records if not r.deleted_at]
    result = []
    for rule in app.schedules:
        for target in rows:
            if target.collection != rule.target or (rule.when and not target.data.get(rule.when)):
                continue
            readings = [
                r for r in rows if r.collection == rule.record and r.data.get(rule.via) == target.id
            ]
            dates = [
                r.created_at if rule.at_field == "created_at" else r.data.get(rule.at_field)
                for r in readings
            ]
            dates = [_timestamp(v) for v in dates if v]
            latest = max(dates) if dates else None
            note = ""
            if latest is None:
                state, note = "überfällig", "noch nie erfasst"
            elif rule.every_hours:
                state = (
                    "überfällig" if now > latest + timedelta(hours=rule.every_hours) else "erledigt"
                )
            else:
                interval = (
                    rule.every_days
                    if rule.every_days is not None
                    else target.data.get(rule.every_days_field)
                )
                if not isinstance(interval, int) or interval <= 0:
                    continue
                due = latest.astimezone(HOTEL_TZ).date() + timedelta(days=interval)
                state = "erledigt" if today < due else ("fällig" if today == due else "überfällig")
                note = f"fällig {'seit' if today > due else 'am'} {due:%d.%m.%Y}"
            href = f"/apps/{app.slug}/{rule.record}/neu?{urlencode({rule.via: target.id})}"
            result.append(StatusItem(rule.title, target, state, href, note))
    return result


def alerts(app, records, *, today):
    result = []
    for rule in app.alerts:
        # "Verbrauchen bis 21.10.2026": the date field's label, unless the rule shifts it
        label = (
            app.collection(rule.collection).field(rule.field).label
            if not rule.offset_days
            else "Frist"
        )
        for record in records:
            if (
                record.deleted_at
                or record.collection != rule.collection
                or (rule.unless and record.data.get(rule.unless))
            ):
                continue
            value = record.data.get(rule.field)
            if not value:
                continue
            try:
                deadline = _timestamp(value).astimezone(HOTEL_TZ).date() + timedelta(
                    days=rule.offset_days
                )
            except (ValueError, TypeError):
                continue
            state = (
                "abgelaufen"
                if today > deadline
                else ("läuft ab" if today >= deadline - timedelta(days=rule.warn_days) else None)
            )
            if state:
                result.append(
                    StatusItem(
                        rule.title,
                        record,
                        state,
                        f"/apps/{app.slug}/{record.collection}/{record.id}",
                        f"{label} {deadline:%d.%m.%Y}",
                    )
                )
    return result


def deviations(records, *, today):
    return [
        r
        for r in records
        if not r.deleted_at
        and r.out_of_range
        and today - timedelta(days=6)
        <= (r.updated_at or r.created_at).astimezone(HOTEL_TZ).date()
        <= today
    ]


def business_now(today):
    return datetime.combine(today, datetime.now(UTC).astimezone(HOTEL_TZ).timetz())
