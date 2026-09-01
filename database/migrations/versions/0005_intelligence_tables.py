"""Tabel intelijen: risk_scores, predictions, early_warnings, recommendations.

TASK 013, docs/02 §9–§12. Sekaligus memasang foreign key
`public_alerts.warning_id → early_warnings` yang tertunda sejak TASK 012.

Yang **tidak** dikunci di sini (menunggu keputusan pemilik proyek):
- hubungan `risk_score = round(Σ(bobot × faktor))` — bobot belum ditetapkan (U-02);
- batas kelas `risk_class` dan threshold `severity` — belum ditetapkan (U-01).
Keduanya hanya ditelusuri lewat `weights_version` dan `threshold_version`.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID_PK = sa.text("gen_random_uuid()")
_NOW = sa.text("now()")

_RISK_FACTORS = (
    "historical_factor",
    "recent_trend_factor",
    "temporal_factor",
    "spatial_factor",
    "context_factor",
)


def upgrade() -> None:
    op.create_table(
        "risk_scores",
        sa.Column("risk_score_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("assessment_date", sa.Date(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("threat_type", sa.String(length=50), nullable=False),
        sa.Column("time_window", sa.String(length=50), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_score", sa.SmallInteger(), nullable=False),
        sa.Column("risk_class", sa.String(length=20), nullable=False),
        *(sa.Column(factor, sa.SmallInteger(), nullable=True) for factor in _RISK_FACTORS),
        sa.Column("weights_version", sa.String(length=50), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("risk_score_id", name="pk_risk_scores"),
        sa.UniqueConstraint("code", name="uq_risk_scores_code"),
        sa.UniqueConstraint(
            "location_id",
            "threat_type",
            "window_start",
            "assessment_date",
            name="uq_risk_scores_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.location_id"],
            name="fk_risk_scores_location_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("risk_score BETWEEN 0 AND 100", name="risk_score_range"),
        sa.CheckConstraint("window_end > window_start", name="window_order"),
        *(
            sa.CheckConstraint(
                f"{factor} IS NULL OR ({factor} BETWEEN 0 AND 100)",
                name=f"{factor}_range",
            )
            for factor in _RISK_FACTORS
        ),
    )
    op.create_index("ix_risk_scores_assessment_date", "risk_scores", ["assessment_date"])
    op.create_index(
        "ix_risk_scores_location_window", "risk_scores", ["location_id", "window_start"]
    )

    op.create_table(
        "predictions",
        sa.Column("prediction_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("prediction_date", sa.Date(), nullable=False),
        sa.Column("forecast_horizon", sa.String(length=10), nullable=False),
        sa.Column("threat_type", sa.String(length=50), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("time_window", sa.String(length=50), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_score", sa.SmallInteger(), nullable=False),
        sa.Column("confidence", sa.SmallInteger(), nullable=False),
        sa.Column("dominant_factors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("baseline_risk_score_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("prediction_id", name="pk_predictions"),
        sa.UniqueConstraint("code", name="uq_predictions_code"),
        sa.UniqueConstraint(
            "location_id",
            "threat_type",
            "window_start",
            "forecast_horizon",
            "model_version",
            "prediction_date",
            name="uq_predictions_forecast",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.location_id"],
            name="fk_predictions_location_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["baseline_risk_score_id"],
            ["risk_scores.risk_score_id"],
            name="fk_predictions_baseline_risk_score_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("risk_score BETWEEN 0 AND 100", name="risk_score_range"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 100", name="confidence_range"),
        sa.CheckConstraint("window_end > window_start", name="window_order"),
        sa.CheckConstraint(
            "forecast_horizon IN ('6H', '12H', '24H', '3D', '7D')",
            name="forecast_horizon_allowed",
        ),
    )
    op.create_index("ix_predictions_prediction_date", "predictions", ["prediction_date"])
    op.create_index(
        "ix_predictions_location_window", "predictions", ["location_id", "window_start"]
    )
    op.create_index("ix_predictions_status", "predictions", ["status"])

    op.create_table(
        "early_warnings",
        sa.Column("warning_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("prediction_id", sa.UUID(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("threat_type", sa.String(length=50), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("time_window", sa.String(length=50), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk_score", sa.SmallInteger(), nullable=False),
        sa.Column("confidence", sa.SmallInteger(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("acknowledged_by", sa.UUID(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.UUID(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("threshold_version", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("warning_id", name="pk_early_warnings"),
        sa.UniqueConstraint("code", name="uq_early_warnings_code"),
        sa.ForeignKeyConstraint(
            ["prediction_id"],
            ["predictions.prediction_id"],
            name="fk_early_warnings_prediction_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.location_id"],
            name="fk_early_warnings_location_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by"],
            ["users.user_id"],
            name="fk_early_warnings_acknowledged_by",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"],
            ["users.user_id"],
            name="fk_early_warnings_resolved_by",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("risk_score BETWEEN 0 AND 100", name="risk_score_range"),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence BETWEEN 0 AND 100)",
            name="confidence_range",
        ),
        sa.CheckConstraint("window_end > window_start", name="window_order"),
        sa.CheckConstraint(
            "acknowledged_at IS NULL OR acknowledged_by IS NOT NULL",
            name="acknowledged_needs_actor",
        ),
        sa.CheckConstraint(
            "resolved_at IS NULL OR resolved_by IS NOT NULL",
            name="resolved_needs_actor",
        ),
    )
    op.create_index("ix_early_warnings_status_created", "early_warnings", ["status", "created_at"])
    op.create_index("ix_early_warnings_location", "early_warnings", ["location_id"])
    op.create_index("ix_early_warnings_prediction", "early_warnings", ["prediction_id"])

    op.create_table(
        "recommendations",
        sa.Column("recommendation_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("prediction_id", sa.UUID(), nullable=False),
        sa.Column("warning_id", sa.UUID(), nullable=True),
        sa.Column("recommended_function", sa.String(length=50), nullable=False),
        sa.Column("recommendation_text", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=30), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("recommendation_id", name="pk_recommendations"),
        sa.UniqueConstraint("code", name="uq_recommendations_code"),
        sa.ForeignKeyConstraint(
            ["prediction_id"],
            ["predictions.prediction_id"],
            name="fk_recommendations_prediction_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["warning_id"],
            ["early_warnings.warning_id"],
            name="fk_recommendations_warning_id",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_recommendations_status", "recommendations", ["status"])
    op.create_index("ix_recommendations_prediction", "recommendations", ["prediction_id"])
    op.create_index("ix_recommendations_function", "recommendations", ["recommended_function"])

    # Utang dari TASK 012: kolomnya sudah ada, tabel acuannya baru tersedia sekarang.
    op.create_foreign_key(
        "fk_public_alerts_warning_id",
        "public_alerts",
        "early_warnings",
        ["warning_id"],
        ["warning_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_public_alerts_warning_id", "public_alerts", type_="foreignkey")
    op.drop_table("recommendations")
    op.drop_table("early_warnings")
    op.drop_table("predictions")
    op.drop_table("risk_scores")
