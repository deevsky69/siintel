"""Permintaan bantuan darurat dari aplikasi warga — `panic_events` (migration 0012).

Keputusan pemilik proyek 8 Oktober 2026: tombol darurat di aplikasi Android warga, yang
otomatis memberi tahu akun Administrator, Polsek, dan Pimpinan. Sampai hari itu kanal ini
sengaja tidak dibuat (lihat `app/(app)/panic/page.tsx` versi lama): yang kurang bukan
teknik, melainkan KOMITMEN RESPONS — siapa menerima, dalam berapa lama, apa yang terjadi
bila tidak ada yang menjawab. Penerimanya kini ditetapkan; waktu tanggap dan eskalasinya
masih PROPOSED (docs/01 §19.2) dan layar menyatakan 110 tetap jalur resmi.

TANPA IDENTITAS, seperti laporan masyarakat: tidak ada kolom nama/telepon. Yang disimpan
hanya titik peranti (bila ada), kelurahan terdekat, catatan singkat, dan jejak siapa yang
menerima serta menutup.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .location import Location
    from .rbac import User

STATUS_OPEN = "OPEN"
STATUS_ACKNOWLEDGED = "ACKNOWLEDGED"
STATUS_CLOSED = "CLOSED"
STATUSES = (STATUS_OPEN, STATUS_ACKNOWLEDGED, STATUS_CLOSED)


class PanicEvent(TimestampMixin, Base):
    """Satu penekanan tombol darurat."""

    __tablename__ = "panic_events"

    event_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    #: Waktu sebenarnya saat tombol ditekan — bukan waktu acuan peragaan: permintaan
    #: bantuan tidak boleh ikut "mundur" ke tanggal peragaan.
    pressed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    geom: Mapped[object | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    accuracy_m: Mapped[float | None] = mapped_column(Numeric(8, 1))
    #: Kelurahan terdekat dari titik peranti; kosong bila tidak ada titik.
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.location_id", ondelete="RESTRICT")
    )
    note: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=STATUS_OPEN)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="RESTRICT")
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="RESTRICT")
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closing_note: Mapped[str | None] = mapped_column(Text)

    location: Mapped[Location | None] = relationship()
    acknowledger: Mapped[User | None] = relationship(foreign_keys=[acknowledged_by])
    closer: Mapped[User | None] = relationship(foreign_keys=[closed_by])

    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'ACKNOWLEDGED', 'CLOSED')", name="panic_status_allowed"
        ),
        CheckConstraint(
            "(latitude IS NULL) = (longitude IS NULL)", name="panic_coordinates_paired"
        ),
        Index("ix_panic_events_status_pressed", "status", "pressed_at"),
        Index("ix_panic_events_location", "location_id"),
        Index("ix_panic_events_acknowledged_by", "acknowledged_by"),
        Index("ix_panic_events_closed_by", "closed_by"),
    )
