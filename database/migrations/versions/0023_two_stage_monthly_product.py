"""Produk bulanan dua tahap; peran Kasat Intelkam dibekukan.

Keputusan pemilik proyek 10 November 2026 (1B, catatan 177): tahap KBO dan validasi Kasat
Intelkam dihapus — Analis menyusun, memeriksa, dan langsung mengirim ke Pimpinan. Akibatnya:

- permission `monthly_product:review` dan `monthly_product:validate` dicabut dan dihapus;
- peran **Kasat Intelkam** (ROLE-02) dihapus setelah pemegangnya dipindahkan ke Analis
  Intelkam (ROLE-03) — FK users.role_id RESTRICT menolak menghapus peran yang masih dipakai;
- akun peragaan `demo.kasat` DIKUNCI (password_hash '!', status INACTIVE), bukan dihapus:
  jejak audit merujuk ke akun itu dan tidak boleh putus.

Tidak ada perubahan tabel. Status KBO_CHECKED / VALIDATED dan tahap KBO / KASAT yang sudah
tersimpan tetap sah; produk di status itu langsung dapat ditetapkan Pimpinan.

Revision ID: 0023
Revises: 0022
Create Date: 2026-11-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RETIRED_ROLE = ("ROLE-02", "Kasat Intelkam", 2)
FALLBACK_ROLE = "Analis Intelkam"
LOCKED_USER = "demo.kasat"
RETIRED_PERMISSIONS = {
    ("monthly_product", "review"): "Memeriksa mutu analisis (tahap KBO)",
    ("monthly_product", "validate"): "Memvalidasi produk intelijen (Kasat Intelkam)",
}
READS = (
    "dashboard:read", "location:read", "crime:read", "intelligence:read", "map:read",
    "analytics:read", "risk_score:read", "prediction:read", "warning:read", "public_alert:read",
    "recommendation:read", "commander_decision:read", "evaluation:read", "babin:read",
    "bulletin:read", "ranking:read", "monthly_product:read",
)  # fmt: skip


def upgrade() -> None:
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    # 1. Cabut dan hapus dua permission tahap yang tidak ada lagi.
    bind.execute(
        sa.text(
            "DELETE FROM role_permissions rp USING permissions p WHERE rp.permission_id = p.permission_id "
            "AND p.resource = 'monthly_product' AND p.action IN ('review', 'validate')"
        )
    )
    bind.execute(
        sa.text("DELETE FROM permissions WHERE resource = 'monthly_product' AND action IN ('review', 'validate')")
    )
    # 2. Kunci akun peragaan Kasat (tetap ada demi jejak audit).
    bind.execute(
        sa.text("UPDATE users SET password_hash = '!', status = 'INACTIVE', updated_at = now() WHERE username = :u"),
        {"u": LOCKED_USER},
    )
    # 3. Pindahkan seluruh pemegang peran Kasat ke Analis Intelkam, lalu hapus perannya.
    bind.execute(
        sa.text(
            "UPDATE users SET role_id = (SELECT role_id FROM roles WHERE role_name = :fallback), updated_at = now() "
            "WHERE role_id IN (SELECT role_id FROM roles WHERE role_name = :retired OR code = :code)"
        ),
        {"fallback": FALLBACK_ROLE, "retired": RETIRED_ROLE[1], "code": RETIRED_ROLE[0]},
    )
    bind.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE role_id IN (SELECT role_id FROM roles WHERE role_name = :retired OR code = :code)"
        ),
        {"retired": RETIRED_ROLE[1], "code": RETIRED_ROLE[0]},
    )
    bind.execute(
        sa.text("DELETE FROM roles WHERE role_name = :retired OR code = :code"),
        {"retired": RETIRED_ROLE[1], "code": RETIRED_ROLE[0]},
    )


def downgrade() -> None:
    """Memulihkan peran, permission, dan hak Kasat Intelkam. Akun demo.kasat tetap terkunci
    (kata sandinya ditetapkan ulang lewat scripts/sandi-peragaan-produksi.sh bila perlu)."""
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    code, name, level = RETIRED_ROLE
    bind.execute(
        sa.text(
            "INSERT INTO roles (role_id, code, role_name, level, created_at, updated_at) "
            "SELECT gen_random_uuid(), CAST(:code AS VARCHAR), CAST(:name AS VARCHAR), :level, now(), now() "
            "WHERE NOT EXISTS (SELECT 1 FROM roles WHERE role_name = :name OR code = :code)"
        ),
        {"code": code, "name": name, "level": level},
    )
    bind.execute(
        sa.text(
            "UPDATE users SET role_id = (SELECT role_id FROM roles WHERE code = :code), updated_at = now() WHERE username = :u"
        ),
        {"code": code, "u": LOCKED_USER},
    )
    for (resource, action), description in RETIRED_PERMISSIONS.items():
        if bind.execute(sa.text("SELECT 1 FROM permissions WHERE resource = :r AND action = :a"), {"r": resource, "a": action}).first():
            continue
        nxt = bind.execute(sa.text("SELECT COALESCE(MAX(CAST(SUBSTRING(code FROM 6) AS INTEGER)), 0) + 1 FROM permissions WHERE code LIKE 'PERM-%'")).scalar_one()
        bind.execute(
            sa.text("INSERT INTO permissions (permission_id, code, resource, action, description, created_at, updated_at) VALUES (gen_random_uuid(), :code, :r, :a, :d, now(), now())"),
            {"code": f"PERM-{int(nxt):03d}", "r": resource, "a": action, "d": description},
        )
    grants = {
        name: [*READS, "monthly_product:review", "monthly_product:validate"],
        FALLBACK_ROLE: ["monthly_product:review"],
    }
    for role_name, permissions in grants.items():
        for permission in permissions:
            resource, action = permission.split(":")
            bind.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id, scope) SELECT r.role_id, p.permission_id, 'ALL' "
                    "FROM roles r, permissions p WHERE r.role_name = :role AND p.resource = :res AND p.action = :act "
                    "AND NOT EXISTS (SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.role_id AND rp.permission_id = p.permission_id)"
                ),
                {"role": role_name, "res": resource, "act": action},
            )
