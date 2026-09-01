"""Layer risiko prediktif — `predictions` (docs/02 §10).

Perkiraan untuk jendela waktu **ke depan**, membawa `risk_score` dan `confidence` sendiri.
Menjadi satu-satunya sumber `early_warnings` dan `recommendations` (docs/04).

`dominant_factors` wajib terisi: setiap prediksi harus dapat menjelaskan WHY dari mekanisme
yang benar-benar dipakai, dan `source` membedakan hasil rule dari hasil model
(CLAUDE.md §10, §27). Penjelasan fiktif dilarang.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .early_warning import EarlyWarning
    from .location import Location
    from .prediction_actual import PredictionActual
    from .recommendation import Recommendation
    from .risk_score import RiskScore

#: Horizon prediksi sesuai docs/01 §5.5.
FORECAST_HORIZONS = ("6H", "12H", "24H", "3D", "7D")


class Prediction(TimestampMixin, Base):
    """Satu prediksi: wilayah + jendela waktu + jenis ancaman."""

    __tablename__ = "predictions"

    prediction_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    prediction_date: Mapped[date] = mapped_column(Date, nullable=False)

    #: Jarak dari prediction_date ke awal jendela yang diprediksi.
    forecast_horizon: Mapped[str] = mapped_column(String(10), nullable=False)

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
    confidence: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    #: Daftar objek {factor, contribution, source} dengan source ∈ {RULE, MODEL}.
    dominant_factors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)

    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    #: Penelusuran opsional ke penilaian risiko berjalan yang menjadi acuan.
    baseline_risk_score_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("risk_scores.risk_score_id", ondelete="RESTRICT"),
    )

    #: DRAFT / PUBLISHED / VALIDATED. Taksonomi status belum final (U-16), tidak dikunci CHECK.
    status: Mapped[str] = mapped_column(String(30), nullable=False)

    location: Mapped[Location] = relationship(back_populates="predictions")
    baseline_risk_score: Mapped[RiskScore | None] = relationship()
    early_warnings: Mapped[list[EarlyWarning]] = relationship(back_populates="prediction")
    recommendations: Mapped[list[Recommendation]] = relationship(back_populates="prediction")
    evaluations: Mapped[list[PredictionActual]] = relationship(back_populates="prediction")

    __table_args__ = (
        UniqueConstraint(
            "location_id",
            "threat_type",
            "window_start",
            "forecast_horizon",
            "model_version",
            "prediction_date",
            name="uq_predictions_forecast",
        ),
        CheckConstraint("risk_score BETWEEN 0 AND 100", name="risk_score_range"),
        CheckConstraint("confidence BETWEEN 0 AND 100", name="confidence_range"),
        CheckConstraint("window_end > window_start", name="window_order"),
        CheckConstraint(
            "forecast_horizon IN ('6H', '12H', '24H', '3D', '7D')",
            name="forecast_horizon_allowed",
        ),
        Index("ix_predictions_prediction_date", "prediction_date"),
        Index("ix_predictions_location_window", "location_id", "window_start"),
        Index("ix_predictions_status", "status"),
    )
