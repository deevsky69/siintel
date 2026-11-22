"""Catatan pelaksanaan butir berkala SOP (migration 0034).

Naskah Taskap revisi, Lampiran I: beberapa ketentuan SOP berjadwal (data diterima paling lambat
tanggal 5, peta dan IKW terbit pada minggu pertama, catatan akses diperiksa tiap bulan,
pencadangan, laporan triwulan). Aplikasi tidak dapat MEMASTIKAN hal-hal itu terjadi di luar
dirinya; yang dapat dilakukannya adalah menyediakan tempat pejabat yang berwenang mencatat
bahwa butir itu sudah dikerjakan untuk satu periode — siapa, kapan, dengan catatan apa.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .base import uuid_pk


class SopCheck(Base):
    __tablename__ = "sop_checks"

    check_id: Mapped[uuid.UUID] = uuid_pk()
    #: YYYY-MM siklus bulanan yang dicatat.
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    item: Mapped[str] = mapped_column(String(40), nullable=False)
    done_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL")
    )
    done_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    note: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("period", "item", name="uq_sop_checks_period_item"),
        Index("ix_sop_checks_done_by", "done_by"),
    )
