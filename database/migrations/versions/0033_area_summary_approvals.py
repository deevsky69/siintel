"""Persetujuan Humas atas ringkasan wilayah untuk masyarakat.

Keputusan pemilik proyek 21 November 2026: ringkasan wilayah di SIGAP BERSAMA disamakan
dengan naskah Taskap revisi (Lampiran K huruf I: "Humas menyajikan ringkasan wilayah yang
disetujui"). Sebelum ini ringkasan terbit otomatis dari data.

Tabel `area_summary_approvals`: satu baris per periode (bulan terakhir jendela dua belas
bulan). Selama periode berjalan belum disetujui, `GET /public/areas/summary` hanya mengirim
daftar wilayah — tanpa angka, tingkat kerawanan, maupun rincian per jenis.

TIDAK ada persetujuan yang dibuatkan migrasi: setelah naik, halaman warga menampilkan
keterangan "menunggu persetujuan Humas" sampai akun Humas menyetujuinya.

Revision ID: 0033
Revises: 0032
Create Date: 2026-11-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "area_summary_approvals",
        sa.Column(
            "approval_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "approved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("approval_id", name="pk_area_summary_approvals"),
        sa.UniqueConstraint("period", name="uq_area_summary_approvals_period"),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.user_id"],
            name="fk_area_summary_approvals_approved_by",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_area_summary_approvals_approved_by", "area_summary_approvals", ["approved_by"]
    )


def downgrade() -> None:
    op.drop_index("ix_area_summary_approvals_approved_by", table_name="area_summary_approvals")
    op.drop_table("area_summary_approvals")
