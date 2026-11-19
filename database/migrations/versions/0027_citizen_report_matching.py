"""Pencocokan laporan warga dengan kejadian resmi (Modul 1 naskah Taskap).

Naskah Bab IV 4.1 "Pencocokan antarkanal": sistem mengusulkan pasangan laporan yang mungkin
merujuk peristiwa yang sama; analis memutuskan kecocokannya dan alasannya dicatat. Laporan
yang cocok DITAUTKAN pada kejadian resmi sehingga satu peristiwa terhitung sekali; laporan
terverifikasi yang tidak punya padanan resmi menjadi "kejadian tambahan terverifikasi".

Lima kolom pada `citizen_reports`:

    matched_incident_id   kejadian resmi yang ditautkan (NULL bila tidak cocok / belum diputus)
    match_decision        MATCHED / NOT_MATCHED; NULL = belum diputus
    match_reason          alasan keputusan — wajib diisi oleh endpoint
    matched_by, matched_at

Tidak ada baris yang diubah.

Revision ID: 0027
Revises: 0026
Create Date: 2026-11-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "citizen_reports"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("matched_incident_id", postgresql.UUID(as_uuid=True)))
    op.add_column(TABLE, sa.Column("match_decision", sa.String(20)))
    op.add_column(TABLE, sa.Column("match_reason", sa.Text()))
    op.add_column(TABLE, sa.Column("matched_by", postgresql.UUID(as_uuid=True)))
    op.add_column(TABLE, sa.Column("matched_at", sa.DateTime(timezone=True)))
    op.create_foreign_key(
        "fk_citizen_reports_matched_incident_id",
        TABLE,
        "crime_incidents",
        ["matched_incident_id"],
        ["incident_id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_citizen_reports_matched_by",
        TABLE,
        "users",
        ["matched_by"],
        ["user_id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "match_decision_allowed",
        TABLE,
        "match_decision IS NULL OR match_decision IN ('MATCHED', 'NOT_MATCHED')",
    )
    op.create_check_constraint(
        "matched_needs_incident",
        TABLE,
        "match_decision IS DISTINCT FROM 'MATCHED' OR matched_incident_id IS NOT NULL",
    )
    op.create_index("ix_citizen_reports_matched_incident_id", TABLE, ["matched_incident_id"])
    op.create_index("ix_citizen_reports_matched_by", TABLE, ["matched_by"])


def downgrade() -> None:
    op.drop_index("ix_citizen_reports_matched_by", table_name=TABLE)
    op.drop_index("ix_citizen_reports_matched_incident_id", table_name=TABLE)
    op.drop_constraint("matched_needs_incident", TABLE, type_="check")
    op.drop_constraint("match_decision_allowed", TABLE, type_="check")
    op.drop_constraint("fk_citizen_reports_matched_by", TABLE, type_="foreignkey")
    op.drop_constraint("fk_citizen_reports_matched_incident_id", TABLE, type_="foreignkey")
    for column in (
        "matched_at",
        "matched_by",
        "match_reason",
        "match_decision",
        "matched_incident_id",
    ):
        op.drop_column(TABLE, column)
