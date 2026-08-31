"""Kejadian kriminal — `crime_incidents` (docs/02 §3).

Tidak menyimpan identitas korban/pelaku/saksi (CLAUDE.md §16, docs/02 K-10).
Kolom wilayah tidak diduplikasi di sini; diperoleh lewat join ke `locations` (docs/02 K-8).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .location import Location


class CrimeIncident(TimestampMixin, Base):
    """Satu kejadian yang dilaporkan/ditangani."""

    __tablename__ = "crime_incidents"

    incident_id: Mapped[uuid.UUID] = uuid_pk()

    #: ID anonim pada dataset dummy, mis. "INC-00001"
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    #: CURANMOR / CURAT / CURAS / TAWURAN / KEJAHATAN_JALANAN — taksonomi final menunggu U-16.
    incident_type: Mapped[str] = mapped_column(String(50), nullable=False)

    #: Waktu kejadian sebagai satu nilai (UTC). Sumber kebenaran untuk query rentang waktu.
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    #: Dipertahankan untuk agregasi harian dan analisis jam rawan (docs/02 §3).
    incident_date: Mapped[date] = mapped_column(Date, nullable=False)
    incident_time: Mapped[time] = mapped_column(Time, nullable=False)

    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.location_id", ondelete="RESTRICT"),
        nullable=False,
    )

    location_type: Mapped[str | None] = mapped_column(String(100))
    modus: Mapped[str | None] = mapped_column(String(100))
    target_type: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str | None] = mapped_column(String(50))

    location: Mapped[Location] = relationship(back_populates="crime_incidents")

    __table_args__ = (
        Index("ix_crime_incidents_occurred_at", "occurred_at"),
        Index("ix_crime_incidents_location_occurred", "location_id", "occurred_at"),
        Index("ix_crime_incidents_incident_type", "incident_type"),
    )
