"""Shared persistence for declarative apps; uninstalling never drops records."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from kurort_app.db import Base


class AppInstallation(Base):
    __tablename__ = "app_installations"

    slug: Mapped[str] = mapped_column(String(40), primary_key=True)
    version: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    installed_by: Mapped[str] = mapped_column(String(60))


class AppRecord(Base):
    __tablename__ = "app_records"
    __table_args__ = (
        Index("ix_app_records_scope", "app_slug", "collection", "deleted_at"),
        Index("ix_app_records_created_at", "created_at"),
        Index(
            "ix_app_records_data",
            "data",
            postgresql_using="gin",
            postgresql_ops={"data": "jsonb_path_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    app_slug: Mapped[str] = mapped_column(String(40))
    collection: Mapped[str] = mapped_column(String(40))
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    out_of_range: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    definition_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(60))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_by: Mapped[str | None] = mapped_column(String(60))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[str | None] = mapped_column(String(60))
