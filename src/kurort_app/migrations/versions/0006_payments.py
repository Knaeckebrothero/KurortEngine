"""Payment methods and received/deferred payments (schema only)."""

import sqlalchemy as sa
from alembic import op

revision = "0006_payments"
down_revision = "0003_app_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_methods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("label", sa.String(60), nullable=False),
        sa.Column("deferred", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "reservation_id",
            sa.Integer(),
            sa.ForeignKey("reservations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("method_id", sa.Integer(), sa.ForeignKey("payment_methods.id"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("received_on", sa.Date()),
        sa.Column("payer", sa.String(120)),
        sa.Column("note", sa.String(200)),
        sa.Column("recorded_by", sa.String(60), nullable=False),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_by", sa.String(60)),
        sa.Column("cancel_reason", sa.String(200)),
        sa.CheckConstraint("amount > 0", name="payment_amount"),
    )
    op.create_index("ix_payments_reservation_id", "payments", ["reservation_id"])


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("payment_methods")
