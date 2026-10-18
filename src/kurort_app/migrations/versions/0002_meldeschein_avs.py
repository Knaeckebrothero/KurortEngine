"""Record printing in AVS instead of producing local papers."""

import sqlalchemy as sa
from alembic import op

revision = "0002_meldeschein_avs"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("meldeschein_status", "reservation_guests", type_="check")
    op.execute(
        "UPDATE reservation_guests SET meldeschein_status = 'gedruckt' WHERE meldeschein_status = 'erzeugt'"
    )
    op.create_check_constraint(
        "meldeschein_status",
        "reservation_guests",
        "meldeschein_status IN ('offen', 'gedruckt', 'unterschrieben')",
    )
    op.alter_column(
        "reservation_guests", "meldeschein_generated_at", new_column_name="meldeschein_printed_at"
    )
    for column in (
        "meldeschein_pdf",
        "meldeschein_form_id",
        "kurkarte_code",
        "kurkarte_qr_payload",
        "kurkarte_issued_at",
    ):
        op.drop_column("reservation_guests", column)


def downgrade() -> None:
    for name, type_ in (
        ("meldeschein_pdf", sa.LargeBinary()),
        ("meldeschein_form_id", sa.String(64)),
        ("kurkarte_code", sa.String(64)),
        ("kurkarte_qr_payload", sa.Text()),
        ("kurkarte_issued_at", sa.DateTime(timezone=True)),
    ):
        op.add_column("reservation_guests", sa.Column(name, type_, nullable=True))
    op.alter_column(
        "reservation_guests", "meldeschein_printed_at", new_column_name="meldeschein_generated_at"
    )
    op.drop_constraint("meldeschein_status", "reservation_guests", type_="check")
    op.execute(
        "UPDATE reservation_guests SET meldeschein_status = 'erzeugt' WHERE meldeschein_status = 'gedruckt'"
    )
    op.create_check_constraint(
        "meldeschein_status",
        "reservation_guests",
        "meldeschein_status IN ('offen', 'erzeugt', 'unterschrieben')",
    )
