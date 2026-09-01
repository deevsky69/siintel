"""Keputusan komandan — `commander_decisions` (docs/02 §13).

Titik human-in-the-loop: AI mengusulkan, manusia memutuskan (CLAUDE.md §13).

`modified_text` menyimpan isi rekomendasi hasil modifikasi **tanpa menimpa** usulan asli
pada `recommendations.recommendation_text`, sehingga jejak "apa yang diusulkan sistem"
dan "apa yang diputuskan manusia" keduanya tetap utuh dan dapat diaudit.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .operational_action import OperationalAction
    from .rbac import User
    from .recommendation import Recommendation

#: Keputusan yang mungkin (CLAUDE.md §13, docs/05 §2.8). Menentukan boleh-tidaknya
#: sebuah tindakan operasional lahir, sehingga dikunci di database.
DECISIONS = ("APPROVED", "MODIFIED", "REJECTED")

#: Keputusan yang mengizinkan tindakan operasional dibuat.
DECISIONS_ALLOWING_ACTION = ("APPROVED", "MODIFIED")


class CommanderDecision(TimestampMixin, Base):
    """Keputusan pejabat berwenang atas sebuah rekomendasi."""

    __tablename__ = "commander_decisions"

    decision_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recommendations.recommendation_id", ondelete="RESTRICT"),
        nullable=False,
    )

    #: Wajib: keputusan operasional selalu punya pejabat yang bertanggung jawab.
    decision_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )

    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    decision_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    reason: Mapped[str | None] = mapped_column(Text)

    #: Isi rekomendasi setelah dimodifikasi komandan. Wajib bila decision = MODIFIED.
    modified_text: Mapped[str | None] = mapped_column(Text)

    recommendation: Mapped[Recommendation] = relationship(back_populates="decisions")
    decided_by: Mapped[User] = relationship()
    operational_actions: Mapped[list[OperationalAction]] = relationship(back_populates="decision")

    __table_args__ = (
        CheckConstraint(
            "decision IN ('APPROVED', 'MODIFIED', 'REJECTED')",
            name="decision_allowed",
        ),
        # U-07: modifikasi tanpa isi baru tidak bermakna, dan menimpa usulan asli dilarang.
        CheckConstraint(
            "decision <> 'MODIFIED' OR modified_text IS NOT NULL",
            name="modified_needs_text",
        ),
        Index("ix_commander_decisions_recommendation", "recommendation_id"),
        Index("ix_commander_decisions_decision", "decision"),
        Index("ix_commander_decisions_decided_at", "decision_at"),
        Index("ix_commander_decisions_decision_by", "decision_by"),
    )
