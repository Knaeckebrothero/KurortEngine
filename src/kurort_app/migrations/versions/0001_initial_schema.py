"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-14 22:32:10.988850
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column(
            "at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("actor", sa.String(length=60), nullable=False),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("entity", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_events_at"), "audit_events", ["at"], unique=False)
    op.create_index(op.f("ix_audit_events_entity_id"), "audit_events", ["entity_id"], unique=False)
    op.create_table(
        "guests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("first_name", sa.String(length=80), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("nationality", sa.String(length=2), nullable=False),
        sa.Column("street", sa.String(length=160), nullable=True),
        sa.Column("postal_code", sa.String(length=16), nullable=True),
        sa.Column("city", sa.String(length=80), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("id_document_number", sa.String(length=40), nullable=True),
        sa.Column("disability_pct", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("number", sa.String(length=10), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("floor", sa.Integer(), nullable=False),
        sa.Column("max_occupancy", sa.Integer(), nullable=False),
        sa.Column("nightly_rate", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("features", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("number"),
    )
    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=True),
        sa.Column("arrival", sa.Date(), nullable=False),
        sa.Column("departure", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("eta", sa.Time(), nullable=True),
        sa.Column("rate_total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("package_code", sa.String(length=20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "channel IN ('direct', 'phone', 'email', 'booking.com', 'walk-in')",
            name="reservation_channel",
        ),
        sa.CheckConstraint(
            "status IN ('reserved', 'checked_in', 'checked_out', 'cancelled', 'no_show')",
            name="reservation_status",
        ),
        sa.CheckConstraint("departure > arrival", name="reservation_dates"),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["rooms.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_reservations_arrival"), "reservations", ["arrival"], unique=False)
    op.create_index(op.f("ix_reservations_departure"), "reservations", ["departure"], unique=False)
    op.create_index(op.f("ix_reservations_room_id"), "reservations", ["room_id"], unique=False)
    op.create_index(op.f("ix_reservations_status"), "reservations", ["status"], unique=False)
    op.create_table(
        "kurtaxe_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reservation_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("nights", sa.Integer(), nullable=False),
        sa.Column("breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("satzung_label", sa.String(length=120), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reservation_id"),
    )
    op.create_table(
        "reservation_guests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("reservation_id", sa.Integer(), nullable=False),
        sa.Column("guest_id", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("exemption_category", sa.String(length=32), nullable=True),
        sa.Column("exemption_evidence", sa.String(length=200), nullable=True),
        sa.Column("meldeschein_status", sa.String(length=16), nullable=False),
        sa.Column("meldeschein_form_id", sa.String(length=64), nullable=True),
        sa.Column("meldeschein_pdf", sa.LargeBinary(), nullable=True),
        sa.Column("meldeschein_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meldeschein_signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("kurkarte_code", sa.String(length=64), nullable=True),
        sa.Column("kurkarte_qr_payload", sa.Text(), nullable=True),
        sa.Column("kurkarte_issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "exemption_category IS NULL OR exemption_category IN ('geschaeftsreisender', 'schwerbehindert_100')",
            name="exemption_category",
        ),
        sa.CheckConstraint(
            "meldeschein_status IN ('offen', 'erzeugt', 'unterschrieben')",
            name="meldeschein_status",
        ),
        sa.ForeignKeyConstraint(
            ["guest_id"],
            ["guests.id"],
        ),
        sa.ForeignKeyConstraint(["reservation_id"], ["reservations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reservation_id", "guest_id"),
    )
    op.create_index(
        op.f("ix_reservation_guests_guest_id"), "reservation_guests", ["guest_id"], unique=False
    )
    op.create_index(
        op.f("ix_reservation_guests_reservation_id"),
        "reservation_guests",
        ["reservation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_reservation_guests_reservation_id"), table_name="reservation_guests")
    op.drop_index(op.f("ix_reservation_guests_guest_id"), table_name="reservation_guests")
    op.drop_table("reservation_guests")
    op.drop_table("kurtaxe_assessments")
    op.drop_index(op.f("ix_reservations_status"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_room_id"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_departure"), table_name="reservations")
    op.drop_index(op.f("ix_reservations_arrival"), table_name="reservations")
    op.drop_table("reservations")
    op.drop_table("rooms")
    op.drop_table("guests")
    op.drop_index(op.f("ix_audit_events_entity_id"), table_name="audit_events")
    op.drop_index(op.f("ix_audit_events_at"), table_name="audit_events")
    op.drop_table("audit_events")
