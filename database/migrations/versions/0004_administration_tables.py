"""Tabel administrasi: roles, users, permissions, role_permissions, audit_logs.

TASK 015, docs/02 §16–§20.

Dikerjakan **sebelum** TASK 013/014 (urutan diubah, nomor task tetap) supaya foreign key
ke `users` pada `early_warnings`, `commander_decisions`, dan `operational_actions`
dapat dipasang langsung tanpa menumpuk constraint tertunda. Lihat docs/08 PHASE 2.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID_PK = sa.text("gen_random_uuid()")
_NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("role_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("role_name", sa.String(length=100), nullable=False),
        sa.Column("level", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("role_id", name="pk_roles"),
        sa.UniqueConstraint("code", name="uq_roles_code"),
        sa.UniqueConstraint("role_name", name="uq_roles_role_name"),
        sa.CheckConstraint("level BETWEEN 1 AND 6", name="level_range"),
    )

    op.create_table(
        "users",
        sa.Column("user_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("polsek", sa.String(length=100), nullable=True),
        sa.Column("function", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("must_change_password", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("user_id", name="pk_users"),
        sa.UniqueConstraint("code", name="uq_users_code"),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.role_id"],
            name="fk_users_role_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_users_role", "users", ["role_id"])
    op.create_index("ix_users_polsek", "users", ["polsek"])

    op.create_table(
        "permissions",
        sa.Column("permission_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("resource", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("permission_id", name="pk_permissions"),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
        sa.UniqueConstraint("resource", "action", name="uq_permissions_resource_action"),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("permission_id", sa.UUID(), nullable=False),
        sa.Column("scope", sa.String(length=30), server_default="ALL", nullable=False),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name="pk_role_permissions"),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.role_id"],
            name="fk_role_permissions_role_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.permission_id"],
            name="fk_role_permissions_permission_id",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "scope IN ('ALL', 'OWN_JURISDICTION', 'OWN_FUNCTION')",
            name="scope_allowed",
        ),
    )

    op.create_table(
        "audit_logs",
        sa.Column("audit_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("audit_id", name="pk_audit_logs"),
        sa.UniqueConstraint("code", name="uq_audit_logs_code"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name="fk_audit_logs_user_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "result IN ('SUCCESS', 'DENIED', 'FAILED')",
            name="result_allowed",
        ),
    )
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("ix_audit_logs_user_timestamp", "audit_logs", ["user_id", "timestamp"])
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("users")
    op.drop_table("roles")
