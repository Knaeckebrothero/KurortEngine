"""Shared app installations and JSONB records.

Revision ID: 0003_app_platform
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_app_platform"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_installations",
        sa.Column("slug", sa.String(40), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "installed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("installed_by", sa.String(60), nullable=False),
    )
    op.create_table(
        "app_records",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("app_slug", sa.String(40), nullable=False),
        sa.Column("collection", sa.String(40), nullable=False),
        sa.Column("data", JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("out_of_range", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("definition_version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("created_by", sa.String(60), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.Column("updated_by", sa.String(60)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_by", sa.String(60)),
    )
    op.create_index("ix_app_records_scope", "app_records", ["app_slug", "collection", "deleted_at"])
    op.create_index("ix_app_records_created_at", "app_records", ["created_at"])
    op.create_index(
        "ix_app_records_data",
        "app_records",
        ["data"],
        postgresql_using="gin",
        postgresql_ops={"data": "jsonb_path_ops"},
    )


def downgrade() -> None:
    op.drop_table("app_records")
    op.drop_table("app_installations")
