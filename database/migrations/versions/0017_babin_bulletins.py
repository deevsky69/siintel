"""Tahap 3 SIGAP WARGA — `babinkamtibmas`, `bulletins`, permission babin:* dan bulletin:*.

Keputusan pemilik proyek 2 November 2026 (butir 5, 7, 8, dan buletin mingguan kelurahan).
Grant: Pimpinan babin:read, bulletin:read, bulletin:approve; Polsek babin:read, bulletin:read;
Administrator babin:read/manage, bulletin:read/manage.

Revision ID: 0017
Revises: 0016
Create Date: 2026-11-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_PERMISSIONS = {
    ("babin", "read"): "Membaca kontak Babinkamtibmas",
    ("babin", "manage"): "Mengelola kontak Babinkamtibmas",
    ("bulletin", "read"): "Membaca buletin mingguan kelurahan",
    ("bulletin", "manage"): "Menyusun buletin mingguan kelurahan",
    ("bulletin", "approve"): "Menyetujui buletin mingguan untuk dikirim ke masyarakat",
}
GRANTS = {
    "Pimpinan": {"ALL": ["babin:read", "bulletin:read", "bulletin:approve"]},
    "Polsek": {"ALL": ["babin:read", "bulletin:read"]},
    "Administrator": {"ALL": ["babin:read", "babin:manage", "bulletin:read", "bulletin:manage"]},
}
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "babinkamtibmas",
        sa.Column("babin_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("kelurahan", sa.String(100), nullable=False),
        sa.Column("kecamatan", sa.String(100), nullable=False),
        sa.Column("polsek", sa.String(100), nullable=False),
        sa.Column("rank", sa.String(40), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("phone_display", sa.String(32), nullable=False),
        sa.Column("telegram_chat_id", sa.String(32), nullable=True),
        sa.Column("whatsapp_group_link", sa.String(200), nullable=True),
        sa.Column("whatsapp_number", sa.String(20), nullable=True),
        sa.Column("is_dummy", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("babin_id", name="pk_babinkamtibmas"),
        sa.UniqueConstraint("kelurahan", name="uq_babinkamtibmas_kelurahan"),
    )
    op.create_index("ix_babinkamtibmas_kecamatan", "babinkamtibmas", ["kecamatan"])
    op.create_index("ix_babinkamtibmas_polsek", "babinkamtibmas", ["polsek"])
    op.execute("CREATE TRIGGER trg_babinkamtibmas_set_updated_at BEFORE UPDATE ON babinkamtibmas FOR EACH ROW EXECUTE FUNCTION set_updated_at()")

    op.create_table(
        "bulletins",
        sa.Column("bulletin_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("kelurahan", sa.String(100), nullable=False),
        sa.Column("kecamatan", sa.String(100), nullable=False),
        sa.Column("polsek", sa.String(100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("figures", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", sa.String(20), server_default="DRAFT", nullable=False),
        sa.Column("generated_at", TS, nullable=False),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", TS, nullable=True),
        sa.Column("sent_at", TS, nullable=True),
        sa.Column("delivery", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", TS, server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("bulletin_id", name="pk_bulletins"),
        sa.UniqueConstraint("week_start", "kelurahan", name="uq_bulletins_week_kelurahan"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.user_id"], name="fk_bulletins_approved_by", ondelete="RESTRICT"),
        sa.CheckConstraint("status IN ('DRAFT', 'APPROVED', 'SENT')", name="bulletin_status_allowed"),
    )
    op.create_index("ix_bulletins_status", "bulletins", ["status"])
    op.create_index("ix_bulletins_approved_by", "bulletins", ["approved_by"])
    op.execute("CREATE TRIGGER trg_bulletins_set_updated_at BEFORE UPDATE ON bulletins FOR EACH ROW EXECUTE FUNCTION set_updated_at()")

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
        bind.execute(sa.text("DELETE FROM role_permissions rp USING permissions p WHERE rp.permission_id = p.permission_id AND p.resource IN ('babin', 'bulletin')"))
        bind.execute(sa.text("DELETE FROM permissions WHERE resource IN ('babin', 'bulletin')"))
    op.execute("DROP TRIGGER IF EXISTS trg_bulletins_set_updated_at ON bulletins")
    op.execute("DROP INDEX IF EXISTS ix_bulletins_approved_by")
    op.execute("DROP INDEX IF EXISTS ix_bulletins_status")
    op.drop_table("bulletins")
    op.execute("DROP TRIGGER IF EXISTS trg_babinkamtibmas_set_updated_at ON babinkamtibmas")
    op.execute("DROP INDEX IF EXISTS ix_babinkamtibmas_polsek")
    op.execute("DROP INDEX IF EXISTS ix_babinkamtibmas_kecamatan")
    op.drop_table("babinkamtibmas")
