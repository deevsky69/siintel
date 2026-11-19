"""Isian dampak pada laporan kejadian — dasar unsur D pada IKW.

Naskah Taskap final Bab IV B.4.2 dan Lampiran 9: Indeks Kerawanan Wilayah memakai frekuensi
(F), DAMPAK (D), dan keberulangan antarbulan (T). Dampak dinilai dari isian yang diperiksa
petugas terhadap sumbernya:

    loss_status      kerugian atau kerusakan: PRESENT / NONE / UNKNOWN
    injury_level     NONE / INJURY / SEVERE / DEATH / UNKNOWN
    impact_source    rujukan laporan polisi atau keterangan resmi
    impact_status    VERIFIED / PENDING / NEEDS_CLARIFICATION (NULL = belum diisi)
    impact_verified_by, impact_verified_at

Seluruh kolom nullable; tidak ada baris yang diubah. Data Pusiknas tidak memuat dampak, jadi
sampai diisi petugas IKW kelurahan yang punya kejadian berstatus "ditahan".

Revision ID: 0028
Revises: 0027
Create Date: 2026-11-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "crime_incidents"
CHECKS = {
    "impact_loss_allowed": "loss_status IS NULL OR loss_status IN ('PRESENT', 'NONE', 'UNKNOWN')",
    "impact_injury_allowed": (
        "injury_level IS NULL OR injury_level IN ('NONE', 'INJURY', 'SEVERE', 'DEATH', 'UNKNOWN')"
    ),
    "impact_status_allowed": (
        "impact_status IS NULL OR impact_status IN ('VERIFIED', 'PENDING', 'NEEDS_CLARIFICATION')"
    ),
}


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("loss_status", sa.String(20)))
    op.add_column(TABLE, sa.Column("injury_level", sa.String(20)))
    op.add_column(TABLE, sa.Column("impact_source", sa.String(200)))
    op.add_column(TABLE, sa.Column("impact_status", sa.String(30)))
    op.add_column(TABLE, sa.Column("impact_verified_by", postgresql.UUID(as_uuid=True)))
    op.add_column(TABLE, sa.Column("impact_verified_at", sa.DateTime(timezone=True)))
    op.create_foreign_key(
        "fk_crime_incidents_impact_verified_by",
        TABLE,
        "users",
        ["impact_verified_by"],
        ["user_id"],
        ondelete="SET NULL",
    )
    for name, clause in CHECKS.items():
        op.create_check_constraint(name, TABLE, clause)
    op.create_index("ix_crime_incidents_impact_verified_by", TABLE, ["impact_verified_by"])


def downgrade() -> None:
    op.drop_index("ix_crime_incidents_impact_verified_by", table_name=TABLE)
    for name in CHECKS:
        op.drop_constraint(name, TABLE, type_="check")
    op.drop_constraint("fk_crime_incidents_impact_verified_by", TABLE, type_="foreignkey")
    for column in (
        "impact_verified_at",
        "impact_verified_by",
        "impact_status",
        "impact_source",
        "injury_level",
        "loss_status",
    ):
        op.drop_column(TABLE, column)
