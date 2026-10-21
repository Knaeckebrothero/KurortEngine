"""Claude as the command bar's planner: it reads the request, the plan builders write the steps.

Claude sees one tool per workflow, picks one and fills its fields from what
staff typed or said (names, dates, nights, room). The plan itself always comes
from the builders the phrase rules use, so URLs, room numbers and form fields
are real, and the last step of any change is still a person pressing save.

Any failure (no key, timeout, API error, refusal, an unusable answer) returns
None, and the caller answers from the rules instead.
"""

from __future__ import annotations

import logging
import os
from datetime import date
from functools import lru_cache
from typing import Any

import anthropic
from sqlalchemy.orm import Session

from kurort_app.config import get_settings
from kurort_app.services.assistant import parsing as p
from kurort_app.services.assistant import planner
from kurort_app.services.assistant import schema as s

log = logging.getLogger(__name__)

ENGINE = "claude"
CATEGORIES = [category for _, category in p.CATEGORIES]
WEEKDAYS = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag")
# With `fallbacks="default"`, a request the model declines is rerouted to
# Anthropic's recommended fallback model inside the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

SYSTEM = """\
You are the command bar of the staff app of Hotel Rheinland, a 33-room hotel in \
the spa town Bad Orb. Reception, housekeeping and kitchen staff type or speak short \
German requests. Speech recognition may garble words; read for the intent.

Answer every request with exactly one tool call. The app turns the call into steps \
on screen (open a page, fill a form, highlight a row). Nothing is saved until a \
person presses save, so pick the most likely tool rather than asking.

- Names: pass the guest's name as said, with salutation if given ("Frau Müller").
- Dates: resolve relative dates ("morgen", "Freitag", "am Wochenende", "15.10.") \
against today's date from the request; use ISO format (YYYY-MM-DD). A weekend stay \
is Friday night to Sunday morning unless said otherwise.
- Leave a field out when the request does not say it. Never invent names, rooms or \
dates.

Only when no tool fits, or a required detail is missing and cannot be guessed, \
reply with one short German sentence instead of a tool call (formal "Sie").\
"""

_GUEST = {
    "type": "string",
    "description": "The guest's name as said, e.g. 'Frau Müller' or 'Anna Schmidt'.",
}


def _date(description: str) -> dict[str, Any]:
    return {"type": "string", "format": "date", "description": description}


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    # Not strict: strict tool use makes Claude write the fields in schema order, so a
    # detail it reaches late is dropped ("Einzelzimmer für drei Nächte" lost the
    # nights). _run checks every field itself instead.
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


TOOLS = [
    _tool(
        "walk_in",
        "Open the walk-in form for a guest without a reservation who arrives today. "
        "The app picks the first free room of the category and prefills the form.",
        {
            "nights": {"type": "integer", "description": "Nights to stay, 1 to 28."},
            "category": {"type": "string", "enum": CATEGORIES},
            "first_name": {"type": "string"},
            "last_name": {"type": "string"},
        },
        [],
    ),
    _tool(
        "check_in",
        "Start the check-in of a guest who arrives today. Without a name the app lists "
        "today's open arrivals.",
        {"guest": _GUEST},
        [],
    ),
    _tool(
        "move_arrival",
        "Move the arrival of a guest's next reservation to another day; the number of "
        "nights stays the same. The app opens the reservation with the new dates filled in.",
        {"guest": _GUEST, "new_arrival": _date("The new arrival day.")},
        ["guest"],
    ),
    _tool(
        "room_availability",
        "Check whether a room is free and show it in the room plan.",
        {
            "room": {"type": "string", "description": "Room number, e.g. '204'."},
            "first_night": _date("First night to check. Default: tonight."),
            "departure": _date("Morning the stay would end. Default: the day after."),
        },
        ["room"],
    ),
    _tool("arrivals", "List today's arrivals that have not checked in yet.", {}, []),
    _tool("departures", "List today's departures that have not checked out yet.", {}, []),
    _tool(
        "dashboard",
        "Change the dashboard: which cards it shows, how many days the occupancy chart "
        "covers, which rows the Heute table lists, or reset it to the default. Cards: "
        "metrics (Kennzahlen), today (the arrivals and departures table, Heute), "
        "occupancy (Belegung).",
        {
            "show": {
                "type": "array",
                "items": {"type": "string", "enum": list(s.WIDGETS)},
                "description": "The cards to show; leave out to keep the current cards.",
            },
            "occupancy_days": {"type": "integer", "description": "Days in the chart, 7 to 60."},
            "today_filter": {
                "type": "string",
                "enum": list(planner.TODAY_FILTERS),
                "description": "Rows of the Heute table: all, only arrivals or only departures.",
            },
            "reset": {"type": "boolean", "description": "Back to the default layout."},
        },
        [],
    ),
    _tool(
        "search",
        "Search reservations by guest name, reservation code (R-2026-0012) or room number.",
        {"term": {"type": "string"}},
        ["term"],
    ),
]


@lru_cache
def _client(timeout: float) -> anthropic.Anthropic | None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.warning("assistant: KURORT_ASSISTANT_ENGINE=claude but ANTHROPIC_API_KEY is not set")
        return None
    # No retries: staff are waiting, and the rules answer at once.
    return anthropic.Anthropic(timeout=timeout, max_retries=0)


def plan(session: Session, text: str, *, day: date, client: Any = None) -> dict | None:
    """Plan for ``text`` with Claude, or None so the caller falls back to the rules."""
    settings = get_settings()
    client = client or _client(settings.assistant_timeout)
    if client is None:
        return None
    request = f"Heute ist {WEEKDAYS[day.weekday()]}, {day.isoformat()}.\n\nAnfrage: {text}"
    try:
        response = client.beta.messages.create(
            model=settings.assistant_model,
            max_tokens=4096,
            system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
            tools=TOOLS,
            messages=[{"role": "user", "content": request}],
            output_config={"effort": "low"},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
    except anthropic.APIStatusError as exc:
        log.warning("assistant: Claude answered %s (request %s)", exc.status_code, exc.request_id)
        return None
    except anthropic.APIConnectionError as exc:
        log.warning("assistant: Claude not reachable: %s", exc)
        return None
    except anthropic.APIError as exc:
        log.warning("assistant: Claude call failed: %s", exc)
        return None
    if response.stop_reason == "refusal":
        log.warning("assistant: Claude declined the request")
        return None

    call = next((block for block in response.content if block.type == "tool_use"), None)
    if call is not None:
        result = _run(session, day, call.name, call.input, text=text)
    else:
        reply = " ".join(b.text.strip() for b in response.content if b.type == "text").strip()
        if not reply or response.stop_reason == "max_tokens":
            return None
        result = s.plan(
            "unknown", "Antwort", message=reply, suggestions=planner.suggestions(session, day=day)
        )
    if result is not None:
        result["engine"] = ENGINE
    return result


def _run(
    session: Session, day: date, name: str, args: dict[str, Any], *, text: str = ""
) -> dict | None:
    """The plan for one tool call (``text``: the request); None for a call the app cannot carry out."""
    if name == "walk_in":
        first, last = _text(args.get("first_name")), _text(args.get("last_name"))
        category = args.get("category")
        return planner.walk_in_plan(
            session,
            day,
            nights=_int(args.get("nights")),
            category=category if category in CATEGORIES else None,
            name=(first, last) if first or last else None,
        )
    if name == "check_in":
        guest = _text(args.get("guest"))
        return planner.check_in_plan(session, day, p.fold(guest or ""), mentioned=guest)
    if name == "move_arrival":
        guest = _text(args.get("guest"))
        return planner.move_arrival_plan(
            session,
            day,
            p.fold(guest or ""),
            mentioned=guest,
            target=_iso(args.get("new_arrival")),
        )
    if name == "room_availability":
        room = "".join(ch for ch in str(args.get("room") or "") if ch.isdigit())
        if not room:
            return None
        return planner.room_availability_plan(
            session,
            day,
            room,
            start=_iso(args.get("first_night")),
            end=_iso(args.get("departure")),
        )
    if name == "arrivals":
        return planner.arrivals_plan(session, day)
    if name == "departures":
        return planner.departures_plan(session, day)
    if name == "dashboard":
        show = [w for w in args.get("show") or [] if w in s.WIDGETS]
        return planner.dashboard_plan(
            show=show or None,
            occupancy_days=_int(args.get("occupancy_days")),
            reset=args.get("reset") is True,
            today_filter=_text(args.get("today_filter")),
        )
    if name == "search":
        term = _text(args.get("term"))
        return planner.search_plan(term, request=text) if term else None
    log.warning("assistant: Claude called an unknown tool %r", name)
    return None


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _iso(value: Any) -> date | None:
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None
