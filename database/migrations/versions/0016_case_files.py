"""Berkas perkara 3C — `case_files`, `case_file_stages`, permission `case_file:read/write`.

Keputusan pemilik proyek 2 November 2026 (SIGAP WARGA butir 2, 3, 6): lacak laporan dengan
nomor LP + PIN, cek kendaraan dengan plat/nomor rangka, data dummy berlabel. Lihat
`models/case_file.py`. Grant: Pimpinan ALL read; Polsek OWN_JURISDICTION read+write;
Administrator ALL read+write.

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_PERMISSIONS = {
    ("case_file", "read"): "Membaca berkas perkara 3C (lacak laporan)",
    ("case_file", "write"): "Mencatat dan memperbarui tahap berkas perkara 3C",
}
GRANTS = {
    "Pimpinan": {"ALL": ["case_file:read"]},
    "Polsek": {"OWN_JURISDICTION": ["case_file:read", "case_file:write"]},
    "Administrator": {"ALL": ["case_file:read", "case_file:write"]},
}


def upgrade() -> None:
    op.create_table(
        "case_files",
        sa.Column("case_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("lp_number", sa.String(80), nullable=False),
        sa.Column("crime_type", sa.String(50), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reported_on", sa.Date(), nullable=False),
        sa.Column("stage", sa.String(20), server_default="DITERIMA", nullable=False),
        sa.Column("stage_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("vehicle_plate", sa.String(16), nullable=True),
        sa.Column("vehicle_plate_display", sa.String(20), nullable=True),
        sa.Column("vehicle_vin", sa.String(30), nullable=True),
        sa.Column("vehicle_engine", sa.String(30), nullable=True),
        sa.Column("vehicle_desc", sa.String(120), nullable=True),
        sa.Column("vehicle_recovered", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("reporter_pin_hash", sa.String(64), nullable=False),
        sa.Column("is_dummy", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("dummy_pin", sa.String(4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("case_id", name="pk_case_files"),
        sa.UniqueConstraint("lp_number", name="uq_case_files_lp_number"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.location_id"], name="fk_case_files_location_id", ondelete="RESTRICT"),
        sa.CheckConstraint("stage IN ('DITERIMA', 'LIDIK', 'SIDIK', 'P21', 'SP3', 'SELESAI')", name="case_stage_allowed"),
        sa.CheckConstraint("crime_type IN ('CURANMOR', 'CURAT', 'CURAS')", name="case_crime_type_allowed"),
        sa.CheckConstraint("is_dummy OR dummy_pin IS NULL", name="case_dummy_pin_only_for_dummy"),
    )
    op.create_index("ix_case_files_location", "case_files", ["location_id"])
    op.create_index("ix_case_files_plate", "case_files", ["vehicle_plate"])
    op.create_index("ix_case_files_vin", "case_files", ["vehicle_vin"])
    op.create_index("ix_case_files_stage", "case_files", ["stage"])
    op.execute(
        "CREATE TRIGGER trg_case_files_set_updated_at BEFORE UPDATE ON case_files "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )
    op.create_table(
        "case_file_stages",
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage", sa.String(20), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.String(300), nullable=True),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("stage_id", name="pk_case_file_stages"),
        sa.ForeignKeyConstraint(["case_id"], ["case_files.case_id"], name="fk_case_file_stages_case_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.user_id"], name="fk_case_file_stages_changed_by", ondelete="RESTRICT"),
        sa.CheckConstraint("stage IN ('DITERIMA', 'LIDIK', 'SIDIK', 'P21', 'SP3', 'SELESAI')", name="case_stage_history_allowed"),
    )
    op.create_index("ix_case_file_stages_case", "case_file_stages", ["case_id", "changed_at"])
    op.create_index("ix_case_file_stages_changed_by", "case_file_stages", ["changed_by"])

    if context.is_offline_mode():
        return
    bind = op.get_bind()
    for (resource, action), description in NEW_PERMISSIONS.items():
        exists = bind.execute(
            sa.text("SELECT 1 FROM permissions WHERE resource = :r AND action = :a"),
            {"r": resource, "a": action},
        ).first()
        if exists:
            continue
        nxt = bind.execute(
            sa.text(
                "SELECT COALESCE(MAX(CAST(SUBSTRING(code FROM 6) AS INTEGER)), 0) + 1 "
                "FROM permissions WHERE code LIKE 'PERM-%'"
            )
        ).scalar_one()
        bind.execute(
            sa.text(
                "INSERT INTO permissions (permission_id, code, resource, action, description, "
                "created_at, updated_at) VALUES (gen_random_uuid(), :code, :r, :a, :d, now(), now())"
            ),
            {"code": f"PERM-{int(nxt):03d}", "r": resource, "a": action, "d": description},
        )
    for role_name, scopes in GRANTS.items():
        for scope, permissions in scopes.items():
            for permission in permissions:
                resource, action = permission.split(":")
                bind.execute(
                    sa.text(
                        "INSERT INTO role_permissions (role_id, permission_id, scope) "
                        "SELECT r.role_id, p.permission_id, :scope FROM roles r, permissions p "
                        "WHERE r.role_name = :role AND p.resource = :res AND p.action = :act "
                        "AND NOT EXISTS (SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.role_id "
                        "AND rp.permission_id = p.permission_id)"
                    ),
                    {"scope": scope, "role": role_name, "res": resource, "act": action},
                )


def downgrade() -> None:
    if not context.is_offline_mode():
        bind = op.get_bind()
        bind.execute(
            sa.text(
                "DELETE FROM role_permissions rp USING permissions p WHERE rp.permission_id = "
                "p.permission_id AND p.resource = 'case_file'"
            )
        )
        bind.execute(sa.text("DELETE FROM permissions WHERE resource = 'case_file'"))
    op.execute("DROP INDEX IF EXISTS ix_case_file_stages_changed_by")
    op.execute("DROP INDEX IF EXISTS ix_case_file_stages_case")
    op.drop_table("case_file_stages")
    op.execute("DROP TRIGGER IF EXISTS trg_case_files_set_updated_at ON case_files")
    for name in ("ix_case_files_stage", "ix_case_files_vin", "ix_case_files_plate", "ix_case_files_location"):
        op.execute(f"DROP INDEX IF EXISTS {name}")
    op.drop_table("case_files")
