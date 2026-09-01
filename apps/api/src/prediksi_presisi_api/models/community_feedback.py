"""Umpan balik masyarakat — `community_feedback` (docs/02 §8)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .citizen_report import CitizenReport


class CommunityFeedback(TimestampMixin, Base):
    """Tanggapan masyarakat atas sebuah laporan."""

    __tablename__ = "community_feedback"

    feedback_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citizen_reports.report_id", ondelete="RESTRICT"),
        nullable=False,
    )

    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)

    report: Mapped[CitizenReport] = relationship(back_populates="feedback")

    __table_args__ = (
        Index("ix_community_feedback_report", "report_id"),
        Index("ix_community_feedback_status", "status"),
    )
