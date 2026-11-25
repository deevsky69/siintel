"""Rekap kriminalitas Polda Metro Jaya per Polres.

Keputusan pemilik proyek 25 November 2026 (catatan 196): aplikasi memuat data seluruh Polres
di Polda Metro Jaya dari rekap Pusiknas posisi 10 November 2026. Datanya agregat (CT dan CC
per satuan per tahun), disimpan satu paket per posisi data.

Revision ID: 0035
Revises: 0034
Create Date: 2026-11-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "polda_recaps",
        sa.Column(
            "recap_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("position_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(300), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("imported_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("recap_id", name="pk_polda_recaps"),
        sa.UniqueConstraint("position_at", name="uq_polda_recaps_position_at"),
        sa.ForeignKeyConstraint(
            ["imported_by"],
            ["users.user_id"],
            name="fk_polda_recaps_imported_by",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_polda_recaps_imported_by", "polda_recaps", ["imported_by"])


def downgrade() -> None:
    op.drop_index("ix_polda_recaps_imported_by", table_name="polda_recaps")
    op.drop_table("polda_recaps")
