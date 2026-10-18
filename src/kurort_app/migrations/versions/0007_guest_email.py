"""Guest mail, safe compartments and the late-arrival lifecycle (schema only)."""

import sqlalchemy as sa
from alembic import op

revision = "0007_guest_email"
down_revision = "0006_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(40), nullable=False, unique=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("system", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_by", sa.String(60), nullable=False, server_default="rezeption"),
    )
    op.create_table(
        "email_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "reservation_id", sa.Integer(), sa.ForeignKey("reservations.id", ondelete="SET NULL")
        ),
        sa.Column("template_key", sa.String(40)),
        sa.Column("to_address", sa.String(160), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("transport", sa.String(8), nullable=False, server_default="log"),
        sa.Column("status", sa.String(10), nullable=False, server_default="queued"),
        sa.Column("error", sa.Text()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("created_by", sa.String(60), nullable=False, server_default="rezeption"),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("transport IN ('log', 'smtp')", name="email_transport"),
        sa.CheckConstraint("status IN ('queued', 'sent', 'failed', 'logged')", name="email_status"),
        sa.CheckConstraint("attempts >= 0", name="email_attempts"),
    )
    op.create_index("ix_email_messages_reservation_id", "email_messages", ["reservation_id"])
    op.create_index("ix_email_messages_status", "email_messages", ["status"])
    op.create_table(
        "safe_compartments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("label", sa.String(40), nullable=False, unique=True),
        sa.Column("fixed_pin", sa.String(8)),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint(
            "fixed_pin IS NULL OR fixed_pin ~ '^[0-9]{1,8}$'", name="safe_fixed_pin_digits"
        ),
    )
    op.create_table(
        "late_arrivals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "reservation_id",
            sa.Integer(),
            sa.ForeignKey("reservations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "compartment_id", sa.Integer(), sa.ForeignKey("safe_compartments.id"), nullable=False
        ),
        sa.Column("pin", sa.String(8)),
        sa.Column("key_in_safe", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("meldeschein_in_safe", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(16), nullable=False, server_default="vorbereitet"),
        sa.Column("email_message_id", sa.Integer(), sa.ForeignKey("email_messages.id")),
        sa.Column("phone_notified_at", sa.DateTime(timezone=True)),
        sa.Column(
            "prepared_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("prepared_by", sa.String(60), nullable=False, server_default="rezeption"),
        sa.Column("arrived_confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("meldeschein_returned_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('vorbereitet', 'angereist', 'abgeschlossen', 'abgebrochen', 'nicht_angereist')",
            name="late_arrival_status",
        ),
        sa.CheckConstraint("pin IS NULL OR pin ~ '^[0-9]{1,8}$'", name="late_arrival_pin_digits"),
    )
    op.create_index("ix_late_arrivals_status", "late_arrivals", ["status"])
    op.create_index(
        "uq_late_arrivals_open_compartment",
        "late_arrivals",
        ["compartment_id"],
        unique=True,
        postgresql_where=sa.text("status = 'vorbereitet'"),
    )


def downgrade() -> None:
    op.drop_table("late_arrivals")
    op.drop_table("safe_compartments")
    op.drop_table("email_messages")
    op.drop_table("email_templates")
