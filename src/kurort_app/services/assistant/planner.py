"""Demo planner: German phrases → action plans, using the real database.

A deliberately small rule set standing in for the LLM that will later produce
the same plans via tool calling (see ``schema``). Rules run in a fixed order;
the first that recognises the request builds the plan. Nothing here writes
to the database.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlencode

from sqlalchemy import case, or_, select
from sqlalchemy.orm import Session, selectinload

from kurort_app.config import today as business_today
from kurort_app.models import CHECKED_IN, RESERVED, Guest, Reservation, ReservationGuest, Room
from kurort_app.seed import FIRST_NAMES_F, FIRST_NAMES_M
from kurort_app.services.assistant import parsing as p
from kurort_app.services.assistant import schema as s
from kurort_app.services.availability import blocking_reservations, free_rooms
from kurort_app.web import STATUS_LABELS, fmt_date, fmt_money, fmt_time

Plan = dict[str, Any]
Rule = Callable[[Session, str, str, date], Plan | None]

DASHBOARD_WIDGET_WORDS = {
    "metrics": r"\b(kennzahlen|zahlen|metriken|kpis?)\b",
    "today": r"\b(heute|tabelle|anreisen?|abreisen?|ankuenfte)\b",
    "occupancy": r"\b(belegung|auslastung|diagramm|chart)\b",
}
WIDGET_LABELS = {
    "metrics": "Kennzahlen",
    "today": "Heute",
    "occupancy": "Belegung",
}
NOT_YET = "Das kann ich noch nicht."


def _span(start: date, end: date) -> str:
    """``Sa 17.10.–Mo 19.10.``"""
    return f"{fmt_date(start, 'day')}–{fmt_date(end, 'day')}"


def _short_span(start: date, end: date) -> str:
    return f"{start:%d.%m.}–{end:%d.%m.}"


def _with_guests(stmt):
    return stmt.options(
        selectinload(Reservation.guests).selectinload(ReservationGuest.guest),
        selectinload(Reservation.room),
    )


def _salutation(guest: Guest) -> str:
    if guest.first_name in FIRST_NAMES_F:
        return f"Frau {guest.last_name}"
    if guest.first_name in FIRST_NAMES_M:
        return f"Herrn {guest.last_name}"
    return guest.full_name


def _best_name_matches(folded: str, reservations: list[Reservation]) -> list[Reservation]:
    """Reservations naming a guest in the text; a first-name match beats last-name only."""
    scored: list[tuple[int, Reservation]] = []
    for res in reservations:
        score = max(
            (p.name_score(folded, rg.guest.first_name, rg.guest.last_name) for rg in res.guests),
            default=0,
        )
        if score:
            scored.append((score, res))
    if not scored:
        return []
    best = max(score for score, _ in scored)
    return [res for score, res in scored if score == best]


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


def _walk_in(session: Session, text: str, folded: str, day: date) -> Plan | None:
    if not p.has_any(folded, r"\bwalk[- ]?in\b", r"\bohne reservierung\b", r"\bspontan"):
        return None
    return walk_in_plan(
        session,
        day,
        nights=p.parse_nights(folded),
        category=p.parse_category(folded),
        name=p.extract_new_guest_name(text),
    )


def walk_in_plan(
    session: Session,
    day: date,
    *,
    nights: int | None = None,
    category: str | None = None,
    name: tuple[str | None, str | None] | None = None,
) -> Plan:
    """Walk-in form for a guest arriving today, prefilled with the first fitting free room."""
    nights = max(1, min(nights or 1, 28))
    departure = day + timedelta(days=nights)
    free = free_rooms(session, day, departure)
    candidates = [r for r in free if category is None or r.category == category]
    if not candidates:
        offered = sorted({r.category for r in free})
        wanted = f"{'Keine' if category == 'Suite' else 'Kein'} {category or 'Zimmer'}"
        message = f"{wanted} frei · {_span(day, departure)}"
        message += (
            f"\nFrei sind noch: {', '.join(offered)}"
            if offered
            else "\nKein Zimmer ist für den ganzen Zeitraum frei – kürzer buchen oder Zimmerplan prüfen."
        )
        return s.plan("walk_in", "Walk-in anlegen", message=message)

    room = candidates[0]
    query = {"walkin": "1", "abreise": departure.isoformat(), "zimmer": room.number}
    steps = [s.navigate("Walk-in-Formular öffnen", f"/reservierungen/neu?{urlencode(query)}")]
    if name:
        first, last = name
        fields = {key: value for key, value in (("vorname", first), ("nachname", last)) if value}
        steps.append(s.fill(f"Gast eintragen: {' '.join(fields.values())}", fields))
    steps.append(s.confirm("Bitte Gastdaten ergänzen, prüfen und speichern"))
    nights_label = "1 Nacht" if nights == 1 else f"{nights} Nächte"
    message = (
        f"Zimmer {room.number} · {room.category} · {_short_span(day, departure)} "
        f"({nights_label}) · {fmt_money(room.nightly_rate * nights)}"
    )
    return s.plan("walk_in", "Walk-in anlegen", message=message, steps=steps)


def _check_in(session: Session, text: str, folded: str, day: date) -> Plan | None:
    if not p.has_any(folded, r"\bcheck[- ]?in\b", r"\beinchecken\b", r"\beingecheckt\b"):
        return None
    return check_in_plan(session, day, folded, mentioned=_mentioned_name(text))


def check_in_plan(
    session: Session, day: date, folded: str, *, mentioned: str | None = None
) -> Plan:
    """Check-in of today's arrival named in ``folded`` (folded text, may be the whole request).

    ``mentioned`` is the name as said, for the reply when nobody matches.
    """
    arrivals = list(
        session.scalars(
            _with_guests(
                select(Reservation).where(
                    Reservation.arrival == day, Reservation.status == RESERVED
                )
            ).order_by(Reservation.eta.nulls_last(), Reservation.id)
        )
    )
    matches = _best_name_matches(folded, arrivals)
    if len(matches) == 1:
        res = matches[0]
        guest = res.primary_guest
        room = f" · Zimmer {res.room.number}" if res.room else ""
        return s.plan(
            "check_in",
            "Check-in starten",
            message=f"{guest.full_name if guest else res.code} · {res.code}{room}",
            steps=[
                s.navigate(
                    f"Check-in für {guest.full_name if guest else res.code} öffnen",
                    f"/check-in/{res.id}",
                )
            ],
        )
    if len(matches) > 1:
        lines = [
            f"{r.primary_guest.full_name} · {r.code} · Zimmer {r.room.number if r.room else '–'}"
            for r in matches
        ]
        steps = [s.navigate("Anreisen öffnen", "/anreisen?filter=offen")]
        steps += [
            s.highlight(f"{r.primary_guest.full_name} markieren", "reservation-row", r.id)
            for r in matches
        ]
        return s.plan(
            "check_in",
            "Check-in starten",
            message="Mehrere Anreisen passen – bitte wählen:\n" + "\n".join(lines),
            steps=steps,
        )
    if mentioned:
        return s.plan(
            "check_in",
            "Check-in starten",
            message=f"Keine offene Anreise heute für {mentioned}.",
            steps=[
                s.navigate(
                    f"Nach „{mentioned}“ suchen", f"/reservierungen?{urlencode({'q': mentioned})}"
                )
            ],
        )
    lines = [
        f"{r.primary_guest.full_name} · Zimmer {r.room.number if r.room else '–'}" for r in arrivals
    ]
    message = (
        "Für wen? Offene Anreisen heute:\n" + "\n".join(lines)
        if lines
        else "Heute sind keine Anreisen mehr offen."
    )
    return s.plan(
        "check_in", "Check-in starten", message=message,
        steps=[s.navigate("Anreisen öffnen", "/anreisen?filter=offen")],
    )  # fmt: skip


def _mentioned_name(text: str) -> str | None:
    name = p.extract_new_guest_name(text)
    if name is None:
        return None
    return " ".join(part for part in name if part)


def _move_arrival(session: Session, text: str, folded: str, day: date) -> Plan | None:
    if not (
        p.has_any(folded, r"\bverschieb", r"\bverleg", r"\baender", r"\bumbuch")
        and p.has_any(folded, r"\banreise\b", r"\bankunft\b")
    ):
        return None
    return move_arrival_plan(
        session,
        day,
        folded,
        mentioned=_mentioned_name(text),
        target=p.parse_target_date(folded, day),
    )


def move_arrival_plan(
    session: Session,
    day: date,
    folded: str,
    *,
    mentioned: str | None = None,
    target: date | None = None,
) -> Plan:
    """Move the nearest upcoming arrival of the guest named in ``folded`` to ``target``."""
    title = "Anreise verschieben"
    upcoming = list(
        session.scalars(
            _with_guests(
                select(Reservation).where(
                    Reservation.arrival >= day, Reservation.status == RESERVED
                )
            ).order_by(Reservation.arrival, Reservation.id)
        )
    )
    matches = _best_name_matches(folded, upcoming)
    if not matches:
        who = f" für {mentioned}" if mentioned else ""
        return s.plan("move_arrival", title, message=f"Keine kommende Reservierung{who} gefunden.")
    people = {(r.primary_guest.first_name, r.primary_guest.last_name) for r in matches}
    if len(people) > 1:
        lines = [
            f"{r.primary_guest.full_name} · {r.code} · Anreise {fmt_date(r.arrival, 'day')}"
            for r in matches
        ]
        return s.plan(
            "move_arrival",
            title,
            message="Mehrere Gäste passen – bitte mit Vornamen sagen:\n" + "\n".join(lines),
        )
    res = matches[0]  # nearest arrival of that guest
    if target is None:
        return s.plan(
            "move_arrival", title, message="Auf welchen Tag soll die Anreise verschoben werden?"
        )
    if target < day:
        return s.plan(
            "move_arrival", title, message=f"{fmt_date(target, 'day')} liegt in der Vergangenheit."
        )
    nights = res.nights
    new_departure = target + timedelta(days=nights)
    old = _span(res.arrival, res.departure)
    new = _span(target, new_departure)
    guest = res.primary_guest.full_name
    if target == res.arrival:
        return s.plan(
            "move_arrival", title, message=f"{guest} reist bereits am {fmt_date(target, 'day')} an."
        )
    lines = [
        f"{guest} · {res.code}",
        f"Bisher {old} → neu {new} ({nights} {'Nacht' if nights == 1 else 'Nächte'})",
    ]
    if res.room:
        clash = session.scalars(
            blocking_reservations(target, new_departure, exclude_reservation_id=res.id).where(
                Reservation.room_id == res.room_id
            )
        ).first()
        lines.append(
            f"Zimmer {res.room.number} ist dann frei."
            if clash is None
            else f"Zimmer {res.room.number} ist dann belegt ({clash.code}) – bitte anderes Zimmer wählen."
        )
    steps = [
        s.navigate(f"Reservierung {res.code} bearbeiten", f"/reservierungen/{res.id}/bearbeiten"),
        s.fill(
            f"Neue Daten eintragen: {new}",
            {"anreise": target.isoformat(), "abreise": new_departure.isoformat()},
        ),
        s.confirm("Bitte prüfen und speichern"),
    ]
    return s.plan("move_arrival", title, message="\n".join(lines), steps=steps)


def _room_availability(session: Session, text: str, folded: str, day: date) -> Plan | None:
    number = p.parse_room_number(folded)
    if number is None or not p.has_any(
        folded, r"\bfrei\b", r"\bbelegt\b", r"\bverfuegbar", r"\bbesetzt\b"
    ):
        return None
    start, end = p.parse_span(folded, day) or (None, None)
    return room_availability_plan(session, day, number, start=start, end=end)


def room_availability_plan(
    session: Session,
    day: date,
    number: str,
    *,
    start: date | None = None,
    end: date | None = None,
) -> Plan:
    """Is room ``number`` free from ``start`` until the departure morning ``end``? Default: tonight."""
    title = f"Zimmer {number} prüfen"
    room = session.scalar(select(Room).where(Room.number == number))
    if room is None:
        return s.plan("room_availability", title, message=f"Zimmer {number} gibt es nicht.")
    start = start or day
    if end is None or end <= start:
        end = start + timedelta(days=1)
    blockers = list(
        session.scalars(
            _with_guests(
                blocking_reservations(start, end).where(Reservation.room_id == room.id)
            ).order_by(Reservation.arrival)
        )
    )
    if blockers:
        stays = "; ".join(
            f"{b.primary_guest.last_name if b.primary_guest else '–'} ({b.code}) {_short_span(b.arrival, b.departure)}"
            for b in blockers
        )
        message = f"Zimmer {number} ist {_span(start, end)} belegt: {stays}"
    else:
        message = f"Zimmer {number} ist {_span(start, end)} frei."
    steps = [
        s.navigate(
            "Zimmerplan öffnen",
            f"/zimmerplan?{urlencode({'von': (start - timedelta(days=1)).isoformat()})}",
        ),
        s.highlight(f"Zimmer {number} markieren", "room-row", number),
    ]
    return s.plan("room_availability", title, message=message, steps=steps)


def _departures(session: Session, text: str, folded: str, day: date) -> Plan | None:
    if not p.has_any(
        folded, r"\breist\b.*\bab\b", r"\babreisen?\b", r"\bcheck[- ]?outs?\b", r"\bauschecken\b"
    ):
        return None
    return departures_plan(session, day)


def departures_plan(session: Session, day: date) -> Plan:
    open_departures = list(
        session.scalars(
            _with_guests(
                select(Reservation).where(
                    Reservation.departure == day, Reservation.status == CHECKED_IN
                )
            ).order_by(Reservation.id)
        )
    )
    open_departures.sort(key=lambda r: r.room.number if r.room else "")
    if open_departures:
        names = ", ".join(
            f"{r.room.number if r.room else '–'} {r.primary_guest.last_name if r.primary_guest else r.code}"
            for r in open_departures
        )
        count = len(open_departures)
        message = f"{count} {'Abreise' if count == 1 else 'Abreisen'} offen: {names}"
    else:
        message = "Heute sind keine Abreisen mehr offen."
    return s.plan(
        "departures",
        "Abreisen heute",
        message=message,
        steps=[s.navigate("Abreisen öffnen", "/abreisen")],
    )


def _arrivals(session: Session, text: str, folded: str, day: date) -> Plan | None:
    if not p.has_any(
        folded,
        r"\bwer kommt\b",
        r"\breist\b.*\ban\b",
        r"\b(offene|naechste|heutige)n? anreisen?\b",
        r"\banreisen\b.*\bheute\b",
        r"\bheute\b.*\banreisen\b",
        r"\bankuenfte\b",
    ):
        return None
    return arrivals_plan(session, day)


def arrivals_plan(session: Session, day: date) -> Plan:
    arrivals = list(
        session.scalars(
            _with_guests(
                select(Reservation).where(
                    Reservation.arrival == day, Reservation.status == RESERVED
                )
            ).order_by(Reservation.eta.nulls_last(), Reservation.id)
        )
    )
    if arrivals:
        lines = [
            f"{fmt_time(r.eta) if r.eta else 'offen'} · {r.primary_guest.full_name if r.primary_guest else r.code}"
            f" · Zimmer {r.room.number if r.room else '–'}"
            for r in arrivals
        ]
        count = len(arrivals)
        message = f"{count} {'Anreise' if count == 1 else 'Anreisen'} offen:\n" + "\n".join(lines)
    else:
        message = "Heute sind keine Anreisen mehr offen."
    return s.plan(
        "arrivals", "Anreisen heute", message=message,
        steps=[s.navigate("Offene Anreisen öffnen", "/anreisen?filter=offen")],
    )  # fmt: skip


DASHBOARD_TITLE = "Übersicht anpassen"


def dashboard_plan(
    *, show: list[str] | None = None, occupancy_days: int | None = None, reset: bool = False
) -> Plan:
    """Dashboard layout: ``show`` picks the cards (None = unchanged), or ``reset`` to the default."""
    if reset:
        return s.plan(
            "dashboard", DASHBOARD_TITLE, message="Übersicht wieder in der Standardansicht.",
            steps=[s.dashboard_reset("Standardansicht wiederherstellen"), s.navigate("Übersicht öffnen", "/")],
        )  # fmt: skip
    widgets = [w for w in s.WIDGETS if w in show] if show else None  # keep the page order
    summary = (
        "Angezeigt: " + ", ".join(WIDGET_LABELS[w] for w in widgets)
        if widgets
        else "Kacheln unverändert"
    )
    return _dashboard_layout(widgets, occupancy_days, summary)


def _dashboard_layout(widgets: list[str] | None, days: int | None, summary: str) -> Plan:
    occupancy_days = max(7, min(days, 60)) if days else None
    if occupancy_days:
        summary += f" · Belegung für {occupancy_days} Tage"
    return s.plan(
        "dashboard", DASHBOARD_TITLE, message=summary,
        steps=[
            s.dashboard("Ansicht speichern", widgets=widgets, occupancy_days=occupancy_days),
            s.navigate("Übersicht öffnen", "/"),
        ],
    )  # fmt: skip


def _dashboard(session: Session, text: str, folded: str, day: date) -> Plan | None:
    mentions_board = p.has_any(folded, r"\buebersicht\b", r"\bdashboard\b", r"\bstartseite\b")
    if p.has_any(folded, r"zuruecksetzen", r"\bstandard", r"\balles wieder\b") and (
        mentions_board or p.has_any(folded, r"ansicht")
    ):
        return dashboard_plan(reset=True)
    mentioned = [
        key for key, pattern in DASHBOARD_WIDGET_WORDS.items() if re.search(pattern, folded)
    ]
    days = p.parse_days(folded)
    hide = p.has_any(folded, r"\bblende\b.*\baus\b", r"\bausblenden\b", r"\bohne\b", r"\bversteck")
    only = p.has_any(folded, r"\bnur\b")
    if not (mentions_board or hide or only or (days and "occupancy" in mentioned)):
        return None
    if not (mentioned or days):
        return None
    widgets: list[str] | None = None
    # "Belegung für 30 Tage" only changes the range; "nur …" picks the cards.
    picks_cards = mentioned and (only or (mentions_board and not days))
    if hide and mentioned:
        widgets = [w for w in s.WIDGETS if w not in mentioned]
        summary = "Ausgeblendet: " + ", ".join(WIDGET_LABELS[w] for w in mentioned)
    elif picks_cards:
        widgets = [w for w in s.WIDGETS if w in mentioned]  # keep the page order
        summary = "Angezeigt: " + ", ".join(WIDGET_LABELS[w] for w in widgets)
    else:
        summary = "Kacheln unverändert"
    return _dashboard_layout(widgets, days, summary)


_CODE = re.compile(r"^r-?\d{4}-\d{4}$")
_VERBS = re.compile(
    r"\b(zeig|oeffne|mach|leg|starte?|such|finde|verschieb|buch|ist|sind|wer|was|wie|wann|wo|bitte|kannst)\b"
)


def _search(session: Session, text: str, folded: str, day: date) -> Plan | None:
    term = re.sub(r"^(herrn?|frau|familie|fam\.?)\s+", "", text.strip(), flags=re.IGNORECASE)
    folded = p.fold(term)
    if _CODE.match(folded) or re.fullmatch(r"\d{3}", folded):
        pass
    elif (
        len(folded.split()) > 3 or _VERBS.search(folded) or not re.fullmatch(r"[\w\s.'-]+", folded)
    ):
        return None
    return search_plan(term)


def search_plan(term: str) -> Plan:
    """Reservation search for a guest name, reservation code or room number."""
    return s.plan(
        "search", f"Suche: {term}",
        steps=[s.navigate(f"Nach „{term}“ suchen", f"/reservierungen?{urlencode({'q': term})}")],
    )  # fmt: skip


RULES: tuple[Rule, ...] = (
    _walk_in,
    _check_in,
    _move_arrival,
    _room_availability,
    _dashboard,
    _departures,
    _arrivals,
    _search,
)


def plan_for(session: Session, text: str, *, day: date | None = None) -> Plan:
    day = day or business_today()
    folded = p.fold(text)
    if folded:
        for rule in RULES:
            result = rule(session, text, folded, day)
            if result is not None:
                return result
    return unknown_plan(session, day, NOT_YET if folded else None)


def unknown_plan(session: Session, day: date, message: str | None) -> Plan:
    """No workflow fits: say so (or ask back) and offer working examples."""
    return s.plan(
        "unknown",
        "Nicht verstanden" if message else "Was möchten Sie tun?",
        message=message,
        suggestions=suggestions(session, day=day),
    )


# ---------------------------------------------------------------------------
# Search and suggestions
# ---------------------------------------------------------------------------


def _like(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def search(
    session: Session, q: str, *, day: date | None = None, limit: int = 6
) -> list[dict[str, str]]:
    """Quick matches for the command bar: same matching as /reservierungen."""
    q = q.strip()
    if not q:
        return []
    day = day or business_today()
    pattern = _like(q)
    guest_match = (
        select(ReservationGuest.reservation_id)
        .join(Guest, Guest.id == ReservationGuest.guest_id)
        .where(
            or_(
                Guest.first_name.ilike(pattern, escape="\\"),
                Guest.last_name.ilike(pattern, escape="\\"),
                (Guest.first_name + " " + Guest.last_name).ilike(pattern, escape="\\"),
            )
        )
    )
    room_match = select(Room.id).where(Room.number == q)
    is_past = case((Reservation.departure < day, 1), else_=0)
    rows = session.scalars(
        _with_guests(
            select(Reservation).where(
                or_(
                    Reservation.id.in_(guest_match),
                    Reservation.code.ilike(pattern, escape="\\"),
                    Reservation.room_id.in_(room_match),
                )
            )
        )
        .order_by(is_past, case((is_past == 0, Reservation.arrival)), Reservation.arrival.desc())
        .limit(limit)
    ).all()
    results = []
    for res in rows:
        guest = res.primary_guest
        room = f" · Zimmer {res.room.number}" if res.room else ""
        results.append(
            {
                "label": guest.full_name if guest else res.code,
                "sub": f"{res.code}{room} · {_short_span(res.arrival, res.departure)}",
                "status": STATUS_LABELS.get(res.status, res.status),
                "url": f"/reservierungen/{res.id}",
            }
        )
    return results


def _ready(res: Reservation) -> bool:
    return all(
        rg.guest.birth_date and (not rg.exemption_category or rg.exemption_evidence)
        for rg in res.guests
    )


def suggestions(session: Session, *, day: date | None = None) -> list[str]:
    """One working example per workflow, built from the current data."""
    day = day or business_today()
    out: list[str] = []

    # Walk-in: a double room if one is free for two nights, else whatever is.
    free = free_rooms(session, day, day + timedelta(days=2))
    categories = {r.category for r in free}
    category = (
        "Doppelzimmer"
        if "Doppelzimmer" in categories
        else (min(categories) if categories else None)
    )
    out.append(f"Walk-in: Herr Klaus Becker, zwei Nächte, {category or 'Doppelzimmer'}")

    # Check-in: an arrival that is ready, named unambiguously.
    arrivals = list(
        session.scalars(
            _with_guests(
                select(Reservation).where(
                    Reservation.arrival == day, Reservation.status == RESERVED
                )
            ).order_by(Reservation.eta.nulls_last(), Reservation.id)
        )
    )
    candidates = sorted(arrivals, key=lambda r: not _ready(r))
    for res in candidates:
        guest = res.primary_guest
        if guest is None:
            continue
        phrase = f"Check-in für {_salutation(guest)}"
        if len(_best_name_matches(p.fold(phrase), arrivals)) == 1:
            out.append(phrase)
            break
    else:
        out.append("Wer kommt heute noch?")

    out.append("Wer reist heute noch ab?")

    # Room availability: the first room free over the coming weekend.
    start, end = p.weekend(day)
    weekend_free = free_rooms(session, start, end)
    preferred = [r for r in weekend_free if r.category == "Doppelzimmer"] or weekend_free
    out.append(f"Ist Zimmer {preferred[0].number if preferred else '204'} am Wochenende frei?")

    out.append(_move_suggestion(session, day))
    out.append("Zeig mir nur Anreisen und Belegung, 30 Tage")
    return out


def _move_suggestion(session: Session, day: date) -> str:
    """A guest with a later arrival whose room stays free if it moves to Friday."""
    friday = p.next_weekday(day, 4)
    upcoming = list(
        session.scalars(
            _with_guests(
                select(Reservation).where(Reservation.arrival > day, Reservation.status == RESERVED)
            ).order_by(Reservation.arrival, Reservation.id)
        )
    )
    for res in upcoming:
        guest = res.primary_guest
        if guest is None or res.arrival == friday or res.room_id is None:
            continue
        phrase = f"Verschieb die Anreise von {guest.full_name} auf Freitag"
        if {
            (r.primary_guest.first_name, r.primary_guest.last_name)
            for r in _best_name_matches(p.fold(phrase), upcoming)
        } != {(guest.first_name, guest.last_name)}:
            continue
        new_departure = friday + timedelta(days=res.nights)
        clash = session.scalars(
            blocking_reservations(friday, new_departure, exclude_reservation_id=res.id).where(
                Reservation.room_id == res.room_id
            )
        ).first()
        if clash is None:
            return phrase
    return "Verschieb die Anreise von Klaus Weber auf Freitag"
