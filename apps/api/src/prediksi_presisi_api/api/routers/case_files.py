"""Berkas perkara 3C — layar petugas (`case_file:read` / `case_file:write`, cakupan Polsek).

```text
GET  /case-files?stage=&q=        daftar (PIN dummy ikut, PIN perkara nyata tidak pernah)
POST /case-files                  mencatat perkara baru; PIN dibuat sistem dan dijawab SEKALI
POST /case-files/{lp}/stage       memindahkan tahap + catatan untuk pelapor
```
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ...models import CaseFile, CaseStage, Location
from ...models.case_file import CRIME_TYPES, STAGE_LABELS, STAGES, hash_pin, normalize_plate
from ...services import audit, clock
from ..deps import CurrentUser, get_db, jurisdiction_filter, not_found, require_permission
from ..errors import ApiError

router = APIRouter(prefix="/case-files", tags=["berkas perkara"])
MAX_ROWS = 300


def _row(case: CaseFile) -> dict[str, Any]:
    return {
        "lp_number": case.lp_number,
        "crime_type": case.crime_type,
        "kelurahan": case.location.kelurahan,
        "kecamatan": case.location.kecamatan,
        "polsek": case.location.polsek,
        "reported_on": case.reported_on,
        "stage": case.stage,
        "stage_label": STAGE_LABELS.get(case.stage, case.stage),
        "stage_updated_at": case.stage_updated_at,
        "summary": case.summary,
        "vehicle_plate": case.vehicle_plate_display,
        "vehicle_vin": case.vehicle_vin,
        "vehicle_desc": case.vehicle_desc,
        "vehicle_recovered": case.vehicle_recovered,
        "is_dummy": case.is_dummy,
        # PIN hanya untuk baris DUMMY — perkara nyata tidak pernah mengembalikan PIN-nya.
        "dummy_pin": case.dummy_pin if case.is_dummy else None,
        "history": [
            {
                "stage": s.stage,
                "stage_label": STAGE_LABELS.get(s.stage, s.stage),
                "changed_at": s.changed_at,
                "note": s.note,
            }
            for s in case.stages
        ],
    }


def _scoped(query: Any, polsek: str | None) -> Any:
    query = query.join(Location, Location.location_id == CaseFile.location_id)
    return query.where(Location.polsek == polsek) if polsek else query


@router.get("", summary="Daftar berkas perkara")
def list_case_files(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("case_file:read"),
    stage: str | None = Query(None),
    q: str | None = Query(None, max_length=80, description="Cari nomor LP atau plat"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "case_file:read")
    query = _scoped(select(CaseFile), polsek)
    if stage:
        wanted = stage.upper()
        if wanted not in STAGES:
            raise ApiError(status.HTTP_400_BAD_REQUEST, "Tahap tidak dikenal.")
        query = query.where(CaseFile.stage == wanted)
    if q:
        needle = q.strip().upper()
        query = query.where(
            or_(
                CaseFile.lp_number.ilike(f"%{needle}%"),
                CaseFile.vehicle_plate == normalize_plate(needle),
            )
        )
    rows = session.scalars(query.order_by(CaseFile.reported_on.desc()).limit(MAX_ROWS)).all()
    total = session.scalar(_scoped(select(func.count()).select_from(CaseFile), polsek))
    return {
        "data": [_row(row) for row in rows],
        "total": int(total or 0),
        "stages": [{"code": s, "label": STAGE_LABELS[s]} for s in STAGES],
    }


class CaseFileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lp_number: str = Field(min_length=5, max_length=80)
    crime_type: str
    kecamatan: str = Field(max_length=100)
    kelurahan: str = Field(max_length=100)
    reported_on: str = Field(description="YYYY-MM-DD")
    summary: str | None = Field(default=None, max_length=1000)
    vehicle_plate: str | None = Field(default=None, max_length=20)
    vehicle_vin: str | None = Field(default=None, max_length=30)
    vehicle_engine: str | None = Field(default=None, max_length=30)
    vehicle_desc: str | None = Field(default=None, max_length=120)
    is_dummy: bool = False


@router.post("", status_code=status.HTTP_201_CREATED, summary="Mencatat berkas perkara")
def create_case_file(
    payload: CaseFileRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("case_file:write"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "case_file:write")
    crime = payload.crime_type.upper()
    if crime not in CRIME_TYPES:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST, "Jenis perkara harus CURANMOR, CURAT, atau CURAS."
        )
    location = session.scalar(
        select(Location).where(
            Location.kecamatan == payload.kecamatan,
            func.lower(Location.kelurahan) == payload.kelurahan.strip().lower(),
        )
    )
    if location is None or (polsek and location.polsek != polsek):
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            "Kelurahan tidak dikenal atau di luar wilayah akun Anda.",
        )
    lp_number = payload.lp_number.strip().upper()
    if session.scalar(select(CaseFile).where(CaseFile.lp_number == lp_number)) is not None:
        raise ApiError(status.HTTP_409_CONFLICT, "Nomor LP itu sudah tercatat.")
    try:
        reported_on = datetime.fromisoformat(payload.reported_on).date()
    except ValueError as error:
        raise ApiError(status.HTTP_400_BAD_REQUEST, "Tanggal laporan harus YYYY-MM-DD.") from error
    pin = f"{secrets.randbelow(10000):04d}"
    now = clock.reference_now()
    plate = normalize_plate(payload.vehicle_plate) if payload.vehicle_plate else None
    case = CaseFile(
        lp_number=lp_number,
        crime_type=crime,
        location_id=location.location_id,
        reported_on=reported_on,
        stage="DITERIMA",
        stage_updated_at=now,
        summary=(payload.summary or "").strip() or None,
        vehicle_plate=plate or None,
        vehicle_plate_display=(payload.vehicle_plate or "").strip().upper() or None,
        vehicle_vin=(payload.vehicle_vin or "").strip().upper() or None,
        vehicle_engine=(payload.vehicle_engine or "").strip().upper() or None,
        vehicle_desc=(payload.vehicle_desc or "").strip() or None,
        reporter_pin_hash=hash_pin(lp_number, pin),
        is_dummy=payload.is_dummy,
        dummy_pin=pin if payload.is_dummy else None,
        stages=[
            CaseStage(
                stage="DITERIMA",
                changed_at=now,
                note="Laporan diterima.",
                changed_by=current.user.user_id,
            )
        ],
    )
    session.add(case)
    session.flush()
    audit.record(
        session,
        action="CREATE_CASE_FILE",
        resource_type="case_file",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=case.lp_number,
        detail={"crime_type": crime, "kelurahan": location.kelurahan, "is_dummy": payload.is_dummy},
    )
    session.commit()
    session.refresh(case)
    # PIN dijawab SEKALI untuk disampaikan ke pelapor; yang tersimpan hanya hash-nya.
    return {**_row(case), "reporter_pin": pin}


class StageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str
    note: str | None = Field(default=None, max_length=300)
    vehicle_recovered: bool | None = None


# `{lp:path}`: nomor LP memuat garis miring (LP/B/123/XI/2026/SPKT/…).
@router.post("/{lp:path}/stage", summary="Memindahkan tahap perkara")
def advance_stage(
    payload: StageRequest,
    lp: str = Path(),
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("case_file:write"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "case_file:write")
    lp_number = unquote(lp).strip().upper()
    case = session.scalar(_scoped(select(CaseFile), polsek).where(CaseFile.lp_number == lp_number))
    if case is None:
        raise not_found()
    wanted = payload.stage.upper()
    if wanted not in STAGES:
        raise ApiError(status.HTTP_400_BAD_REQUEST, "Tahap tidak dikenal.")
    if wanted == case.stage and payload.vehicle_recovered is None:
        raise ApiError(status.HTTP_409_CONFLICT, f"Perkara sudah pada tahap {wanted}.")
    previous = case.stage
    now = datetime.now(UTC)
    if wanted != case.stage:
        case.stage = wanted
        case.stage_updated_at = now
        case.stages.append(
            CaseStage(
                stage=wanted,
                changed_at=now,
                note=(payload.note or "").strip() or None,
                changed_by=current.user.user_id,
            )
        )
    if payload.vehicle_recovered is not None:
        case.vehicle_recovered = payload.vehicle_recovered
    audit.record(
        session,
        action="UPDATE_CASE_STAGE",
        resource_type="case_file",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=case.lp_number,
        detail={"from": previous, "to": wanted, "vehicle_recovered": payload.vehicle_recovered},
    )
    session.commit()
    session.refresh(case)
    return _row(case)
