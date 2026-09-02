"""API mesin penilaian risiko — menjalankan dan memperlihatkan dasarnya (TASK 09x).

Dua endpoint, dan keduanya ada karena alasan yang berbeda:

```text
POST /risk-scores/run      menghitung `risk_scores` dari data nyata   risk_score:run
GET  /risk-scores/config   memperlihatkan bobot yang menghasilkannya  config:read
```

Yang dihitung adalah **penilaian risiko atas keadaan berjalan**, bukan prediksi: tidak ada
pernyataan tentang apa yang akan terjadi, tidak ada `confidence`, dan tidak ada model
terlatih. Seluruh faktor dominan berlabel `RULE` (CLAUDE.md §27).

TIGA KEPUTUSAN YANG MENENTUKAN BENTUK MODUL INI

1. **`dry_run` bernilai benar secara bawaan.** Menjalankan penilaian mengubah angka yang
   dipakai peta, dashboard, dan brief. Bawaan yang menulis akan membuat "coba jalankan
   dulu" berakhir sebagai perubahan data — jadi yang harus dinyatakan secara sadar adalah
   menulisnya, bukan menahannya.

2. **Penilaian yang sudah ada tidak boleh ditimpa (409).** Skor yang sudah dipakai
   menerbitkan peringatan tidak boleh berubah di belakang peringatan itu: peringatan akan
   merujuk angka yang tidak lagi ada, dan evaluasi ketepatan kehilangan dasarnya. Cara
   yang benar untuk menilai ulang adalah tanggal penilaian baru — bukan menimpa.

3. **Menulis ditolak bila ada faktor berbobot yang tidak punya kolom.** Tabel
   `risk_scores` menyimpan lima kolom faktor (migration 0005). Bila versi bobot aktif
   memberi bobot pada faktor di luar kelima itu, baris yang tersimpan tidak lagi dapat
   menjelaskan skornya sendiri — hubungan `risk_score = round(Sum(bobot x faktor))` putus
   pada data yang sudah tertulis. Lebih baik menolak daripada menyimpan baris yang
   tampak lengkap tetapi tidak dapat ditelusuri.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import Location, RiskScore
from ...services import audit, clock
from ...services import risk_engine as engine
from ..deps import CurrentUser, get_db, require_permission, scope_of
from ..errors import ApiError

router = APIRouter(tags=["penilaian risiko"])

AUDIT_ACTION = "RUN_RISK_SCORING"
AUDIT_RESOURCE = "risk_score"

#: Banyaknya baris contoh yang dibawa respons. Ringkasan dimaksudkan untuk dibaca
#: sekilas sebelum memutuskan menulis; daftar lengkapnya ada di `GET /risk-scores`.
SAMPLE_ROWS = 10

#: Banyaknya alasan berbeda yang ditampilkan untuk baris yang tidak dinilai.
SAMPLE_REASONS = 5

PERSISTENCE_BASIS = (
    "Tabel risk_scores menyimpan lima kolom faktor: "
    f"{', '.join(engine.PERSISTED_FACTORS)}. Faktor di luar kelimanya tetap dihitung dan "
    "ditampilkan pada respons ini — sehingga jalurnya terlihat — tetapi TIDAK tersimpan; "
    "menambah kolomnya memerlukan migration dan persetujuan pemilik proyek. Selama faktor "
    "itu berbobot nol pada versi aktif, skor tersimpan tetap dapat dijelaskan sepenuhnya "
    "oleh kelima kolom yang ada."
)

DRY_RUN_BASIS = (
    "dry_run bernilai true secara bawaan: tidak ada satu baris risk_scores pun yang "
    "ditulis, dan angka pada respons ini adalah hasil perhitungan di memori. Menulis harus "
    "dinyatakan secara sadar dengan dry_run=false."
)

CONFIG_BASIS = (
    "Bobot berasal dari config/risk/risk-weights.yaml dan ambang kelas dari "
    "config/risk/warning-thresholds.yaml. Keduanya berstatus DEMO / PROPOSED (U-01, U-02) "
    "dan BUKAN ketentuan resmi — status setiap versi dibawa apa adanya pada respons ini. "
    "Tidak ada bobot maupun ambang yang ditulis di kode (CLAUDE.md §11, §12)."
)


class RunRequest(BaseModel):
    """Permintaan menjalankan penilaian."""

    assessment_date: date | None = Field(
        default=None,
        description=(
            "Tanggal penilaian. Kosong berarti tanggal pada waktu acuan aplikasi — "
            "dataset berhenti Desember 2025 dan jam dinding tidak dipakai (SDL-16)."
        ),
    )
    dry_run: bool = Field(
        default=True,
        description=("Bawaan true: menghitung dan mengembalikan ringkasan tanpa menulis apa pun."),
    )


def _profile_summary(profile: engine.ProfileAssessment) -> dict[str, Any]:
    """Ringkasan satu profil: sebaran kelas, alasan yang tidak dinilai, dan contohnya."""
    classes: dict[str, int] = {}
    threats: dict[str, dict[str, Any]] = {}

    for cell in profile.scored:
        # `profile.scored` hanya memuat sel yang benar-benar dinilai; nilai bawaan di
        # bawah ada agar pembacaan tipenya tetap jelas, bukan untuk menutupi sel kosong.
        score = cell.risk_score or 0
        classes[cell.risk_class or "TIDAK DIKETAHUI"] = (
            classes.get(cell.risk_class or "TIDAK DIKETAHUI", 0) + 1
        )
        threat = threats.setdefault(
            cell.threat_type,
            {"threat_type": cell.threat_type, "cells": 0, "highest": 0, "score_total": 0},
        )
        threat["cells"] = int(threat["cells"]) + 1
        threat["score_total"] = int(threat["score_total"]) + score
        threat["highest"] = max(int(threat["highest"]), score)

    for threat in threats.values():
        threat["average"] = round(int(threat["score_total"]) / int(threat["cells"]))
        del threat["score_total"]

    reasons: dict[str, int] = {}
    for cell in profile.unscored:
        key = cell.unscored_reason or "tidak diketahui"
        reasons[key] = reasons.get(key, 0) + 1

    top = sorted(profile.scored, key=lambda cell: cell.risk_score or 0, reverse=True)

    return {
        "profile": profile.profile,
        "weights_version": profile.version,
        "threat_types": list(profile.threat_types),
        "weights": profile.weights,
        "combinations": len(profile.cells),
        "scored": len(profile.scored),
        "unscored": len(profile.unscored),
        "risk_class_distribution": classes,
        "by_threat_type": sorted(
            threats.values(), key=lambda item: int(item["highest"]), reverse=True
        ),
        "unscored_reasons": [
            {"reason": reason, "combinations": count}
            for reason, count in sorted(reasons.items(), key=lambda item: -item[1])[:SAMPLE_REASONS]
        ],
        "sample": [cell.as_dict() for cell in top[:SAMPLE_ROWS]],
        "not_computed_reason": profile.not_computed_reason,
        "unscored_basis": engine.UNSCORED_BASIS,
    }


def _next_code_number(session: Session) -> int:
    latest = session.scalar(select(func.max(RiskScore.code)))
    if latest is None:
        return 1
    return int(latest.rsplit("-", 1)[-1]) + 1


def _reject_partial_scope(current: CurrentUser) -> None:
    """Akun yang dibatasi wilayah/fungsi tidak boleh menjalankan penilaian menyeluruh.

    Hasilnya akan menjadi penilaian sebagian yang tersimpan seolah menyeluruh: sel di luar
    cakupan pengguna tidak pernah dinilai, tetapi tanggal penilaiannya terlihat lengkap
    bagi semua orang.
    """
    scope = scope_of(current, "risk_score:run")
    if scope != "ALL":
        raise ApiError(
            status.HTTP_403_FORBIDDEN,
            "Penilaian risiko menyeluruh tidak dapat dijalankan oleh akun yang dibatasi "
            f"cakupan ({scope}): hasilnya akan tersimpan sebagai penilaian sebagian yang "
            "terlihat menyeluruh.",
        )


def _reject_unpersistable(assessment: engine.Assessment) -> None:
    """Menolak menulis bila ada faktor berbobot yang tidak punya kolom penyimpanan."""
    orphans = sorted(
        {
            name
            for profile in assessment.profiles
            for name, weight in profile.weights.items()
            if weight != 0 and name not in engine.PERSISTED_FACTORS
        }
    )
    if orphans:
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Versi bobot '{assessment.weights_version}' memberi bobot pada "
            f"{', '.join(orphans)}, sedangkan tabel risk_scores tidak memiliki kolomnya. "
            "Baris yang tersimpan tidak akan dapat menjelaskan skornya sendiri. "
            "Diperlukan migration dan persetujuan pemilik proyek sebelum versi ini "
            "dipakai menulis.",
        )


@router.post("/risk-scores/run", summary="Menjalankan penilaian risiko keadaan berjalan")
def run_scoring(
    payload: RunRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("risk_score:run"),
) -> dict[str, Any]:
    """Menghitung risk score dari `crime_incidents`, `intelligence_reports`, dan seterusnya.

    Bawaan `dry_run=true` hanya menghitung. `dry_run=false` menulis baris baru, dan
    **menolak** bila tanggal penilaian tersebut sudah memiliki baris (409).
    """
    _reject_partial_scope(current)
    assessment_date = payload.assessment_date or clock.reference_now().date()

    try:
        assessment = engine.assess(session, assessment_date)
    except engine.RiskEngineError as error:
        # Konfigurasi risiko rusak bukan kesalahan pemakai; pesannya tetap disampaikan
        # karena hanya menyebut config/risk/, bukan struktur internal.
        audit.record(
            session,
            action=AUDIT_ACTION,
            resource_type=AUDIT_RESOURCE,
            result=audit.RESULT_FAILED,
            user_id=current.user.user_id,
            resource_id=assessment_date.isoformat(),
            detail={"reason": str(error)},
        )
        session.commit()
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    existing = (
        session.scalar(
            select(func.count())
            .select_from(RiskScore)
            .where(RiskScore.assessment_date == assessment_date)
        )
        or 0
    )

    historical = assessment.profile(engine.PROFILE_HISTORICAL)
    written = 0

    if not payload.dry_run:
        if existing:
            audit.record(
                session,
                action=AUDIT_ACTION,
                resource_type=AUDIT_RESOURCE,
                result=audit.RESULT_FAILED,
                user_id=current.user.user_id,
                resource_id=assessment_date.isoformat(),
                detail={"reason": f"{existing} baris sudah ada", "dry_run": False},
            )
            session.commit()
            raise ApiError(
                status.HTTP_409_CONFLICT,
                f"Tanggal penilaian {assessment_date.isoformat()} sudah memiliki "
                f"{existing} baris risk_scores. Penilaian yang sudah dipakai menerbitkan "
                "peringatan tidak ditimpa; jalankan pada tanggal penilaian baru.",
            )

        _reject_unpersistable(assessment)
        written = _persist(session, assessment, historical)

    audit.record(
        session,
        action=AUDIT_ACTION,
        resource_type=AUDIT_RESOURCE,
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=assessment_date.isoformat(),
        # Dry-run ikut dicatat: yang tidak ditulis adalah baris penilaiannya, bukan jejak
        # siapa menjalankan apa (CLAUDE.md §29).
        detail={
            "dry_run": payload.dry_run,
            "weights_version": assessment.weights_version,
            "written": written,
        },
    )
    session.commit()

    return {
        "assessment_date": assessment_date,
        "dry_run": payload.dry_run,
        "written": written,
        "existing_rows": existing,
        "reference_time": assessment.reference_time,
        "demo_clock": clock.is_demo_clock(),
        "weights_version": assessment.weights_version,
        "weights_status": assessment.weights_status,
        "threshold_version": assessment.threshold_version,
        "threshold_status": assessment.threshold_status,
        "evidence": {
            "incidents": assessment.incidents_considered,
            "date_from": assessment.evidence_from,
            "date_to": assessment.evidence_to,
        },
        "profiles": [_profile_summary(profile) for profile in assessment.profiles],
        "score_basis": engine.SCORE_BASIS,
        "dry_run_basis": DRY_RUN_BASIS,
        "persistence_basis": PERSISTENCE_BASIS,
    }


def _persist(
    session: Session,
    assessment: engine.Assessment,
    historical: engine.ProfileAssessment | None,
) -> int:
    """Menulis baris hasil penilaian. Hanya kombinasi yang benar-benar dinilai."""
    if historical is None:
        return 0

    number = _next_code_number(session)
    written = 0

    for cell in historical.scored:
        values = {factor.name: factor.value for factor in cell.factors}
        session.add(
            RiskScore(
                code=f"RS-{number:05d}",
                assessment_date=assessment.assessment_date,
                location_id=cell.location_id,
                threat_type=cell.threat_type,
                time_window=cell.time_window,
                window_start=cell.window_start,
                window_end=cell.window_end,
                risk_score=cell.risk_score,
                risk_class=cell.risk_class,
                weights_version=assessment.weights_version,
                # Sengaja kosong: penilaian ini berbasis aturan yang dibaca dari config,
                # bukan model terlatih. Mengisinya akan mengklaim model yang tidak ada.
                model_version=None,
                **{name: values.get(name) for name in engine.PERSISTED_FACTORS},
            )
        )
        number += 1
        written += 1

    return written


@router.get("/risk-scores/config", summary="Bobot dan ambang yang mendasari penilaian")
def scoring_config(
    session: Session = Depends(get_db),
    _current: CurrentUser = require_permission("config:read"),
) -> dict[str, Any]:
    """Seluruh versi bobot beserta profil, faktor, dan jenis ancaman yang dicakupnya.

    Dipakai layar `/skoring` untuk menampilkan **dasar** perhitungan, bukan hanya
    hasilnya: angka risiko yang tidak dapat dikembalikan ke bobot yang menghasilkannya
    tidak dapat diperdebatkan siapa pun.

    Kontrak `docs/05` §2.2 juga menyebut `GET /config/risk-weights` untuk membaca berkas
    konfigurasi apa adanya. Endpoint ini berbeda maksudnya — ia menyajikan konfigurasi
    **sebagaimana dipakai mesin penilaian**, termasuk faktor mana yang dapat disimpan —
    dan diletakkan bersama `/risk-scores/run` yang menjadi pemakainya.
    """
    try:
        catalogue = engine.load_weights()
        thresholds = engine.load_thresholds()
    except engine.RiskEngineError as error:
        raise ApiError(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    versions = [
        {
            "version": version.version,
            "status": version.status,
            "active": version.version == catalogue.active_version,
            "profiles": [
                {
                    "profile": profile.name,
                    "applies_to": list(profile.applies_to),
                    "positive_weight_total": round(profile.positive_total, 4),
                    "factors": [
                        {
                            "factor": name,
                            "weight": weight,
                            "sign": "negative" if weight < 0 else "positive",
                            "persisted": name in engine.PERSISTED_FACTORS,
                            "basis": engine.FACTOR_BASIS.get(name),
                        }
                        for name, weight in profile.weights.items()
                    ],
                }
                for profile in version.profiles.values()
            ],
        }
        for version in catalogue.versions.values()
    ]

    scored_dates = session.scalar(select(func.count(func.distinct(RiskScore.assessment_date))))
    cells = session.scalar(select(func.count()).select_from(Location))

    return {
        "active_version": catalogue.active_version,
        "active_status": catalogue.active.status,
        "versions": versions,
        "thresholds": {
            "version": thresholds.version,
            "status": thresholds.status,
            "risk_classes": [
                {"class": band.risk_class, "min": band.minimum, "max": band.maximum}
                for band in thresholds.bands
            ],
        },
        "time_windows": list(engine.TIME_WINDOWS),
        "persisted_factors": list(engine.PERSISTED_FACTORS),
        "coverage": {"locations": int(cells or 0), "assessment_dates": int(scored_dates or 0)},
        "reference_time": clock.reference_now(),
        "demo_clock": clock.is_demo_clock(),
        "config_basis": CONFIG_BASIS,
        "score_basis": engine.SCORE_BASIS,
        "persistence_basis": PERSISTENCE_BASIS,
    }
