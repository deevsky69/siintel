"""API dashboard eksekutif (TASK 070).

Menyediakan agregat untuk layar utama pada `design/gambaran-website.png`. Seluruh angka
dihitung dari database — tidak ada nilai yang ditanam di kode.

"24 jam terakhir" dihitung terhadap **waktu acuan** aplikasi, bukan waktu sebenarnya
(keputusan SDL-16). Respons menyertakan `reference_time` dan penanda `demo_clock`
sehingga antarmuka dapat menyatakannya terbuka kepada pembaca.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.orm import Session

from ...models import (
    CrimeIncident,
    EarlyWarning,
    Location,
    OperationalAction,
    PoliceUnit,
    Prediction,
    RiskScore,
)
from ...services import clock
from ..deps import CurrentUser, get_db, jurisdiction_filter, require_permission

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

#: Berapa jauh ke belakang panel "kejadian 24 jam" melihat.
RECENT_HOURS = 24

#: Skor keamanan = 100 dikurangi rata-rata **seluruh** sel risiko pada tanggal penilaian
#: terakhir.
#:
#: Rata-rata dihitung atas seluruh sel, bukan atas puncak tiap kecamatan: memakai puncak
#: membuat satu sel kritis mewakili seluruh wilayah dan indeksnya melebih-lebihkan keadaan.
#:
#: Rumus ini **turunan tampilan**, bukan indeks resmi — belum ada penetapan (U-01/U-02),
#: sehingga responsnya selalu menyertakan `security_index_basis`.
SECURITY_INDEX_BASE = 100

#: Ambang "wilayah berisiko tinggi", sepadan config/risk/warning-thresholds.yaml
#: versi dummy-v1 yang ditetapkan 9 September 2026 (U-01).
HIGH_RISK_THRESHOLD = 70


def _latest_assessment_date(session: Session) -> Any:
    return session.scalar(select(func.max(RiskScore.assessment_date)))


@router.get("/summary", summary="Ringkasan situasi untuk layar utama")
def summary(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("dashboard:read"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "dashboard:read")
    since, now = clock.window(RECENT_HOURS)
    forward_start, forward_end = clock.forward_window(RECENT_HOURS)

    def scoped(query: Any) -> Any:
        return query if polsek is None else query.where(Location.polsek == polsek)

    incidents_24h = session.scalar(
        scoped(
            select(func.count())
            .select_from(CrimeIncident)
            .join(Location, Location.location_id == CrimeIncident.location_id)
            .where(CrimeIncident.occurred_at.between(since, now))
        )
    )

    predictions_24h = session.scalar(
        scoped(
            select(func.count())
            .select_from(Prediction)
            .join(Location, Location.location_id == Prediction.location_id)
            .where(Prediction.window_start.between(forward_start, forward_end))
        )
    )

    active_warnings = session.scalar(
        scoped(
            select(func.count())
            .select_from(EarlyWarning)
            .join(Location, Location.location_id == EarlyWarning.location_id)
            .where(EarlyWarning.status == "ACTIVE")
        )
    )

    latest_date = _latest_assessment_date(session)

    # Risiko tertinggi per kecamatan pada tanggal penilaian terakhir.
    per_district_query = scoped(
        select(Location.kecamatan, func.max(RiskScore.risk_score).label("risk_score"))
        .select_from(RiskScore)
        .join(Location, Location.location_id == RiskScore.location_id)
        .where(RiskScore.assessment_date == latest_date)
        .group_by(Location.kecamatan)
        .order_by(func.max(RiskScore.risk_score).desc())
    )
    per_district = [
        {"kecamatan": kecamatan, "risk_score": int(score)}
        for kecamatan, score in session.execute(per_district_query).all()
    ]

    high_risk_areas = sum(1 for row in per_district if row["risk_score"] >= HIGH_RISK_THRESHOLD)

    average_risk = session.scalar(
        scoped(
            select(func.avg(RiskScore.risk_score))
            .select_from(RiskScore)
            .join(Location, Location.location_id == RiskScore.location_id)
            .where(RiskScore.assessment_date == latest_date)
        )
    )
    average_risk = round(float(average_risk)) if average_risk is not None else 0

    top_threats_query = scoped(
        select(RiskScore.threat_type, func.max(RiskScore.risk_score))
        .select_from(RiskScore)
        .join(Location, Location.location_id == RiskScore.location_id)
        .where(RiskScore.assessment_date == latest_date)
        .group_by(RiskScore.threat_type)
        .order_by(func.max(RiskScore.risk_score).desc())
    )
    top_threats = [
        {"threat_type": threat, "risk_score": int(score)}
        for threat, score in session.execute(top_threats_query).all()
    ]

    units = session.execute(
        select(PoliceUnit.status, func.count()).group_by(PoliceUnit.status)
    ).all()
    active_actions = session.scalar(
        select(func.count())
        .select_from(OperationalAction)
        .where(OperationalAction.status.in_(["PLANNED", "ACTIVE"]))
    )

    # Jam paling rawan menurut sebaran kejadian historis.
    critical_window = session.execute(
        scoped(
            select(RiskScore.time_window, func.max(RiskScore.risk_score))
            .select_from(RiskScore)
            .join(Location, Location.location_id == RiskScore.location_id)
            .where(RiskScore.assessment_date == latest_date)
            .group_by(RiskScore.time_window)
            .order_by(func.max(RiskScore.risk_score).desc())
            .limit(1)
        )
    ).first()

    return {
        "reference_time": now,
        "demo_clock": clock.is_demo_clock(),
        "assessment_date": latest_date,
        "security_index": max(0, SECURITY_INDEX_BASE - average_risk),
        "security_index_basis": (
            "100 dikurangi rata-rata seluruh sel risiko pada tanggal penilaian terakhir. "
            "Indeks keamanan resmi belum ditetapkan (U-01/U-02); angka ini turunan tampilan."
        ),
        "high_risk_basis": (
            f"Kecamatan dengan sel risiko tertinggi mencapai {HIGH_RISK_THRESHOLD}. "
            "Ambang ditetapkan 9 September 2026 (U-01)."
        ),
        "incidents_24h": incidents_24h or 0,
        "predictions_24h": predictions_24h or 0,
        "high_risk_areas": high_risk_areas,
        "active_warnings": active_warnings or 0,
        "active_operations": active_actions or 0,
        "critical_time_window": critical_window[0] if critical_window else None,
        "top_threats": top_threats,
        "risk_by_district": per_district,
        "units": [{"status": status, "count": total} for status, total in units],
    }


@router.get("/trends", summary="Tren kejadian per bulan")
def trends(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("dashboard:read"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "dashboard:read")

    query = (
        select(
            cast(func.extract("year", CrimeIncident.incident_date), Integer).label("tahun"),
            cast(func.extract("month", CrimeIncident.incident_date), Integer).label("bulan"),
            func.count().label("jumlah"),
        )
        .select_from(CrimeIncident)
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .group_by("tahun", "bulan")
        .order_by("tahun", "bulan")
    )
    if polsek:
        query = query.where(Location.polsek == polsek)

    series: dict[int, list[int]] = {}
    for year, month, total in session.execute(query).all():
        series.setdefault(int(year), [0] * 12)[int(month) - 1] = int(total)

    return {
        "years": sorted(series),
        "series": [{"year": year, "monthly": series[year]} for year in sorted(series)],
    }


@router.get("/predictive-outlook", summary="Prediksi per horizon untuk panel NOW→+24H")
def predictive_outlook(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("prediction:read"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "prediction:read")

    horizons = ["6H", "12H", "24H", "3D", "7D"]
    outlook: list[dict[str, Any]] = []

    for horizon in horizons:
        query = (
            select(Location.kecamatan, Prediction.risk_score, Prediction.threat_type)
            .select_from(Prediction)
            .join(Location, Location.location_id == Prediction.location_id)
            .where(Prediction.forecast_horizon == horizon, Prediction.status != "DRAFT")
            .order_by(Prediction.risk_score.desc())
            .limit(1)
        )
        if polsek:
            query = query.where(Location.polsek == polsek)

        row = session.execute(query).first()
        outlook.append(
            {
                "horizon": horizon,
                "kecamatan": row[0] if row else None,
                "risk_score": int(row[1]) if row else None,
                "threat_type": row[2] if row else None,
            }
        )

    return {"reference_time": clock.reference_now(), "outlook": outlook}
