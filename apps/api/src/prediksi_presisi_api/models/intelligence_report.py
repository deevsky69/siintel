"""Laporan intelijen — `intelligence_reports` (docs/02 §4)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .location import Location


class IntelligenceReport(TimestampMixin, Base):
    """Indikasi/kerawanan yang dilaporkan fungsi intelijen."""

    __tablename__ = "intelligence_reports"

    intelligence_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.location_id", ondelete="RESTRICT"),
        nullable=False,
    )

    #: Skala kepercayaan sumber (A/B/C pada dataset dummy).
    reliability: Mapped[str | None] = mapped_column(String(10))

    confidence: Mapped[int | None] = mapped_column(SmallInteger)
    urgency: Mapped[int | None] = mapped_column(SmallInteger)
    impact: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str | None] = mapped_column(String(50))

    location: Mapped[Location] = relationship(back_populates="intelligence_reports")

    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence BETWEEN 0 AND 100)",
            name="ck_intelligence_reports_confidence_range",
        ),
        CheckConstraint(
            "urgency IS NULL OR (urgency BETWEEN 0 AND 100)",
            name="ck_intelligence_reports_urgency_range",
        ),
        Index("ix_intelligence_reports_report_date", "report_date"),
        Index("ix_intelligence_reports_location", "location_id"),
    )
