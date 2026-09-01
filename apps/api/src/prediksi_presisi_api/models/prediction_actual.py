"""Evaluasi prediksi vs kejadian nyata — `prediction_actual` (docs/02 §15).

`prediction_id` **nullable** dan `match_type` menerima `FALSE_NEGATIVE`, sehingga kejadian
aktual yang **tidak** diprediksi tetap dapat direpresentasikan. Tanpa itu, false negative
tidak terlihat dan recall tidak dapat dihitung — persyaratan CLAUDE.md §26.

Aturan integritas:
- `HIT` / `FALSE_POSITIVE` → `prediction_id` wajib terisi;
- `FALSE_NEGATIVE` → `prediction_id` NULL dan `actual_incident_id` wajib terisi.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .crime_incident import CrimeIncident
    from .location import Location
    from .prediction import Prediction

#: Hasil pencocokan prediksi dengan kejadian nyata. Menentukan perhitungan
#: precision/recall, sehingga dikunci di database.
MATCH_TYPES = ("HIT", "FALSE_POSITIVE", "FALSE_NEGATIVE")


class PredictionActual(TimestampMixin, Base):
    """Satu baris evaluasi.

    Mewakili prediksi yang terbukti (`HIT`), prediksi yang meleset (`FALSE_POSITIVE`),
    atau kejadian nyata yang sama sekali tidak diprediksi (`FALSE_NEGATIVE`).
    """

    __tablename__ = "prediction_actual"

    evaluation_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    evaluation_date: Mapped[date] = mapped_column(Date, nullable=False)

    #: NULL untuk false negative — kejadian yang tidak diprediksi sama sekali.
    prediction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("predictions.prediction_id", ondelete="RESTRICT"),
    )

    #: Kejadian nyata yang dievaluasi. Wajib untuk false negative.
    actual_incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("crime_incidents.incident_id", ondelete="RESTRICT"),
    )

    actual_event: Mapped[bool] = mapped_column(Boolean, nullable=False)
    actual_threat_type: Mapped[str | None] = mapped_column(String(50))

    actual_location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.location_id", ondelete="RESTRICT"),
    )

    actual_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    match_type: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    prediction: Mapped[Prediction | None] = relationship(back_populates="evaluations")
    actual_incident: Mapped[CrimeIncident | None] = relationship(back_populates="evaluations")
    actual_location: Mapped[Location | None] = relationship()

    __table_args__ = (
        CheckConstraint(
            "match_type IN ('HIT', 'FALSE_POSITIVE', 'FALSE_NEGATIVE')",
            name="match_type_allowed",
        ),
        CheckConstraint(
            "(match_type IN ('HIT', 'FALSE_POSITIVE') AND prediction_id IS NOT NULL)"
            " OR (match_type = 'FALSE_NEGATIVE' AND prediction_id IS NULL"
            " AND actual_incident_id IS NOT NULL)",
            name="match_type_consistency",
        ),
        CheckConstraint(
            "actual_window_end IS NULL OR actual_window_start IS NULL"
            " OR actual_window_end > actual_window_start",
            name="window_order",
        ),
        Index("ix_prediction_actual_evaluation_date", "evaluation_date"),
        Index("ix_prediction_actual_match_type", "match_type"),
        Index("ix_prediction_actual_prediction", "prediction_id"),
    )
