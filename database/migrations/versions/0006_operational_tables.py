"""Tabel operasional: commander_decisions, operational_actions, prediction_actual.

TASK 014, docs/02 §13–§15. Menutup rangkaian tabel PHASE 2.

Dua invarian penting ditegakkan di database, bukan hanya di lapisan aplikasi:

1. **Tindakan operasional hanya boleh lahir dari keputusan `APPROVED`/`MODIFIED`.**
   Ditegakkan lewat trigger karena CHECK tidak dapat merujuk tabel lain. Ini invarian
   inti produk: AI tidak pernah langsung memerintahkan tindakan (CLAUDE.md §13).
2. **Kejadian aktual yang tidak diprediksi tetap dapat direpresentasikan**
   (`match_type = FALSE_NEGATIVE` dengan `prediction_id` NULL), supaya recall terhitung
   (CLAUDE.md §26).

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID_PK = sa.text("gen_random_uuid()")
_NOW = sa.text("now()")

_REQUIRE_APPROVED_DECISION = """
CREATE OR REPLACE FUNCTION enforce_action_requires_approved_decision()
RETURNS trigger AS $$
DECLARE
    decision_value text;
BEGIN
    SELECT decision INTO decision_value
    FROM commander_decisions
    WHERE decision_id = NEW.decision_id;

    IF decision_value IS NULL OR decision_value NOT IN ('APPROVED', 'MODIFIED') THEN
        RAISE EXCEPTION
            'operational_actions hanya boleh dari keputusan APPROVED/MODIFIED (decision: %)',
            COALESCE(decision_value, 'TIDAK DITEMUKAN')
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

_TRIGGER = """
CREATE TRIGGER trg_operational_actions_require_approved_decision
BEFORE INSERT OR UPDATE OF decision_id ON operational_actions
FOR EACH ROW EXECUTE FUNCTION enforce_action_requires_approved_decision();
"""


def upgrade() -> None:
    op.create_table(
        "commander_decisions",
        sa.Column("decision_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("recommendation_id", sa.UUID(), nullable=False),
        sa.Column("decision_by", sa.UUID(), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("decision_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("modified_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("decision_id", name="pk_commander_decisions"),
        sa.UniqueConstraint("code", name="uq_commander_decisions_code"),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["recommendations.recommendation_id"],
            name="fk_commander_decisions_recommendation_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["decision_by"],
            ["users.user_id"],
            name="fk_commander_decisions_decision_by",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "decision IN ('APPROVED', 'MODIFIED', 'REJECTED')",
            name="decision_allowed",
        ),
        sa.CheckConstraint(
            "decision <> 'MODIFIED' OR modified_text IS NOT NULL",
            name="modified_needs_text",
        ),
    )
    op.create_index(
        "ix_commander_decisions_recommendation", "commander_decisions", ["recommendation_id"]
    )
    op.create_index("ix_commander_decisions_decision", "commander_decisions", ["decision"])
    op.create_index("ix_commander_decisions_decided_at", "commander_decisions", ["decision_at"])

    op.create_table(
        "operational_actions",
        sa.Column("action_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("decision_id", sa.UUID(), nullable=False),
        sa.Column("unit_id", sa.UUID(), nullable=False),
        sa.Column("location_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("action_id", name="pk_operational_actions"),
        sa.UniqueConstraint("code", name="uq_operational_actions_code"),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["commander_decisions.decision_id"],
            name="fk_operational_actions_decision_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["police_units.unit_id"],
            name="fk_operational_actions_unit_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.location_id"],
            name="fk_operational_actions_location_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.user_id"],
            name="fk_operational_actions_created_by",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("end_at IS NULL OR end_at > start_at", name="time_order"),
    )
    op.create_index("ix_operational_actions_decision", "operational_actions", ["decision_id"])
    op.create_index("ix_operational_actions_unit", "operational_actions", ["unit_id"])
    op.create_index("ix_operational_actions_status", "operational_actions", ["status"])
    op.create_index("ix_operational_actions_start_at", "operational_actions", ["start_at"])

    op.execute(_REQUIRE_APPROVED_DECISION)
    op.execute(_TRIGGER)

    op.create_table(
        "prediction_actual",
        sa.Column("evaluation_id", sa.UUID(), server_default=_UUID_PK, nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("evaluation_date", sa.Date(), nullable=False),
        sa.Column("prediction_id", sa.UUID(), nullable=True),
        sa.Column("actual_incident_id", sa.UUID(), nullable=True),
        sa.Column("actual_event", sa.Boolean(), nullable=False),
        sa.Column("actual_threat_type", sa.String(length=50), nullable=True),
        sa.Column("actual_location_id", sa.UUID(), nullable=True),
        sa.Column("actual_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("match_type", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
        sa.PrimaryKeyConstraint("evaluation_id", name="pk_prediction_actual"),
        sa.UniqueConstraint("code", name="uq_prediction_actual_code"),
        sa.ForeignKeyConstraint(
            ["prediction_id"],
            ["predictions.prediction_id"],
            name="fk_prediction_actual_prediction_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actual_incident_id"],
            ["crime_incidents.incident_id"],
            name="fk_prediction_actual_actual_incident_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actual_location_id"],
            ["locations.location_id"],
            name="fk_prediction_actual_actual_location_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "match_type IN ('HIT', 'FALSE_POSITIVE', 'FALSE_NEGATIVE')",
            name="match_type_allowed",
        ),
        sa.CheckConstraint(
            "(match_type IN ('HIT', 'FALSE_POSITIVE') AND prediction_id IS NOT NULL)"
            " OR (match_type = 'FALSE_NEGATIVE' AND prediction_id IS NULL"
            " AND actual_incident_id IS NOT NULL)",
            name="match_type_consistency",
        ),
        sa.CheckConstraint(
            "actual_window_end IS NULL OR actual_window_start IS NULL"
            " OR actual_window_end > actual_window_start",
            name="window_order",
        ),
    )
    op.create_index(
        "ix_prediction_actual_evaluation_date", "prediction_actual", ["evaluation_date"]
    )
    op.create_index("ix_prediction_actual_match_type", "prediction_actual", ["match_type"])
    op.create_index("ix_prediction_actual_prediction", "prediction_actual", ["prediction_id"])


def downgrade() -> None:
    op.drop_table("prediction_actual")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_operational_actions_require_approved_decision"
        " ON operational_actions"
    )
    op.execute("DROP FUNCTION IF EXISTS enforce_action_requires_approved_decision()")
    op.drop_table("operational_actions")
    op.drop_table("commander_decisions")
