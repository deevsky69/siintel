"""Evaluasi mundur: prediksi H-1 dibandingkan kejadian nyata hari H (`services/backtest.py`).

Dijalankan di atas fixture sampel dalam transaksi yang dibatalkan. Yang dijaga bukan angka
precision tertentu — itu hasil, bukan aturan — melainkan bahwa evaluasi tidak melihat masa
depan, tidak menghitung dua kali, dan tidak menyembunyikan kejadian yang tidak dapat
dievaluasi.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.models import (
    AuditLog,
    CrimeIncident,
    Location,
    Prediction,
    PredictionActual,
)
from prediksi_presisi_api.services import backtest, clock
from prediksi_presisi_api.services import prediction_engine as engine
from prediksi_presisi_api.services import risk_engine as risk

DATABASE_URL = os.environ.get("DATABASE_URL", "")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL tidak diisi")


@pytest.fixture
def session() -> Iterator[Session]:
    db = create_engine(DATABASE_URL, future=True)
    connection = db.connect()
    transaction = connection.begin()
    opened = sessionmaker(bind=connection, expire_on_commit=False)()
    yield opened
    opened.close()
    transaction.rollback()
    connection.close()
    db.dispose()


def _incident(
    session: Session,
    *,
    day: date,
    hour: int | None,
    reported_on: date | None = None,
    threat: str = "CURANMOR",
    location: Location | None = None,
) -> CrimeIncident:
    location = location or session.scalar(select(Location).order_by(Location.grid_id))
    assert location is not None
    local = datetime.combine(day, time(hour=hour or 0), tzinfo=clock.JAKARTA)
    reported = datetime.combine(reported_on or day, time(hour=23), tzinfo=clock.JAKARTA)
    row = CrimeIncident(
        code=f"KJD-UJI-{uuid.uuid4().hex[:6]}",
        incident_type=threat,
        occurred_at=local.astimezone(UTC),
        incident_date=day,
        incident_time=None if hour is None else time(hour=hour),
        time_known=hour is not None,
        location_id=location.location_id,
        reported_at=reported.astimezone(UTC),
        data_source="UJI",
    )
    session.add(row)
    session.flush()
    return row


# ---------------------------------------------------------------------------
# Bukti tidak melihat masa depan
# ---------------------------------------------------------------------------


def test_evidence_as_of_excludes_incidents_reported_later(session: Session) -> None:
    """Kejadian yang terjadi sebelum as_of tetapi baru dilaporkan sesudahnya BELUM ada."""
    before = risk.collect_evidence(session, as_of=date(2098, 1, 10)).total_incidents
    _incident(session, day=date(2098, 1, 5), hour=10, reported_on=date(2098, 1, 12))
    after = risk.collect_evidence(session, as_of=date(2098, 1, 10)).total_incidents
    assert after == before, "kejadian yang belum dilaporkan ikut dinilai"

    assert risk.collect_evidence(session, as_of=date(2098, 1, 12)).total_incidents == before + 1
    assert risk.collect_evidence(session).total_incidents >= before + 1


def test_the_recent_window_moves_with_as_of(session: Session) -> None:
    location = session.scalar(select(Location).order_by(Location.grid_id))
    assert location is not None
    _incident(session, day=date(2098, 3, 1), hour=9, location=location)
    key = (location.location_id, "CURANMOR")

    inside = risk.collect_evidence(session, as_of=date(2098, 3, 5)).recent.get(key, 0)
    outside = risk.collect_evidence(session, as_of=date(2098, 6, 1)).recent.get(key, 0)
    assert inside >= 1
    assert outside == 0, "jendela 30 hari harus dihitung mundur dari as_of"


# ---------------------------------------------------------------------------
# Pencocokan
# ---------------------------------------------------------------------------


def test_a_dry_run_writes_nothing_but_counts_everything(session: Session) -> None:
    predictions_before = session.scalar(select(func.count()).select_from(Prediction))
    evaluations_before = session.scalar(select(func.count()).select_from(PredictionActual))

    summary = backtest.run_backtest(session, date(2025, 12, 20), date(2025, 12, 21), write=False)

    assert len(summary.days) == 2
    assert summary.written is False
    assert summary.predictions == summary.hits + summary.false_positives
    assert session.scalar(select(func.count()).select_from(Prediction)) == predictions_before
    assert session.scalar(select(func.count()).select_from(PredictionActual)) == evaluations_before


def test_an_incident_without_an_hour_is_unevaluable_not_a_false_negative(
    session: Session,
) -> None:
    """Kejadian tanpa jam tidak punya jendela; menghitungnya sebagai FN menghukum model atas
    sesuatu yang tidak pernah dapat dicocokkan, mengabaikannya menyembunyikan 21,9% data."""
    day = date(2098, 2, 2)
    _incident(session, day=day, hour=None)

    summary = backtest.run_backtest(session, day, day, write=False)
    assert summary.unevaluable == 1
    assert summary.false_negatives == 0


def test_an_incident_in_an_unpredicted_unit_is_a_false_negative_that_names_the_incident(
    session: Session,
) -> None:
    """CLAUDE.md §26: kejadian yang tidak diprediksi harus tetap terwakili — dan menunjuk
    kejadian nyatanya, bukan sekadar menambah hitungan."""
    day = date(2098, 2, 3)
    # Sel tanpa riwayat apa pun pada 2098 tidak akan mencapai ambang peringatan.
    incident = _incident(session, day=day, hour=14, threat="CURAS")

    summary = backtest.run_backtest(session, day, day, write=True)
    assert summary.false_negatives >= 1

    row = session.scalar(
        select(PredictionActual).where(PredictionActual.actual_incident_id == incident.incident_id)
    )
    assert row is not None
    assert row.match_type == "FALSE_NEGATIVE"
    assert row.prediction_id is None
    assert row.actual_event is True
    assert row.actual_threat_type == "CURAS"
    assert row.actual_location_id == incident.location_id
    assert row.actual_window_start is not None and row.actual_window_end is not None
    assert row.evaluation_date == day


def test_written_predictions_are_validated_and_every_hit_or_fp_points_to_one(
    session: Session,
) -> None:
    start, end = date(2025, 12, 22), date(2025, 12, 23)
    summary = backtest.run_backtest(session, start, end, write=True)

    written = session.scalars(
        select(Prediction).where(
            Prediction.prediction_date.in_([start - timedelta(days=1), end - timedelta(days=1)]),
            Prediction.status == engine.STATUS_VALIDATED,
            Prediction.model_version == engine.RULE_VERSION,
        )
    ).all()
    assert len(written) == summary.predictions
    assert all(row.risk_score >= summary.minimum_score for row in written)
    assert all(
        row.dominant_factors and row.dominant_factors[0]["source"] == "RULE" for row in written
    )

    linked = session.scalars(
        select(PredictionActual).where(
            PredictionActual.prediction_id.in_([row.prediction_id for row in written])
        )
    ).all()
    assert len(linked) == summary.predictions
    assert {row.match_type for row in linked} <= {"HIT", "FALSE_POSITIVE"}
    assert sum(1 for row in linked if row.match_type == "HIT") == summary.hits

    entry = session.scalar(
        select(AuditLog)
        .where(AuditLog.action == backtest.AUDIT_ACTION)
        .order_by(AuditLog.timestamp.desc())
    )
    assert entry is not None and entry.detail is not None
    assert entry.detail["hits"] == summary.hits


def test_a_day_already_evaluated_is_skipped_not_doubled(session: Session) -> None:
    day = date(2098, 2, 4)
    first = backtest.run_backtest(session, day, day, write=True)
    second = backtest.run_backtest(session, day, day, write=True)

    assert first.days[0].skipped_reason is None
    assert second.days[0].skipped_reason is not None
    assert second.predictions == 0 and second.hits == 0 and second.false_negatives == 0


def test_the_metrics_follow_the_counts(session: Session) -> None:
    summary = backtest.BacktestSummary(
        start=date(2026, 1, 1),
        end=date(2026, 1, 1),
        horizon="24H",
        weights_version="v",
        threshold_version="t",
        minimum_score=70,
        threat_types=("CURANMOR",),
        written=False,
        days=[backtest.DayResult(date(2026, 1, 1), date(2025, 12, 31), 10, 2, 8, 3, 1)],
    )
    assert summary.precision == 0.2
    assert summary.recall == 0.4
    assert summary.unevaluable == 1

    empty = backtest.BacktestSummary(
        start=date(2026, 1, 1),
        end=date(2026, 1, 1),
        horizon="24H",
        weights_version="v",
        threshold_version="t",
        minimum_score=70,
        threat_types=("CURANMOR",),
        written=False,
    )
    assert empty.precision is None and empty.recall is None, "nol dibagi nol bukan nol"


def test_a_same_day_horizon_is_refused(session: Session) -> None:
    with pytest.raises(backtest.BacktestError):
        backtest.run_backtest(session, date(2026, 1, 1), date(2026, 1, 1), horizon="6H")
