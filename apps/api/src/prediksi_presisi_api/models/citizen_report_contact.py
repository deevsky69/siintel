"""Kontak pelapor pada kanal perpesanan (Telegram / WhatsApp) — keputusan pemilik proyek
8 Oktober 2026: identitas pelapor BOLEH disimpan untuk mengabari perkembangan laporannya.

INI PENGECUALIAN YANG DISENGAJA, DAN BATASNYA DITULIS DI SINI

Laporan masyarakat lewat web dan aplikasi tetap tanpa identitas (`citizen_reports` tidak
punya kolomnya, dan test menjaganya). Kanal perpesanan berbeda: bot selalu MELIHAT pengirim
— Telegram memberi `chat_id`, WhatsApp memberi nomor telepon — dan pemilik proyek memilih
memanfaatkannya agar pelapor menerima kabar ketika laporannya diverifikasi, diteruskan,
ditangani, atau ditutup. Mengikuti CLAUDE.md §16:

Tujuan: mengirim kabar perkembangan ke percakapan yang sama.
Field minimum: kanal + pengenal percakapan; TIDAK ada nama, nomor yang ditampilkan, foto profil.
Akses: hanya endpoint `/messaging/*` berkunci bersama untuk layanan bot; tidak ada endpoint
petugas yang mengembalikannya.
Perlindungan: tabel terpisah dari `citizen_reports`, satu baris per laporan, dapat dihapus
tanpa menyentuh laporannya.
Audit: pengiriman laporan mencatat `channel`; setiap kabar yang terkirim mencatat
`NOTIFY_CITIZEN_REPORTER`.

Pada WhatsApp `chat_id` adalah nomor telepon pengirim dalam format internasional — itu
data pribadi, dan karena itu tabel ini bukan bagian dari respons endpoint mana pun yang
dibaca peran di layar.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .citizen_report import CitizenReport

CHANNEL_TELEGRAM = "TELEGRAM"
CHANNEL_WHATSAPP = "WHATSAPP"
CHANNELS = (CHANNEL_TELEGRAM, CHANNEL_WHATSAPP)


class CitizenReportContact(TimestampMixin, Base):
    """Satu percakapan yang menunggu kabar atas satu laporan."""

    __tablename__ = "citizen_report_contacts"

    contact_id: Mapped[uuid.UUID] = uuid_pk()
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citizen_reports.report_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    #: Pengenal percakapan pada kanal itu: chat id Telegram, nomor WhatsApp.
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False)
    #: Status laporan yang terakhir dikabarkan ke percakapan ini. Kabar baru = status
    #: laporan sekarang berbeda dari ini. Diisi status awal saat laporan dibuat, karena
    #: tiketnya sudah disampaikan saat itu juga.
    last_notified_status: Mapped[str] = mapped_column(String(50), nullable=False)

    report: Mapped[CitizenReport] = relationship(back_populates="contact")

    __table_args__ = (
        CheckConstraint("channel IN " + str(CHANNELS), name="contact_channel_known"),
        Index("ix_citizen_report_contacts_chat", "channel", "chat_id"),
    )
