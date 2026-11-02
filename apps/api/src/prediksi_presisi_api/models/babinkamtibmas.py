"""Babinkamtibmas per kelurahan — kontak yang ditampilkan kepada warga (keputusan pemilik
proyek 2 November 2026, butir 5, 7, 8): **nomor dinas**, dikelola Administrator, data dummy
berlabel sampai data resmi diisi. Satu baris per kelurahan.

Kolom grup (Telegram chat id, tautan grup WhatsApp) adalah tujuan buletin mingguan kelurahan
(tahap 3): Telegram dikirimi langsung oleh bot; WhatsApp dikirim ke nomor Babin secara
perorangan karena API resmi tidak menjangkau grup.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .base import TimestampMixin, uuid_pk


class Babinkamtibmas(TimestampMixin, Base):
    __tablename__ = "babinkamtibmas"

    babin_id: Mapped[uuid.UUID] = uuid_pk()
    kelurahan: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    kecamatan: Mapped[str] = mapped_column(String(100), nullable=False)
    polsek: Mapped[str] = mapped_column(String(100), nullable=False)
    rank: Mapped[str | None] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    #: Nomor DINAS yang boleh ditampilkan ke warga (keputusan pemilik proyek), bentuk tampil.
    phone_display: Mapped[str] = mapped_column(String(32), nullable=False)
    #: Chat id grup Telegram kelurahan (negatif untuk grup); kosong = belum ada grup.
    telegram_chat_id: Mapped[str | None] = mapped_column(String(32))
    #: Tautan undangan grup WhatsApp kelurahan, untuk ditampilkan — bukan untuk dikirimi.
    whatsapp_group_link: Mapped[str | None] = mapped_column(String(200))
    #: Nomor WhatsApp Babin (internasional, tanpa +) untuk dikirimi buletin perorangan.
    whatsapp_number: Mapped[str | None] = mapped_column(String(20))
    is_dummy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_babinkamtibmas_kecamatan", "kecamatan"),
        Index("ix_babinkamtibmas_polsek", "polsek"),
    )
