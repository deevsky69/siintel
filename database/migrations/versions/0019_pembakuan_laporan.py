"""Modul 1 "Membakukan laporan kejadian" (Mekanisme dan Fungsi SIGAP, 6 November 2026).

Empat hal yang diminta dokumen mekanisme dan belum ada:

1. `vehicle_object` — penanda objek kendaraan bermotor pada kolom tersendiri. Diisi dari
   `target_type = 'Kendaraan bermotor'` (nilai Pusiknas apa adanya); pada data asli 644
   kejadian 2025 — persis angka Uji Prediksi 2025 dalam dokumen.
2. `area_pending` — kejadian yang kelurahannya belum pasti (dipetakan ke lokasi tingkat
   kecamatan, 413 baris) menunggu konfirmasi dan dihitung terpisah; masuk perhitungan
   wilayah setelah kelurahannya dipastikan.
3. `duplicate_of` + `duplicate_status` — dugaan laporan ganda ditandai dan dicocokkan
   sebelum digabung (SUSPECTED → CONFIRMED / CLEARED). Yang CONFIRMED disembunyikan dari
   seluruh perhitungan lewat saringan ORM global (`services/visibility.py`).
4. `crime_incident_revisions` — riwayat setiap koreksi (bidang, nilai sebelum/sesudah,
   siapa, kapan, catatan).

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "crime_incidents",
        sa.Column("vehicle_object", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "crime_incidents",
        sa.Column("area_pending", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("crime_incidents", sa.Column("duplicate_of", sa.String(50), nullable=True))
    op.add_column(
        "crime_incidents", sa.Column("duplicate_status", sa.String(20), nullable=True)
    )
    op.create_check_constraint(
        "duplicate_status_known",
        "crime_incidents",
        "duplicate_status IS NULL OR duplicate_status IN ('SUSPECTED', 'CONFIRMED', 'CLEARED')",
    )
    op.create_index(
        "ix_crime_incidents_area_pending",
        "crime_incidents",
        ["area_pending"],
        postgresql_where=sa.text("area_pending"),
    )
    op.create_index(
        "ix_crime_incidents_duplicate_status",
        "crime_incidents",
        ["duplicate_status"],
        postgresql_where=sa.text("duplicate_status IS NOT NULL"),
    )

    # Isi ulang dari data yang sudah ada: objek kendaraan dari kolom sasaran Pusiknas,
    # kelurahan tertunda dari lokasi tingkat kecamatan.
    op.execute(
        "UPDATE crime_incidents SET vehicle_object = TRUE "
        "WHERE target_type = 'Kendaraan bermotor'"
    )
    op.execute(
        "UPDATE crime_incidents c SET area_pending = TRUE FROM locations l "
        "WHERE l.location_id = c.location_id AND l.kelurahan IS NULL"
    )

    op.create_table(
        "crime_incident_revisions",
        sa.Column(
            "revision_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crime_incidents.incident_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "changed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.user_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("field", sa.String(50), nullable=False),
        sa.Column("value_before", sa.Text(), nullable=True),
        sa.Column("value_after", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_crime_incident_revisions_incident",
        "crime_incident_revisions",
        ["incident_id", "changed_at"],
    )
    op.create_index(
        "ix_crime_incident_revisions_changed_by", "crime_incident_revisions", ["changed_by"]
    )


def downgrade() -> None:
    op.drop_index("ix_crime_incident_revisions_changed_by", table_name="crime_incident_revisions")
    op.drop_index("ix_crime_incident_revisions_incident", table_name="crime_incident_revisions")
    op.drop_table("crime_incident_revisions")
    op.drop_index("ix_crime_incidents_duplicate_status", table_name="crime_incidents")
    op.drop_index("ix_crime_incidents_area_pending", table_name="crime_incidents")
    op.drop_constraint("duplicate_status_known", "crime_incidents", type_="check")
    op.drop_column("crime_incidents", "duplicate_status")
    op.drop_column("crime_incidents", "duplicate_of")
    op.drop_column("crime_incidents", "area_pending")
    op.drop_column("crime_incidents", "vehicle_object")
