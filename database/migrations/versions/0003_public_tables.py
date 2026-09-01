"""Tabel publik: citizen_reports, public_alerts, community_feedback.

TASK 012. Definisi mengikuti docs/02-data-dictionary.md §6–§8.

Catatan `public_alerts.warning_id`: kolomnya dibuat di sini, tetapi **foreign key**-nya
ke `early_warnings` belum dapat dipasang karena tabel tersebut baru dibuat pada TASK 013.
FK ditambahkan pada migration TASK 013. Sampai saat itu, keterkaitan alert publik dengan
peringatan internal belum ditegakkan database.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID_PK = sa.text("gen_random_uuid()")
_NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "citizen_reports",
        sa.Column("report_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("incident_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("location_id", sa.UUID(), nullable=True),
        sa.Column("location_text", sa.String(length=255), nullable=True),
        sa.Column("urgency_score", sa.SmallInteger(), nullable=True),
        sa.Column("verification_score", sa.SmallInteger(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("report_id", name="pk_citizen_reports"),
        sa.UniqueConstraint("code", name="uq_citizen_reports_code"),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.location_id"],
            name="fk_citizen_reports_location_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "urgency_score IS NULL OR (urgency_score BETWEEN 0 AND 100)",
            name="urgency_score_range",
        ),
        sa.CheckConstraint(
            "verification_score IS NULL OR (verification_score BETWEEN 0 AND 100)",
            name="verification_score_range",
        ),
    )
    op.create_index("ix_citizen_reports_reported_at", "citizen_reports", ["reported_at"])
    op.create_index("ix_citizen_reports_status", "citizen_reports", ["status"])
    op.create_index("ix_citizen_reports_location", "citizen_reports", ["location_id"])
    op.create_index("ix_citizen_reports_geom", "citizen_reports", ["geom"], postgresql_using="gist")

    op.create_table(
        "public_alerts",
        sa.Column("public_alert_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("warning_id", sa.UUID(), nullable=True),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("threat_type", sa.String(length=50), nullable=False),
        sa.Column("area_text", sa.String(length=255), nullable=False),
        sa.Column("time_window", sa.String(length=50), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("public_message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("public_alert_id", name="pk_public_alerts"),
        sa.UniqueConstraint("code", name="uq_public_alerts_code"),
        sa.CheckConstraint(
            "window_end IS NULL OR window_start IS NULL OR window_end > window_start",
            name="window_order",
        ),
    )
    op.create_index("ix_public_alerts_status", "public_alerts", ["status"])
    op.create_index("ix_public_alerts_warning", "public_alerts", ["warning_id"])
    op.create_index("ix_public_alerts_window_start", "public_alerts", ["window_start"])

    op.create_table(
        "community_feedback",
        sa.Column("feedback_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("report_id", sa.UUID(), nullable=False),
        sa.Column("feedback_type", sa.String(length=50), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("feedback_id", name="pk_community_feedback"),
        sa.UniqueConstraint("code", name="uq_community_feedback_code"),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["citizen_reports.report_id"],
            name="fk_community_feedback_report_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_community_feedback_report", "community_feedback", ["report_id"])
    op.create_index("ix_community_feedback_status", "community_feedback", ["status"])


def downgrade() -> None:
    op.drop_table("community_feedback")
    op.drop_table("public_alerts")
    op.drop_index("ix_citizen_reports_geom", table_name="citizen_reports")
    op.drop_table("citizen_reports")
