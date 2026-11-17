"""Langganan pemberitahuan wilayah oleh warga (migration 0025; naskah Taskap 4.7 b).

Warga yang MEMILIH menerima pemberitahuan mengetik `/langganan <kelurahan>` di percakapan
pribadinya dengan bot; imbauan bulanan kelurahan itu lalu dikirim ke percakapan tersebut.

DATA PRIBADI (CLAUDE.md §16). Pengenal percakapan (`chat_id`) pada WhatsApp memuat nomor
telepon, jadi ia data pribadi:

    tujuan          mengirim imbauan bulanan kelurahan yang dipilih warga itu sendiri
    isian minimum   kanal, pengenal percakapan, kelurahan — tanpa nama, tanpa alamat
    akses           hanya bot (kunci MESSAGING_API_KEY); tidak ada layar yang menampilkannya
    perlindungan    `/berhenti` MENGHAPUS barisnya, bukan menonaktifkan
    audit           berlangganan/berhenti dicatat tanpa pengenal percakapan

Satu percakapan hanya untuk satu kelurahan; berlangganan lagi menggantinya.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .base import TimestampMixin, uuid_pk

CHANNELS = ("WHATSAPP", "TELEGRAM")


class AreaSubscription(TimestampMixin, Base):
    __tablename__ = "area_subscriptions"

    subscription_id: Mapped[uuid.UUID] = uuid_pk()
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    kelurahan: Mapped[str] = mapped_column(String(100), nullable=False)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #: YYYY-MM imbauan terakhir yang terkirim; kosong = belum pernah.
    advisory_sent_month: Mapped[str | None] = mapped_column(String(7))

    __table_args__ = (
        UniqueConstraint("channel", "chat_id", name="uq_area_subscriptions_chat"),
        CheckConstraint("channel IN " + str(CHANNELS), name="area_subscription_channel_allowed"),
        Index("ix_area_subscriptions_kelurahan", "kelurahan"),
    )
