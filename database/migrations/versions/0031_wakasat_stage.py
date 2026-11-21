"""Tahap Wakasat Intelkam pada rantai produk bulanan.

Keputusan pemilik proyek 21 November 2026: aplikasi disamakan dengan naskah Taskap revisi
(`docs/TASKAP - IRKHAMUL KHAKIM - 202608003058 REVISI.docx`). Gambar 4.3 (Desain Program),
Tabel 4.16, dan Lampiran I butir 7 menyebut lima pemeriksa berjenjang:

    analis → KBO → Wakasatintelkam → Kasatintelkam → Kapolres

- Status baru `WAKASAT_CHECKED` (sudah diperiksa Wakasat, menunggu telaah Kasat) dan tahap
  baru `WAKASAT`. Produk berstatus `KBO_CHECKED` kini menunggu Wakasat, bukan Kasat.
- Peran **Wakasat Intelkam** (ROLE-09) dengan `monthly_product:examine`; Administrator ikut
  memegangnya (catatan 187: Administrator memegang seluruh kewenangan).
- Akun peragaan `demo.wakasat` dibuat TANPA kata sandi yang sah (hash '!'); kata sandinya
  ditetapkan lewat scripts/sandi-peragaan-produksi.sh.

Revision ID: 0031
Revises: 0030
Create Date: 2026-11-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE = ("ROLE-09", "Wakasat Intelkam", 2)
USER = ("USER-011", "demo.wakasat", "ROLE-09")
PERMISSION = ("monthly_product", "examine", "Memeriksa produk bulanan (Wakasat Intelkam)")
GRANTS = {
    "Wakasat Intelkam": (
        "dashboard:read", "location:read", "crime:read", "intelligence:read", "map:read",
        "analytics:read", "risk_score:read", "prediction:read", "warning:read",
        "public_alert:read", "recommendation:read", "commander_decision:read",
        "evaluation:read", "babin:read", "bulletin:read", "ranking:read",
        "monthly_product:read", "monthly_product:examine",
    ),
    "Administrator": ("monthly_product:examine",),
}  # fmt: skip

STATUS_NEW = (
    "('DRAFT', 'ANALYST_REVIEWED', 'KBO_CHECKED', 'WAKASAT_CHECKED', 'VALIDATED', 'DECIDED')"
)
STATUS_OLD = "('DRAFT', 'ANALYST_REVIEWED', 'KBO_CHECKED', 'VALIDATED', 'DECIDED')"
STAGE_NEW = "('ANALYST', 'KBO', 'WAKASAT', 'KASAT', 'PIMPINAN')"
STAGE_OLD = "('ANALYST', 'KBO', 'KASAT', 'PIMPINAN')"


def _constraints(status: str, stage: str) -> None:
    op.drop_constraint("monthly_product_status_allowed", "monthly_products", type_="check")
    op.create_check_constraint(
        "monthly_product_status_allowed", "monthly_products", f"status IN {status}"
    )
    op.drop_constraint("monthly_stage_allowed", "monthly_product_stages", type_="check")
    op.create_check_constraint(
        "monthly_stage_allowed", "monthly_product_stages", f"stage IN {stage}"
    )


def upgrade() -> None:
    _constraints(STATUS_NEW, STAGE_NEW)
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    code, name, level = ROLE
    bind.execute(
        sa.text(
            "INSERT INTO roles (role_id, code, role_name, level, created_at, updated_at) "
            "SELECT gen_random_uuid(), CAST(:code AS VARCHAR), CAST(:name AS VARCHAR), "
            ":level, now(), now() "
            "WHERE NOT EXISTS (SELECT 1 FROM roles WHERE role_name = :name OR code = :code)"
        ),
        {"code": code, "name": name, "level": level},
    )
    resource, action, description = PERMISSION
    exists = bind.execute(
        sa.text("SELECT 1 FROM permissions WHERE resource = :r AND action = :a"),
        {"r": resource, "a": action},
    ).first()
    if not exists:
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
            res, act = permission.split(":")
            bind.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id, scope) "
                    "SELECT r.role_id, p.permission_id, 'ALL' FROM roles r, permissions p "
                    "WHERE r.role_name = :role AND p.resource = :res AND p.action = :act "
                    "AND NOT EXISTS (SELECT 1 FROM role_permissions rp "
                    "WHERE rp.role_id = r.role_id AND rp.permission_id = p.permission_id)"
                ),
                {"role": role, "res": res, "act": act},
            )
    user_code, username, role_code = USER
    bind.execute(
        sa.text(
            "INSERT INTO users (user_id, code, username, password_hash, role_id, status, "
            "must_change_password, created_at, updated_at) "
            "SELECT gen_random_uuid(), CAST(:code AS VARCHAR), CAST(:username AS VARCHAR), "
            "'!', r.role_id, 'ACTIVE', true, now(), now() FROM roles r "
            "WHERE r.code = :role_code AND NOT EXISTS "
            "(SELECT 1 FROM users WHERE username = :username OR code = :code)"
        ),
        {"code": user_code, "username": username, "role_code": role_code},
    )


def downgrade() -> None:
    """Kembali ke empat pemeriksa. Produk yang sedang menunggu Kasat (WAKASAT_CHECKED)
    dikembalikan ke KBO_CHECKED; catatan tahap WAKASAT dihapus (alur lama tidak mengenalnya).
    Akun demo.wakasat DIKUNCI dan dipindah ke peran Fungsi, lalu perannya dihapus."""
    if not context.is_offline_mode():
        bind = op.get_bind()
        bind.execute(
            sa.text(
                "UPDATE monthly_products SET status = 'KBO_CHECKED' "
                "WHERE status = 'WAKASAT_CHECKED'"
            )
        )
        bind.execute(sa.text("DELETE FROM monthly_product_stages WHERE stage = 'WAKASAT'"))
        bind.execute(
            sa.text(
                "UPDATE users SET status = 'INACTIVE', password_hash = '!', role_id = "
                "(SELECT role_id FROM roles WHERE role_name = 'Fungsi') "
                "WHERE role_id = (SELECT role_id FROM roles WHERE role_name = :name)"
            ),
            {"name": ROLE[1]},
        )
        bind.execute(
            sa.text(
                "DELETE FROM role_permissions WHERE permission_id IN "
                "(SELECT permission_id FROM permissions WHERE resource = :r AND action = :a) "
                "OR role_id IN (SELECT role_id FROM roles WHERE role_name = :name)"
            ),
            {"r": PERMISSION[0], "a": PERMISSION[1], "name": ROLE[1]},
        )
        bind.execute(
            sa.text("DELETE FROM permissions WHERE resource = :r AND action = :a"),
            {"r": PERMISSION[0], "a": PERMISSION[1]},
        )
        bind.execute(sa.text("DELETE FROM roles WHERE role_name = :name"), {"name": ROLE[1]})
    _constraints(STATUS_OLD, STAGE_OLD)
