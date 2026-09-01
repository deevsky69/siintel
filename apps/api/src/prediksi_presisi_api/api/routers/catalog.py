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

from ...models import CrimeIncident, Location, PoliceUnit
from ..deps import (
    CurrentUser,
    function_filter,
    get_db,
    jurisdiction_filter,
    require_permission,
)
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


#: Penjelasan cara satuan disaring, ikut dikembalikan agar tidak menjadi perilaku tersembunyi.
UNIT_SCOPE_BASIS = (
    "Pengguna yang dibatasi wilayah menerima satuan di polseknya, ditambah satuan tingkat "
    "Polres — sebab satuan tingkat Polres memang bertugas melintasi seluruh polsek, "
    "termasuk wilayahnya."
)


@router.get("/police-units", summary="Daftar satuan")
def list_police_units(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("police_unit:read"),
    status: str | None = Query(None, description="ACTIVE, STANDBY, atau lainnya"),
) -> dict[str, Any]:
    """Satuan yang dapat ditugaskan, tersaring menurut cakupan pengguna.

    `police_units.jurisdiction` berisi nama polsek **atau** nama Polres untuk satuan yang
    bertugas lintas polsek. Menyaring dengan pencocokan tepat akan menyembunyikan satuan
    tingkat Polres dari pengguna polsek — padahal satuan itu justru bertugas di
    wilayahnya juga.

    Karena itu satuan tingkat Polres dikenali dari **datanya sendiri**: satuan yang
    `jurisdiction`-nya bukan salah satu polsek pada tabel `locations`. Tidak ada nama
    Polres yang ditanam di kode, sehingga penggantian nama satuan wilayah tidak
    menyisakan konstanta usang di sini.
    """
    polsek = jurisdiction_filter(current, "police_unit:read")
    function = function_filter(current, "police_unit:read")

    query = select(PoliceUnit).order_by(PoliceUnit.code)
    if polsek is not None:
        known_polsek = select(Location.polsek).where(Location.polsek.is_not(None)).distinct()
        query = query.where(
            (PoliceUnit.jurisdiction == polsek) | PoliceUnit.jurisdiction.not_in(known_polsek)
        )
    if function is not None:
        query = query.where(PoliceUnit.function == function)
    if status:
        query = query.where(PoliceUnit.status == status.upper())

    units = session.scalars(query).all()

    return {
        "data": [
            {
                "code": unit.code,
                "unit_name": unit.unit_name,
                "function": unit.function,
                "jurisdiction": unit.jurisdiction,
                "status": unit.status,
            }
            for unit in units
        ],
        "scope_basis": UNIT_SCOPE_BASIS,
    }
