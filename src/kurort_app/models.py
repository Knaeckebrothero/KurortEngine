"""Persistent domain model of the front desk.

Status vocabularies are plain strings (checked in the database) so the
Alembic history stays simple; the constants below are the single source
for code and templates.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kurort_app.db import Base

# Reservation lifecycle.
RESERVED = "reserved"
CHECKED_IN = "checked_in"
CHECKED_OUT = "checked_out"
CANCELLED = "cancelled"
NO_SHOW = "no_show"
RESERVATION_STATUSES = (RESERVED, CHECKED_IN, CHECKED_OUT, CANCELLED, NO_SHOW)

# Booking channels.
CHANNELS = ("direct", "phone", "email", "booking.com", "walk-in")

# Meldeschein (§29 BMG) per guest: not started → printed in AVS → signed.
MELDESCHEIN_OPEN = "offen"
MELDESCHEIN_PRINTED = "gedruckt"
MELDESCHEIN_SIGNED = "unterschrieben"
MELDESCHEIN_STATUSES = (MELDESCHEIN_OPEN, MELDESCHEIN_PRINTED, MELDESCHEIN_SIGNED)

# Exemption categories the engine recognises (kurort_engine.exemptions).
EXEMPTION_CATEGORIES = ("geschaeftsreisender", "schwerbehindert_100")


def _in(values: tuple[str, ...]) -> str:
    return "(" + ", ".join(f"'{v}'" for v in values) + ")"


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(10), unique=True)
    category: Mapped[str] = mapped_column(String(40))
    floor: Mapped[int] = mapped_column(Integer)
    max_occupancy: Mapped[int] = mapped_column(Integer)
    nightly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    features: Mapped[str | None] = mapped_column(String(200))

    reservations: Mapped[list[Reservation]] = relationship(back_populates="room")


class Guest(Base):
    __tablename__ = "guests"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(120))
    birth_date: Mapped[date | None] = mapped_column(Date)
    nationality: Mapped[str] = mapped_column(String(2), default="DE")
    street: Mapped[str | None] = mapped_column(String(160))
    postal_code: Mapped[str | None] = mapped_column(String(16))
    city: Mapped[str | None] = mapped_column(String(80))
    country: Mapped[str] = mapped_column(String(2), default="DE")
    email: Mapped[str | None] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(40))
    id_document_number: Mapped[str | None] = mapped_column(String(40))
    disability_pct: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    stays: Mapped[list[ReservationGuest]] = relationship(back_populates="guest")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def address_line(self) -> str:
        parts = [self.street, " ".join(p for p in (self.postal_code, self.city) if p)]
        return ", ".join(p for p in parts if p)


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint(f"status IN {_in(RESERVATION_STATUSES)}", name="reservation_status"),
        CheckConstraint(f"channel IN {_in(CHANNELS)}", name="reservation_channel"),
        CheckConstraint("departure > arrival", name="reservation_dates"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), index=True)
    arrival: Mapped[date] = mapped_column(Date, index=True)
    departure: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(16), default=RESERVED, index=True)
    channel: Mapped[str] = mapped_column(String(16), default="direct")
    eta: Mapped[time | None] = mapped_column(Time)
    rate_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    package_code: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    room: Mapped[Room | None] = relationship(back_populates="reservations")
    guests: Mapped[list[ReservationGuest]] = relationship(
        back_populates="reservation",
        order_by="ReservationGuest.position",
        cascade="all, delete-orphan",
    )
    kurtaxe: Mapped[KurtaxeAssessment | None] = relationship(
        back_populates="reservation", cascade="all, delete-orphan", uselist=False
    )

    @property
    def nights(self) -> int:
        return (self.departure - self.arrival).days

    @property
    def primary_guest(self) -> Guest | None:
        for rg in self.guests:
            if rg.is_primary:
                return rg.guest
        return self.guests[0].guest if self.guests else None


class ReservationGuest(Base):
    """One person on a reservation, with their per-guest compliance state."""

    __tablename__ = "reservation_guests"
    __table_args__ = (
        UniqueConstraint("reservation_id", "guest_id"),
        CheckConstraint(
            f"meldeschein_status IN {_in(MELDESCHEIN_STATUSES)}", name="meldeschein_status"
        ),
        CheckConstraint(
            f"exemption_category IS NULL OR exemption_category IN {_in(EXEMPTION_CATEGORIES)}",
            name="exemption_category",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_id: Mapped[int] = mapped_column(
        ForeignKey("reservations.id", ondelete="CASCADE"), index=True
    )
    guest_id: Mapped[int] = mapped_column(ForeignKey("guests.id"), index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    exemption_category: Mapped[str | None] = mapped_column(String(32))
    exemption_evidence: Mapped[str | None] = mapped_column(String(200))

    meldeschein_status: Mapped[str] = mapped_column(String(16), default=MELDESCHEIN_OPEN)
    meldeschein_printed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    meldeschein_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    reservation: Mapped[Reservation] = relationship(back_populates="guests")
    guest: Mapped[Guest] = relationship(back_populates="stays")


class KurtaxeAssessment(Base):
    """The tourist tax computed by kurort_engine for one reservation."""

    __tablename__ = "kurtaxe_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_id: Mapped[int] = mapped_column(
        ForeignKey("reservations.id", ondelete="CASCADE"), unique=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    nights: Mapped[int] = mapped_column(Integer)
    # [{"guest_id", "name", "band", "rate_per_day", "days", "amount", "exempt", "exemption"}]
    breakdown: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    satzung_label: Mapped[str] = mapped_column(String(120))
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    reservation: Mapped[Reservation] = relationship(back_populates="kurtaxe")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    actor: Mapped[str] = mapped_column(String(60), default="rezeption")
    action: Mapped[str] = mapped_column(String(60))
    entity: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(40), index=True)
    summary: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
