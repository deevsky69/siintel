"""Layer risiko berjalan — `risk_scores` (docs/02 §9).

`risk_scores` adalah penilaian risiko **kondisi berjalan** per
(lokasi × jendela waktu × jenis ancaman × tanggal penilaian).
Menjadi sumber layer *Current Risk* pada peta (CLAUDE.md §24, TASK 082).

**Bukan** tahap antara antara prediction dan early warning — lihat docs/04.

Bobot faktor tidak disimpan di sini maupun di kode: `risk_score = round(Σ(bobot × faktor))`
dengan bobot dari `config/risk/`, dan versinya dicatat pada `weights_version`.
Nilai bobot final belum ditetapkan (U-02), sehingga hubungan itu **belum** dijadikan
CHECK constraint (docs/06 §3).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .location import Location

#: Kolom faktor penyusun risiko (docs/02 §9).
RISK_FACTORS = (
    "historical_factor",
    "recent_trend_factor",
    "temporal_factor",
    "spatial_factor",
    "context_factor",
)


class RiskScore(TimestampMixin, Base):
    """Penilaian risiko berjalan pada satu wilayah dan jendela waktu."""

    __tablename__ = "risk_scores"

    risk_score_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    assessment_date: Mapped[date] = mapped_column(Date, nullable=False)

    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.location_id", ondelete="RESTRICT"),
        nullable=False,
    )

    threat_type: Mapped[str] = mapped_column(String(50), nullable=False)

    #: Label jendela waktu untuk tampilan; batasnya pada window_start/window_end.
    time_window: Mapped[str | None] = mapped_column(String(50))
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    risk_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    #: LOW / MODERATE / HIGH / CRITICAL. Batas antar kelas belum ditetapkan (U-01),
    #: sehingga tidak dikunci CHECK.
    risk_class: Mapped[str] = mapped_column(String(20), nullable=False)

    historical_factor: Mapped[int | None] = mapped_column(SmallInteger)
    recent_trend_factor: Mapped[int | None] = mapped_column(SmallInteger)
    temporal_factor: Mapped[int | None] = mapped_column(SmallInteger)
    spatial_factor: Mapped[int | None] = mapped_column(SmallInteger)
    context_factor: Mapped[int | None] = mapped_column(SmallInteger)

    #: Versi bobot dari config/risk/ yang dipakai menghitung risk_score.
    weights_version: Mapped[str | None] = mapped_column(String(50))
    model_version: Mapped[str | None] = mapped_column(String(50))

    location: Mapped[Location] = relationship(back_populates="risk_scores")

    __table_args__ = (
        UniqueConstraint(
            "location_id",
            "threat_type",
            "window_start",
            "assessment_date",
            name="uq_risk_scores_assessment",
        ),
        CheckConstraint("risk_score BETWEEN 0 AND 100", name="risk_score_range"),
        CheckConstraint("window_end > window_start", name="window_order"),
        *(
            CheckConstraint(
                f"{factor} IS NULL OR ({factor} BETWEEN 0 AND 100)",
                name=f"{factor}_range",
            )
            for factor in RISK_FACTORS
        ),
        Index("ix_risk_scores_assessment_date", "assessment_date"),
        Index("ix_risk_scores_location_window", "location_id", "window_start"),
    )
