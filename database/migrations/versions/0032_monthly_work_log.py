"""Catatan mutu draf dan waktu kerja pada produk bulanan (Modul 5).

Naskah Taskap revisi: Tabel 4.17 menyebut isi Modul 5 Evaluasi "cakupan kejadian, mutu draf,
waktu kerja, dan catatan tindak lanjut"; Lampiran L huruf D merinci rubrik mutu draf (empat
unsur, skor 0–2, jumlah 8) dan cap waktu kerja. Cakupan dan tindak lanjut sudah ada; dua yang
lain disimpan di kolom JSONB `monthly_products.work_log` (kosong = belum dicatat).

Revision ID: 0032
Revises: 0031
Create Date: 2026-11-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "monthly_products",
        sa.Column(
            "work_log",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("monthly_products", "work_log")
