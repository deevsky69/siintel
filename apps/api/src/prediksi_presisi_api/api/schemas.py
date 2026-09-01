"""Skema respons API (TASK 031–040).

Bentuk respons sengaja dekat dengan kebutuhan layar, tetapi **tidak menyembunyikan
asal datanya**: setiap prediksi membawa `dominant_factors` lengkap dengan `source`
(`RULE`/`MODEL`), dan setiap skor membawa versi konfigurasi yang dipakai.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LocationOut(Model):
    code: str
    grid_id: str
    polsek: str
    kecamatan: str
    kelurahan: str | None
    latitude: float
    longitude: float
    location_type: str | None


class CrimeIncidentOut(Model):
    code: str
    incident_type: str
    occurred_at: datetime
    incident_date: date
    incident_time: Any
    location_type: str | None
    modus: str | None
    target_type: str | None
    status: str | None
    kecamatan: str
    kelurahan: str | None
    polsek: str
    grid_id: str


class RiskScoreOut(Model):
    code: str
    assessment_date: date
    threat_type: str
    time_window: str | None
    window_start: datetime
    window_end: datetime
    risk_score: int
    risk_class: str
    kecamatan: str
    grid_id: str
    #: Versi bobot yang dipakai — angka risiko tidak boleh tampil tanpa asalnya.
    weights_version: str | None


class PredictionOut(Model):
    code: str
    prediction_date: date
    forecast_horizon: str
    threat_type: str
    time_window: str | None
    window_start: datetime
    window_end: datetime
    risk_score: int
    confidence: int
    #: WHY — daftar {factor, contribution, source}. `source` wajib ikut ditampilkan UI.
    dominant_factors: list[dict[str, Any]]
    model_version: str
    status: str
    kecamatan: str
    kelurahan: str | None
    grid_id: str


class WarningOut(Model):
    code: str
    severity: str
    threat_type: str
    time_window: str | None
    window_start: datetime
    window_end: datetime
    risk_score: int
    confidence: int | None
    status: str
    created_at: datetime
    kecamatan: str
    kelurahan: str | None
    grid_id: str
    prediction_code: str
    threshold_version: str | None


class RecommendationOut(Model):
    code: str
    recommended_function: str
    recommendation_text: str
    priority: str | None
    status: str
    created_at: datetime
    prediction_code: str
    warning_code: str | None


class EvaluationMetrics(Model):
    """Metrik evaluasi model.

    `basis` menyatakan cakupan yang dipakai. Selama aturan pencocokan belum ditetapkan
    (U-03), angka ini **wajib** disajikan sebagai `PROPOSED` (docs/05 §2.10).
    """

    hits: int
    false_positives: int
    false_negatives: int
    precision: float | None
    recall: float | None
    evaluated_rows: int
    status: str = "PROPOSED"
    basis: str
