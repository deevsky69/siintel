"""Modul 4 mekanisme: produk bulanan dengan empat tahap pemeriksaan, dua peran Satintelkam,
pencatatan pelaksanaan.

Keputusan pemilik proyek 6 November 2026 (1B): peran Kasat Intelkam (ROLE-02, level 2) dan
Analis Intelkam (ROLE-03, level 3) — menempati jenjang yang kosong sejak Command Center dan
Analyst dilebur. Akun peragaan demo.kasat dan demo.analis dibuat TERKUNCI; kata sandinya
ditetapkan di server (scripts/sandi-peragaan-produksi.sh). Rantai: DRAFT → ANALYST_REVIEWED
→ KBO_CHECKED → VALIDATED → DECIDED; alasan wajib pada penolakan/perbaikan.

Revision ID: 0021
Revises: 0020
Create Date: 2026-11-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TS = sa.DateTime(timezone=True)
NEW_ROLES = (("ROLE-02", "Kasat Intelkam", 2), ("ROLE-03", "Analis Intelkam", 3))
NEW_USERS = (("USER-007", "demo.kasat", "ROLE-02"), ("USER-008", "demo.analis", "ROLE-03"))
NEW_PERMISSIONS = {
    ("monthly_product", "read"): "Membaca produk bulanan",
    ("monthly_product", "draft"): "Menyusun draf produk bulanan dan memeriksanya sebagai analis",
    ("monthly_product", "review"): "Memeriksa mutu analisis (tahap KBO)",
    ("monthly_product", "validate"): "Memvalidasi produk intelijen (Kasat Intelkam)",
    ("monthly_product", "decide"): "Menetapkan jumlah dan kelurahan prioritas (Pimpinan)",
    ("monthly_product", "execute"): "Mencatat pelaksanaan di kelurahan prioritas",
}
READS = [
    "dashboard:read", "location:read", "crime:read", "intelligence:read", "map:read",
    "analytics:read", "risk_score:read", "prediction:read", "warning:read", "public_alert:read",
    "recommendation:read", "commander_decision:read", "evaluation:read", "babin:read",
    "bulletin:read", "ranking:read", "monthly_product:read",
]  # fmt: skip
GRANTS = {
    "Pimpinan": {"ALL": ["monthly_product:read", "monthly_product:decide"]},
    "Kasat Intelkam": {"ALL": [*READS, "monthly_product:review", "monthly_product:validate"]},
    "Analis Intelkam": {"ALL": [*READS, "ranking:manage", "monthly_product:draft", "monthly_product:review"]},
    "Fungsi": {"ALL": ["monthly_product:read", "monthly_product:execute"]},
    "Polsek": {"ALL": ["monthly_product:read", "monthly_product:execute"]},
    "Administrator": {"ALL": ["monthly_product:read", "monthly_product:draft"]},
}


def upgrade() -> None:
    op.create_table(
        "monthly_products",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("target_month", sa.Date(), nullable=False),
        sa.Column("ranking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), server_default="DRAFT", nullable=False),
        sa.Column("facts", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("priority_count", sa.Integer(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", TS, nullable=True),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("product_id", name="pk_monthly_products"),
        sa.UniqueConstraint("target_month", name="uq_monthly_products_target_month"),
        sa.ForeignKeyConstraint(["ranking_id"], ["monthly_rankings.ranking_id"], name="fk_monthly_products_ranking_id", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.user_id"], name="fk_monthly_products_created_by", ondelete="SET NULL"),
        sa.CheckConstraint("status IN ('DRAFT', 'ANALYST_REVIEWED', 'KBO_CHECKED', 'VALIDATED', 'DECIDED')", name="monthly_product_status_allowed"),
    )
    op.create_index("ix_monthly_products_ranking_id", "monthly_products", ["ranking_id"])
    op.create_index("ix_monthly_products_created_by", "monthly_products", ["created_by"])
    op.execute("CREATE TRIGGER trg_monthly_products_set_updated_at BEFORE UPDATE ON monthly_products FOR EACH ROW EXECUTE FUNCTION set_updated_at()")

    op.create_table(
        "monthly_product_items",
        sa.Column("item_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("kelurahan", sa.String(100), nullable=False),
        sa.Column("kecamatan", sa.String(100), nullable=False),
        sa.Column("polsek", sa.String(100), nullable=False),
        sa.Column("predicted_count", sa.Numeric(8, 2), nullable=False),
        sa.Column("pattern", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("proposal_text", sa.Text(), nullable=False),
        sa.Column("proposed_function", sa.String(30), nullable=False),
        sa.Column("analyst_status", sa.String(10), nullable=True),
        sa.Column("analyst_text", sa.Text(), nullable=True),
        sa.Column("analyst_reason", sa.Text(), nullable=True),
        sa.Column("selected", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("decided_action", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("item_id", name="pk_monthly_product_items"),
        sa.UniqueConstraint("product_id", "kelurahan", name="uq_monthly_product_items_kelurahan"),
        sa.ForeignKeyConstraint(["product_id"], ["monthly_products.product_id"], name="fk_monthly_product_items_product_id", ondelete="CASCADE"),
        sa.CheckConstraint("analyst_status IS NULL OR analyst_status IN ('ACCEPTED', 'REVISED', 'REJECTED')", name="monthly_item_analyst_status_allowed"),
    )
    op.create_index("ix_monthly_product_items_product", "monthly_product_items", ["product_id", "rank"])

    op.create_table(
        "monthly_product_stages",
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage", sa.String(10), nullable=False),
        sa.Column("outcome", sa.String(10), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("acted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("acted_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("stage_id", name="pk_monthly_product_stages"),
        sa.ForeignKeyConstraint(["product_id"], ["monthly_products.product_id"], name="fk_monthly_product_stages_product_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["acted_by"], ["users.user_id"], name="fk_monthly_product_stages_acted_by", ondelete="SET NULL"),
        sa.CheckConstraint("stage IN ('ANALYST', 'KBO', 'KASAT', 'PIMPINAN')", name="monthly_stage_allowed"),
        sa.CheckConstraint("outcome IN ('ACCEPTED', 'REVISED', 'REJECTED', 'DECIDED')", name="monthly_stage_outcome_allowed"),
    )
    op.create_index("ix_monthly_product_stages_product", "monthly_product_stages", ["product_id", "acted_at"])
    op.create_index("ix_monthly_product_stages_acted_by", "monthly_product_stages", ["acted_by"])

    op.create_table(
        "monthly_actions",
        sa.Column("action_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("unit", sa.String(100), nullable=False),
        sa.Column("acted_at", TS, nullable=False),
        sa.Column("place", sa.String(200), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("action_id", name="pk_monthly_actions"),
        sa.ForeignKeyConstraint(["item_id"], ["monthly_product_items.item_id"], name="fk_monthly_actions_item_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.user_id"], name="fk_monthly_actions_recorded_by", ondelete="SET NULL"),
    )
    op.create_index("ix_monthly_actions_item", "monthly_actions", ["item_id", "acted_at"])
    op.create_index("ix_monthly_actions_recorded_by", "monthly_actions", ["recorded_by"])

    if context.is_offline_mode():
        return
    bind = op.get_bind()
    for code, name, level in NEW_ROLES:
        bind.execute(
            sa.text(
                "INSERT INTO roles (role_id, code, role_name, level, created_at, updated_at) "
                "SELECT gen_random_uuid(), CAST(:code AS VARCHAR), CAST(:name AS VARCHAR), :level, now(), now() "
                "WHERE NOT EXISTS (SELECT 1 FROM roles WHERE role_name = :name OR code = :code)"
            ),
            {"code": code, "name": name, "level": level},
        )
    for code, username, role_code in NEW_USERS:
        bind.execute(
            sa.text(
                "INSERT INTO users (user_id, code, username, password_hash, role_id, status, must_change_password, created_at, updated_at) "
                "SELECT gen_random_uuid(), CAST(:code AS VARCHAR), CAST(:username AS VARCHAR), '!', r.role_id, 'ACTIVE', true, now(), now() FROM roles r "
                "WHERE r.code = :role_code AND NOT EXISTS (SELECT 1 FROM users WHERE username = :username OR code = :code)"
            ),
            {"code": code, "username": username, "role_code": role_code},
        )
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
        bind.execute(sa.text("DELETE FROM role_permissions rp USING permissions p WHERE rp.permission_id = p.permission_id AND p.resource = 'monthly_product'"))
        bind.execute(sa.text("DELETE FROM permissions WHERE resource = 'monthly_product'"))
    for table, indexes in (
        ("monthly_actions", ("ix_monthly_actions_recorded_by", "ix_monthly_actions_item")),
        ("monthly_product_stages", ("ix_monthly_product_stages_acted_by", "ix_monthly_product_stages_product")),
        ("monthly_product_items", ("ix_monthly_product_items_product",)),
    ):
        for index in indexes:
            op.execute(f"DROP INDEX IF EXISTS {index}")
        op.drop_table(table)
    op.execute("DROP TRIGGER IF EXISTS trg_monthly_products_set_updated_at ON monthly_products")
    op.execute("DROP INDEX IF EXISTS ix_monthly_products_created_by")
    op.execute("DROP INDEX IF EXISTS ix_monthly_products_ranking_id")
    op.drop_table("monthly_products")
