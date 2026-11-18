"""Pembakuan laporan kejadian (Modul 1 mekanisme, 6 November 2026).

Tiga pekerjaan Administrator (`crime:triage`) atas data yang sudah masuk:

- memastikan kelurahan kejadian yang masih tertunda (`area_pending`);
- mencocokkan dugaan laporan ganda (CONFIRMED → disembunyikan dari perhitungan; CLEARED);
- membaca riwayat koreksi satu kejadian.

Hitungan "masih memerlukan konfirmasi" dikembalikan apa adanya supaya layar dan laporan
bulanan menyebutnya, seperti diminta dokumen mekanisme.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import CitizenReport, CrimeIncident, CrimeIncidentRevision, Location
from ...services import audit, data_quality, standardization
from ..deps import CurrentUser, get_db, jurisdiction_filter, not_found, require_permission
from ..errors import ApiError

router = APIRouter(tags=["pembakuan"])


class AreaRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    location_code: str = Field(min_length=1, max_length=50)
    note: str | None = Field(default=None, max_length=500)


class DuplicateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: str = Field(pattern="^(CONFIRMED|CLEARED)$")
    duplicate_of: str | None = Field(default=None, max_length=50)
    #: Alasan WAJIB sejak 18 November 2026 (naskah Taskap 4.1: "keputusan dan alasan dicatat").
    note: str = Field(min_length=3, max_length=500)


class MatchRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    decision: str = Field(pattern="^(MATCHED|NOT_MATCHED)$")
    incident_code: str | None = Field(default=None, max_length=50)
    reason: str = Field(min_length=3, max_length=1000)


def _incident(session: Session, current: CurrentUser, code: str) -> tuple[CrimeIncident, Location]:
    polsek = jurisdiction_filter(current, "crime:triage")
    query = (
        select(CrimeIncident, Location)
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .where(CrimeIncident.code == code)
    )
    if polsek is not None:
        query = query.where(Location.polsek == polsek)
    row = session.execute(query).first()
    if row is None:
        raise not_found()
    return row[0], row[1]


def _summary(incident: CrimeIncident, location: Location) -> dict[str, Any]:
    return {
        "code": incident.code,
        "incident_type": incident.incident_type,
        "incident_date": incident.incident_date,
        "kecamatan": location.kecamatan,
        "kelurahan": location.kelurahan,
        "polsek": location.polsek,
        "location_code": location.code,
        "street": incident.street,
        "vehicle_object": incident.vehicle_object,
        "area_pending": incident.area_pending,
        "duplicate_of": incident.duplicate_of,
        "duplicate_status": incident.duplicate_status,
        "data_source": incident.data_source,
    }


@router.get(
    "/crimes/standardization", summary="Antrean pembakuan: kelurahan tertunda dan dugaan ganda"
)
def standardization_queue(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("crime:triage"),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "crime:triage")
    base = select(CrimeIncident, Location).join(
        Location, Location.location_id == CrimeIncident.location_id
    )
    if polsek is not None:
        base = base.where(Location.polsek == polsek)

    pending_q = base.where(CrimeIncident.area_pending.is_(True)).order_by(
        CrimeIncident.incident_date.desc()
    )
    suspected_q = base.where(CrimeIncident.duplicate_status == "SUSPECTED").order_by(
        CrimeIncident.incident_date.desc()
    )
    pending_total = session.scalar(select(func.count()).select_from(pending_q.subquery())) or 0
    suspected_total = session.scalar(select(func.count()).select_from(suspected_q.subquery())) or 0
    # Pilihan kelurahan per kecamatan untuk formulir konfirmasi.
    options: dict[str, list[dict[str, str]]] = {}
    for loc in session.scalars(
        select(Location)
        .where(Location.kelurahan.is_not(None))
        .order_by(Location.kecamatan, Location.kelurahan)
    ):
        options.setdefault(loc.kecamatan, []).append(
            {"code": loc.code, "kelurahan": str(loc.kelurahan)}
        )

    return {
        "area_pending": {
            "total": pending_total,
            "data": [_summary(i, loc) for i, loc in session.execute(pending_q.limit(limit)).all()],
        },
        "suspected_duplicates": {
            "total": suspected_total,
            "data": [
                _summary(i, loc) for i, loc in session.execute(suspected_q.limit(limit)).all()
            ],
        },
        "kelurahan_options": options,
        "duplicate_basis": standardization.DUPLICATE_BASIS,
    }


@router.post("/crimes/{code}/area", summary="Memastikan kelurahan satu kejadian")
def confirm_area(
    code: str,
    payload: AreaRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("crime:triage"),
) -> dict[str, Any]:
    incident, before = _incident(session, current, code)
    target = session.scalar(select(Location).where(Location.code == payload.location_code))
    if target is None or target.kelurahan is None:
        raise ApiError(status.HTTP_400_BAD_REQUEST, "Lokasi tujuan harus satu kelurahan.")
    if target.kecamatan != before.kecamatan:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            f"Kelurahan {target.kelurahan} bukan di Kecamatan {before.kecamatan}.",
        )
    incident.location_id = target.location_id
    incident.area_pending = False
    standardization.record_revision(
        session, incident, current.user.user_id, "location", before.code, target.code, payload.note
    )
    audit.record(
        session,
        action="CONFIRM_CRIME_AREA",
        resource_type="crime",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=incident.code,
        detail={"from": before.code, "to": target.code},
    )
    session.commit()
    session.refresh(incident)
    return _summary(incident, target)


@router.post("/crimes/{code}/duplicate", summary="Mencocokkan dugaan laporan ganda")
def resolve_duplicate(
    code: str,
    payload: DuplicateRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("crime:triage"),
) -> dict[str, Any]:
    incident, location = _incident(session, current, code)
    if payload.status == "CONFIRMED":
        original = payload.duplicate_of or incident.duplicate_of
        if not original or original == incident.code:
            raise ApiError(status.HTTP_400_BAD_REQUEST, "Sebutkan kode kejadian aslinya.")
        if session.scalar(select(CrimeIncident.code).where(CrimeIncident.code == original)) is None:
            raise ApiError(status.HTTP_400_BAD_REQUEST, f"Kejadian {original} tidak dikenal.")
        incident.duplicate_of = original
    previous = incident.duplicate_status
    incident.duplicate_status = payload.status
    standardization.record_revision(
        session,
        incident,
        current.user.user_id,
        "duplicate_status",
        previous,
        payload.status,
        payload.note,
    )
    audit.record(
        session,
        action="RESOLVE_CRIME_DUPLICATE",
        resource_type="crime",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=incident.code,
        detail={"status": payload.status, "duplicate_of": incident.duplicate_of},
    )
    session.commit()
    session.refresh(incident)
    return _summary(incident, location)


@router.get("/crimes/{code}/revisions", summary="Riwayat koreksi satu kejadian")
def revisions(
    code: str,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("crime:read"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "crime:read")
    query = (
        select(CrimeIncident, Location)
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .where(CrimeIncident.code == code)
    )
    if polsek is not None:
        query = query.where(Location.polsek == polsek)
    row = session.execute(query).first()
    if row is None:
        raise not_found()
    rows = session.scalars(
        select(CrimeIncidentRevision)
        .where(CrimeIncidentRevision.incident_id == row[0].incident_id)
        .order_by(CrimeIncidentRevision.changed_at)
    ).all()
    return {
        "code": code,
        "data": [
            {
                "changed_at": r.changed_at,
                "changed_by": str(r.changed_by) if r.changed_by else None,
                "field": r.field,
                "before": r.value_before,
                "after": r.value_after,
                "note": r.note,
            }
            for r in rows
        ],
    }


# ---------------------------------------------------------------------------------------
# Mutu data (naskah Taskap 4.1 dan Tabel 22 "Mutu data"; 18 November 2026).
# ---------------------------------------------------------------------------------------


@router.get("/data-quality", summary="Mutu data: kelengkapan, tanda, dan hitungan kejadian")
def quality_summary(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("crime:triage"),
) -> dict[str, Any]:
    return data_quality.summary(session, jurisdiction_filter(current, "crime:triage"))


@router.get("/data-quality/flags", summary="Kejadian yang ditandai untuk diperiksa")
def quality_flags(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("crime:triage"),
    kind: str = Query(..., description="NO_TIME, NO_TARGET, NO_PLACE, LABEL_OBJECT, ..."),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    try:
        return data_quality.flagged(
            session, kind.upper(), jurisdiction_filter(current, "crime:triage"), limit
        )
    except data_quality.QualityError as error:
        raise ApiError(error.status, str(error)) from error


@router.get(
    "/data-quality/matches", summary="Laporan warga terverifikasi dan usulan kejadian padanannya"
)
def quality_matches(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("crime:triage"),
    limit: int = Query(30, ge=1, le=100),
) -> dict[str, Any]:
    return data_quality.match_queue(session, jurisdiction_filter(current, "crime:triage"), limit)


@router.post(
    "/citizen-reports/{code}/match", summary="Memutuskan kecocokan laporan warga dengan kejadian"
)
def decide_match(
    code: str,
    payload: MatchRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("crime:triage"),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "crime:triage")
    query = select(CitizenReport).where(CitizenReport.code == code)
    if polsek is not None:
        query = query.join(Location, Location.location_id == CitizenReport.location_id).where(
            Location.polsek == polsek
        )
    report = session.scalar(query)
    if report is None:
        raise not_found()
    try:
        result = data_quality.decide_match(
            session, report, payload.decision, payload.incident_code, payload.reason, current.user
        )
    except data_quality.QualityError as error:
        raise ApiError(error.status, str(error)) from error
    audit.record(
        session,
        action="MATCH_CITIZEN_REPORT",
        resource_type="citizen_report",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=report.code,
        detail={"decision": payload.decision, "incident": result["matched_incident"]},
    )
    session.commit()
    return result
