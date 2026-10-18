"""Seminar room defaults, pricing and half-day availability."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from kurort_app.models import FunctionSpace, SpaceBooking


def ensure_function_spaces(session: Session) -> None:
    if session.scalar(select(FunctionSpace.id).limit(1)) is None:
        session.add(
            FunctionSpace(
                name="Seminarraum",
                capacity=20,
                price_half_day=Decimal("190.00"),
                price_full_day=Decimal("340.00"),
            )
        )


def calculate_price(space: FunctionSpace, start: date, end: date, slot: str) -> Decimal:
    rate = space.price_full_day if slot == "ganztags" else space.price_half_day
    return rate * ((end - start).days + 1)


def find_clash(
    session: Session,
    space_id: int,
    start: date,
    end: date,
    slot: str,
    exclude_booking_id: int | None = None,
) -> SpaceBooking | None:
    query = select(SpaceBooking).where(
        SpaceBooking.space_id == space_id,
        SpaceBooking.start_date <= end,
        SpaceBooking.end_date >= start,
        SpaceBooking.status != "storniert",
    )
    if slot != "ganztags":
        query = query.where(SpaceBooking.slot.in_((slot, "ganztags")))
    if exclude_booking_id is not None:
        query = query.where(SpaceBooking.id != exclude_booking_id)
    return session.scalar(query.order_by(SpaceBooking.start_date, SpaceBooking.id).limit(1))


def catering_text(booking: SpaceBooking) -> str:
    return " · ".join(
        label
        for flag, label in (
            (booking.catering_coffee, "Kaffeepause"),
            (booking.catering_lunch, "Mittagessen"),
            (booking.catering_drinks, "Getränke"),
        )
        if flag
    )


def week_rows(session: Session, start: date) -> list[dict]:
    from datetime import timedelta

    spaces = session.scalars(
        select(FunctionSpace)
        .where(FunctionSpace.active)
        .order_by(FunctionSpace.position, FunctionSpace.id)
    ).all()
    bookings = session.scalars(
        select(SpaceBooking)
        .where(
            SpaceBooking.start_date <= start + timedelta(days=6),
            SpaceBooking.end_date >= start,
            SpaceBooking.status != "storniert",
        )
        .order_by(SpaceBooking.start_date, SpaceBooking.id)
    ).all()
    rows = []
    for space in spaces:
        days = []
        for offset in range(7):
            day = start + timedelta(days=offset)
            halves = {
                slot: next(
                    (
                        b
                        for b in bookings
                        if b.space_id == space.id
                        and b.start_date <= day <= b.end_date
                        and b.slot in (slot, "ganztags")
                    ),
                    None,
                )
                for slot in ("vormittag", "nachmittag")
            }
            days.append({"date": day, "halves": halves})
        rows.append({"space": space, "days": days})
    return rows


def plan_rows(session: Session, start: date, end: date) -> list[dict]:
    from datetime import timedelta

    spaces = session.scalars(
        select(FunctionSpace)
        .where(FunctionSpace.active)
        .order_by(FunctionSpace.position, FunctionSpace.id)
    ).all()
    bookings = session.scalars(
        select(SpaceBooking)
        .where(
            SpaceBooking.start_date < end,
            SpaceBooking.end_date >= start,
            SpaceBooking.status != "storniert",
        )
        .order_by(SpaceBooking.start_date, SpaceBooking.id)
    ).all()
    rows = []
    for space in spaces:
        bars = []
        for booking in bookings:
            if booking.space_id != space.id:
                continue
            first, last = (
                max(start, booking.start_date),
                min(end - timedelta(days=1), booking.end_date),
            )
            if booking.slot == "ganztags":
                spans = [(2 * (first - start).days, 2 * ((last - start).days + 1))]
            else:
                half = int(booking.slot == "nachmittag")
                spans = [
                    (2 * offset + half, 2 * offset + half + 1)
                    for offset in range((first - start).days, (last - start).days + 1)
                ]
            bars.extend(
                {
                    "booking": booking,
                    "start": left + 2,
                    "end": right + 2,
                    "label": booking.display_name,
                }
                for left, right in spans
            )
        rows.append({"space": space, "bars": bars})
    return rows
