"""Catatan pelaksanaan butir berkala SOP (Kalender SOP).

Keputusan pemilik proyek 22 November 2026 (catatan 192): ketentuan berjadwal pada SOP
(naskah Taskap revisi, Lampiran I) — data diterima paling lambat tanggal 5, catatan akses
diperiksa tiap bulan, pencadangan diperiksa, laporan triwulan — sebelumnya hanya ditampilkan.
Tabel `sop_checks` menyimpan pernyataan pejabat yang berwenang bahwa satu butir sudah
dikerjakan untuk satu periode: satu baris per (periode, butir).

Revision ID: 0034
Revises: 0033
Create Date: 2026-11-22
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sop_checks",
        sa.Column(
            "check_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("item", sa.String(40), nullable=False),
        sa.Column("done_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "done_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("check_id", name="pk_sop_checks"),
        sa.UniqueConstraint("period", "item", name="uq_sop_checks_period_item"),
        sa.ForeignKeyConstraint(
            ["done_by"], ["users.user_id"], name="fk_sop_checks_done_by", ondelete="SET NULL"
        ),
    )
    op.create_index("ix_sop_checks_done_by", "sop_checks", ["done_by"])


def downgrade() -> None:
    op.drop_index("ix_sop_checks_done_by", table_name="sop_checks")
    op.drop_table("sop_checks")
