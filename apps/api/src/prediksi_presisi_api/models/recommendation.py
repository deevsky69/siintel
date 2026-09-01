"""Rekomendasi tindakan — `recommendations` (docs/02 §12).

Rekomendasi adalah **opsi**, bukan perintah. Tidak boleh langsung menjadi tindakan
operasional; wajib melewati keputusan komandan (CLAUDE.md §13, §14).

`status` di sini adalah **cerminan** keputusan terakhir pada `commander_decisions`
(dibuat pada TASK 014) dan hanya boleh diubah oleh proses yang menulis keputusan tersebut.
Sumber kebenaran keputusan tetap `commander_decisions` (docs/02 §12).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .commander_decision import CommanderDecision
    from .early_warning import EarlyWarning
    from .prediction import Prediction


class Recommendation(TimestampMixin, Base):
    """Satu opsi tindakan yang diusulkan sistem untuk sebuah prediksi."""

    __tablename__ = "recommendations"

    recommendation_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    prediction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("predictions.prediction_id", ondelete="RESTRICT"),
        nullable=False,
    )

    #: Peringatan yang menyertai, bila rekomendasi lahir dari sebuah peringatan.
    warning_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("early_warnings.warning_id", ondelete="RESTRICT"),
    )

    #: SAMAPTA / BINMAS / INTELKAM / RESKRIM / LANTAS (CLAUDE.md §14).
    recommended_function: Mapped[str] = mapped_column(String(50), nullable=False)

    recommendation_text: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str | None] = mapped_column(String(30))

    #: PENDING_REVIEW / APPROVED / MODIFIED / REJECTED.
    status: Mapped[str] = mapped_column(String(30), nullable=False)

    prediction: Mapped[Prediction] = relationship(back_populates="recommendations")
    warning: Mapped[EarlyWarning | None] = relationship(back_populates="recommendations")
    decisions: Mapped[list[CommanderDecision]] = relationship(back_populates="recommendation")

    __table_args__ = (
        Index("ix_recommendations_status", "status"),
        Index("ix_recommendations_prediction", "prediction_id"),
        Index("ix_recommendations_function", "recommended_function"),
    )
