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

from ...models import Prediction, PredictionActual
from ...seeding.regenerate import EVALUATED_THREATS
from ..deps import CurrentUser, get_db, require_permission

router = APIRouter(prefix="/evaluation", tags=["evaluasi"])

BASIS = (
    "Cakupan: kejadian nyata pada periode prediksi untuk jenis ancaman yang diprediksi "
    f"({', '.join(EVALUATED_THREATS)}). False negative dihitung dari kejadian pada sel "
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

    return {
        "hits": hits,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        # Pembagian nol dijawab None, bukan 0: "tidak dapat dihitung" berbeda maknanya
        # dari "nilainya nol".
        "precision": round(hits / predicted, 3) if predicted else None,
        "recall": round(hits / actual, 3) if actual else None,
        "evaluated_rows": sum(counts.values()),
        "status": "PROPOSED",
        "basis": BASIS,
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
        "basis": BASIS,
    }
