"""API AI Prediction Center — menjalankan prediksi dan mempublikasikannya (docs/05 §2.6).

Dua endpoint, dan keduanya ada karena alasan yang berbeda:

```text
POST /predictions/run              memproyeksikan penilaian risiko ke depan  prediction:run
POST /predictions/{code}/publish   DRAFT -> PUBLISHED                    prediction:publish
```

Yang dihasilkan **bukan** keluaran model terlatih. Prediksi di sini adalah proyeksi
persistensi berbasis aturan atas baris `risk_scores` yang sudah ada: `model_version`
menyebut versi aturan, bukan nama model, dan seluruh `dominant_factors` berlabel `RULE`
(CLAUDE.md §25, §27). Rincian mekanismenya ada di `services/prediction_engine.py`.

EMPAT KEPUTUSAN YANG MENENTUKAN BENTUK MODUL INI

1. **`dry_run` bernilai benar secara bawaan**, sama seperti `POST /risk-scores/run`.
   Menjalankan prediksi menambah ratusan baris yang akan terbaca di peta dan Warning
   Center. Yang harus dinyatakan secara sadar adalah menulisnya, bukan menahannya.

2. **Prediksi yang sudah ada pada tanggal + horizon yang sama tidak ditimpa (409).**
   Prediksi adalah pernyataan bertanggal tentang apa yang akan terjadi; menimpanya
   berarti mengubah pernyataan itu setelah kenyataannya diketahui, dan evaluasi
   precision/recall kehilangan artinya (CLAUDE.md §26). Cara yang benar untuk memprediksi
   ulang adalah tanggal prediksi baru.

3. **Publikasi adalah tindakan tersendiri, bukan efek samping menjalankan prediksi.**
   Hanya prediksi `PUBLISHED` yang boleh melahirkan peringatan dini. Menjadikannya
   otomatis akan membuat satu penekanan tombol menerbitkan ratusan peringatan tanpa
   seorang pun membacanya lebih dahulu — persis kebalikan dari human-in-the-loop
   (CLAUDE.md §13). Kewenangannya pun terpisah: `prediction:run` dan `prediction:publish`.

4. **Prediksi yang sudah `PUBLISHED` atau `VALIDATED` tidak dapat dipublikasikan ulang
   (409).** `VALIDATED` berarti sudah dibandingkan dengan kenyataan; mengembalikannya ke
   jalur publikasi akan menghapus urutan waktu yang menjadi dasar evaluasi.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Path, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import Location, Prediction
from ...models.prediction import FORECAST_HORIZONS
from ...services import audit, clock
from ...services import prediction_engine as engine
from ..deps import (
    CurrentUser,
    get_db,
    jurisdiction_filter,
    not_found,
    require_permission,
    scope_of,
)
from ..errors import ApiError

router = APIRouter(tags=["prediksi"])

AUDIT_RUN = "RUN_PREDICTION"
AUDIT_PUBLISH = "PUBLISH_PREDICTION"
AUDIT_RESOURCE = "prediction"

#: Baris contoh yang dibawa respons penjalanan. Ringkasan dimaksudkan untuk dibaca sekilas
#: sebelum memutuskan menulis; daftar lengkapnya ada di `GET /predictions`.
SAMPLE_ROWS = 10

#: Banyaknya alasan berbeda yang ditampilkan untuk kombinasi yang tidak diprediksi.
SAMPLE_REASONS = 5

DRY_RUN_BASIS = (
    "dry_run bernilai true secara bawaan: tidak ada satu baris predictions pun yang "
    "ditulis, dan angka pada respons ini adalah hasil perhitungan di memori. Menulis harus "
    "dinyatakan secara sadar dengan dry_run=false."
)

STATUS_BASIS = (
    "Prediksi baru berstatus DRAFT dan tidak melahirkan peringatan apa pun. Publikasi "
    "dilakukan terpisah melalui POST /predictions/{code}/publish dengan kewenangan "
    "prediction:publish."
)


class RunRequest(BaseModel):
    """Permintaan menjalankan prediksi."""

    prediction_date: date | None = Field(
        default=None,
        description=(
            "Tanggal prediksi dibuat. Kosong berarti tanggal pada waktu acuan aplikasi — "
            "dataset berhenti Desember 2025 dan jam dinding tidak dipakai (SDL-16)."
        ),
    )
    horizon: str = Field(
        default="24H",
        description=(
            f"Jarak dari tanggal prediksi ke hari yang diprediksi: "
            f"{', '.join(FORECAST_HORIZONS)}. Bukan panjang rentang — satu prediksi selalu "
            "mencakup tepat satu jendela 6 jam."
        ),
    )
    dry_run: bool = Field(
        default=True,
        description="Bawaan true: menghitung dan mengembalikan ringkasan tanpa menulis apa pun.",
    )


def _reject_partial_scope(current: CurrentUser, permission: str) -> None:
    """Akun yang dibatasi wilayah tidak boleh menjalankan prediksi menyeluruh.

    Alasannya sama dengan `POST /risk-scores/run`: hasilnya akan tersimpan sebagai
    prediksi sebagian yang terlihat menyeluruh — sel di luar cakupan pengguna tidak pernah
    diprediksi, tetapi tanggal prediksinya terbaca lengkap bagi semua orang.
    """
    scope = scope_of(current, permission)
    if scope != "ALL":
        raise ApiError(
            status.HTTP_403_FORBIDDEN,
            "Prediksi menyeluruh tidak dapat dijalankan oleh akun yang dibatasi cakupan "
            f"({scope}): hasilnya akan tersimpan sebagai prediksi sebagian yang terlihat "
            "menyeluruh.",
        )


def _summary(projection: engine.Projection) -> dict[str, Any]:
    """Sebaran kelas risiko, ringkasan per jenis ancaman, dan alasan yang tidak diprediksi."""
    classes: dict[str, int] = {}
    threats: dict[str, dict[str, Any]] = {}

    for forecast in projection.predicted:
        score = forecast.risk_score or 0
        label = forecast.risk_class or "TIDAK DIKETAHUI"
        classes[label] = classes.get(label, 0) + 1

        threat = threats.setdefault(
            forecast.threat_type,
            {
                "threat_type": forecast.threat_type,
                "windows": 0,
                "highest": 0,
                "score_total": 0,
                "confidence_total": 0,
            },
        )
        threat["windows"] = int(threat["windows"]) + 1
        threat["score_total"] = int(threat["score_total"]) + score
        threat["confidence_total"] = int(threat["confidence_total"]) + (forecast.confidence or 0)
        threat["highest"] = max(int(threat["highest"]), score)

    for threat in threats.values():
        windows = int(threat["windows"])
        threat["average"] = round(int(threat["score_total"]) / windows)
        threat["average_confidence"] = round(int(threat["confidence_total"]) / windows)
        del threat["score_total"]
        del threat["confidence_total"]

    reasons: dict[str, int] = {}
    for forecast in projection.not_predicted:
        key = forecast.not_predicted_reason or "tidak diketahui"
        reasons[key] = reasons.get(key, 0) + 1

    top = sorted(projection.predicted, key=lambda item: item.risk_score or 0, reverse=True)

    return {
        "risk_class_distribution": classes,
        "by_threat_type": sorted(
            threats.values(), key=lambda item: int(item["highest"]), reverse=True
        ),
        "not_predicted_reasons": [
            {"reason": reason, "combinations": count}
            for reason, count in sorted(reasons.items(), key=lambda item: -item[1])[:SAMPLE_REASONS]
        ],
        "sample": [forecast.as_dict() for forecast in top[:SAMPLE_ROWS]],
    }


#: Bentuk kode prediksi yang dihasilkan mesin ini. Penomoran hanya melihat kode berbentuk
#: `PRD-00001`; kode lain yang mungkin ada di tabel tidak ikut menentukan nomor berikutnya,
#: sehingga satu baris berkode lain tidak dapat menghentikan seluruh penulisan.
CODE_PATTERN = "^PRD-[0-9]+$"


def _next_code_number(session: Session) -> int:
    latest = session.scalar(
        select(func.max(Prediction.code)).where(Prediction.code.regexp_match(CODE_PATTERN))
    )
    if latest is None:
        return 1
    return int(latest.rsplit("-", 1)[-1]) + 1


def _persist(session: Session, projection: engine.Projection) -> int:
    """Menulis baris prediksi. Hanya kombinasi yang benar-benar dapat diproyeksikan."""
    number = _next_code_number(session)
    written = 0

    for forecast in projection.predicted:
        session.add(
            Prediction(
                code=f"PRD-{number:05d}",
                prediction_date=projection.prediction_date,
                forecast_horizon=projection.horizon,
                threat_type=forecast.threat_type,
                location_id=forecast.location_id,
                time_window=forecast.time_window,
                window_start=forecast.window_start,
                window_end=forecast.window_end,
                risk_score=forecast.risk_score,
                confidence=forecast.confidence,
                dominant_factors=list(forecast.dominant_factors),
                # Versi ATURAN, bukan nama model: tidak ada model terlatih di baliknya.
                model_version=projection.rule_version,
                baseline_risk_score_id=(
                    None if forecast.baseline is None else forecast.baseline.risk_score_id
                ),
                status=engine.STATUS_DRAFT,
            )
        )
        number += 1
        written += 1

    return written


@router.post("/predictions/run", summary="Menjalankan prediksi untuk satu horizon")
def run_prediction(
    payload: RunRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("prediction:run"),
) -> dict[str, Any]:
    """Memproyeksikan penilaian risiko terakhir ke jendela waktu pada rentang horizon.

    Bawaan `dry_run=true` hanya menghitung. `dry_run=false` menulis baris berstatus
    `DRAFT`, dan **menolak** bila tanggal prediksi + horizon tersebut sudah memiliki baris
    (409).
    """
    _reject_partial_scope(current, "prediction:run")
    prediction_date = payload.prediction_date or clock.reference_now().date()
    horizon = payload.horizon.upper()

    try:
        projection = engine.project(session, prediction_date, horizon)
    except engine.PredictionEngineError as error:
        # Horizon tidak dikenal atau konfigurasi risiko rusak. Pesannya disampaikan apa
        # adanya karena hanya menyebut config/risk/ dan daftar horizon, bukan struktur
        # internal.
        audit.record(
            session,
            action=AUDIT_RUN,
            resource_type=AUDIT_RESOURCE,
            result=audit.RESULT_FAILED,
            user_id=current.user.user_id,
            resource_id=f"{prediction_date.isoformat()}/{horizon}",
            detail={"reason": str(error)},
        )
        session.commit()
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    existing = (
        session.scalar(
            select(func.count())
            .select_from(Prediction)
            .where(
                Prediction.prediction_date == prediction_date,
                Prediction.forecast_horizon == horizon,
            )
        )
        or 0
    )

    written = 0
    if not payload.dry_run:
        if existing:
            audit.record(
                session,
                action=AUDIT_RUN,
                resource_type=AUDIT_RESOURCE,
                result=audit.RESULT_FAILED,
                user_id=current.user.user_id,
                resource_id=f"{prediction_date.isoformat()}/{horizon}",
                detail={"reason": f"{existing} baris sudah ada", "dry_run": False},
            )
            session.commit()
            raise ApiError(
                status.HTTP_409_CONFLICT,
                f"Tanggal prediksi {prediction_date.isoformat()} dengan horizon {horizon} "
                f"sudah memiliki {existing} baris predictions. Prediksi adalah pernyataan "
                "bertanggal dan tidak ditimpa; jalankan pada tanggal prediksi baru.",
            )

        written = _persist(session, projection)

    audit.record(
        session,
        action=AUDIT_RUN,
        resource_type=AUDIT_RESOURCE,
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=f"{prediction_date.isoformat()}/{horizon}",
        # Uji coba ikut dicatat: yang tidak ditulis adalah baris prediksinya, bukan jejak
        # siapa menjalankan apa (CLAUDE.md §29).
        detail={
            "dry_run": payload.dry_run,
            "horizon": horizon,
            "rule_version": projection.rule_version,
            "written": written,
        },
    )
    session.commit()

    return {
        "prediction_date": prediction_date,
        "horizon": horizon,
        "dry_run": payload.dry_run,
        "written": written,
        "existing_rows": existing,
        "status_written": engine.STATUS_DRAFT,
        "target_date": projection.target_date,
        "window_from": projection.window_from,
        "window_to": projection.window_to,
        "time_windows": list(projection.time_windows),
        "threat_types": list(projection.threat_types),
        "combinations": len(projection.forecasts),
        "predicted": len(projection.predicted),
        "not_predicted": len(projection.not_predicted),
        "reference_time": projection.reference_time,
        "demo_clock": clock.is_demo_clock(),
        "rule_version": projection.rule_version,
        "weights_versions": list(projection.weights_versions),
        "threshold_version": projection.threshold_version,
        "threshold_status": projection.threshold_status,
        "evidence": {
            "incidents": projection.incidents_considered,
            "date_from": projection.evidence_from,
            "date_to": projection.evidence_to,
        },
        "not_computed_reason": projection.not_computed_reason,
        **_summary(projection),
        "horizon_basis": engine.HORIZON_BASIS,
        "projection_basis": engine.PROJECTION_BASIS,
        "confidence_basis": engine.CONFIDENCE_BASIS,
        "not_predicted_basis": engine.NOT_PREDICTED_BASIS,
        "model_disclaimer": engine.MODEL_DISCLAIMER,
        "publication_basis": engine.PUBLICATION_BASIS,
        "dry_run_basis": DRY_RUN_BASIS,
        "status_basis": STATUS_BASIS,
    }


def _serialize(prediction: Prediction) -> dict[str, Any]:
    """Bentuk respons publikasi, sejalan dengan `GET /predictions`."""
    location = prediction.location

    return {
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
        # Waktu transisi memakai waktu acuan aplikasi, bukan jam dinding (SDL-16). Waktu
        # sebenarnya tetap terekam pada `audit_logs.timestamp`.
        "reference_time": clock.reference_now(),
        "demo_clock": clock.is_demo_clock(),
        "publication_basis": engine.PUBLICATION_BASIS,
        "model_disclaimer": engine.MODEL_DISCLAIMER,
    }


@router.post("/predictions/{code}/publish", summary="Mempublikasikan satu prediksi")
def publish_prediction(
    code: str = Path(description="Kode prediksi, mis. PRD-00123"),
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("prediction:publish"),
) -> dict[str, Any]:
    """`DRAFT` → `PUBLISHED`. Hanya prediksi terpublikasi yang boleh melahirkan peringatan."""
    polsek = jurisdiction_filter(current, "prediction:publish")

    query = (
        select(Prediction)
        .join(Location, Location.location_id == Prediction.location_id)
        .where(Prediction.code == code)
    )
    if polsek is not None:
        # Penyaringan wilayah ada di query: prediksi di luar cakupan tidak pernah terambil,
        # sehingga tidak ada kesempatan membocorkannya lewat pesan kesalahan yang berbeda.
        query = query.where(Location.polsek == polsek)

    prediction = session.scalar(query)
    if prediction is None:
        raise not_found()

    previous = prediction.status
    if previous != engine.STATUS_DRAFT:
        audit.record(
            session,
            action=AUDIT_PUBLISH,
            resource_type=AUDIT_RESOURCE,
            resource_id=prediction.code,
            result=audit.RESULT_FAILED,
            user_id=current.user.user_id,
            detail={"status_before": previous, "reason": "transisi tidak sah"},
        )
        session.commit()
        raise ApiError(
            status.HTTP_409_CONFLICT,
            f"Prediksi berstatus {previous} tidak dapat dipublikasikan ulang.",
            details=[
                {
                    "field": "status",
                    "issue": f"publikasi hanya sah dari {engine.STATUS_DRAFT}",
                }
            ],
        )

    prediction.status = engine.STATUS_PUBLISHED

    audit.record(
        session,
        action=AUDIT_PUBLISH,
        resource_type=AUDIT_RESOURCE,
        resource_id=prediction.code,
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        detail={"status_before": previous, "status_after": engine.STATUS_PUBLISHED},
    )
    session.commit()
    session.refresh(prediction)

    return _serialize(prediction)
