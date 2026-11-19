"""Administrator memegang seluruh kewenangan.

Keputusan pemilik proyek 19 November 2026 (catatan 187): "seluruh privilege yang dimiliki
akun lain, baik pimpinan, humas, fungsi dll harus bisa dilakukan oleh admin."

Sembilan kewenangan yang sebelumnya sengaja tidak dipegang Administrator kini diberikan
dengan cakupan ALL: seluruh rantai produk bulanan (draft, review, validate, decide, execute),
`bulletin:approve`, `public_info:approve`, `public_alert:publish`, dan `evaluation:run`.

Tidak ada perubahan tabel dan tidak ada peran lain yang berubah. Pemisahan tugas tetap
berlaku antarperan selain Administrator; untuk Administrator ia tinggal jejak audit.

Revision ID: 0030
Revises: 0029
Create Date: 2026-11-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE = "Administrator"
GRANTS = (
    "monthly_product:draft", "monthly_product:review", "monthly_product:validate",
    "monthly_product:decide", "monthly_product:execute", "bulletin:approve",
    "public_info:approve", "public_alert:publish", "evaluation:run",
)  # fmt: skip


def upgrade() -> None:
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    for permission in GRANTS:
        resource, action = permission.split(":")
        bind.execute(
            sa.text(
                "INSERT INTO role_permissions (role_id, permission_id, scope) "
                "SELECT r.role_id, p.permission_id, 'ALL' FROM roles r, permissions p "
                "WHERE r.role_name = :role AND p.resource = :res AND p.action = :act "
                "AND NOT EXISTS (SELECT 1 FROM role_permissions rp "
                "WHERE rp.role_id = r.role_id AND rp.permission_id = p.permission_id)"
            ),
            {"role": ROLE, "res": resource, "act": action},
        )


def downgrade() -> None:
    """Mencabut kembali kesembilan kewenangan dari Administrator."""
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    for permission in GRANTS:
        resource, action = permission.split(":")
        bind.execute(
            sa.text(
                "DELETE FROM role_permissions rp USING roles r, permissions p "
                "WHERE rp.role_id = r.role_id AND rp.permission_id = p.permission_id "
                "AND r.role_name = :role AND p.resource = :res AND p.action = :act"
            ),
            {"role": ROLE, "res": resource, "act": action},
        )
