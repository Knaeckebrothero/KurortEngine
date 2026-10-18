"""Room cleaning changes and today's guest-free housekeeping situations."""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from kurort_app import audit
from kurort_app.auth import current_actor
from kurort_app.models import (
    CHECKED_IN,
    CHECKED_OUT,
    HOUSEKEEPING_STATUSES,
    RESERVED,
    ROOM_DIRTY,
    ROOM_OUT_OF_ORDER,
    ROOM_READY,
    Reservation,
    Room,
)
from kurort_app.web import HOUSEKEEPING_LABELS


def set_status(
    session: Session, room: Room, status: str, *, reason: str, note: str | None = None
) -> None:
    if status not in HOUSEKEEPING_STATUSES:
        raise ValueError("Unbekannter Zimmerstatus.")
    previous = room.housekeeping_status
    if previous == status:
        return
    room.housekeeping_status = status
    room.housekeeping_note = (note or "").strip() or None if status == ROOM_OUT_OF_ORDER else None
    room.housekeeping_changed_at = datetime.now(UTC)
    room.housekeeping_changed_by = current_actor.get() or audit.DEFAULT_ACTOR
    audit.record(
        session,
        action="room.status_changed",
        entity="room",
        entity_id=room.id,
        summary=f"Zimmer {room.number}: {HOUSEKEEPING_LABELS[previous]} → {HOUSEKEEPING_LABELS[status]}",
        payload={"from": previous, "to": status, "reason": reason, "note": room.housekeeping_note},
    )


@dataclass
class RoomSituation:
    room: Room
    departure: Reservation | None = None
    arrival: Reservation | None = None
    stayover: bool = False

    @property
    def label(self) -> str:
        if self.departure and self.arrival:
            return "Abreise · Anreise heute"
        if self.departure:
            return "Abgereist" if self.departure.status == CHECKED_OUT else "Abreise heute"
        if self.arrival:
            eta = f" · ca. {self.arrival.eta:%H:%M}" if self.arrival.eta else ""
            return f"Anreise heute{eta}"
        return "Bleibe" if self.stayover else "frei"

    @property
    def priority(self) -> int:
        status = self.room.housekeeping_status
        if self.arrival and status not in ROOM_READY:
            return 0
        if self.departure and self.departure.status == CHECKED_OUT and status == ROOM_DIRTY:
            return 1
        if status == ROOM_DIRTY:
            return 2
        return 3 if status == ROOM_OUT_OF_ORDER else 4


def situations(session: Session, day: date) -> list[RoomSituation]:
    rooms = list(session.scalars(select(Room).order_by(Room.number)))
    by_room = {room.id: RoomSituation(room) for room in rooms}
    stays = session.scalars(
        select(Reservation)
        .where(
            Reservation.arrival <= day,
            Reservation.departure >= day,
            Reservation.status.in_((RESERVED, CHECKED_IN, CHECKED_OUT)),
        )
        .order_by(Reservation.id)
    )
    for stay in stays:
        item = by_room.get(stay.room_id)
        if item is None:
            continue
        if stay.departure == day and stay.status in (CHECKED_IN, CHECKED_OUT):
            item.departure = stay
        if stay.arrival == day and stay.status == RESERVED:
            item.arrival = stay
        if stay.status == CHECKED_IN and stay.arrival < day < stay.departure:
            item.stayover = True
    return list(by_room.values())


def stayover_rooms(items: list[RoomSituation]) -> list[Room]:
    return [
        item.room
        for item in items
        if item.label == "Bleibe" and item.room.housekeeping_status in ROOM_READY
    ]
