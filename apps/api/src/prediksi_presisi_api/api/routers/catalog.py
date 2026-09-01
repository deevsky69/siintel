"""API lokasi dan kejadian (TASK 031, 032).

Penyaringan cakupan dilakukan **di query**, bukan setelah data terambil: pengguna
ber-scope `OWN_JURISDICTION` tidak pernah menerima baris di luar wilayahnya, bahkan
tidak dalam bentuk jumlah total pada pagination.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ...models import CrimeIncident, Location
from ..deps import CurrentUser, get_db, jurisdiction_filter, require_permission
from ..pagination import PageParams, page_params, paginate

router = APIRouter(tags=["data kamtibmas"])


def _scoped_locations(query: Select[Any], polsek: str | None) -> Select[Any]:
    return query if polsek is None else query.where(Location.polsek == polsek)


@router.get("/locations", summary="Daftar wilayah/grid")
def list_locations(
    session: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    current: CurrentUser = require_permission("location:read"),
    kecamatan: str | None = Query(None),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "location:read")

    query = select(Location).order_by(Location.grid_id)
    query = _scoped_locations(query, polsek)
    if kecamatan:
        query = query.where(Location.kecamatan == kecamatan)

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.scalars(query.offset(params.offset).limit(params.page_size)).all()

    return paginate(
        [
            {
                "code": row.code,
                "grid_id": row.grid_id,
                "polsek": row.polsek,
                "kecamatan": row.kecamatan,
                "kelurahan": row.kelurahan,
                "latitude": float(row.latitude),
                "longitude": float(row.longitude),
                "location_type": row.location_type,
            }
            for row in rows
        ],
        total,
        params,
    )


@router.get("/crimes", summary="Daftar kejadian")
def list_crimes(
    session: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    current: CurrentUser = require_permission("crime:read"),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    incident_type: str | None = Query(None),
    kecamatan: str | None = Query(None),
) -> dict[str, Any]:
    polsek = jurisdiction_filter(current, "crime:read")

    query = (
        select(CrimeIncident, Location)
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .order_by(CrimeIncident.occurred_at.desc())
    )
    if polsek:
        query = query.where(Location.polsek == polsek)
    if date_from:
        query = query.where(CrimeIncident.incident_date >= date_from)
    if date_to:
        query = query.where(CrimeIncident.incident_date <= date_to)
    if incident_type:
        query = query.where(CrimeIncident.incident_type == incident_type)
    if kecamatan:
        query = query.where(Location.kecamatan == kecamatan)

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.execute(query.offset(params.offset).limit(params.page_size)).all()

    return paginate(
        [
            {
                "code": incident.code,
                "incident_type": incident.incident_type,
                "occurred_at": incident.occurred_at,
                "incident_date": incident.incident_date,
                "incident_time": incident.incident_time.isoformat(),
                "location_type": incident.location_type,
                "modus": incident.modus,
                "target_type": incident.target_type,
                "status": incident.status,
                "kecamatan": location.kecamatan,
                "kelurahan": location.kelurahan,
                "polsek": location.polsek,
                "grid_id": location.grid_id,
            }
            for incident, location in rows
        ],
        total,
        params,
    )
