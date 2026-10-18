"""Stock counts and rule-based breakfast orders on the shared app store."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_CEILING, Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from kurort_app.apps import store
from kurort_app.config import HOTEL_TZ
from kurort_app.models import Reservation


@dataclass(frozen=True)
class Suggestion:
    stock: Decimal
    amount: Decimal | None
    flags: tuple[str, ...]


def number(value):
    return Decimal(str(value)) if value is not None and value != "" else None


def suggest(article, breakfasts, stock=None):
    flags = []
    if stock is None:
        stock = Decimal(0)
        flags.append("Bestand unbekannt")
    minimum = number(article.get("mindestbestand"))
    rate = number(article.get("pro_fruehstueck"))
    target = number(article.get("zielbestand"))
    if minimum is not None and stock < minimum:
        flags.append("unter Mindestbestand")
    if rate is not None:
        need = rate * breakfasts + (minimum or Decimal(0))
    else:
        need = target if target is not None else minimum
    if need is None:
        flags.append("Kein Zielbestand")
        amount = None
    else:
        pack = number(article.get("packungsgroesse")) or Decimal(1)
        amount = max(
            Decimal(0), ((need - stock) / pack).to_integral_value(rounding=ROUND_CEILING) * pack
        )
    return Suggestion(stock, amount, tuple(flags))


def expected_breakfasts(reservations, start, end):
    """Guests who slept in the hotel the night before each breakfast."""
    total = 0
    for reservation in reservations:
        if reservation.status in {"cancelled", "no_show"}:
            continue
        first = max(start, reservation.arrival + timedelta(days=1))
        stop = min(end, reservation.departure + timedelta(days=1))
        total += max(0, (stop - first).days) * len(reservation.guests)
    return total


def reservations_for(session, start, end):
    return session.scalars(
        select(Reservation)
        .options(selectinload(Reservation.guests))
        .where(
            Reservation.arrival < end,
            Reservation.departure >= start,
            Reservation.status.not_in(("cancelled", "no_show")),
        )
    ).all()


def latest_counts(counts):
    latest = {}
    for record in counts:
        key = record.data["artikel"]
        at = datetime.fromisoformat(record.data["gezaehlt_am"])
        previous = latest.get(key)
        if previous is None or (at, record.id) > (
            datetime.fromisoformat(previous.data["gezaehlt_am"]),
            previous.id,
        ):
            latest[key] = record
    return latest


def order_history(ctx, supplier, articles):
    prices = {a.id: number(a.data.get("preis")) for a in articles}
    orders = sorted(
        ctx.records("bestellungen", {"lieferant": supplier.id}),
        key=lambda r: (r.data["bestellt_am"], r.id),
        reverse=True,
    )[:5]
    all_lines = ctx.records("positionen")
    result = []
    for order in orders:
        lines = [line for line in all_lines if line.data["bestellung"] == order.id]
        entry = {
            "order": order,
            "date": date.fromisoformat(order.data["bestellt_am"]),
            "differences": sum(
                number(line.data.get("vorschlag")) != number(line.data["bestellt"])
                for line in lines
            ),
        }
        for key in ("vorschlag", "bestellt"):
            entry[key] = sum(
                (
                    (number(line.data.get(key)) or Decimal(0)) * prices[line.data["artikel"]]
                    for line in lines
                    if prices.get(line.data["artikel"]) is not None
                ),
                Decimal(0),
            )
        result.append(entry)
    return result


async def bestellvorschlag(ctx):
    from fastapi import HTTPException

    from kurort_app import web
    from kurort_app.apps import values
    from kurort_app.config import today

    posted = ctx.request.method == "POST"
    raw = dict(await ctx.request.form()) if posted else dict(ctx.request.query_params)
    action = raw.get("aktion", "berechnen")
    if posted and action not in {"berechnen", "speichern"}:
        raise HTTPException(422, "Bitte eine gültige Aktion wählen.")
    if posted and action == "speichern":
        ctx._require("bestellungen", "edit")
    articles = ctx.records("artikel")
    active = [a for a in articles if a.data.get("aktiv") is True]
    suppliers = sorted(ctx.records("lieferanten"), key=lambda r: r.data["name"])
    default = next((s for s in suppliers if any(a.data["lieferant"] == s.id for a in active)), None)
    supplier = (
        next((s for s in suppliers if str(s.id) == raw.get("lieferant")), None)
        if raw.get("lieferant")
        else default
    )
    errors = {}
    if supplier is None and raw.get("lieferant"):
        errors["lieferant"] = "Bitte einen gültigen Lieferanten wählen."
    delivery = today() + timedelta(days=1)
    next_delivery = delivery + timedelta(days=3)
    for key in ("lieferung_am", "naechste_lieferung"):
        try:
            fallback = delivery if key == "lieferung_am" else delivery + timedelta(days=3)
            parsed = date.fromisoformat(raw[key]) if key in raw else fallback
            if key == "lieferung_am":
                delivery = parsed
            else:
                next_delivery = parsed
        except ValueError:
            errors[key] = "Bitte ein gültiges Datum eingeben."
    if next_delivery <= delivery:
        errors["naechste_lieferung"] = "Die nächste Lieferung muss nach der Lieferung liegen."
    raw.setdefault("lieferung_am", delivery.isoformat())
    raw.setdefault("naechste_lieferung", next_delivery.isoformat())
    breakfasts = expected_breakfasts(
        reservations_for(ctx.session, delivery, next_delivery), delivery, next_delivery
    )
    latest = latest_counts(ctx.records("bestaende"))
    choices = ctx.definition.collection("positionen").field("grund").options
    selected = sorted(
        (a for a in active if supplier and a.data["lieferant"] == supplier.id),
        key=lambda r: (r.data["kategorie"], r.data["name"]),
    )
    rows = []
    for article in selected:
        id = article.id
        count_raw = raw.get(f"bestand_{id}", "")
        ordered_raw = raw.get(f"bestellt_{id}", "")
        reason = raw.get(f"grund_{id}", "")
        parsed = {}
        for key, value in (("bestand", count_raw), ("bestellt", ordered_raw)):
            try:
                parsed[key] = values.typed(
                    ctx.definition.collection("positionen").field(key), value.strip()
                )
                if parsed[key] is not None and parsed[key] < 0:
                    errors[f"{key}_{id}"] = "Bitte mindestens 0 eingeben."
            except ValueError as exc:
                errors[f"{key}_{id}"] = str(exc)
                parsed[key] = None
        if reason and reason not in {o.key for o in choices}:
            errors[f"grund_{id}"] = "Bitte einen gültigen Grund wählen."
        last = latest.get(id)
        stock = (
            parsed["bestand"]
            if parsed["bestand"] is not None
            else number(last.data["menge"])
            if last
            else None
        )
        suggestion = suggest(article.data, breakfasts, stock)
        ordered = parsed["bestellt"] if ordered_raw.strip() else suggestion.amount or Decimal(0)
        rows.append(
            {
                "article": article,
                "latest": last,
                "latest_at": datetime.fromisoformat(last.data["gezaehlt_am"]) if last else None,
                "suggestion": suggestion,
                "count_raw": count_raw,
                "ordered_raw": ordered_raw,
                "ordered": ordered,
                "reason": reason,
            }
        )
    if posted and action == "berechnen" and not errors:
        for row in rows:
            row["ordered"] = row["suggestion"].amount or Decimal(0)
    if not errors:
        for row in rows:
            row["ordered_raw"] = str(row["ordered"]).replace(".", ",")
    total = sum(
        (
            (row["ordered"] or Decimal(0)) * number(row["article"].data["preis"])
            for row in rows
            if number(row["article"].data.get("preis")) is not None
        ),
        Decimal(0),
    )
    missing_prices = [
        row["article"].data["name"]
        for row in rows
        if number(row["article"].data.get("preis")) is None
    ]
    if posted and action == "speichern" and not errors and supplier:
        actor = ctx.user.username if ctx.user else "rezeption"
        at = datetime.combine(today(), datetime.now(HOTEL_TZ).timetz()).astimezone(UTC)
        with ctx.session.begin_nested():
            for row in rows:
                if row["count_raw"].strip():
                    ctx.create(
                        "bestaende",
                        {
                            "artikel": row["article"].id,
                            "gezaehlt_am": at,
                            "menge": row["count_raw"].strip(),
                            "mitarbeiter": actor,
                        },
                    )
            order = ctx.create(
                "bestellungen",
                {
                    "lieferant": supplier.id,
                    "bestellt_am": today(),
                    "lieferung_am": delivery,
                    "naechste_lieferung": next_delivery,
                    "fruehstuecke": breakfasts,
                    "status": "bestellt",
                    "mitarbeiter": actor,
                },
            )
            lines = 0
            for row in rows:
                suggestion = row["suggestion"]
                if (suggestion.amount or 0) > 0 or row["ordered"] > 0:
                    ctx.create(
                        "positionen",
                        {
                            "bestellung": order.id,
                            "artikel": row["article"].id,
                            "bestand": suggestion.stock,
                            "vorschlag": suggestion.amount,
                            "bestellt": row["ordered"],
                            "grund": row["reason"],
                        },
                        parent=order,
                    )
                    lines += 1
        ctx.session.commit()
        notice = f"Bestellung bei {supplier.data['name']} gespeichert – {lines} Positionen, ca. {web.fmt_money(total)}."
        return web.redirect_with_notice(f"/apps/inventur/bestellungen/{order.id}", notice)
    response = ctx.render(
        "inventur/bestellvorschlag.html",
        raw=raw,
        errors=errors,
        supplier=supplier,
        suppliers=suppliers,
        rows=rows,
        breakfasts=breakfasts,
        delivery=delivery,
        next_delivery=next_delivery,
        last_breakfast=next_delivery - timedelta(days=1),
        total=total,
        missing_prices=missing_prices,
        history=order_history(ctx, supplier, articles) if supplier else [],
        reasons=choices,
        display=lambda field, value: values.display(
            ctx.definition.collection("artikel").field(field), value
        ),
        decimal=lambda value: str(value).replace(".", ",") if value is not None else "–",
    )
    response.status_code = 422 if errors else 200
    return response


# name, unit, supplier index, minimum, target, pack, breakfast rate, net price
ARTICLES = (
    ("Eier", "stueck", 0, "60", None, "30", "1.0", "0.28"),
    ("Gouda in Scheiben", "kg", 0, "1", None, "0.5", "0.03", "9.90"),
    ("Kochschinken in Scheiben", "kg", 0, "0.5", None, "0.5", "0.02", "14.50"),
    ("Salami in Scheiben", "kg", 0, "0.5", None, "0.5", "0.015", "16.90"),
    ("Konfitüre Portionen", "portion", 0, "100", "300", "100", None, "0.12"),
    ("Honig Portionen", "portion", 0, "50", "200", "100", None, "0.14"),
    ("Nuss-Nougat-Creme Portionen", "portion", 0, "50", "200", "120", None, "0.18"),
    ("Müsli", "kg", 0, "2", None, "1", "0.03", "5.40"),
    ("Cornflakes", "kg", 0, "1", "3", "0.75", None, "4.20"),
    ("Orangensaft", "l", 0, "6", None, "6", "0.15", "1.60"),
    ("Apfelsaft", "l", 0, "6", None, "6", "0.08", "1.20"),
    ("Kaffeebohnen", "kg", 0, "2", "8", "1", None, "14.80"),
    ("Tee sortiert (100 Beutel)", "packung", 0, "1", "4", "1", None, "6.50"),
    ("Mineralwasser (12 × 0,75 l)", "kiste", 0, "3", "10", "1", None, "5.90"),
    ("Vollmilch", "l", 2, "6", None, "6", "0.12", "1.15"),
    ("Butter Portionen", "portion", 2, "100", None, "100", "1.5", "0.09"),
    ("Naturjoghurt 500 g", "stueck", 2, "4", None, "6", "0.05", "0.89"),
    ("Fruchtjoghurt", "stueck", 2, "12", None, "12", "0.25", "0.45"),
    ("Sahne 200 ml", "stueck", 2, "5", "10", "10", None, "0.99"),
    ("Brötchen", "stueck", 1, "0", None, "10", "1.8", "0.38"),
    ("Croissants", "stueck", 1, "0", None, "10", "0.4", "0.65"),
    ("Vollkornbrot", "stueck", 1, "0", None, "1", "0.06", "3.90"),
    ("Äpfel", "kg", 3, "1", None, "1", "0.06", "2.40"),
    ("Bananen", "kg", 3, "1", None, "1", "0.05", "1.80"),
    ("Tomaten", "kg", 3, "0.5", None, "1", "0.04", "3.20"),
    ("Gurken", "stueck", 3, "2", None, "1", "0.05", "0.79"),
)


def seed_demo(session, anchor):
    from kurort_app.apps.registry import AppRegistry

    app = AppRegistry().valid["inventur"]
    rng = random.Random(20261014 + 8)
    suppliers = []
    for name, method, days in (
        ("Großmarkt Main-Kinzig", "telefon", "Mo und Do"),
        ("Bäckerei am Kurpark", "telefon", "täglich"),
        ("Hofmolkerei Spessart", "email", "Di und Fr"),
        ("Obst & Gemüse Gelnhausen", "telefon", "Mo und Do"),
    ):
        suppliers.append(
            store.create(
                session,
                app,
                "lieferanten",
                {
                    "name": name,
                    "bestellweg": method,
                    "liefertage": days,
                    "notiz": "Fiktiver Demo-Lieferant",
                },
                actor="j.becker",
            )
        )
    articles = []
    for name, unit, supplier, minimum, target, pack, rate, price in ARTICLES:
        category = (
            "getraenke"
            if name
            in {
                "Orangensaft",
                "Apfelsaft",
                "Kaffeebohnen",
                "Tee sortiert (100 Beutel)",
                "Mineralwasser (12 × 0,75 l)",
            }
            else "kueche"
            if name == "Sahne 200 ml"
            else "fruehstueck"
        )
        articles.append(
            store.create(
                session,
                app,
                "artikel",
                {
                    "name": name,
                    "einheit": unit,
                    "lieferant": suppliers[supplier].id,
                    "kategorie": category,
                    "mindestbestand": minimum,
                    "zielbestand": target,
                    "packungsgroesse": pack,
                    "pro_fruehstueck": rate,
                    "preis": price,
                    "aktiv": True,
                    "lagerort": "Trockenlager"
                    if category == "getraenke" or unit in {"portion", "packung"}
                    else "Kühlraum",
                },
                actor="j.becker",
            )
        )
    reservations = reservations_for(
        session, anchor - timedelta(days=28), anchor + timedelta(days=4)
    )
    for offset in range(-28, 0):
        day = anchor + timedelta(days=offset)
        at = datetime.combine(day, time(7), HOTEL_TZ).astimezone(UTC)
        for index, supplier in enumerate(suppliers):
            weekdays = {0, 3} if index in {0, 3} else {1, 4} if index == 2 else set(range(7))
            if day.weekday() not in weekdays:
                continue
            delivery = day + timedelta(days=1)
            next_day = day + timedelta(days=1)
            while next_day.weekday() not in weekdays:
                next_day += timedelta(days=1)
            next_delivery = next_day + timedelta(days=1)
            breakfasts = expected_breakfasts(reservations, delivery, next_delivery)
            order = store.create(
                session,
                app,
                "bestellungen",
                {
                    "lieferant": supplier.id,
                    "bestellt_am": day,
                    "lieferung_am": delivery,
                    "naechste_lieferung": next_delivery,
                    "fruehstuecke": breakfasts,
                    "status": "geliefert",
                    "mitarbeiter": "j.becker",
                },
                actor="j.becker",
                created_at=at,
            )
            for article in (a for a in articles if a.data["lieferant"] == supplier.id):
                data = article.data
                stock = (
                    Decimal(rng.randrange(20, 90))
                    / 100
                    * (
                        number(data.get("zielbestand"))
                        or number(data.get("mindestbestand"))
                        or Decimal(10)
                    )
                ).quantize(Decimal("0.01"))
                store.create(
                    session,
                    app,
                    "bestaende",
                    {
                        "artikel": article.id,
                        "gezaehlt_am": at,
                        "menge": stock,
                        "mitarbeiter": "j.becker",
                    },
                    actor="j.becker",
                    created_at=at,
                )
                suggestion = suggest(data, breakfasts, stock).amount or Decimal(0)
                ordered, reason = suggestion, None
                if rng.randrange(5) == 0:
                    if rng.randrange(4):
                        ordered, reason = (
                            max(Decimal(0), suggestion - number(data["packungsgroesse"])),
                            "genug_da",
                        )
                    else:
                        ordered, reason = suggestion + number(data["packungsgroesse"]), "gruppe"
                store.create(
                    session,
                    app,
                    "positionen",
                    {
                        "bestellung": order.id,
                        "artikel": article.id,
                        "bestand": stock,
                        "vorschlag": suggestion,
                        "bestellt": ordered,
                        "grund": reason,
                    },
                    actor="j.becker",
                    created_at=at,
                )
    # A Monday/Thursday supplier can otherwise have its last count four days ago.
    for article in articles:
        at = datetime.combine(anchor - timedelta(days=1), time(16), HOTEL_TZ)
        minimum = number(article.data.get("mindestbestand")) or Decimal(1)
        store.create(
            session,
            app,
            "bestaende",
            {
                "artikel": article.id,
                "gezaehlt_am": at,
                "menge": (minimum * Decimal("0.8")).quantize(Decimal("0.01")),
                "mitarbeiter": "m.schmidt",
            },
            actor="m.schmidt",
            created_at=at,
        )
