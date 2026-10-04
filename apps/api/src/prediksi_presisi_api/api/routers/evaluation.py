"""API evaluasi model (TASK 040).

Menopang success criteria #06 Taskap: **Prediction vs Actual**.

Angka precision/recall di sini **selalu** disertai penanda `PROPOSED` dan penjelasan
cakupannya. Aturan pencocokan spasial-temporal antara prediksi dan kejadian nyata belum
ditetapkan (U-03), sehingga menyajikannya sebagai angka final akan melampaui yang benar-benar
dapat dipertanggungjawabkan (docs/05 §2.10, CLAUDE.md §26).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import CrimeIncident, Prediction, PredictionActual
from ...services import risk_engine as risk
from ...services import visibility
from ..deps import CurrentUser, get_db, require_permission

router = APIRouter(prefix="/evaluation", tags=["evaluasi"])


def _evaluated_threats() -> tuple[str, ...]:
    """Jenis yang benar-benar dinilai versi bobot aktif — bukan daftar tetap di kode.

    Sampai 1 Oktober 2026 daftar ini diambil dari konstanta seeder sintetis. Begitu versi
    aktif menyempit ke tiga jenis data asli, konstanta itu kebetulan masih benar — dan
    kebetulan bukan dasar yang boleh diandalkan evaluasi.
    """
    profile = risk.load_weights().active.profiles.get(risk.PROFILE_HISTORICAL)
    return () if profile is None else profile.applies_to


def evaluation_basis() -> str:
    return (
        "Cakupan: kejadian nyata pada periode prediksi untuk jenis ancaman yang diprediksi "
        f"({', '.join(_evaluated_threats())}). False negative dihitung dari kejadian pada sel "
        "tanpa prediksi terbit. Aturan pencocokan final belum ditetapkan (U-03)."
    )


def _counts(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(PredictionActual.match_type, func.count()).group_by(PredictionActual.match_type)
    ).all()
    return {match_type: total for match_type, total in rows}


@router.get("/metrics", summary="Precision, recall, FP, FN")
def metrics(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("evaluation:read"),
) -> dict[str, Any]:
    counts = _counts(session)
    hits = counts.get("HIT", 0)
    false_positives = counts.get("FALSE_POSITIVE", 0)
    false_negatives = counts.get("FALSE_NEGATIVE", 0)

    predicted = hits + false_positives
    actual = hits + false_negatives

    period = session.execute(
        select(
            func.min(PredictionActual.evaluation_date), func.max(PredictionActual.evaluation_date)
        )
    ).one()
    threats = _evaluated_threats()
    unevaluable = 0
    if period[0] is not None and threats:
        # Kejadian tanpa jam pada periode evaluasi: tidak dapat ditempatkan pada jendela
        # mana pun, sehingga tidak masuk HIT/FN. Disebut, bukan disembunyikan (CLAUDE.md §26).
        unevaluable = (
            session.scalar(
                # Periode evaluasi berada di luar batas tampilan layar; dinyatakan eksplisit.
                visibility.all_incidents(
                    select(func.count())
                    .select_from(CrimeIncident)
                    .where(
                        CrimeIncident.incident_date >= period[0],
                        CrimeIncident.incident_date <= period[1],
                        CrimeIncident.incident_type.in_(threats),
                        CrimeIncident.time_known.is_(False),
                    )
                )
            )
            or 0
        )
    thresholds = risk.load_thresholds()

    return {
        "hits": hits,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "unevaluable_incidents": unevaluable,
        "evaluated_from": period[0],
        "evaluated_to": period[1],
        "warning_floor": thresholds.minimum_warning_score,
        "threshold_version": thresholds.version,
        "threat_types": list(threats),
        # Pembagian nol dijawab None, bukan 0: "tidak dapat dihitung" berbeda maknanya
        # dari "nilainya nol".
        "precision": round(hits / predicted, 3) if predicted else None,
        "recall": round(hits / actual, 3) if actual else None,
        "evaluated_rows": sum(counts.values()),
        "status": "PROPOSED",
        "basis": evaluation_basis(),
    }


@router.get("/summary", summary="Ringkasan evaluasi per jenis ancaman")
def summary(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("evaluation:read"),
) -> dict[str, Any]:
    rows = session.execute(
        select(
            PredictionActual.actual_threat_type,
            PredictionActual.match_type,
            func.count(),
        ).group_by(PredictionActual.actual_threat_type, PredictionActual.match_type)
    ).all()

    per_threat: dict[str, dict[str, int]] = {}
    for threat, match_type, total in rows:
        bucket = per_threat.setdefault(threat or "TIDAK DIKETAHUI", {})
        bucket[match_type] = total

    evaluated_models = session.scalars(
        select(Prediction.model_version).distinct().order_by(Prediction.model_version)
    ).all()

    return {
        "per_threat": per_threat,
        "model_versions": list(evaluated_models),
        "status": "PROPOSED",
        "basis": evaluation_basis(),
    }
