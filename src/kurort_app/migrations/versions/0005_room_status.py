"""Room cleaning status and last staff change."""

import sqlalchemy as sa
from alembic import op

revision = "0005_room_status"
down_revision = "0007_guest_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rooms",
        sa.Column("housekeeping_status", sa.String(16), nullable=False, server_default="clean"),
    )
    op.add_column("rooms", sa.Column("housekeeping_note", sa.String(200), nullable=True))
    op.add_column(
        "rooms", sa.Column("housekeeping_changed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("rooms", sa.Column("housekeeping_changed_by", sa.String(60), nullable=True))
    op.create_check_constraint(
        "room_housekeeping_status",
        "rooms",
        "housekeeping_status IN ('dirty', 'clean', 'inspected', 'out_of_order')",
    )


def downgrade() -> None:
    op.drop_constraint("room_housekeeping_status", "rooms", type_="check")
    for column in (
        "housekeeping_changed_by",
        "housekeeping_changed_at",
        "housekeeping_note",
        "housekeeping_status",
    ):
        op.drop_column("rooms", column)
