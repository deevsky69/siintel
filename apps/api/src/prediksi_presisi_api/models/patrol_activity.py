"""Kegiatan patroli — `patrol_activity` (docs/02 §5)."""

from __future__ import annotations

import uuid
from datetime import date, time
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .location import Location
    from .police_unit import PoliceUnit


class PatrolActivity(TimestampMixin, Base):
    """Kegiatan patroli oleh satu unit pada satu wilayah dan rentang waktu."""

    __tablename__ = "patrol_activity"

    patrol_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

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

    patrol_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)

    activity_type: Mapped[str | None] = mapped_column(String(100))
    result: Mapped[str | None] = mapped_column(String(255))

    unit: Mapped[PoliceUnit] = relationship(back_populates="patrol_activities")
    location: Mapped[Location] = relationship(back_populates="patrol_activities")

    __table_args__ = (
        Index("ix_patrol_activity_patrol_date", "patrol_date"),
        Index("ix_patrol_activity_location", "location_id"),
        Index("ix_patrol_activity_unit", "unit_id"),
    )
