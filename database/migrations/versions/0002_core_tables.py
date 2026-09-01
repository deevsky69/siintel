"""Tabel inti: locations, police_units, crime_incidents, intelligence_reports, patrol_activity.

TASK 011. Definisi kolom mengikuti docs/02-data-dictionary.md §1–§5,
constraint dan index mengikuti docs/06-database-schema.md §3–§4.

Catatan taksonomi: kolom seperti `incident_type`, `modus`, `target_type`, `location_type`,
dan seluruh kolom `status` sengaja bertipe teks, **bukan** ENUM database, karena daftar
nilainya belum final (U-16 / keputusan B-3). Validasi dilakukan di lapisan aplikasi
terhadap `config/taxonomy/`. Dengan begitu perubahan taksonomi tidak memerlukan
migration ALTER TYPE.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-31
"""

from __future__ import annotations

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID_PK = sa.text("gen_random_uuid()")
_NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "locations",
        sa.Column("location_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("grid_id", sa.String(length=50), nullable=False),
        sa.Column("polsek", sa.String(length=100), nullable=False),
        sa.Column("kecamatan", sa.String(length=100), nullable=False),
        sa.Column("kelurahan", sa.String(length=100), nullable=True),
        sa.Column("grid_size_m", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("location_type", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("location_id", name="pk_locations"),
        sa.UniqueConstraint("code", name="uq_locations_code"),
        sa.UniqueConstraint("grid_id", name="uq_locations_grid_id"),
    )
    op.create_index("ix_locations_polsek", "locations", ["polsek"])
    op.create_index("ix_locations_kecamatan", "locations", ["kecamatan"])
    op.create_index("ix_locations_geom", "locations", ["geom"], postgresql_using="gist")

    op.create_table(
        "police_units",
        sa.Column("unit_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("function", sa.String(length=50), nullable=False),
        sa.Column("unit_name", sa.String(length=150), nullable=False),
        sa.Column("jurisdiction", sa.String(length=150), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("unit_id", name="pk_police_units"),
        sa.UniqueConstraint("code", name="uq_police_units_code"),
    )
    op.create_index("ix_police_units_function", "police_units", ["function"])
    op.create_index("ix_police_units_jurisdiction", "police_units", ["jurisdiction"])

    op.create_table(
        "crime_incidents",
        sa.Column("incident_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("incident_type", sa.String(length=50), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("incident_date", sa.Date(), nullable=False),
        sa.Column("incident_time", sa.Time(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("location_type", sa.String(length=100), nullable=True),
        sa.Column("modus", sa.String(length=100), nullable=True),
        sa.Column("target_type", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("incident_id", name="pk_crime_incidents"),
        sa.UniqueConstraint("code", name="uq_crime_incidents_code"),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.location_id"],
            name="fk_crime_incidents_location_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_crime_incidents_occurred_at", "crime_incidents", ["occurred_at"])
    op.create_index(
        "ix_crime_incidents_location_occurred",
        "crime_incidents",
        ["location_id", "occurred_at"],
    )
    op.create_index("ix_crime_incidents_incident_type", "crime_incidents", ["incident_type"])

    op.create_table(
        "intelligence_reports",
        sa.Column("intelligence_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("reliability", sa.String(length=10), nullable=True),
        sa.Column("confidence", sa.SmallInteger(), nullable=True),
        sa.Column("urgency", sa.SmallInteger(), nullable=True),
        sa.Column("impact", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("intelligence_id", name="pk_intelligence_reports"),
        sa.UniqueConstraint("code", name="uq_intelligence_reports_code"),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.location_id"],
            name="fk_intelligence_reports_location_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence BETWEEN 0 AND 100)",
            name="confidence_range",
        ),
        sa.CheckConstraint(
            "urgency IS NULL OR (urgency BETWEEN 0 AND 100)",
            name="urgency_range",
        ),
    )
    op.create_index("ix_intelligence_reports_report_date", "intelligence_reports", ["report_date"])
    op.create_index("ix_intelligence_reports_location", "intelligence_reports", ["location_id"])

    op.create_table(
        "patrol_activity",
        sa.Column("patrol_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("unit_id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("patrol_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("activity_type", sa.String(length=100), nullable=True),
        sa.Column("result", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("patrol_id", name="pk_patrol_activity"),
        sa.UniqueConstraint("code", name="uq_patrol_activity_code"),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["police_units.unit_id"],
            name="fk_patrol_activity_unit_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.location_id"],
            name="fk_patrol_activity_location_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_patrol_activity_patrol_date", "patrol_activity", ["patrol_date"])
    op.create_index("ix_patrol_activity_location", "patrol_activity", ["location_id"])
    op.create_index("ix_patrol_activity_unit", "patrol_activity", ["unit_id"])


def downgrade() -> None:
    op.drop_table("patrol_activity")
    op.drop_table("intelligence_reports")
    op.drop_table("crime_incidents")
    op.drop_table("police_units")
    op.drop_index("ix_locations_geom", table_name="locations")
    op.drop_table("locations")
