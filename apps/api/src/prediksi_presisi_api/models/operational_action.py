"""Tindakan operasional — `operational_actions` (docs/02 §14).

Tindakan hanya boleh lahir dari keputusan komandan berstatus `APPROVED` atau `MODIFIED`.
Aturan itu ditegakkan **di database** lewat trigger (lihat migration `0006` dan docs/06 §3),
bukan hanya di lapisan aplikasi: inilah invarian yang menjamin AI tidak pernah langsung
memerintahkan tindakan operasional (CLAUDE.md §13).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .commander_decision import CommanderDecision
    from .location import Location
    from .police_unit import PoliceUnit
    from .rbac import User


class OperationalAction(TimestampMixin, Base):
    """Penugasan lapangan yang lahir dari keputusan komandan."""

    __tablename__ = "operational_actions"

    action_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commander_decisions.decision_id", ondelete="RESTRICT"),
        nullable=False,
    )
    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("police_units.unit_id", ondelete="RESTRICT"),
        nullable=False,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.location_id", ondelete="RESTRICT"),
        nullable=False,
    )

    #: Petugas yang membuat penugasan (ERD: USERS ||--o{ OPERATIONAL_ACTIONS : creates).
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="RESTRICT"),
    )

    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: PLANNED / ACTIVE / COMPLETED / CANCELLED.
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    result: Mapped[str | None] = mapped_column(Text)

    decision: Mapped[CommanderDecision] = relationship(back_populates="operational_actions")
    unit: Mapped[PoliceUnit] = relationship(back_populates="operational_actions")
    location: Mapped[Location] = relationship(back_populates="operational_actions")
    creator: Mapped[User | None] = relationship()

    __table_args__ = (
        CheckConstraint(
            "end_at IS NULL OR end_at > start_at",
            name="time_order",
        ),
        Index("ix_operational_actions_decision", "decision_id"),
        Index("ix_operational_actions_unit", "unit_id"),
        Index("ix_operational_actions_status", "status"),
        Index("ix_operational_actions_start_at", "start_at"),
        Index("ix_operational_actions_location", "location_id"),
        Index("ix_operational_actions_created_by", "created_by"),
    )
