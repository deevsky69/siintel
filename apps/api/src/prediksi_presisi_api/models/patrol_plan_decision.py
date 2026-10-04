"""Keputusan Pimpinan atas rencana patroli tahunan — `patrol_plan_decisions` (migration 0011).

Titik human-in-the-loop bagi rencana tahunan: sistem mengusulkan slot patroli dari pola
tahun dasar, Pimpinan menyetujui, mengubah (memilih sebagian slot), atau menolaknya.
Usulan yang dibaca saat memutus disalin ke `plan_snapshot` (U-07), dan setiap keputusan
adalah baris baru — yang berlaku adalah yang terakhir untuk tahun dan cakupan yang sama.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .rbac import User

#: Keputusan yang mungkin — sama dengan keputusan harian (CLAUDE.md §13).
DECISIONS = ("APPROVED", "MODIFIED", "REJECTED")


class PatrolPlanDecision(TimestampMixin, Base):
    """Satu keputusan atas usulan rencana patroli satu tahun sasaran."""

    __tablename__ = "patrol_plan_decisions"

    decision_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    target_year: Mapped[int] = mapped_column(Integer, nullable=False)
    #: Polsek bila keputusan dibatasi wilayah; None = seluruh Polres.
    scope: Mapped[str | None] = mapped_column(String(100))
    plan_version: Mapped[str] = mapped_column(String(50), nullable=False)
    #: Usulan persis seperti yang dibaca pemutus saat memutus.
    plan_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    #: Slot yang dipertahankan bila MODIFIED: [{threat_type, kelurahan, block_start}].
    kept_slots: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    decision_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    decision_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    decided_by: Mapped[User] = relationship()

    __table_args__ = (
        CheckConstraint(
            "decision IN ('APPROVED', 'MODIFIED', 'REJECTED')",
            name="decision_allowed",
        ),
        CheckConstraint(
            "decision <> 'MODIFIED' OR kept_slots IS NOT NULL",
            name="modified_needs_kept_slots",
        ),
        CheckConstraint(
            "decision <> 'REJECTED' OR reason IS NOT NULL",
            name="rejected_needs_reason",
        ),
        Index("ix_patrol_plan_decisions_year_scope", "target_year", "scope", "decision_at"),
        Index("ix_patrol_plan_decisions_decision_by", "decision_by"),
    )
