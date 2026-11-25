"""Rekap kriminalitas Polda Metro Jaya per Polres (migration 0035).

Data AGREGAT dari Pusiknas — jumlah Laporan Polisi (CT) dan penyelesaian (CC) per satuan per
tahun, bukan data per kejadian. Satu baris per POSISI DATA; isinya disimpan utuh sebagai JSONB
karena ini tabel acuan yang hanya dibaca dan selalu diganti satu paket, bukan data yang
disaring atau digabung per baris. Posisi terbaru yang ditampilkan.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .base import uuid_pk


class PoldaRecap(Base):
    __tablename__ = "polda_recaps"

    recap_id: Mapped[uuid.UUID] = uuid_pk()
    #: Posisi data menurut sumber (mis. 10 November 2026 pukul 17.19 WIB).
    position_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(300), nullable=False)
    #: SHA-256 berkas sumber, untuk menelusuri angka di layar ke berkasnya.
    source_sha256: Mapped[str | None] = mapped_column(String(64))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    imported_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL")
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("position_at", name="uq_polda_recaps_position_at"),
        Index("ix_polda_recaps_imported_by", "imported_by"),
    )
