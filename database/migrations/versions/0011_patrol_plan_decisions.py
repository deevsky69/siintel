"""Keputusan Pimpinan atas rencana patroli tahunan — `patrol_plan_decisions`.

Permintaan pemilik proyek, 4 Oktober 2026 (lanjutan rencana patroli): "usulan kepada
Pimpinan" harus benar-benar dapat diputus di aplikasi — disetujui, diubah, atau ditolak —
dan meninggalkan jejak yang dapat diaudit (CLAUDE.md §13, §29).

MENGAPA TABEL SENDIRI, BUKAN `commander_decisions`

    `commander_decisions` memutus SATU rekomendasi harian yang menunjuk satu prediksi.
    Rencana patroli adalah SATU pernyataan untuk setahun yang memuat puluhan slot, dan
    usulannya tidak disimpan — ia dihitung dari data saat dibuka. Memaksanya ke tabel
    rekomendasi berarti mengarang prediksi palsu sebagai induknya.

MENGAPA USULAN DISALIN SAAT DIPUTUS (`plan_snapshot`)

    Usulan dihitung ulang dari data; bila data berubah (koreksi impor, kejadian baru
    diinput), usulan yang dibuka besok dapat berbeda dari yang diputus hari ini. Keputusan
    harus menunjuk apa yang BENAR-BENAR dibaca Pimpinan saat memutus — bukan apa yang
    sistem hitung belakangan. Prinsipnya sama dengan `original_recommendation` pada
    keputusan harian (U-07).

MENGAPA RIWAYAT, BUKAN SATU BARIS YANG DITIMPA

    Rencana dapat diputus ulang (misalnya setelah kapasitas satuan berubah). Yang berlaku
    adalah keputusan TERAKHIR untuk tahun dan cakupan yang sama; keputusan sebelumnya tidak
    dihapus, karena jejak keputusan yang dapat disunting bukan bukti (CLAUDE.md §29).

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "patrol_plan_decisions",
        sa.Column(
            "decision_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("target_year", sa.Integer(), nullable=False),
        sa.Column(
            "scope",
            sa.String(100),
            nullable=True,
            comment="Polsek bila keputusan dibatasi wilayah; NULL = seluruh Polres.",
        ),
        sa.Column("plan_version", sa.String(50), nullable=False),
        sa.Column(
            "plan_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Usulan persis seperti yang dibaca pemutus saat memutus (U-07).",
        ),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "kept_slots",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment=(
                "Slot yang dipertahankan bila MODIFIED: [{threat_type, kelurahan, block_start}]."
            ),
        ),
        sa.Column("decision_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "decision_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "decision IN ('APPROVED', 'MODIFIED', 'REJECTED')",
            name="decision_allowed",
        ),
        sa.CheckConstraint(
            "decision <> 'MODIFIED' OR kept_slots IS NOT NULL",
            name="modified_needs_kept_slots",
        ),
        sa.CheckConstraint(
            "decision <> 'REJECTED' OR reason IS NOT NULL",
            name="rejected_needs_reason",
        ),
        sa.ForeignKeyConstraint(
            ["decision_by"],
            ["users.user_id"],
            name="fk_patrol_plan_decisions_decision_by",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("decision_id", name="pk_patrol_plan_decisions"),
        sa.UniqueConstraint("code", name="uq_patrol_plan_decisions_code"),
    )
    op.create_index(
        "ix_patrol_plan_decisions_year_scope",
        "patrol_plan_decisions",
        ["target_year", "scope", "decision_at"],
    )
    op.create_index(
        "ix_patrol_plan_decisions_decision_by", "patrol_plan_decisions", ["decision_by"]
    )
    op.execute(
        "CREATE TRIGGER trg_patrol_plan_decisions_set_updated_at BEFORE UPDATE ON "
        "patrol_plan_decisions FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_patrol_plan_decisions_set_updated_at ON patrol_plan_decisions"
    )
    op.drop_index("ix_patrol_plan_decisions_decision_by", table_name="patrol_plan_decisions")
    op.drop_index("ix_patrol_plan_decisions_year_scope", table_name="patrol_plan_decisions")
    op.drop_table("patrol_plan_decisions")
