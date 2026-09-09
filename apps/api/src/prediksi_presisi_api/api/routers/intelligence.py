"""API prediksi, peringatan, dan rekomendasi (TASK 036, 037, 038).

Prediksi selalu keluar bersama `dominant_factors` — termasuk `source` (`RULE`/`MODEL`).
Menyembunyikan asal penjelasan akan membuat antarmuka menyajikan hasil aturan seolah
temuan model (CLAUDE.md §27).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import EarlyWarning, Location, Prediction, Recommendation, RiskScore
from ...services.risk_engine import threshold_status_of
from ..deps import (
    CurrentUser,
    function_filter,
    get_db,
    jurisdiction_filter,
    require_permission,
)
from ..pagination import PageParams, page_params, paginate

router = APIRouter(tags=["intelijen"])


@router.get("/risk-scores", summary="Layer risiko berjalan")
def list_risk_scores(
    session: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    current: CurrentUser = require_permission("risk_score:read"),
    threat_type: str | None = Query(None),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "risk_score:read")

    query = (
        select(RiskScore, Location)
        .join(Location, Location.location_id == RiskScore.location_id)
        .order_by(RiskScore.assessment_date.desc(), RiskScore.risk_score.desc())
    )
    if polsek:
        query = query.where(Location.polsek == polsek)
    if threat_type:
        query = query.where(RiskScore.threat_type == threat_type)

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.execute(query.offset(params.offset).limit(params.page_size)).all()

    return paginate(
        [
            {
                "code": score.code,
                "assessment_date": score.assessment_date,
                "threat_type": score.threat_type,
                "time_window": score.time_window,
                "window_start": score.window_start,
                "window_end": score.window_end,
                "risk_score": score.risk_score,
                "risk_class": score.risk_class,
                "kecamatan": location.kecamatan,
                "grid_id": location.grid_id,
                "weights_version": score.weights_version,
            }
            for score, location in rows
        ],
        total,
        params,
    )


@router.get("/predictions", summary="Daftar prediksi")
def list_predictions(
    session: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    current: CurrentUser = require_permission("prediction:read"),
    horizon: str | None = Query(None, description="6H, 12H, 24H, 3D, atau 7D"),
    threat_type: str | None = Query(None),
    status: str | None = Query(None),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "prediction:read")

    query = (
        select(Prediction, Location)
        .join(Location, Location.location_id == Prediction.location_id)
        .order_by(Prediction.prediction_date.desc(), Prediction.risk_score.desc())
    )
    if polsek:
        query = query.where(Location.polsek == polsek)
    if horizon:
        query = query.where(Prediction.forecast_horizon == horizon.upper())
    if threat_type:
        query = query.where(Prediction.threat_type == threat_type)
    if status:
        query = query.where(Prediction.status == status.upper())

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.execute(query.offset(params.offset).limit(params.page_size)).all()

    return paginate(
        [
            {
                "code": prediction.code,
                "prediction_date": prediction.prediction_date,
                "forecast_horizon": prediction.forecast_horizon,
                "threat_type": prediction.threat_type,
                "time_window": prediction.time_window,
                "window_start": prediction.window_start,
                "window_end": prediction.window_end,
                "risk_score": prediction.risk_score,
                "confidence": prediction.confidence,
                "dominant_factors": prediction.dominant_factors,
                "model_version": prediction.model_version,
                "status": prediction.status,
                "kecamatan": location.kecamatan,
                "kelurahan": location.kelurahan,
                "grid_id": location.grid_id,
            }
            for prediction, location in rows
        ],
        total,
        params,
    )


@router.get("/warnings", summary="Daftar peringatan dini")
def list_warnings(
    session: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    current: CurrentUser = require_permission("warning:read"),
    status: str | None = Query(None, description="ACTIVE, ACKNOWLEDGED, RESOLVED"),
    severity: str | None = Query(None),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "warning:read")

    query = (
        select(EarlyWarning, Location, Prediction.code)
        .join(Location, Location.location_id == EarlyWarning.location_id)
        .join(Prediction, Prediction.prediction_id == EarlyWarning.prediction_id)
        .order_by(EarlyWarning.risk_score.desc(), EarlyWarning.created_at.desc())
    )
    if polsek:
        query = query.where(Location.polsek == polsek)
    if status:
        query = query.where(EarlyWarning.status == status.upper())
    if severity:
        query = query.where(EarlyWarning.severity == severity.upper())

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.execute(query.offset(params.offset).limit(params.page_size)).all()

    return paginate(
        [
            {
                "code": warning.code,
                "severity": warning.severity,
                "threat_type": warning.threat_type,
                "time_window": warning.time_window,
                "window_start": warning.window_start,
                "window_end": warning.window_end,
                "risk_score": warning.risk_score,
                "confidence": warning.confidence,
                "status": warning.status,
                "created_at": warning.created_at,
                "kecamatan": location.kecamatan,
                "kelurahan": location.kelurahan,
                "grid_id": location.grid_id,
                "prediction_code": prediction_code,
                "threshold_version": warning.threshold_version,
                # Status versi ambang MILIK BARIS INI. Sebelum 9 September 2026 layar
                # peringatan menuliskan "DEMO / PROPOSED" sebagai teks tetap, sehingga ia
                # tidak ikut berubah ketika ambangnya ditetapkan — layar dan konfigurasi
                # menyatakan dua hal berbeda tanpa ada yang gagal.
                "threshold_status": threshold_status_of(warning.threshold_version),
            }
            for warning, location, prediction_code in rows
        ],
        total,
        params,
    )


@router.get("/recommendations", summary="Daftar rekomendasi")
def list_recommendations(
    session: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    current: CurrentUser = require_permission("recommendation:read"),
    warning_code: str | None = Query(None),
    status: str | None = Query(None),
) -> dict[str, Any]:
    warning_alias = EarlyWarning
    # Rekomendasi mewarisi wilayah dari prediksinya; tanpa join ke Location cakupan
    # Polsek tidak dapat ditegakkan dan seluruh Jakarta Selatan ikut terbaca.
    polsek = jurisdiction_filter(current, "recommendation:read")
    function = function_filter(current, "recommendation:read")

    query = (
        select(Recommendation, Prediction.code, warning_alias.code)
        .join(Prediction, Prediction.prediction_id == Recommendation.prediction_id)
        .join(Location, Location.location_id == Prediction.location_id)
        .outerjoin(warning_alias, warning_alias.warning_id == Recommendation.warning_id)
        .order_by(Recommendation.created_at.desc())
    )
    if polsek:
        query = query.where(Location.polsek == polsek)
    if function:
        query = query.where(Recommendation.recommended_function == function)
    if warning_code:
        query = query.where(warning_alias.code == warning_code)
    if status:
        query = query.where(Recommendation.status == status.upper())

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.execute(query.offset(params.offset).limit(params.page_size)).all()

    return paginate(
        [
            {
                "code": recommendation.code,
                "recommended_function": recommendation.recommended_function,
                "recommendation_text": recommendation.recommendation_text,
                "priority": recommendation.priority,
                "status": recommendation.status,
                "created_at": recommendation.created_at,
                "prediction_code": prediction_code,
                "warning_code": warning_code_row,
            }
            for recommendation, prediction_code, warning_code_row in rows
        ],
        total,
        params,
    )
