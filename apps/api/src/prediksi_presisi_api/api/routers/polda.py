"""Rekap kriminalitas Polda Metro Jaya per Polres (catatan 196).

```text
GET /polda/recap   (analytics:read, cakupan ALL)  posisi data terbaru + angka turunan
PUT /polda/recap   (config:manage)                memasukkan satu posisi data (hasil impor)
```

Datanya AGREGAT dari Pusiknas: jumlah Laporan Polisi (CT) menurut TANGGAL LAPORAN dan
penyelesaian (CC) per satuan per tahun — bukan data per kejadian, dan bukan dasar prediksi.
Angka di sini karenanya tidak sama dengan layar lain yang menghitung kejadian Polres Metro
Jakarta Selatan menurut tanggal kejadian; `basis` pada respons menyebutkannya.

**Siapa yang boleh membaca.** Rekap ini berlabel RAHASIA pada sumbernya dan mencakup satuan
lain. Karena itu yang disyaratkan bukan sekadar `analytics:read`, melainkan `analytics:read`
dengan cakupan seluruh wilayah: akun yang analitiknya dibatasi ke satu Polsek tidak
menerimanya. PROPOSED — menunggu penetapan pemilik proyek (catatan 196).

**Impor memvalidasi dirinya.** Sebelum disimpan, jumlah per satuan dicocokkan dengan baris
JUMLAH pada sumber, rincian jenis 3C dengan jumlah 3C, dan jumlah per bulan dengan jumlah
setahun. Satu selisih menggagalkan impor.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import PoldaRecap, User
from ...services import audit
from ...services.permissions import SCOPE_ALL
from ..deps import CurrentUser, get_db, require_permission
from ..errors import ApiError

router = APIRouter(tags=["polda"])

#: Satuan pemilik aplikasi ini — disorot pada layar.
HOME_UNIT = "Polres Metro Jakarta Selatan"

BASIS = (
    "Rekap Pusiknas Bareskrim Polri. CT = Laporan Polisi dalam periode menurut TANGGAL "
    "LAPORAN, satu laporan dihitung satu kali; CC = laporan periode yang sudah diselesaikan "
    "ditambah laporan sebelum periode yang diselesaikan dalam periode; CR = CC dibagi CT. "
    "Polres termasuk Polsek jajarannya. Tahun berjalan belum penuh, sehingga CR-nya wajar "
    "lebih rendah. Ini data agregat per satuan — bukan data per kejadian dan bukan dasar "
    "prediksi; angkanya tidak sama dengan layar yang menghitung kejadian menurut tanggal "
    "kejadian."
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Count(_Strict):
    ct: int = Field(ge=0)
    cc: int = Field(ge=0)


class ThreeC(Count):
    curat: int = Field(ge=0)
    curas: int = Field(ge=0)
    curanmor: int = Field(ge=0)


class Unit(_Strict):
    name: str = Field(min_length=2, max_length=120)
    kind: Literal["POLRES", "SATKER"]
    overall: dict[str, Count]
    c3: dict[str, ThreeC]
    #: Perubahan periode setara tahun berjalan terhadap tahun sebelumnya, menurut sumber.
    change_overall: float | None = None
    change_c3: float | None = None


class Totals(_Strict):
    overall: dict[str, Count]
    c3: dict[str, ThreeC]


class EqualPeriod(_Strict):
    label: str = Field(max_length=120)
    overall: dict[str, Count]
    c3: dict[str, Count]


class Month(_Strict):
    month: int = Field(ge=1, le=12)
    overall: dict[str, int]
    c3: dict[str, int]


class Settlement(_Strict):
    form: str = Field(max_length=120)
    counts: dict[str, int]


class TopType(_Strict):
    rank: int = Field(ge=1, le=50)
    name: str = Field(max_length=200)
    ct: int = Field(ge=0)


class RecapPayload(_Strict):
    position_at: datetime
    source: str = Field(min_length=5, max_length=300)
    source_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    years: list[int] = Field(min_length=1, max_length=10)
    #: Tahun berjalan (belum penuh) dan tanggal terakhir yang tercakup.
    current_year: int
    current_until: date
    units: list[Unit] = Field(min_length=1, max_length=80)
    totals: Totals
    equal_period: EqualPeriod | None = None
    monthly: list[Month] = Field(default_factory=list, max_length=12)
    settlements: list[Settlement] = Field(default_factory=list, max_length=20)
    top_types: dict[str, list[TopType]] = Field(default_factory=dict)


def check(payload: RecapPayload) -> list[str]:
    """Ketidakcocokan internal paket impor; kosong berarti seluruh jumlahnya cocok."""
    problems: list[str] = []
    years = [str(year) for year in payload.years]
    if payload.current_year not in payload.years:
        problems.append("Tahun berjalan tidak ada pada daftar tahun.")
    names = [unit.name for unit in payload.units]
    if len(set(names)) != len(names):
        problems.append("Ada satuan yang tercantum lebih dari satu kali.")
    for year in years:
        if year not in payload.totals.overall or year not in payload.totals.c3:
            problems.append(f"Baris JUMLAH tahun {year} tidak ada.")
            continue
        for unit in payload.units:
            if year not in unit.overall or year not in unit.c3:
                problems.append(f"{unit.name}: angka tahun {year} tidak ada.")
                break
            c3 = unit.c3[year]
            if c3.curat + c3.curas + c3.curanmor != c3.ct:
                problems.append(f"{unit.name} {year}: curat + curas + curanmor ≠ jumlah 3C.")
            if c3.ct > unit.overall[year].ct:
                problems.append(f"{unit.name} {year}: 3C melebihi kriminal keseluruhan.")
        else:
            total, total3 = payload.totals.overall[year], payload.totals.c3[year]
            sums = {
                "CT keseluruhan": (sum(u.overall[year].ct for u in payload.units), total.ct),
                "CC keseluruhan": (sum(u.overall[year].cc for u in payload.units), total.cc),
                "CT 3C": (sum(u.c3[year].ct for u in payload.units), total3.ct),
                "CC 3C": (sum(u.c3[year].cc for u in payload.units), total3.cc),
                "curat": (sum(u.c3[year].curat for u in payload.units), total3.curat),
                "curas": (sum(u.c3[year].curas for u in payload.units), total3.curas),
                "curanmor": (sum(u.c3[year].curanmor for u in payload.units), total3.curanmor),
            }
            for label, (got, expected) in sums.items():
                if got != expected:
                    problems.append(
                        f"{year}: jumlah {label} per satuan {got} ≠ baris JUMLAH {expected}."
                    )
        if payload.monthly and year in payload.totals.overall:
            for scope, expected in (
                ("overall", payload.totals.overall[year].ct),
                ("c3", payload.totals.c3[year].ct),
            ):
                got = sum(getattr(month, scope).get(year, 0) for month in payload.monthly)
                if got != expected:
                    problems.append(
                        f"{year}: jumlah per bulan ({scope}) {got} ≠ jumlah setahun {expected}."
                    )
    return problems


def _rate(cc: int, ct: int) -> float | None:
    return round(cc / ct * 100, 2) if ct else None


def _present(row: PoldaRecap, importer: str | None) -> dict[str, Any]:
    data = row.payload
    years = [str(year) for year in data["years"]]
    current = str(data["current_year"])
    polda_c3 = {year: data["totals"]["c3"][year]["ct"] for year in years}
    polda_all = {year: data["totals"]["overall"][year]["ct"] for year in years}

    def unit(entry: dict[str, Any]) -> dict[str, Any]:
        overall = {
            year: {**entry["overall"][year], "cr": _rate(**_cc_ct(entry["overall"][year]))}
            for year in years
        }
        c3 = {
            year: {
                **entry["c3"][year],
                "cr": _rate(**_cc_ct(entry["c3"][year])),
                # Porsi 3C satuan ini terhadap seluruh 3C Polda pada tahun itu.
                "share_pct": _rate(entry["c3"][year]["ct"], polda_c3[year]),
                # Porsi 3C terhadap seluruh kriminalitas satuan itu.
                "of_overall_pct": _rate(entry["c3"][year]["ct"], entry["overall"][year]["ct"]),
            }
            for year in years
        }
        for year in years:
            overall[year]["share_pct"] = _rate(entry["overall"][year]["ct"], polda_all[year])
        return {
            "name": entry["name"],
            "kind": entry["kind"],
            "home": entry["name"] == HOME_UNIT,
            "overall": overall,
            "c3": c3,
            "change_overall_pct": _pct(entry.get("change_overall")),
            "change_c3_pct": _pct(entry.get("change_c3")),
        }

    units = [unit(entry) for entry in data["units"]]
    # Peringkat di antara Polres (satuan kerja tingkat Polda tidak diperingkat), menurut CT
    # tahun berjalan; 1 = terbanyak.
    for scope in ("c3", "overall"):
        ranked = sorted(
            (u for u in units if u["kind"] == "POLRES"),
            key=lambda u: (-u[scope][current]["ct"], u["name"]),
        )
        for position, entry in enumerate(ranked, start=1):
            entry[f"rank_{scope}"] = position
    totals = {
        scope: {
            year: {
                **data["totals"][scope][year],
                "cr": _rate(**_cc_ct(data["totals"][scope][year])),
            }
            for year in years
        }
        for scope in ("overall", "c3")
    }
    for year in years:
        totals["c3"][year]["of_overall_pct"] = _rate(polda_c3[year], polda_all[year])
    equal = data.get("equal_period")
    if equal:
        equal = {
            "label": equal["label"],
            **{
                scope: {
                    year: {**equal[scope][year], "cr": _rate(**_cc_ct(equal[scope][year]))}
                    for year in years
                    if year in equal[scope]
                }
                for scope in ("overall", "c3")
            },
        }
    return {
        "available": True,
        "position_at": row.position_at,
        "source": row.source,
        "source_sha256": row.source_sha256,
        "imported_at": row.imported_at,
        "imported_by": importer,
        "years": data["years"],
        "current_year": data["current_year"],
        "current_until": data["current_until"],
        "home_unit": HOME_UNIT,
        "polres_count": sum(1 for u in units if u["kind"] == "POLRES"),
        "units": units,
        "totals": totals,
        "equal_period": equal,
        "monthly": data.get("monthly", []),
        "settlements": data.get("settlements", []),
        "top_types": data.get("top_types", {}),
        "basis": BASIS,
    }


def _cc_ct(entry: dict[str, Any]) -> dict[str, int]:
    return {"cc": int(entry["cc"]), "ct": int(entry["ct"])}


def _pct(value: float | None) -> float | None:
    return None if value is None else round(float(value) * 100, 2)


def _require_whole_jurisdiction(current: CurrentUser, session: Session) -> None:
    if current.permissions.scope_for("analytics:read") == SCOPE_ALL:
        return
    audit.record(
        session,
        action="READ_POLDA_RECAP",
        resource_type="polda_recap",
        result=audit.RESULT_DENIED,
        user_id=current.user.user_id,
        detail={"required": "analytics:read dengan cakupan ALL"},
    )
    session.commit()
    raise ApiError(
        status.HTTP_403_FORBIDDEN,
        "Rekap Polda hanya untuk akun yang analitiknya mencakup seluruh wilayah.",
    )


@router.get("/polda/recap", summary="Rekap kriminalitas Polda Metro Jaya per Polres")
def polda_recap(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("analytics:read"),
) -> dict[str, Any]:
    _require_whole_jurisdiction(current, session)
    found = session.execute(
        select(PoldaRecap, User.username)
        .outerjoin(User, User.user_id == PoldaRecap.imported_by)
        .order_by(PoldaRecap.position_at.desc())
        .limit(1)
    ).first()
    if found is None:
        return {"available": False, "home_unit": HOME_UNIT, "basis": BASIS}
    return _present(found[0], found[1])


@router.put("/polda/recap", summary="Memasukkan satu posisi data rekap Polda")
def import_polda_recap(
    payload: RecapPayload,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("config:manage"),
) -> dict[str, Any]:
    problems = check(payload)
    if problems:
        audit.record(
            session,
            action="IMPORT_POLDA_RECAP",
            resource_type="polda_recap",
            result=audit.RESULT_FAILED,
            user_id=current.user.user_id,
            detail={"problems": problems[:20]},
        )
        session.commit()
        raise ApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Rekap ditolak: jumlahnya tidak cocok. " + " ".join(problems[:5]),
        )
    body = payload.model_dump(mode="json", exclude={"position_at", "source", "source_sha256"})
    row = session.scalar(select(PoldaRecap).where(PoldaRecap.position_at == payload.position_at))
    replaced = row is not None
    if row is None:
        row = PoldaRecap(position_at=payload.position_at)
        session.add(row)
    row.source = payload.source
    row.source_sha256 = payload.source_sha256
    row.payload = body
    row.imported_by = current.user.user_id
    row.imported_at = datetime.now(tz=payload.position_at.tzinfo)
    session.flush()
    audit.record(
        session,
        action="IMPORT_POLDA_RECAP",
        resource_type="polda_recap",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=str(row.recap_id),
        detail={
            "position_at": payload.position_at.isoformat(),
            "units": len(payload.units),
            "replaced": replaced,
            "sha256": payload.source_sha256,
        },
    )
    session.commit()
    return {
        "recap_id": str(row.recap_id),
        "position_at": row.position_at,
        "units": len(payload.units),
        "replaced": replaced,
    }
