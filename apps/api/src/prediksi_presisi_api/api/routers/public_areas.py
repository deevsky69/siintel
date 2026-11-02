"""SIGAP WARGA — ringkasan wilayah untuk publik. **Tanpa autentikasi.**

Keputusan pemilik proyek 2 November 2026 (docs/01 §19.2, "SIGAP WARGA" butir 1): yang boleh
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

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import AreaReview, CrimeIncident, Location
from ...models.area_review import STATUS_PUBLISHED
from ...services import clock, visibility
from ...services import patrol_plan as planning
from ..deps import get_db

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

    return {
        "window_from": start.isoformat(),
        "window_to": end.isoformat(),
        "months": months,
        "threat_types": list(threats),
        "level_edges": {"low_max": low_edge, "high_min": high_edge},
        "areas": areas,
        "kecamatan": sorted(kecamatan_totals.values(), key=lambda row: str(row["kecamatan"])),
        "status": "PROPOSED",
        "basis": SUMMARY_BASIS,
    }


@router.get("/summary", summary="Ringkasan historis per wilayah untuk masyarakat")
def area_summary(session: Session = Depends(get_db)) -> dict[str, Any]:
    return build_summary(session)
