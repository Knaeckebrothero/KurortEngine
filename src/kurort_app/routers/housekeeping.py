"""Phone-first room status list; no guest data is rendered."""

from urllib.parse import parse_qs, urlencode, urlsplit

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from kurort_app.auth import require_role, safe_next
from kurort_app.config import today
from kurort_app.db import get_session
from kurort_app.models import HOUSEKEEPING_STATUSES, ROOM_DIRTY, Room
from kurort_app.services import housekeeping
from kurort_app.web import HOUSEKEEPING_LABELS, NAV, NavItem, redirect_with_notice, templates

router = APIRouter(dependencies=[Depends(require_role("housekeeping", "rezeption", "leitung"))])
NAV.append(
    NavItem(
        "/zimmerstatus",
        "Zimmerstatus",
        '<path d="M4 4h16v16H4zM8 12l3 3 5-6"/>',
        "Heute",
        roles=("housekeeping", "rezeption", "leitung"),
    )
)


def _floor(value: str | None) -> int | None:
    """The ?etage= filter; anything that isn't a floor number means all floors."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _on_floor(items: list, floor: int | None) -> list:
    return [item for item in items if floor is None or item.room.floor == floor]


def _counts(items) -> dict[str, int]:
    return {
        s: sum(item.room.housekeeping_status == s for item in items) for s in HOUSEKEEPING_STATUSES
    }


@router.get("/zimmerstatus", response_class=HTMLResponse)
def room_list(
    request: Request,
    etage: str = "",
    status: str = "",
    sort: str = "dringend",
    session: Session = Depends(get_session),
) -> HTMLResponse:
    floor = _floor(etage)
    items = housekeeping.situations(session, today())
    floors = sorted({item.room.floor for item in items})
    floor_items = _on_floor(items, floor)
    counts = _counts(floor_items)
    visible = [
        item for item in floor_items if not status or item.room.housekeeping_status == status
    ]
    if sort not in ("dringend", "zimmer"):
        sort = "dringend"
    visible.sort(
        key=lambda i: (
            i.priority if sort == "dringend" else 0,
            int(i.room.number) if i.room.number.isdigit() else 9999,
            i.room.number,
        )
    )

    def url(**changes):
        params = {"etage": floor, "status": status, "sort": sort, **changes}
        return "/zimmerstatus?" + urlencode(
            {k: v for k, v in params.items() if v not in (None, "")}
        )

    return templates.TemplateResponse(
        request,
        "housekeeping/list.html",
        {
            "items": visible,
            "floors": floors,
            "etage": floor,
            "status": status,
            "sort": sort,
            "counts": counts,
            "floor_count": len(floor_items),
            "statuses": HOUSEKEEPING_LABELS,
            "stayover_count": len(housekeeping.stayover_rooms(items)),
            "url": url,
        },
    )


@router.post("/zimmerstatus/bleibe")
def mark_stayovers(session: Session = Depends(get_session)) -> Response:
    """All floors, whatever the list is filtered to; the button says so."""
    rooms = housekeeping.stayover_rooms(housekeeping.situations(session, today()))
    for room in rooms:
        housekeeping.set_status(session, room, ROOM_DIRTY, reason="stayover")
    session.commit()
    if not rooms:
        return redirect_with_notice("/zimmerstatus", "Keine Bleibezimmer zu setzen.", "info")
    return redirect_with_notice(
        "/zimmerstatus", f"{len(rooms)} Bleibezimmer auf schmutzig gesetzt."
    )


@router.post("/zimmerstatus/{room_id}/{status}")
def change_status(
    request: Request,
    room_id: int,
    status: str,
    notiz: str = Form("", max_length=200),
    zurueck: str = Form(""),
    session: Session = Depends(get_session),
) -> Response:
    if status not in HOUSEKEEPING_STATUSES:
        raise HTTPException(400, "Unbekannter Zimmerstatus.")
    room = session.get(Room, room_id)
    if room is None:
        raise HTTPException(404, "Zimmer nicht gefunden.")
    target = safe_next(zurueck)
    if target.startswith("/zimmerstatus/"):
        target = "/zimmerstatus"
    reason = "checkin_blocker" if target.startswith("/check-in/") else "manual"
    housekeeping.set_status(session, room, status, reason=reason, note=notiz)
    session.commit()
    if request.headers.get("hx-request") == "true":
        # The new card, plus the list's filter counts and bulk button (out-of-band swaps).
        items = housekeeping.situations(session, today())
        page = parse_qs(urlsplit(request.headers.get("hx-current-url", "")).query)
        floor = _floor(page.get("etage", [""])[0])
        return templates.TemplateResponse(
            request,
            "housekeeping/_card_update.html",
            {
                "item": next(i for i in items if i.room.id == room.id),
                "statuses": HOUSEKEEPING_LABELS,
                "counts": _counts(_on_floor(items, floor)),
                "stayover_count": len(housekeeping.stayover_rooms(items)),
                "etage": floor,
                "oob": True,
            },
        )
    return redirect_with_notice(
        target if target != "/" else "/zimmerstatus",
        f"Zimmer {room.number} ist {housekeeping.status_word(status)}.",
    )
