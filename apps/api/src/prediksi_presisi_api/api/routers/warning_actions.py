"""Transisi status peringatan dini — acknowledge dan resolve (TASK 111, docs/05 §2.7).

Peringatan dini adalah titik tempat sistem menyerahkan keputusan kepada manusia
(CLAUDE.md §13). Dua endpoint di sini merekam **siapa** yang menerima peringatan itu dan
**siapa** yang menutupnya — bukan sekadar mengubah sebuah kolom status.

Empat hal yang dijaga modul ini:

1. **Pelaku selalu ikut tercatat.** `acknowledged_at` tidak pernah terisi tanpa
   `acknowledged_by` (CHECK `acknowledged_needs_actor` pada `early_warnings`), demikian
   pula pasangan `resolved_*`. Keduanya ditulis bersama, tidak pernah terpisah.

2. **Transisi tidak sah dijawab 409 CONFLICT**, bukan diam-diam diterima (docs/05 §1).
   Menerima ulang acknowledge akan menimpa pelaku yang pertama — jejak siapa yang
   sebenarnya menerima peringatan itu hilang.

3. **Cakupan ditegakkan.** Peringatan di luar wilayah pengguna dijawab 404, sama seperti
   peringatan yang memang tidak ada, agar keberadaan data wilayah lain tidak bocor.

4. **Audit wajib.** `ACK_WARNING` dan `RESOLVE_WARNING` dicatat dengan status sebelum dan
   sesudah (CLAUDE.md §29).

> `NOT SPECIFIED`: apakah sebuah peringatan **wajib** di-acknowledge sebelum boleh
> di-resolve. Itu aturan SOP, bukan keputusan teknis (CLAUDE.md §2C), dan data dummy
> memuat peringatan `RESOLVED` yang tidak pernah melewati `ACKNOWLEDGED`. Karena itu
> `ACTIVE → RESOLVED` **diizinkan** di sini; yang ditolak hanyalah transisi dari status
> akhir. Jika SOP kelak mensyaratkan urutannya, aturan itu ditambahkan di satu tempat ini.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import EarlyWarning, Location
from ...services import audit, clock
from ..deps import CurrentUser, get_db, jurisdiction_filter, not_found, require_permission
from ..errors import ApiError

router = APIRouter(prefix="/warnings", tags=["peringatan dini"])

STATUS_ACTIVE = "ACTIVE"
STATUS_ACKNOWLEDGED = "ACKNOWLEDGED"
STATUS_RESOLVED = "RESOLVED"

#: Status yang masih boleh menerima acknowledge. Peringatan yang sudah diterima atau
#: sudah ditutup tidak boleh diterima ulang: pelaku pertama akan tertimpa.
ACKNOWLEDGEABLE_FROM = (STATUS_ACTIVE,)

#: Status yang masih boleh ditutup. `ACTIVE` ikut karena kewajiban acknowledge lebih dahulu
#: adalah aturan SOP yang belum ditetapkan — lihat catatan pada docstring modul.
RESOLVABLE_FROM = (STATUS_ACTIVE, STATUS_ACKNOWLEDGED)


def _load_warning(session: Session, code: str, polsek: str | None) -> EarlyWarning:
    """Mengambil satu peringatan dalam cakupan pengguna, atau 404.

    Penyaringan wilayah ada di query: peringatan di luar cakupan tidak pernah terambil,
    sehingga tidak ada kesempatan membocorkannya lewat pesan kesalahan yang berbeda.
    """
    query = (
        select(EarlyWarning)
        .join(Location, Location.location_id == EarlyWarning.location_id)
        .where(EarlyWarning.code == code)
    )
    if polsek is not None:
        query = query.where(Location.polsek == polsek)

    warning = session.scalar(query)
    if warning is None:
        raise not_found()

    return warning


def _reject_transition(current_status: str, allowed: tuple[str, ...], target: str) -> ApiError:
    return ApiError(
        status.HTTP_409_CONFLICT,
        f"Peringatan berstatus {current_status} tidak dapat diubah menjadi {target}.",
        details=[
            {"field": "status", "issue": f"transisi hanya sah dari {', '.join(allowed)}"},
        ],
    )


def _serialize(warning: EarlyWarning) -> dict[str, Any]:
    """Bentuk respons yang sama untuk kedua transisi, sejalan dengan `GET /warnings`."""
    location = warning.location

    return {
        "code": warning.code,
        "severity": warning.severity,
        "threat_type": warning.threat_type,
        "time_window": warning.time_window,
        "window_start": warning.window_start,
        "window_end": warning.window_end,
        "risk_score": warning.risk_score,
        "confidence": warning.confidence,
        "status": warning.status,
        "acknowledged_at": warning.acknowledged_at,
        "resolved_at": warning.resolved_at,
        "kecamatan": location.kecamatan,
        "kelurahan": location.kelurahan,
        "grid_id": location.grid_id,
        "prediction_code": warning.prediction.code,
        "threshold_version": warning.threshold_version,
        # Waktu transisi memakai waktu acuan aplikasi, bukan jam dinding: seluruh sistem
        # memakai satu "sekarang" (keputusan SDL-16). Waktu sebenarnya tetap terekam pada
        # `audit_logs.timestamp`, sehingga jejak pemeriksaan tidak ikut bergeser.
        "reference_time": clock.reference_now(),
        "demo_clock": clock.is_demo_clock(),
    }


@router.post("/{code}/acknowledge", summary="Menerima peringatan dini")
def acknowledge_warning(
    code: str = Path(description="Kode peringatan, mis. WRN-00012"),
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("warning:acknowledge"),
) -> dict[str, Any]:
    """Menandai peringatan sebagai diterima oleh pengguna yang sedang masuk."""
    polsek = jurisdiction_filter(current, "warning:acknowledge")
    warning = _load_warning(session, code, polsek)

    previous = warning.status
    if previous not in ACKNOWLEDGEABLE_FROM:
        audit.record(
            session,
            action="ACK_WARNING",
            resource_type="warning",
            resource_id=warning.code,
            result=audit.RESULT_FAILED,
            user_id=current.user.user_id,
            detail={"status_before": previous, "reason": "transisi tidak sah"},
        )
        session.commit()
        raise _reject_transition(previous, ACKNOWLEDGEABLE_FROM, STATUS_ACKNOWLEDGED)

    # Pelaku dan waktu ditulis bersama — CHECK `acknowledged_needs_actor` menolak
    # `acknowledged_at` yang terisi tanpa `acknowledged_by`.
    warning.acknowledged_by = current.user.user_id
    warning.acknowledged_at = clock.reference_now()
    warning.status = STATUS_ACKNOWLEDGED

    audit.record(
        session,
        action="ACK_WARNING",
        resource_type="warning",
        resource_id=warning.code,
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        detail={"status_before": previous, "status_after": warning.status},
    )
    session.commit()
    session.refresh(warning)

    return _serialize(warning)


@router.post("/{code}/resolve", summary="Menutup peringatan dini")
def resolve_warning(
    code: str = Path(description="Kode peringatan, mis. WRN-00012"),
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("warning:resolve"),
) -> dict[str, Any]:
    """Menandai peringatan sebagai selesai ditangani."""
    polsek = jurisdiction_filter(current, "warning:resolve")
    warning = _load_warning(session, code, polsek)

    previous = warning.status
    if previous not in RESOLVABLE_FROM:
        audit.record(
            session,
            action="RESOLVE_WARNING",
            resource_type="warning",
            resource_id=warning.code,
            result=audit.RESULT_FAILED,
            user_id=current.user.user_id,
            detail={"status_before": previous, "reason": "transisi tidak sah"},
        )
        session.commit()
        raise _reject_transition(previous, RESOLVABLE_FROM, STATUS_RESOLVED)

    warning.resolved_by = current.user.user_id
    warning.resolved_at = clock.reference_now()
    warning.status = STATUS_RESOLVED

    audit.record(
        session,
        action="RESOLVE_WARNING",
        resource_type="warning",
        resource_id=warning.code,
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        detail={"status_before": previous, "status_after": warning.status},
    )
    session.commit()
    session.refresh(warning)

    return _serialize(warning)
