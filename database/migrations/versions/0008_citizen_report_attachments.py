"""Lokasi tepat dan lampiran pada laporan masyarakat.

Keputusan pemilik proyek, 8 September 2026. Ini **keputusan kebijakan**, bukan teknis:
sistem ini sejak awal sengaja tidak menyimpan identitas, dan lokasi laporan warga sengaja
dibatasi sebatas kecamatan (`docs/14` §3). Keduanya ditembus di sini, dengan syarat.

DUA HAL YANG BERUBAH

1. **Koordinat tepat.** Kolom `latitude`/`longitude` sudah ada dan selama ini diisi titik
   pusat kecamatan. Kini ia dapat berisi titik yang dibagikan pelapor — dan karena kedua
   hal itu terlihat sama sebagai sepasang angka, `coordinate_source` menyatakan yang mana.
   Tanpa kolom itu, peta akan menggambar titik pusat kecamatan seolah tempat kejadian.

2. **Lampiran foto, suara, dan video.** Berkasnya TIDAK disimpan di basis data melainkan di
   cakram; tabel ini hanya menyimpan keterangannya. Alasannya bukan ukuran melainkan
   penghapusan: berkas yang habis masa retensinya harus benar-benar hilang dari cakram, dan
   kolom `bytea` yang di-`UPDATE` menjadi NULL meninggalkan salinannya di WAL dan di
   cadangan sampai entah kapan.

SYARAT YANG MENYERTAI KEPUTUSAN ITU

- Metadata berkas (EXIF, termasuk koordinat GPS bawaan kamera) **dilucuti saat unggah**.
  `metadata_stripped_with` mencatat alatnya, sehingga klaim itu dapat diperiksa.
- Berkas dihapus **90 hari setelah laporan selesai**. `purged_at` menandai kapan.
- Hanya peran yang berwenang memverifikasi yang boleh membukanya (ditegakkan di router).

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-08
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: Dari mana koordinat sebuah laporan berasal.
#:
#: Dibatasi CHECK, bukan sekadar disepakati di kode: nilai yang salah di sini membuat peta
#: menggambarkan titik pusat kecamatan sebagai tempat kejadian, dan kesalahan semacam itu
#: tidak menimbulkan galat apa pun — ia hanya berbohong dengan tenang.
COORDINATE_SOURCES = ("KECAMATAN_CENTROID", "REPORTER_GPS")

#: Jenis lampiran yang diterima. Bukan tipe MIME — itu disimpan terpisah dan lebih rinci.
ATTACHMENT_KINDS = ("IMAGE", "AUDIO", "VIDEO")


def upgrade() -> None:
    op.add_column(
        "citizen_reports",
        sa.Column(
            "coordinate_source",
            sa.String(30),
            nullable=False,
            server_default="KECAMATAN_CENTROID",
        ),
    )
    op.add_column(
        "citizen_reports",
        sa.Column(
            "gps_accuracy_m",
            sa.Numeric(7, 1),
            nullable=True,
            comment="Ketelitian yang dilaporkan peranti, dalam meter. NULL bila bukan GPS.",
        ),
    )
    # Kapan laporan dinyatakan selesai. Diperlukan retensi lampiran: janji "90 hari setelah
    # laporan selesai" harus tahu kapan ia selesai.
    #
    # `updated_at` TIDAK dapat dipakai untuk itu. Ia dikelola trigger dan berubah pada setiap
    # penyuntingan apa pun, sehingga satu perbaikan ejaan pada laporan lama akan memundurkan
    # penghapusan berkasnya tiga bulan lagi — diam-diam, tanpa ada yang memutuskannya.
    op.add_column(
        "citizen_reports",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "coordinate_source_known",
        "citizen_reports",
        "coordinate_source IN " + str(COORDINATE_SOURCES),
    )
    # Ketelitian hanya bermakna bagi titik yang datang dari peranti pelapor. Mengisinya
    # untuk titik pusat kecamatan akan menyatakan ketelitian yang tidak pernah diukur.
    op.create_check_constraint(
        "gps_accuracy_only_for_gps",
        "citizen_reports",
        "gps_accuracy_m IS NULL OR coordinate_source = 'REPORTER_GPS'",
    )

    op.create_table(
        "citizen_report_attachments",
        sa.Column(
            "attachment_id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "report_id",
            UUID(as_uuid=True),
            # CASCADE: lampiran tidak punya arti tanpa laporannya, dan meninggalkannya
            # sebagai baris yatim berarti menyimpan berkas yang tidak seorang pun tahu
            # mengapa masih ada.
            sa.ForeignKey("citizen_reports.report_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("media_type", sa.String(100), nullable=False),
        sa.Column("byte_size", sa.BigInteger, nullable=False),
        sa.Column(
            "sha256",
            sa.String(64),
            nullable=False,
            comment=(
                "Ringkasan berkas SETELAH metadata dilucuti — "
                "yang tersimpan, bukan yang diunggah."
            ),
        ),
        sa.Column(
            "storage_key",
            sa.String(255),
            nullable=False,
            unique=True,
            comment="Nama berkas di direktori lampiran. Acak, bukan nama asli dari pelapor.",
        ),
        sa.Column(
            "metadata_stripped_with",
            sa.String(30),
            nullable=False,
            comment="Alat pelucut metadata, agar klaim 'EXIF dibuang' dapat diperiksa.",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "purged_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Kapan berkasnya dihapus dari cakram karena masa retensi habis.",
        ),
        sa.CheckConstraint("kind IN " + str(ATTACHMENT_KINDS), name="attachment_kind_known"),
        sa.CheckConstraint("byte_size > 0", name="attachment_size_positive"),
    )
    op.create_index(
        "ix_citizen_report_attachments_report_id", "citizen_report_attachments", ["report_id"]
    )
    # Tugas retensi mencari lampiran yang BELUM dihapus. Indeks parsial menjaga pencarian
    # itu tetap murah meski tabelnya penuh baris yang sudah dibersihkan.
    op.create_index(
        "ix_citizen_report_attachments_pending_purge",
        "citizen_report_attachments",
        ["created_at"],
        postgresql_where=sa.text("purged_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_citizen_report_attachments_pending_purge", "citizen_report_attachments")
    op.drop_index("ix_citizen_report_attachments_report_id", "citizen_report_attachments")
    op.drop_table("citizen_report_attachments")
    op.drop_constraint("gps_accuracy_only_for_gps", "citizen_reports", type_="check")
    op.drop_constraint("coordinate_source_known", "citizen_reports", type_="check")
    op.drop_column("citizen_reports", "closed_at")
    op.drop_column("citizen_reports", "gps_accuracy_m")
    op.drop_column("citizen_reports", "coordinate_source")
