"""Seminar rooms and independent day bookings."""

import sqlalchemy as sa
from alembic import op

revision = "0004_seminar_room"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "function_spaces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("price_half_day", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_full_day", sa.Numeric(10, 2), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("capacity > 0", name="function_space_capacity"),
    )
    op.create_table(
        "space_bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("space_id", sa.Integer(), sa.ForeignKey("function_spaces.id"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("slot", sa.String(12), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="angefragt"),
        sa.Column("organizer_name", sa.String(160), nullable=False),
        sa.Column("company", sa.String(160)),
        sa.Column("email", sa.String(160)),
        sa.Column("phone", sa.String(40)),
        sa.Column("attendees", sa.Integer(), nullable=False),
        sa.Column("catering_coffee", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("catering_lunch", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("catering_drinks", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("catering_note", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("price_manual", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "reservation_id", sa.Integer(), sa.ForeignKey("reservations.id", ondelete="SET NULL")
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("cancel_reason", sa.Text()),
        sa.CheckConstraint("end_date >= start_date", name="space_booking_dates"),
        sa.CheckConstraint(
            "slot IN ('vormittag', 'nachmittag', 'ganztags')", name="space_booking_slot"
        ),
        sa.CheckConstraint(
            "status IN ('angefragt', 'bestaetigt', 'storniert')", name="space_booking_status"
        ),
        sa.CheckConstraint("attendees > 0", name="space_booking_attendees"),
    )
    op.create_index("ix_space_bookings_space_id", "space_bookings", ["space_id"])
    op.create_index("ix_space_bookings_space_start", "space_bookings", ["space_id", "start_date"])


def downgrade() -> None:
    op.drop_table("space_bookings")
    op.drop_table("function_spaces")
