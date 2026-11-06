"""Imbauan bulanan ke grup warga menunggu persetujuan Pimpinan (keputusan 6 November 2026, 3A).

Mengubah keputusan 4 November 2026 (otomatis tanpa persetujuan) mengikuti dokumen mekanisme:
"Humas dapat menyampaikan imbauan agregat yang telah disetujui". Satu baris per bulan;
bot hanya mengirim bila bulannya sudah disetujui, dan /rekomendasi menolak bulan yang belum.

Revision ID: 0022
Revises: 0021
Create Date: 2026-11-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "advisory_approvals",
        sa.Column("approval_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("approval_id", name="pk_advisory_approvals"),
        sa.UniqueConstraint("month", name="uq_advisory_approvals_month"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.user_id"], name="fk_advisory_approvals_approved_by", ondelete="SET NULL"),
    )
    op.create_index("ix_advisory_approvals_approved_by", "advisory_approvals", ["approved_by"])


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_advisory_approvals_approved_by")
    op.drop_table("advisory_approvals")
