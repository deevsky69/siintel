"""Test data analitik (TASK 022): pembangkitan ulang dan pemuatan.

Menjaga acceptance A-3 sampai A-6 (`docs/08` PHASE 3) agar tidak diam-diam rusak lagi.
"""

from __future__ import annotations

import json
import os
import random
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.models import EarlyWarning, Prediction, Recommendation, RiskScore
from prediksi_presisi_api.seeding import SeedError
from prediksi_presisi_api.seeding import csv_source as src
from prediksi_presisi_api.seeding.analytics import _check_factor_consistency, seed_analytics_data
from prediksi_presisi_api.seeding.regenerate import (
    FACTOR_COLUMNS,
    HORIZONS,
    RANDOM_SEED,
    build_factors,
    explain,
    load_risk_config,
)

DATABASE_URL = os.environ.get("DATABASE_URL", "")


# --------------------------------------------------------------------------------------
# Tanpa database
# --------------------------------------------------------------------------------------


def test_weights_sum_to_one() -> None:
    config = load_risk_config()

    assert abs(sum(config.weights.values()) - 1.0) < 1e-9


def test_generated_factors_actually_produce_the_score() -> None:
    config = load_risk_config()
    rng = random.Random(RANDOM_SEED)  # noqa: S311 — data sintetis

    for target in range(0, 101, 7):
        factors = build_factors(target, config, rng)

        computed = round(sum(config.weights[name] * factors[name] for name in FACTOR_COLUMNS))
        assert computed == target
        assert all(0 <= value <= 100 for value in factors.values())


def test_generation_is_deterministic() -> None:
    config = load_risk_config()

    first = build_factors(76, config, random.Random(RANDOM_SEED))  # noqa: S311
    second = build_factors(76, config, random.Random(RANDOM_SEED))  # noqa: S311

    assert first == second


def test_explanation_is_marked_as_rule_not_model() -> None:
    """CLAUDE.md §27: penjelasan harus menyebut mekanisme yang benar-benar dipakai."""
    config = load_risk_config()
    factors = build_factors(80, config, random.Random(RANDOM_SEED))  # noqa: S311

    factors_explained = explain(factors, 80, config)

    assert len(factors_explained) == 3
    assert {item["source"] for item in factors_explained} == {"RULE"}


def test_dataset_factors_are_consistent_with_the_configured_weights() -> None:
    """A-3 pada berkas sumber: seluruh baris, bukan sebagian."""
    config = load_risk_config()

    for row in src.read_rows("risk_scores.csv"):
        computed = round(sum(config.weights[name] * int(row[name]) for name in FACTOR_COLUMNS))
        assert computed == int(row["risk_score"]), row["risk_score_id"]


def test_dataset_covers_every_forecast_horizon() -> None:
    """A-4: predictive heatmap NOW→+6H→…→+7D butuh kelima horizon."""
    horizons = {row["forecast_horizon"] for row in src.read_rows("predictions.csv")}

    assert horizons == set(HORIZONS)


def test_dataset_explanations_are_not_all_identical() -> None:
    """A-5: WHY yang sama untuk semua prediksi bukan penjelasan, melainkan hiasan."""
    rows = src.read_rows("predictions.csv")

    explanations = {row["dominant_factors"] for row in rows}

    assert len(explanations) == len(rows)


def test_every_prediction_has_a_companion_risk_score() -> None:
    """A-6: layer risiko berjalan dan layer prediktif harus konsisten saat didemokan."""
    risk_keys = {
        (row["grid_id"], row["threat_type"], row["time_window"], row["assessment_date"])
        for row in src.read_rows("risk_scores.csv")
    }

    missing = [
        row["prediction_id"]
        for row in src.read_rows("predictions.csv")
        if (row["grid_id"], row["threat_type"], row["time_window"], row["prediction_date"])
        not in risk_keys
    ]

    assert missing == []


def test_inconsistent_factors_stop_the_seed() -> None:
    config = load_risk_config()
    row = {
        "risk_score": "80",
        "historical_factor": "10",
        "recent_trend_factor": "10",
        "temporal_factor": "10",
        "spatial_factor": "10",
        "context_factor": "10",
    }

    with pytest.raises(SeedError, match="risk_score tertulis"):
        _check_factor_consistency(row, config, "uji")


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
def test_analytics_seed_loads_expected_volumes(session: Session) -> None:
    seed_analytics_data(session)
    session.flush()

    # Sama seperti pada seed kejadian dan operasional: yang diperiksa adalah baris yang
    # berasal dari berkas sumber, bukan jumlah seluruh isi tabel. Penilaian risiko yang
    # dijalankan lewat `/skoring` menambah baris yang sah, dan test yang mengunci
    # `COUNT(*)` akan patah tepat ketika mesin penilaiannya mulai dipakai.
    for name, column, model in (
        ("risk_scores.csv", "risk_score_id", RiskScore),
        ("predictions.csv", "prediction_id", Prediction),
        ("early_warnings.csv", "warning_id", EarlyWarning),
        ("recommendations.csv", "recommendation_id", Recommendation),
    ):
        codes = {row[column] for row in src.read_rows(name)}
        loaded = session.scalar(
            select(func.count()).select_from(model).where(model.code.in_(codes))
        )
        assert loaded == len(codes), f"{name}: {loaded} dari {len(codes)} baris termuat"
    assert session.scalar(select(func.count()).select_from(Recommendation)) == 84


@requires_database
def test_every_prediction_explains_itself(session: Session) -> None:
    seed_analytics_data(session)
    session.flush()

    for prediction in session.scalars(select(Prediction)).all():
        factors = prediction.dominant_factors
        assert factors, prediction.code
        assert all(item["source"] in {"RULE", "MODEL"} for item in factors)


@requires_database
def test_predictions_are_traceable_to_a_baseline_risk_score(session: Session) -> None:
    seed_analytics_data(session)
    session.flush()

    untraceable = session.scalar(
        select(func.count())
        .select_from(Prediction)
        .where(Prediction.baseline_risk_score_id.is_(None))
    )

    assert untraceable == 0


@requires_database
def test_warnings_only_appear_above_the_configured_threshold(session: Session) -> None:
    seed_analytics_data(session)
    session.flush()
    config = load_risk_config()

    below = session.scalar(
        select(func.count())
        .select_from(EarlyWarning)
        .where(EarlyWarning.risk_score < config.minimum_warning_score)
    )

    assert below == 0


@requires_database
def test_analytics_seed_is_idempotent(session: Session) -> None:
    seed_analytics_data(session)
    session.flush()

    second = seed_analytics_data(session)
    session.flush()

    assert sum(second.inserted.values()) == 0


@requires_database
def test_stored_explanations_survive_the_round_trip(session: Session) -> None:
    seed_analytics_data(session)
    session.flush()

    prediction = session.scalar(select(Prediction).where(Prediction.code == "PRD-00001"))
    source_row = next(
        row for row in src.read_rows("predictions.csv") if row["prediction_id"] == "PRD-00001"
    )

    assert prediction is not None
    assert prediction.dominant_factors == json.loads(source_row["dominant_factors"])
