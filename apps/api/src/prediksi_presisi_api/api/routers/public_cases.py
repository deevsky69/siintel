"""SIGAP WARGA — lacak laporan dan cek kendaraan. **Tanpa autentikasi.**

```text
GET /public/cases/track?lp=…&pin=…               tahap perkara milik pelapor (nomor LP + PIN)
GET /public/vehicles/check?plat=… | ?rangka=…    tercatat sebagai laporan kehilangan atau tidak
```

Nomor LP yang tidak ada, PIN yang salah, dan LP tanpa PIN dijawab SAMA (404) — supaya
endpoint ini tidak menjadi alat memastikan sebuah LP ada. Cek kendaraan menjawab hanya
tercatat/tidak, jenis, dan bulan laporan; tanpa nama, nomor LP, atau alamat. Keduanya
dibatasi laju per alamat dan dicatat di audit tanpa menyimpan plat/LP yang dicari.
"""

from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ...models import CaseFile
from ...models.case_file import STAGE_LABELS, hash_pin, normalize_plate
from ...services import audit
from ..deps import get_db
from ..errors import ApiError
from .public_intake import _client_key, _RateLimiter

router = APIRouter(prefix="/public", tags=["kanal publik"])

limiter = _RateLimiter(10, 3600)
#: PIN salah per NOMOR LP: lima kali per jam, apa pun alamatnya. Pembatas per alamat saja
#: dapat dilewati dengan memalsukan header; yang ini mengunci sasarannya, sehingga menebak
#: 10.000 kombinasi PIN memakan ribuan jam.
pin_failures = _RateLimiter(5, 3600)
MONTHS_ID = (
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
)  # fmt: skip

TRACK_BASIS = (
    "Tahap perkara mengikuti istilah SP2HP: Laporan diterima, Penyelidikan, Penyidikan, P21, "
    "SP3, Selesai. Dibuka hanya dengan nomor LP dan PIN pelapor; nomor yang tidak cocok dijawab "
    "sama dengan yang tidak ada. Baris berlabel DUMMY adalah data peragaan, bukan perkara nyata."
)
VEHICLE_BASIS = (
    "Dicocokkan dengan berkas perkara Curanmor yang tercatat pada sistem ini (bukan seluruh "
    "data kepolisian). Jawaban hanya tercatat/tidak, jenis, dan bulan laporan — tanpa nama "
    "pemilik maupun nomor LP. Untuk kepastian hukum, periksa ke Samsat/Polsek. Baris DUMMY "
    "adalah data peragaan."
)


def _month(d: Any) -> str:
    return f"{MONTHS_ID[d.month - 1]} {d.year}"


def _rate_limited(request: Request) -> None:
    if not limiter.allow(_client_key(request)):
        raise ApiError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Terlalu banyak pencarian dari jaringan ini dalam satu jam terakhir.",
        )


@router.get("/cases/track", summary="Lacak tahap laporan dengan nomor LP dan PIN")
def track_case(
    request: Request,
    lp: str = Query(min_length=5, max_length=80),
    pin: str = Query(min_length=4, max_length=4, pattern=r"^\d{4}$"),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    _rate_limited(request)
    lp_key = lp.strip().upper()
    if pin_failures.exhausted(lp_key):
        raise ApiError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Terlalu banyak percobaan PIN untuk nomor LP ini. Coba lagi satu jam lagi.",
        )
    case = session.scalar(select(CaseFile).where(CaseFile.lp_number == lp_key))
    stored = case.reporter_pin_hash if case is not None else "-"
    if case is None or not secrets.compare_digest(stored, hash_pin(lp, pin)):
        pin_failures.allow(lp_key)  # hanya kegagalan yang dihitung
        audit.record(
            session,
            action="TRACK_CASE",
            resource_type="case_file",
            result=audit.RESULT_FAILED,
            user_id=None,
            detail={"found": False},
        )
        session.commit()
        raise ApiError(status.HTTP_404_NOT_FOUND, "Laporan tidak ditemukan atau PIN tidak cocok.")
    audit.record(
        session,
        action="TRACK_CASE",
        resource_type="case_file",
        result=audit.RESULT_SUCCESS,
        user_id=None,
        resource_id=case.lp_number,
        detail={"found": True, "is_dummy": case.is_dummy},
    )
    session.commit()
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
        "vehicle": (
            {
                "plate": case.vehicle_plate_display,
                "description": case.vehicle_desc,
                "recovered": case.vehicle_recovered,
            }
            if case.vehicle_plate
            else None
        ),
        "history": [
            {
                "stage": row.stage,
                "stage_label": STAGE_LABELS.get(row.stage, row.stage),
                "changed_at": row.changed_at,
                "note": row.note,
            }
            for row in case.stages
        ],
        "is_dummy": case.is_dummy,
        "basis": TRACK_BASIS,
    }


@router.get("/vehicles/check", summary="Cek apakah kendaraan tercatat sebagai laporan kehilangan")
def check_vehicle(
    request: Request,
    plat: str | None = Query(None, max_length=20),
    rangka: str | None = Query(None, max_length=30),
    session: Session = Depends(get_db),
) -> dict[str, Any]:
    _rate_limited(request)
    plate = normalize_plate(plat) if plat else ""
    vin = (rangka or "").strip().upper()
    if len(plate) < 4 and len(vin) < 8:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST, "Isi plat nomor (minimal 4 karakter) atau nomor rangka."
        )
    conditions = []
    if len(plate) >= 4:
        conditions.append(CaseFile.vehicle_plate == plate)
    if len(vin) >= 8:
        conditions.append(CaseFile.vehicle_vin == vin)
    rows = session.scalars(
        select(CaseFile).where(or_(*conditions)).order_by(CaseFile.reported_on.desc()).limit(3)
    ).all()
    audit.record(
        session,
        action="CHECK_VEHICLE",
        resource_type="case_file",
        result=audit.RESULT_SUCCESS,
        user_id=None,
        detail={"found": bool(rows), "by": "rangka" if vin and not plate else "plat"},
    )
    session.commit()
    return {
        "found": bool(rows),
        "records": [
            {
                "crime_type": row.crime_type,
                "reported_month": _month(row.reported_on),
                "kecamatan": row.location.kecamatan,
                "recovered": row.vehicle_recovered,
                "is_dummy": row.is_dummy,
            }
            for row in rows
        ],
        "advice": (
            "Kendaraan ini tercatat dalam laporan kehilangan. Jangan lanjutkan transaksi; "
            "laporkan ke Polsek terdekat atau hubungi 110."
            if rows
            else "Tidak ada catatan laporan kehilangan untuk kendaraan ini pada sistem ini. "
            "Tetap periksa keaslian BPKB/STNK di Samsat."
        ),
        "basis": VEHICLE_BASIS,
    }
