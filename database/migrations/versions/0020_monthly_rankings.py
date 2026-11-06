"""Modul 2–3 mekanisme: peringkat bulanan 65 kelurahan yang DISIMPAN sebelum bulan berjalan.

Dokumen: "Simpan peringkat, periode sasaran, batas data, dan versi model sebelum bulan
berjalan." Satu baris `monthly_rankings` per (bulan sasaran, metode, cakupan); isinya 65
baris `monthly_ranking_rows` berurutan (seri: nama kelurahan). Permission `ranking:read`
(semua peran) dan `ranking:manage` (Administrator; Analis Intelkam menyusul pada tahap 3).

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)
NEW_PERMISSIONS = {
    ("ranking", "read"): "Membaca peringkat bulanan kelurahan",
    ("ranking", "manage"): "Menyusun dan membekukan peringkat bulanan",
}
GRANTS = {
    "Pimpinan": {"ALL": ["ranking:read"]},
    "Fungsi": {"ALL": ["ranking:read"]},
    "Polsek": {"ALL": ["ranking:read"]},
    "Administrator": {"ALL": ["ranking:read", "ranking:manage"]},
}


def upgrade() -> None:
    op.create_table(
        "monthly_rankings",
        sa.Column("ranking_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("target_month", sa.Date(), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("data_cutoff", sa.Date(), nullable=False),
        sa.Column("model_version", sa.String(60), nullable=False),
        sa.Column("basis_from", sa.Date(), nullable=False),
        sa.Column("basis_to", sa.Date(), nullable=False),
        sa.Column("pending_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("generated_at", TS, nullable=False),
        sa.Column("generated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("ranking_id", name="pk_monthly_rankings"),
        sa.UniqueConstraint("target_month", "method", "scope", name="uq_monthly_rankings_month_method_scope"),
        sa.ForeignKeyConstraint(["generated_by"], ["users.user_id"], name="fk_monthly_rankings_generated_by", ondelete="SET NULL"),
        sa.CheckConstraint("method IN ('HISTORY_3M', 'HISTORY_12M', 'MODEL')", name="monthly_ranking_method_allowed"),
        sa.CheckConstraint("scope IN ('ALL_3C', 'VEHICLE')", name="monthly_ranking_scope_allowed"),
    )
    op.create_index("ix_monthly_rankings_target_month", "monthly_rankings", ["target_month"])
    op.create_index("ix_monthly_rankings_generated_by", "monthly_rankings", ["generated_by"])
    op.execute("CREATE TRIGGER trg_monthly_rankings_set_updated_at BEFORE UPDATE ON monthly_rankings FOR EACH ROW EXECUTE FUNCTION set_updated_at()")

    op.create_table(
        "monthly_ranking_rows",
        sa.Column("row_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("ranking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("kelurahan", sa.String(100), nullable=False),
        sa.Column("kecamatan", sa.String(100), nullable=False),
        sa.Column("polsek", sa.String(100), nullable=False),
        sa.Column("predicted_count", sa.Numeric(8, 2), nullable=False),
        sa.Column("ikw", sa.Numeric(5, 1), nullable=True),
        sa.Column("ikw_category", sa.String(10), nullable=True),
        sa.Column("basis", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.PrimaryKeyConstraint("row_id", name="pk_monthly_ranking_rows"),
        sa.UniqueConstraint("ranking_id", "kelurahan", name="uq_monthly_ranking_rows_kelurahan"),
        sa.UniqueConstraint("ranking_id", "rank", name="uq_monthly_ranking_rows_rank"),
        sa.ForeignKeyConstraint(["ranking_id"], ["monthly_rankings.ranking_id"], name="fk_monthly_ranking_rows_ranking_id", ondelete="CASCADE"),
    )
    op.create_index("ix_monthly_ranking_rows_ranking", "monthly_ranking_rows", ["ranking_id", "rank"])

    if context.is_offline_mode():
        return
    bind = op.get_bind()
    for (resource, action), description in NEW_PERMISSIONS.items():
        if bind.execute(sa.text("SELECT 1 FROM permissions WHERE resource = :r AND action = :a"), {"r": resource, "a": action}).first():
            continue
        nxt = bind.execute(sa.text("SELECT COALESCE(MAX(CAST(SUBSTRING(code FROM 6) AS INTEGER)), 0) + 1 FROM permissions WHERE code LIKE 'PERM-%'")).scalar_one()
        bind.execute(
            sa.text("INSERT INTO permissions (permission_id, code, resource, action, description, created_at, updated_at) VALUES (gen_random_uuid(), :code, :r, :a, :d, now(), now())"),
            {"code": f"PERM-{int(nxt):03d}", "r": resource, "a": action, "d": description},
        )
    for role_name, scopes in GRANTS.items():
        for scope, permissions in scopes.items():
            for permission in permissions:
                resource, action = permission.split(":")
                bind.execute(
                    sa.text(
                        "INSERT INTO role_permissions (role_id, permission_id, scope) SELECT r.role_id, p.permission_id, :scope "
                        "FROM roles r, permissions p WHERE r.role_name = :role AND p.resource = :res AND p.action = :act "
                        "AND NOT EXISTS (SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.role_id AND rp.permission_id = p.permission_id)"
                    ),
                    {"scope": scope, "role": role_name, "res": resource, "act": action},
                )


def downgrade() -> None:
    if not context.is_offline_mode():
        bind = op.get_bind()
        bind.execute(sa.text("DELETE FROM role_permissions rp USING permissions p WHERE rp.permission_id = p.permission_id AND p.resource = 'ranking'"))
        bind.execute(sa.text("DELETE FROM permissions WHERE resource = 'ranking'"))
    op.execute("DROP INDEX IF EXISTS ix_monthly_ranking_rows_ranking")
    op.drop_table("monthly_ranking_rows")
    op.execute("DROP TRIGGER IF EXISTS trg_monthly_rankings_set_updated_at ON monthly_rankings")
    op.execute("DROP INDEX IF EXISTS ix_monthly_rankings_generated_by")
    op.execute("DROP INDEX IF EXISTS ix_monthly_rankings_target_month")
    op.drop_table("monthly_rankings")
