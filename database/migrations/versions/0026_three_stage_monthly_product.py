"""Produk bulanan tiga tahap: Staf Intelkam → Kasat Intelkam → Pimpinan.

Keputusan pemilik proyek 17 November 2026 (catatan 183) — penyesuaian ke naskah Taskap dan
saran Kasat Intelkam ("Staf – Kasat – Pimpinan; staf/KBO sama saja"):

- peran **Analis Intelkam** (ROLE-03) berganti nama menjadi **Staf Intelkam**; hak dan
  pemegangnya tidak berubah;
- peran **Kasat Intelkam** (ROLE-02, dihapus 0023) dibuat lagi, dengan hak baca yang sama
  seperti sebelumnya dan satu hak tindakan: `monthly_product:validate` (menelaah);
- `monthly_product:draft` dicabut dari **Administrator**, supaya rantainya tidak dapat
  dilewati lewat akun admin;
- akun peragaan `demo.kasat` dikembalikan ke peran Kasat Intelkam dan statusnya ACTIVE lagi,
  tetapi kata sandinya TIDAK disentuh: hash '!' dari 0023 tidak cocok dengan kata sandi apa
  pun, jadi akun itu tetap tidak dapat dipakai masuk sampai kata sandinya ditetapkan lewat
  scripts/sandi-peragaan-produksi.sh.

Tidak ada perubahan tabel: status VALIDATED dan tahap KASAT sudah sah sejak 0021. Produk
yang sedang berstatus ANALYST_REVIEWED kini menunggu telaah Kasat, bukan penetapan Pimpinan.

Revision ID: 0026
Revises: 0025
Create Date: 2026-11-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STAFF_CODE = "ROLE-03"
STAFF_OLD = "Analis Intelkam"
STAFF_NEW = "Staf Intelkam"
KASAT = ("ROLE-02", "Kasat Intelkam", 2)
KASAT_USER = "demo.kasat"
VALIDATE = ("monthly_product", "validate", "Menelaah produk bulanan (Kasat Intelkam)")
KASAT_GRANTS = (
    "dashboard:read", "location:read", "crime:read", "intelligence:read", "map:read",
    "analytics:read", "risk_score:read", "prediction:read", "warning:read", "public_alert:read",
    "recommendation:read", "commander_decision:read", "evaluation:read", "babin:read",
    "bulletin:read", "ranking:read", "monthly_product:read", "monthly_product:validate",
)  # fmt: skip

GRANT = sa.text(
    "INSERT INTO role_permissions (role_id, permission_id, scope) "
    "SELECT r.role_id, p.permission_id, 'ALL' FROM roles r, permissions p "
    "WHERE r.role_name = :role AND p.resource = :res AND p.action = :act "
    "AND NOT EXISTS (SELECT 1 FROM role_permissions rp "
    "WHERE rp.role_id = r.role_id AND rp.permission_id = p.permission_id)"
)
REVOKE = sa.text(
    "DELETE FROM role_permissions rp USING roles r, permissions p "
    "WHERE rp.role_id = r.role_id AND rp.permission_id = p.permission_id "
    "AND r.role_name = :role AND p.resource = :res AND p.action = :act"
)


def upgrade() -> None:
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    # 1. Analis Intelkam → Staf Intelkam (nama saja).
    bind.execute(
        sa.text(
            "UPDATE roles SET role_name = :new, updated_at = now() "
            "WHERE code = :code AND role_name = :old"
        ),
        {"new": STAFF_NEW, "old": STAFF_OLD, "code": STAFF_CODE},
    )
    # 2. Peran Kasat Intelkam.
    code, name, level = KASAT
    bind.execute(
        sa.text(
            "INSERT INTO roles (role_id, code, role_name, level, created_at, updated_at) "
            "SELECT gen_random_uuid(), CAST(:code AS VARCHAR), CAST(:name AS VARCHAR), :level, "
            "now(), now() "
            "WHERE NOT EXISTS (SELECT 1 FROM roles WHERE role_name = :name OR code = :code)"
        ),
        {"code": code, "name": name, "level": level},
    )
    # 3. Permission telaah. Kode berikutnya dari suffix terbesar, bukan jumlah baris.
    resource, action, description = VALIDATE
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
    for permission in KASAT_GRANTS:
        res, act = permission.split(":")
        bind.execute(GRANT, {"role": name, "res": res, "act": act})
    # 4. Administrator keluar dari rantai persetujuan.
    bind.execute(REVOKE, {"role": "Administrator", "res": "monthly_product", "act": "draft"})
    # 5. Akun peragaan Kasat kembali ke perannya. Status aktif, kata sandi tidak disentuh:
    #    selama hash-nya masih '!' (0023) tidak ada kata sandi yang cocok.
    bind.execute(
        sa.text(
            "UPDATE users SET role_id = (SELECT role_id FROM roles WHERE code = :code), "
            "status = 'ACTIVE', updated_at = now() WHERE username = :u"
        ),
        {"code": code, "u": KASAT_USER},
    )


def downgrade() -> None:
    """Kembali ke dua tahap: pemegang peran Kasat dipindah ke staf, peran dan permission
    telaah dihapus, Administrator kembali boleh menyusun, nama peran staf dipulihkan."""
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    code, name, _ = KASAT
    # Akun peragaan Kasat dikunci lagi seperti keadaan sesudah 0023.
    bind.execute(
        sa.text(
            "UPDATE users SET password_hash = '!', status = 'INACTIVE', updated_at = now() "
            "WHERE username = :u"
        ),
        {"u": KASAT_USER},
    )
    bind.execute(
        sa.text(
            "UPDATE users SET role_id = (SELECT role_id FROM roles WHERE code = :staff), "
            "updated_at = now() "
            "WHERE role_id IN (SELECT role_id FROM roles WHERE role_name = :name OR code = :code)"
        ),
        {"staff": STAFF_CODE, "name": name, "code": code},
    )
    bind.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE role_id IN "
            "(SELECT role_id FROM roles WHERE role_name = :name OR code = :code)"
        ),
        {"name": name, "code": code},
    )
    bind.execute(
        sa.text("DELETE FROM roles WHERE role_name = :name OR code = :code"),
        {"name": name, "code": code},
    )
    bind.execute(
        sa.text(
            "DELETE FROM role_permissions rp USING permissions p "
            "WHERE rp.permission_id = p.permission_id AND p.resource = :r AND p.action = :a"
        ),
        {"r": VALIDATE[0], "a": VALIDATE[1]},
    )
    bind.execute(
        sa.text("DELETE FROM permissions WHERE resource = :r AND action = :a"),
        {"r": VALIDATE[0], "a": VALIDATE[1]},
    )
    bind.execute(GRANT, {"role": "Administrator", "res": "monthly_product", "act": "draft"})
    bind.execute(
        sa.text(
            "UPDATE roles SET role_name = :old, updated_at = now() "
            "WHERE code = :code AND role_name = :new"
        ),
        {"new": STAFF_NEW, "old": STAFF_OLD, "code": STAFF_CODE},
    )
