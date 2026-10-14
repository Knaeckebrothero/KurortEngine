"""Room availability: which rooms are free for a span of nights.

A stay occupies the nights ``arrival … departure − 1``. Two stays clash
when their night ranges intersect, so a departure and an arrival on the
same day (back-to-back) never conflict. Cancelled and no-show
reservations do not hold a room.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from kurort_app.models import CANCELLED, NO_SHOW, Reservation, Room

# Statuses that do not occupy a room.
NON_BLOCKING = (CANCELLED, NO_SHOW)


def overlaps(a_arrival: date, a_departure: date, b_arrival: date, b_departure: date) -> bool:
    """True when the night ranges [arrival, departure) intersect."""
    return a_arrival < b_departure and b_arrival < a_departure


def blocking_reservations(
    arrival: date, departure: date, *, exclude_reservation_id: int | None = None
) -> Select[tuple[Reservation]]:
    """Reservations that hold a room for at least one night in [arrival, departure)."""
    stmt = select(Reservation).where(
        Reservation.arrival < departure,
        Reservation.departure > arrival,
        Reservation.status.not_in(NON_BLOCKING),
        Reservation.room_id.is_not(None),
    )
    if exclude_reservation_id is not None:
        stmt = stmt.where(Reservation.id != exclude_reservation_id)
    return stmt


def occupied_room_ids(
    session: Session,
    arrival: date,
    departure: date,
    *,
    exclude_reservation_id: int | None = None,
) -> set[int]:
    stmt = blocking_reservations(
        arrival, departure, exclude_reservation_id=exclude_reservation_id
    ).with_only_columns(Reservation.room_id)
    return {room_id for room_id in session.scalars(stmt) if room_id is not None}


def free_rooms(
    session: Session,
    arrival: date,
    departure: date,
    *,
    exclude_reservation_id: int | None = None,
) -> list[Room]:
    """Rooms with no blocking reservation in the span, ordered by room number."""
    taken = occupied_room_ids(
        session, arrival, departure, exclude_reservation_id=exclude_reservation_id
    )
    rooms = session.scalars(select(Room).order_by(Room.number)).all()
    return [room for room in rooms if room.id not in taken]


def is_room_free(
    session: Session,
    room_id: int,
    arrival: date,
    departure: date,
    *,
    exclude_reservation_id: int | None = None,
) -> bool:
    return room_id not in occupied_room_ids(
        session, arrival, departure, exclude_reservation_id=exclude_reservation_id
    )
