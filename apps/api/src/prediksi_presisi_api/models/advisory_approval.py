"""Persetujuan Pimpinan atas imbauan bulanan ke grup warga (migration 0022; keputusan 3A)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .base import uuid_pk


class AdvisoryApproval(Base):
    __tablename__ = "advisory_approvals"

    approval_id: Mapped[uuid.UUID] = uuid_pk()
    #: YYYY-MM bulan imbauan.
    month: Mapped[str] = mapped_column(String(7), nullable=False, unique=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (Index("ix_advisory_approvals_approved_by", "approved_by"),)
