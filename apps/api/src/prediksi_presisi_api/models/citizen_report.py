"""Laporan masyarakat — `citizen_reports` (docs/02 §6).

Laporan masyarakat **tidak otomatis dianggap fakta**; wajib melewati verifikasi
(`verification_score`, `status`) sebelum dipakai sebagai dasar tindakan.

Identitas/kontak pelapor dan lampiran bukti **tidak** disimpan pada PoC
(CLAUDE.md §16, U-13 — menunggu keputusan kebijakan).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from .community_feedback import CommunityFeedback
    from .location import Location


#: Dari mana koordinat sebuah laporan berasal. Cerminan CHECK pada migrasi 0008.
COORDINATE_SOURCE_CENTROID = "KECAMATAN_CENTROID"
COORDINATE_SOURCE_GPS = "REPORTER_GPS"
COORDINATE_SOURCES = (COORDINATE_SOURCE_CENTROID, COORDINATE_SOURCE_GPS)

#: Jenis lampiran. Cerminan CHECK pada migrasi 0008.
ATTACHMENT_KINDS = ("IMAGE", "AUDIO", "VIDEO")


class CitizenReport(TimestampMixin, Base):
    """Satu laporan dari masyarakat."""

    __tablename__ = "citizen_reports"

    report_id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    #: Kapan laporan masuk.
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    #: Kapan kejadian menurut pelapor. Boleh kosong bila pelapor tidak mengetahuinya.
    incident_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    geom: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=False
    )

    #: Nullable: laporan masuk dengan koordinat bebas dan baru dipetakan ke grid
    #: setelah geo-processing (docs/02 §6).
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.location_id", ondelete="RESTRICT"),
    )

    location_text: Mapped[str | None] = mapped_column(String(255))

    urgency_score: Mapped[int | None] = mapped_column(SmallInteger)
    verification_score: Mapped[int | None] = mapped_column(SmallInteger)

    status: Mapped[str] = mapped_column(String(50), nullable=False)

    #: Dari mana koordinat di atas berasal.
    #:
    #: Sepasang angka lintang/bujur tidak menyatakan asal-usulnya. Titik pusat kecamatan dan
    #: titik yang dibagikan pelapor terlihat persis sama, padahal yang pertama berjarak
    #: kilometer dari tempat kejadian. Tanpa kolom ini peta menggambar keduanya sebagai
    #: "tempat kejadian" dan tidak seorang pun dapat membedakannya.
    coordinate_source: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="KECAMATAN_CENTROID"
    )

    #: Ketelitian yang dilaporkan peranti pelapor, dalam meter. NULL bila bukan dari GPS.
    gps_accuracy_m: Mapped[float | None] = mapped_column(Numeric(7, 1))

    #: Kapan laporan dinyatakan selesai. Dari sinilah masa retensi lampiran dihitung.
    #:
    #: Sengaja terpisah dari `updated_at`, yang dikelola trigger dan berubah pada setiap
    #: penyuntingan apa pun. Memakai `updated_at` berarti satu perbaikan ejaan pada laporan
    #: lama memundurkan penghapusan berkasnya tiga bulan lagi, tanpa ada yang memutuskannya.
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    #: SHA-256 heksadesimal dari token klaim — satu-satunya cara pelapor membuktikan laporan
    #: ini miliknya, pada sistem yang sengaja tidak menyimpan identitas siapa pun.
    #:
    #: Tokennya sendiri TIDAK PERNAH tersimpan di sini: ia diterbitkan sekali saat laporan
    #: dikirim dan hanya ada di ponsel pelapor. Menyimpan hash-nya berarti salinan basis
    #: data yang bocor tidak memberi siapa pun hak membaca status laporan orang lain.
    #:
    #: NULL untuk 150 laporan dummy, dan itu benar — tidak ada pelapor sungguhan di
    #: baliknya. Laporan tanpa token dijawab sama dengan laporan yang tidak ada.
    claim_token_hash: Mapped[str | None] = mapped_column(String(64))

    location: Mapped[Location | None] = relationship(back_populates="citizen_reports")
    feedback: Mapped[list[CommunityFeedback]] = relationship(back_populates="report")
    attachments: Mapped[list[CitizenReportAttachment]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "urgency_score IS NULL OR (urgency_score BETWEEN 0 AND 100)",
            name="urgency_score_range",
        ),
        CheckConstraint(
            "verification_score IS NULL OR (verification_score BETWEEN 0 AND 100)",
            name="verification_score_range",
        ),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
        CheckConstraint(
            "coordinate_source IN " + str(COORDINATE_SOURCES), name="coordinate_source_known"
        ),
        CheckConstraint(
            "gps_accuracy_m IS NULL OR coordinate_source = 'REPORTER_GPS'",
            name="gps_accuracy_only_for_gps",
        ),
        Index("ix_citizen_reports_reported_at", "reported_at"),
        Index("ix_citizen_reports_status", "status"),
        Index("ix_citizen_reports_location", "location_id"),
        Index("ix_citizen_reports_geom", "geom", postgresql_using="gist"),
    )


class CitizenReportAttachment(Base):
    """Satu lampiran pada laporan masyarakat — foto, rekaman suara, atau video.

    **Berkasnya tidak ada di sini.** Baris ini hanya keterangan; isinya di cakram, dirujuk
    lewat `storage_key`. Pemisahan itu disengaja: berkas yang habis masa retensinya harus
    benar-benar hilang, sedangkan kolom `bytea` yang di-`UPDATE` menjadi NULL meninggalkan
    salinannya di WAL dan di cadangan sampai entah kapan.

    `sha256` diambil dari berkas **setelah** metadata dilucuti — yang benar-benar tersimpan,
    bukan yang diunggah. Ringkasan atas berkas yang sudah tidak ada tidak membuktikan apa pun.
    """

    __tablename__ = "citizen_report_attachments"

    attachment_id: Mapped[uuid.UUID] = uuid_pk()
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citizen_reports.report_id", ondelete="CASCADE"),
        nullable=False,
    )

    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    media_type: Mapped[str] = mapped_column(String(100), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    #: Alat pelucut metadata, supaya klaim "EXIF dibuang" dapat diperiksa dan bukan sekadar
    #: dipercaya. Nilainya `pillow` untuk gambar, `ffmpeg` untuk suara dan video.
    metadata_stripped_with: Mapped[str] = mapped_column(String(30), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    #: Kapan berkasnya dihapus dari cakram. Barisnya sengaja dipertahankan: jejak bahwa
    #: pernah ada lampiran, dan kapan ia dimusnahkan, adalah bagian dari pertanggungjawaban.
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    report: Mapped[CitizenReport] = relationship(back_populates="attachments")

    @property
    def is_available(self) -> bool:
        return self.purged_at is None

    __table_args__ = (
        CheckConstraint("kind IN " + str(ATTACHMENT_KINDS), name="attachment_kind_known"),
        CheckConstraint("byte_size > 0", name="attachment_size_positive"),
        Index("ix_citizen_report_attachments_report_id", "report_id"),
        # Indeks parsial: tugas retensi hanya mencari lampiran yang BELUM dihapus, dan
        # pencarian itu harus tetap murah meski tabelnya penuh baris yang sudah dibersihkan.
        Index(
            "ix_citizen_report_attachments_pending_purge",
            "created_at",
            postgresql_where=text("purged_at IS NULL"),
        ),
    )
