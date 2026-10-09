"""Kewenangan 9 Oktober 2026 — keputusan pemilik proyek.

1. `citizen_report:triage` dan `crime:triage` — mengubah status laporan masyarakat dan
   kejadian (laporan petugas) **hanya oleh Administrator**. Sebelumnya status diubah oleh
   pemegang `*:write` (Polsek/Fungsi juga). Mencatat dan mengubah status kini dua kewenangan.
2. Administrator diberi `commander_decision:approve` — boleh memutuskan rekomendasi seperti
   Pimpinan, membalik pemisahan 1 September 2026. Jejak audit tetap mencatat siapa memutus.

Idempoten; dilewati pada mode offline (`--sql`). `config/rbac/permissions.yaml` diperbarui
bersamaan supaya basis data baru (seed) dan lama (migrasi) sama.

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_PERMISSIONS = {
    ("citizen_report", "triage"): "Mengubah status (triase) laporan masyarakat",
    ("crime", "triage"): "Mengubah status penanganan kejadian",
}
GRANTS = {
    "Administrator": {
        "ALL": ["citizen_report:triage", "crime:triage", "commander_decision:approve"],
    },
}


def upgrade() -> None:
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
                        "SELECT r.role_id, p.permission_id, :scope "
                        "FROM roles r, permissions p "
                        "WHERE r.role_name = :role AND p.resource = :res AND p.action = :act "
                        "AND NOT EXISTS (SELECT 1 FROM role_permissions rp "
                        "WHERE rp.role_id = r.role_id AND rp.permission_id = p.permission_id)"
                    ),
                    {"scope": scope, "role": role_name, "res": resource, "act": action},
                )


def downgrade() -> None:
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    for role_name, scopes in GRANTS.items():
        for permissions in scopes.values():
            for permission in permissions:
                resource, action = permission.split(":")
                bind.execute(
                    sa.text(
                        "DELETE FROM role_permissions rp USING roles r, permissions p "
                        "WHERE rp.role_id = r.role_id AND rp.permission_id = p.permission_id "
                        "AND r.role_name = :role AND p.resource = :res AND p.action = :act"
                    ),
                    {"role": role_name, "res": resource, "act": action},
                )
    for resource, action in NEW_PERMISSIONS:
        bind.execute(
            sa.text("DELETE FROM permissions WHERE resource = :r AND action = :a"),
            {"r": resource, "a": action},
        )
