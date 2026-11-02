"""Buletin mingguan kelurahan (tahap 3, 2 November 2026).

Disusun sistem dari minggu sebelumnya (kejadian per jenis di kelurahan, imbauan yang
berlaku, rekomendasi yang disetujui Pimpinan), **disetujui manusia** sebelum terkirim ke
grup kelurahan — ia penerbitan informasi kepada masyarakat, sama seperti imbauan, sehingga
yang menyetujui adalah pemegang `bulletin:approve` (Pimpinan). Bot mengirim yang berstatus
APPROVED, lalu menandai SENT beserta hasil tiap kanal.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .base import TimestampMixin, uuid_pk

STATUS_DRAFT = "DRAFT"
STATUS_APPROVED = "APPROVED"
STATUS_SENT = "SENT"
STATUSES = (STATUS_DRAFT, STATUS_APPROVED, STATUS_SENT)


class Bulletin(TimestampMixin, Base):
    __tablename__ = "bulletins"

    bulletin_id: Mapped[uuid.UUID] = uuid_pk()
    #: Senin minggu yang DILAPORKAN (buletin berisi minggu ini, terbit minggu berikutnya).
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    kelurahan: Mapped[str] = mapped_column(String(100), nullable=False)
    kecamatan: Mapped[str] = mapped_column(String(100), nullable=False)
    polsek: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    #: Angka yang menjadi dasar teks, supaya dapat diperiksa tanpa membaca ulang teksnya.
    figures: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=STATUS_DRAFT)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="RESTRICT")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: Hasil pengiriman per kanal: {"telegram": "ok"|"gagal: …", "whatsapp": …}
    delivery: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("week_start", "kelurahan", name="uq_bulletins_week_kelurahan"),
        CheckConstraint("status IN " + str(STATUSES), name="bulletin_status_allowed"),
        Index("ix_bulletins_status", "status"),
        Index("ix_bulletins_approved_by", "approved_by"),
    )
