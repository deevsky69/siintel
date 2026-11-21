"""SIGAP BERSAMA — ringkasan wilayah untuk publik. **Tanpa autentikasi.**

Keputusan pemilik proyek 2 November 2026 (docs/01 §19.2, "SIGAP BERSAMA" butir 1): yang boleh
dilihat masyarakat hanya **angka historis per wilayah dan tingkat kerawanan kasar** — tanpa
prediksi, tanpa skor, tanpa titik kejadian, tanpa peringkat halus. Sederhana.

Yang dikembalikan per kelurahan: jumlah kejadian 3C dua belas bulan terakhir (sampai batas
tampilan data), rinciannya per jenis dan per bulan, dan satu dari tiga kata: RENDAH, SEDANG,
TINGGI. Kata itu ditentukan dari **tertil** jumlah kejadian di antara seluruh kelurahan —
sepertiga terendah RENDAH, sepertiga tertinggi TINGGI — bukan dari ambang yang ditetapkan
SOP. Aturan ini PROPOSED dan disebut pada `basis` supaya layar tidak menyajikannya sebagai
ketentuan. Kelurahan tanpa kejadian tercatat tetap muncul dengan RENDAH dan angka nol.

Nilai Survey Rasa Aman (rata-rata ulasan yang tayang) ikut disertakan agar peta warga dapat
menyandingkan persepsi dengan angka — keduanya ditandai berbeda di layar.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import AreaReview, AreaSummaryApproval, CrimeIncident, Location
from ...models.area_review import STATUS_PUBLISHED
from ...services import audit, clock, security_guides, visibility
from ...services import patrol_plan as planning
from ..deps import CurrentUser, get_db, require_permission
from ..errors import ApiError

router = APIRouter(prefix="/public/areas", tags=["kanal publik"])

LEVEL_LOW, LEVEL_MID, LEVEL_HIGH = "RENDAH", "SEDANG", "TINGGI"
MONTHS = 12

SUMMARY_BASIS = (
    "Jumlah kejadian Curanmor, Curat, dan Curas yang tercatat dua belas bulan terakhir per "
    "kelurahan (sampai batas tampilan data). Tingkat RENDAH/SEDANG/TINGGI adalah pembagian "
    "tertil di antara seluruh kelurahan Polres Metro Jakarta Selatan, bukan ambang resmi "
    "(PROPOSED). Tidak ada prediksi, skor, maupun titik kejadian pada data ini. Nilai rasa "
    "aman adalah rata-rata ulasan warga yang sudah dimoderasi — persepsi, bukan angka kejadian."
)


def _window(session: Session) -> tuple[date, date]:
    cutoff = visibility.display_cutoff() or clock.reference_now().astimezone(clock.JAKARTA).date()
    index = cutoff.year * 12 + (cutoff.month - 1) - (MONTHS - 1)
    year, month = divmod(index, 12)
    return date(year, month + 1, 1), cutoff


def _level_of(total: int, low_edge: int, high_edge: int) -> str:
    if total <= low_edge:
        return LEVEL_LOW
    if total >= high_edge:
        return LEVEL_HIGH
    return LEVEL_MID


def build_summary(session: Session) -> dict[str, Any]:
    start, end = _window(session)
    threats = planning._threats()

    kelurahan_rows = session.execute(
        select(Location.kelurahan, Location.kecamatan, Location.polsek)
        .where(Location.kelurahan.is_not(None))
        .group_by(Location.kelurahan, Location.kecamatan, Location.polsek)
        .order_by(Location.kecamatan, Location.kelurahan)
    ).all()

    month_key = func.to_char(CrimeIncident.incident_date, "YYYY-MM")
    counts = session.execute(
        select(Location.kelurahan, CrimeIncident.incident_type, month_key, func.count())
        .join(Location, Location.location_id == CrimeIncident.location_id)
        .where(
            CrimeIncident.incident_date >= start,
            CrimeIncident.incident_date <= end,
            CrimeIncident.incident_type.in_(threats),
            Location.kelurahan.is_not(None),
        )
        .group_by(Location.kelurahan, CrimeIncident.incident_type, month_key)
    ).all()

    by_threat: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_month: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total: dict[str, int] = defaultdict(int)
    for kelurahan, threat, month, count in counts:
        by_threat[str(kelurahan)][str(threat)] += int(count)
        by_month[str(kelurahan)][str(month)] += int(count)
        total[str(kelurahan)] += int(count)

    ratings = {
        str(kelurahan): (round(float(average), 1), int(count))
        for kelurahan, average, count in session.execute(
            select(Location.kelurahan, func.avg(AreaReview.rating), func.count())
            .join(Location, Location.location_id == AreaReview.location_id)
            .where(AreaReview.status == STATUS_PUBLISHED)
            .group_by(Location.kelurahan)
        ).all()
    }

    totals_sorted = sorted(total.get(str(row[0]), 0) for row in kelurahan_rows)
    n = len(totals_sorted)
    low_edge = totals_sorted[max(0, n // 3 - 1)] if n else 0
    high_edge = totals_sorted[min(n - 1, (2 * n) // 3)] if n else 0

    months: list[str] = []
    year, month = start.year, start.month
    for _ in range(MONTHS):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year, month = year + 1, 1

    areas = []
    for kelurahan, kecamatan, polsek in kelurahan_rows:
        name = str(kelurahan)
        rating = ratings.get(name)
        areas.append(
            {
                "kelurahan": name,
                "kecamatan": kecamatan,
                "polsek": polsek,
                "total": total.get(name, 0),
                "level": _level_of(total.get(name, 0), low_edge, high_edge),
                "by_threat": {threat: by_threat[name].get(threat, 0) for threat in threats},
                "by_month": [by_month[name].get(key, 0) for key in months],
                "rating": rating[0] if rating else None,
                "rating_count": rating[1] if rating else 0,
            }
        )

    kecamatan_totals: dict[str, dict[str, Any]] = {}
    for area in areas:
        bucket = kecamatan_totals.setdefault(
            str(area["kecamatan"]),
            {
                "kecamatan": area["kecamatan"],
                "total": 0,
                "kelurahan": 0,
                "by_threat": dict.fromkeys(threats, 0),
            },
        )
        bucket["total"] += area["total"]
        bucket["kelurahan"] += 1
        for threat in threats:
            bucket["by_threat"][threat] += area["by_threat"][threat]
    kec_totals_sorted = sorted(row["total"] for row in kecamatan_totals.values())
    m = len(kec_totals_sorted)
    kec_low = kec_totals_sorted[max(0, m // 3 - 1)] if m else 0
    kec_high = kec_totals_sorted[min(m - 1, (2 * m) // 3)] if m else 0
    for row in kecamatan_totals.values():
        row["level"] = _level_of(int(row["total"]), kec_low, kec_high)

    #: Daftar wilayah dan nilai Survey Rasa Aman — bukan bagian ringkasan kejadian, sehingga
    #: selalu tersedia (formulir survei dan layar petugas memerlukannya).
    directory = [
        {
            "kelurahan": area["kelurahan"],
            "kecamatan": area["kecamatan"],
            "polsek": area["polsek"],
            "rating": area["rating"],
            "rating_count": area["rating_count"],
        }
        for area in areas
    ]
    return {
        "window_from": start.isoformat(),
        "window_to": end.isoformat(),
        "months": months,
        "threat_types": list(threats),
        "level_edges": {"low_max": low_edge, "high_min": high_edge},
        "areas": areas,
        "kecamatan": sorted(kecamatan_totals.values(), key=lambda row: str(row["kecamatan"])),
        "directory": directory,
        "status": "PROPOSED",
        "basis": SUMMARY_BASIS,
    }


WITHHELD_NOTICE = (
    "Ringkasan wilayah periode ini belum disetujui Humas, sehingga angkanya belum ditayangkan. "
    "Layanan lapor, lacak laporan, cek kendaraan, panduan, dan survei tetap dapat dipakai."
)


def period_of(summary: dict[str, Any]) -> str:
    """Periode ringkasan = bulan terakhir jendelanya (YYYY-MM)."""
    return str(summary["window_to"])[:7]


def approval_for(session: Session, period: str) -> AreaSummaryApproval | None:
    return session.scalar(select(AreaSummaryApproval).where(AreaSummaryApproval.period == period))


def published_summary(session: Session) -> dict[str, Any]:
    """Ringkasan untuk masyarakat: angkanya hanya ikut bila periode itu sudah disetujui Humas
    (naskah Taskap revisi, Lampiran K huruf I). Sebelum itu yang dikirim hanya daftar wilayah —
    angka, tingkat kerawanan, dan rincian per jenis tidak pernah meninggalkan server."""
    summary = build_summary(session)
    period = period_of(summary)
    approval = approval_for(session, period)
    if approval is not None:
        return {
            **summary,
            "published": True,
            "period": period,
            "approved_at": approval.approved_at,
            "notice": None,
        }
    return {
        **summary,
        "level_edges": {"low_max": 0, "high_min": 0},
        "areas": [],
        "kecamatan": [],
        "published": False,
        "period": period,
        "approved_at": None,
        "notice": WITHHELD_NOTICE,
    }


@router.get("/summary", summary="Ringkasan historis per wilayah untuk masyarakat")
def area_summary(session: Session = Depends(get_db)) -> dict[str, Any]:
    return published_summary(session)


#: Sisi petugas: melihat pratinjau dan menyetujui. Router terpisah karena butuh sesi.
approval_router = APIRouter(tags=["kanal publik"])


class SummaryApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(default=None, max_length=1000)


def _approval_state(session: Session) -> dict[str, Any]:
    summary = build_summary(session)
    period = period_of(summary)
    approval = approval_for(session, period)
    return {
        "period": period,
        "window_from": summary["window_from"],
        "window_to": summary["window_to"],
        "approved": approval is not None,
        "approved_at": approval.approved_at if approval else None,
        "approval_note": approval.note if approval else None,
        "kelurahan": len(summary["areas"]),
        "incidents": sum(int(area["total"]) for area in summary["areas"]),
        "levels": {
            level: sum(1 for area in summary["areas"] if area["level"] == level)
            for level in (LEVEL_HIGH, LEVEL_MID, LEVEL_LOW)
        },
    }


@approval_router.get(
    "/area-summary/approval", summary="Pratinjau dan status persetujuan ringkasan wilayah"
)
def summary_approval_state(
    session: Session = Depends(get_db),
    _: CurrentUser = require_permission("bulletin:read"),
) -> dict[str, Any]:
    return _approval_state(session)


@approval_router.post(
    "/area-summary/approval",
    status_code=status.HTTP_201_CREATED,
    summary="Humas menyetujui ringkasan wilayah untuk masyarakat",
)
def approve_summary(
    payload: SummaryApprovalRequest,
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("public_info:approve"),
) -> dict[str, Any]:
    period = period_of(build_summary(session))
    if approval_for(session, period) is not None:
        raise ApiError(status.HTTP_409_CONFLICT, "Ringkasan periode ini sudah disetujui.")
    row = AreaSummaryApproval(
        period=period,
        approved_by=current.user.user_id,
        approved_at=clock.citizen_now(),
        note=(payload.note or "").strip() or None,
    )
    session.add(row)
    audit.record(
        session,
        action="APPROVE_AREA_SUMMARY",
        resource_type="area_summary",
        result=audit.RESULT_SUCCESS,
        user_id=current.user.user_id,
        resource_id=period,
        detail={"note": bool(row.note)},
    )
    session.commit()
    return _approval_state(session)


#: Router terpisah: panduan bukan bagian `/public/areas`.
guides_router = APIRouter(tags=["kanal publik"])


@guides_router.get("/public/guides", summary="Panduan pengamanan kos, parkir, gedung, dan RT/RW")
def public_guides(session: Session = Depends(get_db)) -> dict[str, Any]:
    """Naskah Taskap 4.7 f. Teks panduan dari konfigurasi (PROPOSED); pola di sampingnya
    agregat se-Polres 12 bulan terakhir — tanpa alamat, tanggal, maupun identitas."""
    return security_guides.guides(session)
