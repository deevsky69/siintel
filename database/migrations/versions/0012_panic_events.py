"""Tombol darurat warga — `panic_events` + permission `panic:read` / `panic:acknowledge`.

Keputusan pemilik proyek 8 Oktober 2026: aplikasi warga mendapat tombol darurat yang
otomatis memberi tahu Administrator, Polsek (wilayahnya), dan Pimpinan. Tabelnya sengaja
terpisah dari `citizen_reports`: laporan masyarakat adalah keterangan yang ditriase, panic
adalah permintaan bantuan yang DITERIMA lalu DITUTUP — alur dan jejaknya berbeda.

Permission ikut ditanam di sini, bukan menunggu seed: produksi memegang data asli dan tidak
boleh di-seed ulang, sedangkan antrean notifikasi hanya menampilkan sumber yang permission-
nya dipegang. Kodenya melanjutkan deret PERM-NNN milik seed; `config/rbac/permissions.yaml`
diperbarui bersamaan supaya basis data baru dan lama sama.

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-08
"""

from __future__ import annotations

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GRANTS = {
    "Pimpinan": {"ALL": ["panic:read"]},
    "Polsek": {"OWN_JURISDICTION": ["panic:read", "panic:acknowledge"]},
    "Administrator": {"ALL": ["panic:read", "panic:acknowledge"]},
}


def upgrade() -> None:
    op.create_table(
        "panic_events",
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column(
            "pressed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Waktu sebenarnya tombol ditekan — bukan waktu acuan peragaan.",
        ),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column("accuracy_m", sa.Numeric(8, 1), nullable=True),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.String(300), nullable=True),
        sa.Column("status", sa.String(20), server_default="OPEN", nullable=False),
        sa.Column("acknowledged_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closing_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("event_id", name="pk_panic_events"),
        sa.UniqueConstraint("code", name="uq_panic_events_code"),
        sa.ForeignKeyConstraint(
            ["location_id"], ["locations.location_id"], name="fk_panic_events_location_id", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by"], ["users.user_id"], name="fk_panic_events_acknowledged_by", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["closed_by"], ["users.user_id"], name="fk_panic_events_closed_by", ondelete="RESTRICT"
        ),
        sa.CheckConstraint("status IN ('OPEN', 'ACKNOWLEDGED', 'CLOSED')", name="panic_status_allowed"),
        sa.CheckConstraint("(latitude IS NULL) = (longitude IS NULL)", name="panic_coordinates_paired"),
    )
    op.create_index("ix_panic_events_status_pressed", "panic_events", ["status", "pressed_at"])
    op.create_index("ix_panic_events_location", "panic_events", ["location_id"])
    op.create_index("ix_panic_events_acknowledged_by", "panic_events", ["acknowledged_by"])
    op.create_index("ix_panic_events_closed_by", "panic_events", ["closed_by"])
    op.execute(
        "CREATE TRIGGER trg_panic_events_set_updated_at BEFORE UPDATE ON "
        "panic_events FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )

    # ---- permission: melanjutkan deret PERM-NNN milik seed, idempoten ----
    # Dilewati pada mode offline (`alembic upgrade --sql`, dipakai test drift): sisipan ini
    # perlu membaca basis data; seed melengkapinya pada basis data yang dibuat dari nol.
    if context.is_offline_mode():
        return
    bind = op.get_bind()
    for action in ("read", "acknowledge"):
        exists = bind.execute(
            sa.text("SELECT 1 FROM permissions WHERE resource = 'panic' AND action = :a"), {"a": action}
        ).first()
        if exists:
            continue
        nxt = bind.execute(
            sa.text("SELECT COALESCE(MAX(CAST(SUBSTRING(code FROM 6) AS INTEGER)), 0) + 1 FROM permissions WHERE code LIKE 'PERM-%'")
        ).scalar_one()
        bind.execute(
            sa.text(
                "INSERT INTO permissions (permission_id, code, resource, action, description, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :code, 'panic', :a, :d, now(), now())"
            ),
            {"code": f"PERM-{int(nxt):03d}", "a": action, "d": f"panic:{action}"},
        )
    for role_name, scopes in GRANTS.items():
        role_id = bind.execute(
            sa.text("SELECT role_id FROM roles WHERE role_name = :r"), {"r": role_name}
        ).scalar()
        if role_id is None:
            continue  # basis data tanpa peran itu (mis. belum di-seed) — seed akan melengkapi
        for scope, entries in scopes.items():
            for entry in entries:
                resource, action = entry.split(":")
                bind.execute(
                    sa.text(
                        "INSERT INTO role_permissions (role_id, permission_id, scope) "
                        "SELECT :role, permission_id, :scope FROM permissions "
                        "WHERE resource = :res AND action = :act "
                        "ON CONFLICT DO NOTHING"
                    ),
                    {"role": role_id, "scope": scope, "res": resource, "act": action},
                )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_panic_events_set_updated_at ON panic_events")
    if context.is_offline_mode():
        op.drop_table("panic_events")
        return
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT permission_id FROM permissions WHERE resource = 'panic')"
        )
    )
    bind.execute(sa.text("DELETE FROM permissions WHERE resource = 'panic'"))
    op.execute("DROP INDEX IF EXISTS ix_panic_events_closed_by")
    op.execute("DROP INDEX IF EXISTS ix_panic_events_acknowledged_by")
    op.execute("DROP INDEX IF EXISTS ix_panic_events_location")
    op.execute("DROP INDEX IF EXISTS ix_panic_events_status_pressed")
    op.drop_table("panic_events")
