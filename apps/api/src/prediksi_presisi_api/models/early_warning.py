"""Peringatan dini — `early_warnings` (docs/02 §11).

Terbit ketika skor risiko sebuah prediksi melewati threshold yang **dikonfigurasi**
(`config/risk/warning-thresholds.yaml`), bukan yang di-hardcode (CLAUDE.md §12).
Threshold final belum ditetapkan (U-01); yang disimpan hanya `threshold_version`.

`severity`, `risk_score`, `threat_type`, dan `location_id` merupakan **snapshot** dari
prediksi sumber pada saat peringatan dibuat, sehingga riwayat peringatan tidak berubah
ketika prediksi diperbarui.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .location import Location
    from .prediction import Prediction
    from .public_alert import PublicAlert
    from .rbac import User
    from .recommendation import Recommendation


class EarlyWarning(TimestampMixin, Base):
    """Peringatan dini yang diturunkan dari sebuah prediksi."""

    __tablename__ = "early_warnings"

    warning_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    prediction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("predictions.prediction_id", ondelete="RESTRICT"),
        nullable=False,
    )

    #: LOW / WATCH / WARNING / CRITICAL — batas antar level belum ditetapkan (U-01).
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    threat_type: Mapped[str] = mapped_column(String(50), nullable=False)

    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.location_id", ondelete="RESTRICT"),
        nullable=False,
    )

    time_window: Mapped[str | None] = mapped_column(String(50))
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    risk_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    confidence: Mapped[int | None] = mapped_column(SmallInteger)

    #: ACTIVE / ACKNOWLEDGED / RESOLVED.
    status: Mapped[str] = mapped_column(String(30), nullable=False)

    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="RESTRICT"),
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="RESTRICT"),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: Versi threshold dari config/risk/ yang memicu peringatan ini.
    threshold_version: Mapped[str | None] = mapped_column(String(50))

    prediction: Mapped[Prediction] = relationship(back_populates="early_warnings")
    location: Mapped[Location] = relationship(back_populates="early_warnings")
    acknowledger: Mapped[User | None] = relationship(foreign_keys=[acknowledged_by])
    resolver: Mapped[User | None] = relationship(foreign_keys=[resolved_by])
    public_alerts: Mapped[list[PublicAlert]] = relationship(back_populates="warning")
    recommendations: Mapped[list[Recommendation]] = relationship(back_populates="warning")

    __table_args__ = (
        CheckConstraint("risk_score BETWEEN 0 AND 100", name="risk_score_range"),
        CheckConstraint(
            "confidence IS NULL OR (confidence BETWEEN 0 AND 100)",
            name="confidence_range",
        ),
        CheckConstraint("window_end > window_start", name="window_order"),
        CheckConstraint(
            "acknowledged_at IS NULL OR acknowledged_by IS NOT NULL",
            name="acknowledged_needs_actor",
        ),
        CheckConstraint(
            "resolved_at IS NULL OR resolved_by IS NOT NULL",
            name="resolved_needs_actor",
        ),
        Index("ix_early_warnings_status_created", "status", "created_at"),
        Index("ix_early_warnings_location", "location_id"),
        Index("ix_early_warnings_prediction", "prediction_id"),
    )
