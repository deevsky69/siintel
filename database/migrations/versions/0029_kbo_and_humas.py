"""Rantai empat tahap (Analis, KBO, Kasat, Pimpinan) dan peran Humas.

Keputusan pemilik proyek 19 November 2026: aplikasi disamakan dengan naskah Taskap final.

- Naskah Bab IV B.4.4 dan Lampiran 9 D: Analis memvalidasi draf → KBO memeriksa mutu →
  Kasatintelkam menelaah → Kapolres menetapkan. Peran **KBO** (ROLE-07) dibuat dengan
  `monthly_product:review`; peran ROLE-03 kembali bernama **Analis Intelkam** (istilah naskah;
  17–19 November 2026 bernama Staf Intelkam).
- Naskah B.4.7 dan Tabel 24: informasi untuk masyarakat disetujui **Humas**. Peran Humas
  (ROLE-08) dibuat dengan `public_info:approve`: imbauan bulanan baru dikirim ke grup dan
  pelanggan setelah disetujui (tabel `advisory_approvals`, 0022, dipakai lagi).
- Akun peragaan `demo.kbo` dan `demo.humas` dibuat TANPA kata sandi yang sah (hash '!');
  kata sandinya ditetapkan lewat scripts/sandi-peragaan-produksi.sh.

Tidak ada perubahan tabel. Produk berstatus ANALYST_REVIEWED kini menunggu pemeriksaan KBO.

Revision ID: 0029
Revises: 0028
Create Date: 2026-11-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ANALYST_CODE = "ROLE-03"
ANALYST_OLD = "Staf Intelkam"
ANALYST_NEW = "Analis Intelkam"
NEW_ROLES = (("ROLE-07", "KBO", 3), ("ROLE-08", "Humas", 4))
NEW_USERS = (("USER-009", "demo.kbo", "ROLE-07"), ("USER-010", "demo.humas", "ROLE-08"))
NEW_PERMISSIONS = (
    ("monthly_product", "review", "Memeriksa mutu produk bulanan (KBO)"),
    ("public_info", "approve", "Menyetujui informasi untuk masyarakat (Humas)"),
)
GRANTS = {
    "KBO": (
        "dashboard:read", "location:read", "crime:read", "intelligence:read", "map:read",
        "analytics:read", "risk_score:read", "prediction:read", "warning:read",
        "public_alert:read", "recommendation:read", "commander_decision:read",
        "evaluation:read", "babin:read", "bulletin:read", "ranking:read",
        "monthly_product:read", "monthly_product:review",
    ),
    "Humas": (
        "dashboard:read", "location:read", "map:read", "public_alert:read", "babin:read",
        "bulletin:read", "community_feedback:read", "public_info:approve",
    ),
}  # fmt: skip


def upgrade() -> None:
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE roles SET role_name = :new, updated_at = now() "
            "WHERE code = :code AND role_name = :old"
        ),
        {"new": ANALYST_NEW, "old": ANALYST_OLD, "code": ANALYST_CODE},
    )
    for code, name, level in NEW_ROLES:
        bind.execute(
            sa.text(
                "INSERT INTO roles (role_id, code, role_name, level, created_at, updated_at) "
                "SELECT gen_random_uuid(), CAST(:code AS VARCHAR), CAST(:name AS VARCHAR), "
                ":level, now(), now() "
                "WHERE NOT EXISTS (SELECT 1 FROM roles WHERE role_name = :name OR code = :code)"
            ),
            {"code": code, "name": name, "level": level},
        )
    for resource, action, description in NEW_PERMISSIONS:
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
                "created_at, updated_at) "
                "VALUES (gen_random_uuid(), :code, :r, :a, :d, now(), now())"
            ),
            {"code": f"PERM-{int(nxt):03d}", "r": resource, "a": action, "d": description},
        )
    for role, permissions in GRANTS.items():
        for permission in permissions:
            resource, action = permission.split(":")
            bind.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id, scope) "
                    "SELECT r.role_id, p.permission_id, 'ALL' FROM roles r, permissions p "
                    "WHERE r.role_name = :role AND p.resource = :res AND p.action = :act "
                    "AND NOT EXISTS (SELECT 1 FROM role_permissions rp "
                    "WHERE rp.role_id = r.role_id AND rp.permission_id = p.permission_id)"
                ),
                {"role": role, "res": resource, "act": action},
            )
    for code, username, role_code in NEW_USERS:
        bind.execute(
            sa.text(
                "INSERT INTO users (user_id, code, username, password_hash, role_id, status, "
                "must_change_password, created_at, updated_at) "
                "SELECT gen_random_uuid(), CAST(:code AS VARCHAR), CAST(:username AS VARCHAR), "
                "'!', r.role_id, 'ACTIVE', true, now(), now() FROM roles r "
                "WHERE r.code = :role_code AND NOT EXISTS "
                "(SELECT 1 FROM users WHERE username = :username OR code = :code)"
            ),
            {"code": code, "username": username, "role_code": role_code},
        )


def downgrade() -> None:
    """Kembali ke tiga tahap tanpa Humas. Akun demo.kbo dan demo.humas DIKUNCI dan dipindah
    ke peran Fungsi (bukan dihapus — jejak audit merujuk ke akun), lalu perannya dihapus."""
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    names = [name for _, name, _ in NEW_ROLES]
    bind.execute(
        sa.text(
            "UPDATE users SET password_hash = '!', status = 'INACTIVE', updated_at = now(), "
            "role_id = (SELECT role_id FROM roles WHERE role_name = 'Fungsi') "
            "WHERE role_id IN (SELECT role_id FROM roles WHERE role_name = ANY(:names))"
        ),
        {"names": names},
    )
    bind.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE role_id IN "
            "(SELECT role_id FROM roles WHERE role_name = ANY(:names))"
        ),
        {"names": names},
    )
    bind.execute(sa.text("DELETE FROM roles WHERE role_name = ANY(:names)"), {"names": names})
    for resource, action, _ in NEW_PERMISSIONS:
        bind.execute(
            sa.text(
                "DELETE FROM role_permissions rp USING permissions p "
                "WHERE rp.permission_id = p.permission_id AND p.resource = :r AND p.action = :a"
            ),
            {"r": resource, "a": action},
        )
        bind.execute(
            sa.text("DELETE FROM permissions WHERE resource = :r AND action = :a"),
            {"r": resource, "a": action},
        )
    bind.execute(
        sa.text(
            "UPDATE roles SET role_name = :old, updated_at = now() "
            "WHERE code = :code AND role_name = :new"
        ),
        {"new": ANALYST_NEW, "old": ANALYST_OLD, "code": ANALYST_CODE},
    )
