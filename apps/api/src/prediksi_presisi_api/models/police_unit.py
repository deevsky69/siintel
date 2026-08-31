"""Satuan/unit kepolisian — `police_units` (docs/02 §2)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .patrol_activity import PatrolActivity


class PoliceUnit(TimestampMixin, Base):
    """Unit pelaksana kegiatan (patroli, penindakan, pembinaan)."""

    __tablename__ = "police_units"

    unit_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    #: SAMAPTA / BINMAS / INTELKAM / RESKRIM / LANTAS — daftar final menunggu U-16.
    function: Mapped[str] = mapped_column(String(50), nullable=False)

    unit_name: Mapped[str] = mapped_column(String(150), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)

    patrol_activities: Mapped[list[PatrolActivity]] = relationship(back_populates="unit")

    __table_args__ = (
        Index("ix_police_units_function", "function"),
        Index("ix_police_units_jurisdiction", "jurisdiction"),
    )
