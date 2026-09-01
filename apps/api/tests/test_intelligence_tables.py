"""Test tabel intelijen (TASK 013): risk_scores, predictions, early_warnings, recommendations."""

from __future__ import annotations

from sqlalchemy import CheckConstraint, UniqueConstraint

from prediksi_presisi_api.db import Base
from prediksi_presisi_api.models.prediction import FORECAST_HORIZONS
from prediksi_presisi_api.models.risk_score import RISK_FACTORS

INTELLIGENCE_TABLES = {"risk_scores", "predictions", "early_warnings", "recommendations"}


def _check_names(table: str) -> set[str]:
    return {
        str(constraint.name)
        for constraint in Base.metadata.tables[table].constraints
        if isinstance(constraint, CheckConstraint)
    }


def test_intelligence_tables_are_registered() -> None:
    assert set(Base.metadata.tables) >= INTELLIGENCE_TABLES


def test_risk_score_and_prediction_are_separate_layers() -> None:
    # docs/04: risk_scores = risiko berjalan, predictions = perkiraan ke depan.
    # Keterkaitannya opsional dan hanya untuk penelusuran, bukan rantai wajib.
    column = Base.metadata.tables["predictions"].c.baseline_risk_score_id

    assert column.nullable is True
    assert next(iter(column.foreign_keys)).column.table.name == "risk_scores"


def test_every_risk_factor_is_range_constrained() -> None:
    checks = _check_names("risk_scores")

    for factor in RISK_FACTORS:
        assert f"ck_risk_scores_{factor}_range" in checks


def test_risk_score_weight_relationship_is_not_locked() -> None:
    # Bobot belum ditetapkan (U-02), jadi hubungan risk_score = Σ(bobot × faktor)
    # sengaja BELUM dijadikan constraint (docs/06 §3). Yang disimpan hanya versinya.
    checks = _check_names("risk_scores")

    assert not any("weight" in name or "sum" in name for name in checks)
    assert "weights_version" in Base.metadata.tables["risk_scores"].c


def test_risk_class_thresholds_are_not_locked() -> None:
    # Batas kelas risiko masih keputusan pemilik proyek (U-01).
    checks = _check_names("risk_scores")

    assert not any("risk_class" in name for name in checks)


def test_prediction_requires_explanation() -> None:
    # CLAUDE.md §10 dan §27: setiap prediksi harus dapat menjelaskan WHY.
    column = Base.metadata.tables["predictions"].c.dominant_factors

    assert column.nullable is False
    assert type(column.type).__name__ == "JSONB"


def test_prediction_horizons_follow_specification() -> None:
    # docs/01 §5.5 menetapkan lima horizon; ini requirement, bukan taksonomi terbuka.
    assert FORECAST_HORIZONS == ("6H", "12H", "24H", "3D", "7D")
    assert "ck_predictions_forecast_horizon_allowed" in _check_names("predictions")


def test_prediction_is_unique_per_forecast() -> None:
    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in Base.metadata.tables["predictions"].constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert (
        "location_id",
        "threat_type",
        "window_start",
        "forecast_horizon",
        "model_version",
        "prediction_date",
    ) in unique_columns


def test_warning_always_comes_from_a_prediction() -> None:
    # docs/04: early_warnings hanya bersumber dari predictions.
    column = Base.metadata.tables["early_warnings"].c.prediction_id

    assert column.nullable is False
    assert next(iter(column.foreign_keys)).column.table.name == "predictions"


def test_warning_handling_records_the_actor() -> None:
    # Status ACKNOWLEDGED/RESOLVED harus dapat ditelusuri ke penggunanya (CLAUDE.md §29).
    columns = Base.metadata.tables["early_warnings"].c
    checks = _check_names("early_warnings")

    assert next(iter(columns.acknowledged_by.foreign_keys)).column.table.name == "users"
    assert next(iter(columns.resolved_by.foreign_keys)).column.table.name == "users"
    assert "ck_early_warnings_acknowledged_needs_actor" in checks
    assert "ck_early_warnings_resolved_needs_actor" in checks


def test_warning_severity_thresholds_are_not_locked() -> None:
    # Threshold severity masih keputusan pemilik proyek (U-01).
    checks = _check_names("early_warnings")

    assert not any("severity" in name for name in checks)
    assert "threshold_version" in Base.metadata.tables["early_warnings"].c


def test_recommendation_is_advisory_only() -> None:
    # Rekomendasi menunjuk prediksi/peringatan, tetapi TIDAK menunjuk unit atau tindakan.
    # Jalur menuju tindakan wajib lewat commander_decisions (TASK 014, CLAUDE.md §13).
    columns = set(Base.metadata.tables["recommendations"].c.keys())

    assert "prediction_id" in columns
    assert "unit_id" not in columns
    assert "action_id" not in columns
    assert "decision_id" not in columns


def test_recommendation_warning_link_is_optional() -> None:
    assert Base.metadata.tables["recommendations"].c.warning_id.nullable is True
