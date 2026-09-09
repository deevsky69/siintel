"""Token klaim: cara pelapor melihat status laporannya sendiri.

Keputusan pemilik proyek, 9 September 2026 — menutup sebagian U-13.

MASALAH YANG DIPECAHKAN

    Spesifikasi §4 meminta pelapor dapat memeriksa status laporannya. Selama ini itu
    mustahil dilakukan dengan aman, dan alasannya bukan kemalasan:

    - Nomor tiket `RPT-0151` **berurut**, sehingga dapat ditebak. Endpoint yang hanya
      menuntut nomor tiket akan membocorkan status laporan siapa pun kepada siapa pun.
    - Sistem ini **sengaja tidak menyimpan identitas pelapor** (CLAUDE.md §16, docs/14 §3),
      sehingga tidak ada apa pun untuk mengikat hak baca — tidak ada akun, tidak ada nomor
      telepon, tidak ada apa-apa.

MENGAPA TOKEN, DAN MENGAPA HANYA HASH-NYA YANG DISIMPAN

    Token acak 256 bit diterbitkan sekali saat laporan dikirim, lalu disimpan di ponsel
    pelapor. Ia menjadi satu-satunya bukti kepemilikan — tanpa menyimpan sepotong pun
    identitas. Yang disimpan basis data hanyalah **hash**-nya, sehingga bocornya salinan
    basis data tidak memberi siapa pun hak membaca status laporan orang lain.

    SHA-256 polos, bukan bcrypt atau argon2. Keduanya dirancang melawan tebakan atas
    rahasia berentropi rendah — kata sandi manusia. Token di sini 256 bit acak; menebaknya
    mustahil, dan memperlambat verifikasi hanya membuat pemeriksaan status lambat tanpa
    menambah keamanan sedikit pun.

    Kolomnya NULLABLE: 150 laporan dummy yang sudah ada tidak punya token, dan tidak
    seharusnya punya — tidak ada pelapor sungguhan di baliknya. Laporan tanpa token
    dijawab sama dengan laporan yang tidak ada.

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "citizen_reports",
        sa.Column(
            "claim_token_hash",
            sa.String(64),
            nullable=True,
            comment=(
                "SHA-256 heksadesimal dari token klaim. Tokennya sendiri TIDAK PERNAH "
                "disimpan — ia hanya ada di ponsel pelapor, diterbitkan sekali saat "
                "laporan dikirim."
            ),
        ),
    )
    # Indeks pada hash-nya TIDAK dibuat: pencarian selalu lewat `code` yang sudah unik,
    # lalu hash-nya dibandingkan. Mencari lewat hash akan membuat token menjadi kunci
    # pencarian, dan itu mengundang pemeriksaan tanpa nomor tiket.


def downgrade() -> None:
    op.drop_column("citizen_reports", "claim_token_hash")
