"""Test data operasional (TASK 023).

Menjaga tiga acceptance criteria: A-1 (pejabat yang memutuskan benar-benar ada),
A-8 (tindakan hanya lahir dari keputusan yang menyetujui), dan A-7 (recall dapat dihitung).
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.models import CommanderDecision, OperationalAction, PredictionActual
from prediksi_presisi_api.seeding import csv_source as src
from prediksi_presisi_api.seeding.operational import seed_operational_data
from prediksi_presisi_api.seeding.regenerate import (
    DECISIONS_ALLOWING_ACTION,
    EVALUATED_THREATS,
)

DATABASE_URL = os.environ.get("DATABASE_URL", "")


# --------------------------------------------------------------------------------------
# Berkas sumber — tanpa database
# --------------------------------------------------------------------------------------


def test_every_decision_points_to_a_real_user() -> None:
    """A-1: sebelumnya 63 dari 63 keputusan menunjuk pengguna yang tidak ada."""
    users = {row["user_id"] for row in src.read_rows("users.csv")}

    deciders = {row["decision_by"] for row in src.read_rows("commander_decisions.csv")}

    assert deciders <= users


def test_modified_decisions_carry_their_new_text() -> None:
    """U-07: modifikasi tanpa isi baru membuat jejak keputusan tidak lengkap."""
    for row in src.read_rows("commander_decisions.csv"):
        if row["decision"] == "Modified":
            assert row["modified_text"], row["decision_id"]


def test_actions_never_come_from_a_rejected_decision() -> None:
    """A-8: dataset semula memuat tindakan yang lahir dari keputusan Rejected."""
    decisions = {
        row["decision_id"]: row["decision"] for row in src.read_rows("commander_decisions.csv")
    }

    for action in src.read_rows("operational_actions.csv"):
        assert decisions[action["decision_id"]] in DECISIONS_ALLOWING_ACTION, action["action_id"]


def test_every_approving_decision_has_an_action() -> None:
    approving = {
        row["decision_id"]
        for row in src.read_rows("commander_decisions.csv")
        if row["decision"] in DECISIONS_ALLOWING_ACTION
    }

    with_action = {row["decision_id"] for row in src.read_rows("operational_actions.csv")}

    assert approving == with_action


def test_evaluation_only_covers_published_predictions() -> None:
    """A-7: prediksi berstatus Draft tidak boleh ikut dievaluasi."""
    statuses = {row["prediction_id"]: row["status"] for row in src.read_rows("predictions.csv")}

    for row in src.read_rows("prediction_actual.csv"):
        if row["prediction_id"]:
            assert statuses[row["prediction_id"]] in {"Published", "Validated"}


def test_false_negatives_exist_and_point_to_real_incidents() -> None:
    """A-7: tanpa baris ini, recall tidak dapat dihitung sama sekali (CLAUDE.md §26)."""
    incidents = {row["incident_id"] for row in src.read_rows("crime_incidents.csv")}
    rows = [
        row
        for row in src.read_rows("prediction_actual.csv")
        if row["match_type"] == "False Negative"
    ]

    assert rows, "dataset tidak memuat satu pun false negative"
    for row in rows:
        assert row["prediction_id"] == ""
        assert row["actual_incident_id"] in incidents
        assert row["actual_threat_type"] in EVALUATED_THREATS


def test_recall_is_computable_from_the_dataset() -> None:
    rows = src.read_rows("prediction_actual.csv")
    hits = sum(1 for row in rows if row["match_type"] == "Hit")
    misses = sum(1 for row in rows if row["match_type"] == "False Negative")

    assert hits + misses > 0
    assert 0 < hits / (hits + misses) < 1


# --------------------------------------------------------------------------------------
# Dengan database
# --------------------------------------------------------------------------------------

requires_database = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tidak diisi — jalankan `pnpm db:up` lalu ulangi",
)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(DATABASE_URL, future=True)
    connection = engine.connect()
    transaction = connection.begin()
    opened = sessionmaker(bind=connection, expire_on_commit=False)()

    yield opened

    opened.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


@requires_database
def test_operational_seed_loads_expected_volumes(session: Session) -> None:
    seed_operational_data(session)
    session.flush()

    assert session.scalar(select(func.count()).select_from(CommanderDecision)) == 63
    assert session.scalar(select(func.count()).select_from(OperationalAction)) == 52
    assert session.scalar(select(func.count()).select_from(PredictionActual)) == 241


@requires_database
def test_database_refuses_an_action_from_a_rejected_decision(session: Session) -> None:
    """Bukti bahwa invarian human-in-the-loop dijaga database, bukan hanya oleh data."""
    seed_operational_data(session)
    session.flush()

    rejected = session.scalar(
        select(CommanderDecision).where(CommanderDecision.decision == "REJECTED").limit(1)
    )
    template = session.scalar(select(OperationalAction).limit(1))
    assert rejected is not None
    assert template is not None

    session.add(
        OperationalAction(
            code="ACT-UJI",
            decision_id=rejected.decision_id,
            unit_id=template.unit_id,
            location_id=template.location_id,
            start_at=template.start_at,
            status="PLANNED",
        )
    )

    with pytest.raises(DatabaseError):
        session.flush()


@requires_database
def test_metrics_can_be_computed(session: Session) -> None:
    seed_operational_data(session)
    session.flush()

    counts = {
        match_type: total
        for match_type, total in session.execute(
            select(PredictionActual.match_type, func.count()).group_by(PredictionActual.match_type)
        ).all()
    }

    hits = counts.get("HIT", 0)
    false_positives = counts.get("FALSE_POSITIVE", 0)
    false_negatives = counts.get("FALSE_NEGATIVE", 0)

    assert hits and false_positives and false_negatives
    assert 0 < hits / (hits + false_positives) < 1  # precision
    assert 0 < hits / (hits + false_negatives) < 1  # recall


@requires_database
def test_operational_seed_is_idempotent(session: Session) -> None:
    seed_operational_data(session)
    session.flush()

    second = seed_operational_data(session)
    session.flush()

    assert sum(second.inserted.values()) == 0
