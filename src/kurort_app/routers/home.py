"""Role-aware entry point and today's front-desk overview."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from kurort_app.auth import home_path
from kurort_app.config import today
from kurort_app.db import get_session
from kurort_app.models import CHECKED_IN, CHECKED_OUT, RESERVED
from kurort_app.routers.front_desk import (
    CHART_NIGHTS_COOKIE,
    _arrivals,
    _departures,
    _in_house,
    _occupancy_by_night,
    _room_count,
    chart_nights,
    occupancy_chart,
)
from kurort_app.services import today as desk
from kurort_app.web import templates

router = APIRouter()


@router.get("/", response_class=Response)
def dashboard(
    request: Request, tage: str = "", zeigen: str = "alle", session: Session = Depends(get_session)
) -> Response:
    target = home_path(getattr(request.state, "user", None))
    if target != "/":
        return RedirectResponse(target, status_code=303)
    day = today()
    # The assistant remembers a chart range in a cookie; an explicit ?tage= wins.
    nights = chart_nights(tage or request.cookies.get(CHART_NIGHTS_COOKIE))
    arrivals = _arrivals(session, day)
    departures = _departures(session, day)
    in_house = _in_house(session)
    capacity = _room_count(session)
    counts = _occupancy_by_night(session, day, nights)

    arrived = [r for r in arrivals if r.status in (CHECKED_IN, CHECKED_OUT)]
    open_arrivals = [r for r in arrivals if r.status == RESERVED]
    departed = [r for r in departures if r.status == CHECKED_OUT]
    open_departures = [r for r in departures if r.status == CHECKED_IN]
    occupied_rooms = len({r.room_id for r in in_house if r.room_id is not None})
    guests_in_house = sum(len(r.guests) for r in in_house)
    tonight = counts[0] if counts else 0
    early = [r for r in open_arrivals if r.eta is not None and r.eta.hour < 14]

    rows = desk.today_rows(session, day)
    row_counts = {
        "alle": len(rows),
        "anreisen": sum(row.kind == "anreise" for row in rows),
        "abreisen": sum(row.kind == "abreise" for row in rows),
    }
    if zeigen not in row_counts:
        zeigen = "alle"
    visible = [
        row
        for row in rows
        if zeigen == "alle"
        or row.kind == {"anreisen": "anreise", "abreisen": "abreise"}.get(zeigen)
    ]

    def is_open(row):
        return row.reservation.status == (RESERVED if row.kind == "anreise" else CHECKED_IN)

    context = {
        "arrivals": arrivals,
        "queue": open_arrivals + arrived,
        "arrived_count": len(arrived),
        "open_arrival_count": len(open_arrivals),
        "early_count": len(early),
        "departure_count": len(departures),
        "departed_count": len(departed),
        "open_departure_count": len(open_departures),
        "occupied_rooms": occupied_rooms,
        "guests_in_house": guests_in_house,
        "capacity": capacity,
        "tonight": tonight,
        "occupancy_pct": round(100 * tonight / capacity) if capacity else 0,
        "chart": occupancy_chart(counts, day, capacity),
        "chart_nights": nights,
        "today_open": [row for row in visible if is_open(row)],
        "today_done": [row for row in visible if not is_open(row)],
        "today_counts": row_counts,
        "zeigen": zeigen,
        "notices": desk.dashboard_notices(session, day),
        "next_arrival": open_arrivals[0] if open_arrivals else None,
        "flags": {r.id: desk.flags_for(session, "anreise", r) for r in arrivals},
    }
    return templates.TemplateResponse(request, "front_desk/dashboard.html", context)
