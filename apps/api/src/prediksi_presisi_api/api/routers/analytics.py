"""API Crime Analytics dan daftar laporan intelijen (TASK 033, 035).

Modul ini memuat dua kelompok endpoint yang kebetulan dibangun bersama karena keduanya
menutup dua layar yang sebelumnya masih berupa halaman rencana:

```text
GET /intelligence-reports        intelligence:read   daftar berpaginasi + penyaring
GET /analytics/trend             analytics:read      kejadian per bulan, lintas jenis
GET /analytics/time-pattern      analytics:read      matriks hari x jam
GET /analytics/spatial-pattern   analytics:read      perbandingan antarwilayah
```

`POST /intelligence-reports` **tidak** ada di sini — ia sudah lebih dulu hidup di
`routers/data_entry.py`. FastAPI mengizinkan path yang sama dilayani method berbeda dari
router berbeda, dan memindahkannya hanya untuk kerapian berarti menyentuh berkas yang
sedang dikerjakan orang lain.

## Apa bedanya modul ini dengan Crime Pattern DNA

`routers/patterns.py` menjawab: **untuk satu jenis gangguan, seperti apa sebarannya**
menurut lima dimensi where–when–how–target–repeat. Modul ini menjawab pertanyaan yang
berbeda arah: **bagaimana jenis-jenis gangguan dibandingkan satu sama lain**, lintas bulan
dan lintas kecamatan. Satu profil mendalam versus satu perbandingan mendatar.

Karena keduanya membaca tabel yang sama, agregasi dasarnya **dipakai ulang, bukan
disalin**: `_incidents`, `_share`, `_threat_types`, `DAY_LABELS`, dan `TIME_BASIS` diimpor
dari `patterns.py`. Nama-nama itu berawalan garis bawah — private menurut kebiasaan
modulnya sendiri — dan impor ini disengaja: menyalin querinya berarti dua definisi
"kejadian dalam cakupan" yang dapat berbeda diam-diam ketika salah satunya diperbaiki.
Bila kelak berkas itu boleh disunting, tempat yang benar bagi kelima nama tersebut adalah
satu modul agregasi bersama.

## Batas yang berlaku sama seperti pada Crime Pattern DNA

1. **Deskriptif, bukan prediktif.** Seluruhnya hitungan kejadian yang sudah terjadi. Tidak
   ada skor risiko, tidak ada tingkat keyakinan (CLAUDE.md §27).
2. **Tidak ada ambang "signifikan".** Tidak satu bulan, sel waktu, atau kecamatan pun
   ditandai menonjol; ambang seperti itu belum ditetapkan siapa pun (CLAUDE.md §11).
   Nilai terbesar tetap disebut — tetapi sebagai fakta aritmetika ("ini yang terbanyak"),
   bukan sebagai temuan.
3. **Setiap persentase membawa penyebutnya**, dan setiap angka turunan membawa `*_basis`.
4. **Cakupan wilayah disaring di query**, bukan setelah data terambil.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import Integer, Select, cast, func, select
from sqlalchemy.orm import Session

from ...models import CrimeIncident, IntelligenceReport, Location
from ..analysis import (
    DAY_LABELS,
    HOURS_PER_DAY,
    MAX_THREAT_TYPE_LENGTH,
    TIME_BASIS,
    incidents,
    share,
    threat_types,
)
from ..deps import CurrentUser, get_db, jurisdiction_filter, require_permission
from ..errors import ApiError
from ..pagination import PageParams, page_params, paginate

router = APIRouter(tags=["analitik"])

#: Singkatan bulan Indonesia untuk label sumbu tren. Bulan diberi nomor 1–12, sehingga
#: indeks 0 sengaja dikosongkan agar `MONTH_LABELS[month]` terbaca apa adanya.
MONTH_LABELS = (
    "",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "Mei",
    "Jun",
    "Jul",
    "Agu",
    "Sep",
    "Okt",
    "Nov",
    "Des",
)

#: Batas panjang sumbu tren. Rentang tanggal berasal dari pengguna; tanpa batas, permintaan
#: `date_from=1800-01-01` akan membangkitkan ribuan bulan kosong di dalam respons.
MAX_TREND_MONTHS = 240

ANALYSIS_BASIS = (
    "Seluruh angka pada layar analitik adalah jumlah kejadian yang SUDAH TERJADI pada "
    "tabel crime_incidents — bukan prediksi, bukan skor risiko, dan tidak memiliki tingkat "
    "keyakinan. Tidak ada bulan, sel waktu, atau wilayah yang ditandai 'signifikan': "
    "ambang untuk itu belum ditetapkan (CLAUDE.md §11). Nilai terbesar disebut sebagai "
    "fakta aritmetika, bukan sebagai temuan."
)

RELATED_ANALYSIS_BASIS = (
    "Layar ini membandingkan jenis gangguan satu sama lain, lintas bulan dan lintas "
    "kecamatan. Profil mendalam SATU jenis — where, when, how, target, repeat — ada pada "
    "Crime Pattern DNA (GET /analytics/crime-pattern-dna). Keduanya membaca tabel yang "
    "sama dan memakai agregasi dasar yang sama, sehingga angkanya konsisten; yang berbeda "
    "adalah sudut pandangnya."
)

#: Perbandingan antarwilayah memakai jumlah mentah. Ini keterbatasan data, bukan pilihan
#: analitik, dan harus dinyatakan — bukan disembunyikan di balik kata "perbandingan".
RATE_BASIS = (
    "Perbandingan antarwilayah ini memakai JUMLAH kejadian, bukan angka per penduduk "
    "maupun per luas wilayah: tabel locations tidak menyimpan jumlah penduduk atau luas. "
    "Kecamatan yang lebih padat atau lebih luas karena itu akan tampak lebih tinggi tanpa "
    "hal itu berarti lebih rawan. Angka per penduduk memerlukan data kependudukan resmi "
    "yang belum ditetapkan sebagai sumber (U-19)."
)

# ---------------------------------------------------------------------------
# Pembantu bersama
# ---------------------------------------------------------------------------


def _ranged(query: Select[Any], date_from: date | None, date_to: date | None) -> Select[Any]:
    """Menyempitkan query kejadian ke rentang tanggal setempat (`incident_date`)."""
    if date_from is not None:
        query = query.where(CrimeIncident.incident_date >= date_from)
    if date_to is not None:
        query = query.where(CrimeIncident.incident_date <= date_to)
    return query


def _validated_range(date_from: date | None, date_to: date | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            "Rentang tanggal terbalik: tanggal awal melewati tanggal akhir.",
            details=[{"field": "date_from", "issue": f"harus <= date_to ({date_to.isoformat()})"}],
        )


def _validated_threat_type(available: list[dict[str, Any]], threat_type: str | None) -> str | None:
    """Jenis gangguan yang diminta, dicocokkan ke jenis yang ada di dalam cakupan pengguna.

    Jenis tak dikenal dijawab 400 beserta daftar yang tersedia — sama seperti Crime Pattern
    DNA. Mengembalikan hasil kosong akan terbaca seolah jenis itu ada tetapi tidak
    berkejadian, padahal yang terjadi adalah nama yang tidak dikenal.
    """
    if threat_type is None:
        return None

    requested = threat_type.strip().upper()
    known = {str(row["threat_type"]) for row in available}
    if len(requested) > MAX_THREAT_TYPE_LENGTH or requested not in known:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            "Jenis gangguan tidak dikenal pada data yang dapat Anda lihat.",
            details=[{"field": "threat_type", "issue": f"harus salah satu dari {sorted(known)}"}],
        )
    return requested


def _extent(
    session: Session,
    polsek: str | None,
    threat_type: str | None,
    date_from: date | None,
    date_to: date | None,
) -> tuple[date | None, date | None, int]:
    """Rentang tanggal dan jumlah baris yang benar-benar menghasilkan angka."""
    query = _ranged(incidents(polsek, threat_type), date_from, date_to).add_columns(
        func.min(CrimeIncident.incident_date),
        func.max(CrimeIncident.incident_date),
        func.count(),
    )
    first, last, total = session.execute(query).one()
    return first, last, int(total)


def _scope_basis(polsek: str | None) -> str:
    return (
        f"Seluruh angka dihitung hanya dari kejadian di wilayah {polsek}."
        if polsek
        else "Seluruh angka dihitung dari kejadian di seluruh wilayah Polres."
    )


def _source(
    table: str,
    first: date | None,
    last: date | None,
    total: int,
    polsek: str | None,
) -> dict[str, Any]:
    return {
        "table": table,
        "date_from": first,
        "date_to": last,
        "incidents": total,
        "scope": polsek,
    }


def _month_axis(first: date, last: date) -> list[tuple[int, int]]:
    """Deretan (tahun, bulan) dari `first` sampai `last`, termasuk bulan tanpa kejadian.

    Bulan kosong tetap muncul sebagai nol karena memang nol — membuangnya akan merapatkan
    grafik dan menyembunyikan jeda yang justru bermakna.
    """
    months: list[tuple[int, int]] = []
    year, month = first.year, first.month
    while (year, month) <= (last.year, last.month):
        months.append((year, month))
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return months


# ---------------------------------------------------------------------------
# Laporan intelijen — daftar berpaginasi
# ---------------------------------------------------------------------------

#: Laporan intelijen membawa tiga angka yang mudah disalahbaca sebagai keluaran model.
#: Ketiganya adalah **penilaian manusia yang tercatat pada laporan**, bukan hasil hitungan
#: sistem, dan responsnya menyatakan itu supaya tidak perlu ditebak dari nama kolomnya.
INTELLIGENCE_ASSESSMENT_BASIS = (
    "reliability (A/B/C), confidence (0-100), dan urgency (0-100) adalah penilaian yang "
    "DICATAT PADA LAPORAN oleh pelapor/penyusunnya — bukan keluaran model dan bukan "
    "hitungan sistem. Sistem tidak memverifikasi ketiganya, tidak menggabungkannya menjadi "
    "satu skor, dan tidak menetapkan ambang 'cukup andal'."
)

INTELLIGENCE_FILTER_BASIS = (
    "Jumlah pada tiap pilihan penyaring dihitung atas SELURUH laporan dalam cakupan Anda, "
    "bukan atas hasil penyaringan yang sedang tampil — supaya terlihat berapa banyak yang "
    "akan muncul bila pilihannya diganti."
)


def _intelligence_scope(polsek: str | None) -> Select[Any]:
    """Kerangka query laporan intelijen yang sudah tersaring cakupan wilayah.

    Cakupan ditegakkan lewat `location_id → locations.polsek`; `intelligence_reports`
    sendiri tidak menyimpan wilayah maupun fungsi (lihat catatan RBAC pada
    `config/rbac/permissions.yaml`).
    """
    query = (
        select()
        .select_from(IntelligenceReport)
        .join(Location, Location.location_id == IntelligenceReport.location_id)
    )
    return query if polsek is None else query.where(Location.polsek == polsek)


def _intelligence_facets(session: Session, polsek: str | None, column: Any) -> list[dict[str, Any]]:
    """Nilai penyaring yang benar-benar ada di dalam cakupan pengguna, beserta jumlahnya.

    Diambil dari data, bukan dari daftar tetap: kategori intelijen memang tidak memiliki
    domain resmi pada `config/taxonomy/mappings.yaml` (lihat `data_entry.create_intelligence`),
    sehingga menuliskan daftarnya di sini berarti mengarang taksonomi.
    """
    query = (
        _intelligence_scope(polsek)
        .add_columns(column, func.count())
        .where(column.is_not(None))
        .group_by(column)
        .order_by(func.count().desc(), column)
    )
    return [
        {"value": str(value), "reports": int(count)}
        for value, count in session.execute(query).all()
    ]


@router.get("/intelligence-reports", summary="Daftar laporan intelijen")
def list_intelligence_reports(
    session: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    current: CurrentUser = require_permission("intelligence:read"),
    status_filter: str | None = Query(
        None, alias="status", description="NEW, VERIFIED, FOLLOWED_UP, atau CLOSED"
    ),
    category: str | None = Query(None, description="Kategori laporan, mis. Potensi Tawuran"),
) -> dict[str, Any]:
    """Laporan intelijen dalam cakupan pengguna, terbaru lebih dulu.

    Diurutkan menurun menurut tanggal laporan, lalu menurut kode agar dua laporan
    bertanggal sama selalu tampil dalam urutan yang sama — halaman kedua tidak boleh
    berisi baris yang sudah muncul di halaman pertama (hasil yang dapat direproduksi).

    Penyaring `status` dicocokkan tanpa memandang huruf besar/kecil; `category` dicocokkan
    persis karena kategori adalah teks bebas yang dimasukkan petugas, dan pencocokan
    longgar akan menggabungkan dua kategori berbeda menjadi satu angka tanpa terlihat.
    """
    polsek = jurisdiction_filter(current, "intelligence:read")

    query = (
        select(IntelligenceReport, Location)
        .join(Location, Location.location_id == IntelligenceReport.location_id)
        .order_by(IntelligenceReport.report_date.desc(), IntelligenceReport.code.desc())
    )
    if polsek:
        query = query.where(Location.polsek == polsek)
    if status_filter:
        query = query.where(IntelligenceReport.status == status_filter.strip().upper())
    if category:
        query = query.where(IntelligenceReport.category == category.strip())

    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = session.execute(query.offset(params.offset).limit(params.page_size)).all()

    page = paginate(
        [
            {
                "code": report.code,
                "report_date": report.report_date,
                "category": report.category,
                "reliability": report.reliability,
                "confidence": report.confidence,
                "urgency": report.urgency,
                "impact": report.impact,
                "status": report.status,
                "location_code": location.code,
                "kecamatan": location.kecamatan,
                "kelurahan": location.kelurahan,
                "polsek": location.polsek,
                "grid_id": location.grid_id,
            }
            for report, location in rows
        ],
        total,
        params,
    )

    # Jumlah seluruh laporan dalam cakupan — pembanding bagi `total` yang sudah tersaring,
    # sehingga pembaca tahu berapa banyak yang sedang disembunyikan oleh penyaringnya.
    scope_total = session.scalar(_intelligence_scope(polsek).add_columns(func.count())) or 0

    return {
        **page,
        "filters": {
            "status": _intelligence_facets(session, polsek, IntelligenceReport.status),
            "category": _intelligence_facets(session, polsek, IntelligenceReport.category),
            "reliability": _intelligence_facets(session, polsek, IntelligenceReport.reliability),
        },
        "source": {
            "table": "intelligence_reports",
            "reports_in_scope": scope_total,
            "scope": polsek,
        },
        "scope_basis": (
            f"Hanya laporan yang wilayahnya berada di {polsek} yang dapat Anda lihat; "
            "penyaringan dilakukan di query lewat location_id → locations.polsek."
            if polsek
            else "Seluruh laporan di wilayah Polres dapat Anda lihat."
        ),
        "filter_basis": INTELLIGENCE_FILTER_BASIS,
        "assessment_basis": INTELLIGENCE_ASSESSMENT_BASIS,
    }


# ---------------------------------------------------------------------------
# Tren kejadian per bulan
# ---------------------------------------------------------------------------


@router.get("/analytics/trend", summary="Tren kejadian per bulan, lintas jenis gangguan")
def crime_trend(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("analytics:read"),
    threat_type: str | None = Query(None, description="Batasi ke satu jenis, mis. CURANMOR"),
    date_from: date | None = Query(None, description="Tanggal awal (incident_date)"),
    date_to: date | None = Query(None, description="Tanggal akhir (incident_date)"),
) -> dict[str, Any]:
    """Jumlah kejadian per bulan, satu deret per jenis gangguan.

    Berbeda dari `/dashboard/trends`, yang membandingkan **tahun terhadap tahun** pada satu
    sumbu dua belas bulan dan tidak memisahkan jenis: di sini sumbunya kalender berurut dan
    tiap jenis punya deretnya sendiri, sehingga yang terbaca adalah komposisi — jenis mana
    yang bergerak, bukan sekadar totalnya.

    Sumbu bulan dibangun dari rentang yang diminta bila diisi, selebihnya dari rentang data
    yang ada. Bulan tanpa kejadian tetap dikirim sebagai nol.
    """
    polsek = jurisdiction_filter(current, "analytics:read")
    _validated_range(date_from, date_to)
    available = threat_types(session, polsek)
    requested = _validated_threat_type(available, threat_type)

    first, last, total = _extent(session, polsek, requested, date_from, date_to)

    axis_from = date_from or first
    axis_to = date_to or last
    months = [] if axis_from is None or axis_to is None else _month_axis(axis_from, axis_to)
    if len(months) > MAX_TREND_MONTHS:
        raise ApiError(
            status.HTTP_400_BAD_REQUEST,
            f"Rentang terlalu panjang: {len(months)} bulan, batasnya {MAX_TREND_MONTHS}.",
            details=[{"field": "date_from", "issue": f"maksimal {MAX_TREND_MONTHS} bulan"}],
        )

    year = cast(func.extract("year", CrimeIncident.incident_date), Integer).label("tahun")
    month = cast(func.extract("month", CrimeIncident.incident_date), Integer).label("bulan")
    query = (
        _ranged(incidents(polsek, requested), date_from, date_to)
        .add_columns(CrimeIncident.incident_type, year, month, func.count())
        .group_by(CrimeIncident.incident_type, year, month)
    )

    index = {(year_month[0], year_month[1]): position for position, year_month in enumerate(months)}
    monthly: dict[str, list[int]] = {}
    for incident_type, row_year, row_month, count in session.execute(query).all():
        position = index.get((int(row_year), int(row_month)))
        if position is None:
            continue
        monthly.setdefault(str(incident_type), [0] * len(months))[position] = int(count)

    # Deret terbesar lebih dulu; nama jenis sebagai pemutus agar urutannya dapat direproduksi.
    series: list[dict[str, Any]] = [
        {
            "threat_type": name,
            "incidents": sum(monthly[name]),
            "share_percent": share(sum(monthly[name]), total),
            "monthly": monthly[name],
        }
        for name in sorted(monthly, key=lambda name: (-sum(monthly[name]), name))
    ]

    total_monthly = [
        sum(values[position] for values in monthly.values()) for position in range(len(months))
    ]
    peak_position = (
        max(range(len(total_monthly)), key=lambda position: total_monthly[position])
        if total_monthly
        else None
    )

    return {
        "threat_type": requested,
        "threat_types": available,
        "months": [
            {
                "key": f"{row_year:04d}-{row_month:02d}",
                "label": f"{MONTH_LABELS[row_month]} {row_year}",
                "year": row_year,
                "month": row_month,
                "incidents": total_monthly[position],
                "share_percent": share(total_monthly[position], total),
            }
            for position, (row_year, row_month) in enumerate(months)
        ],
        "series": series,
        "incidents": total,
        "denominator": total,
        "months_counted": len(months),
        "peak_month": (
            None
            if peak_position is None or total == 0
            else {
                "key": f"{months[peak_position][0]:04d}-{months[peak_position][1]:02d}",
                "incidents": total_monthly[peak_position],
            }
        ),
        "mean_per_month": 0.0 if not months else round(total / len(months), 1),
        "mean_basis": (
            f"Rata-rata = {total} kejadian dibagi {len(months)} bulan pada sumbu, termasuk "
            "bulan yang tidak berkejadian. Bukan ambang dan bukan target."
            if months
            else "Tidak ada bulan pada sumbu, sehingga rata-rata tidak dihitung."
        ),
        "peak_basis": (
            "Bulan terbanyak adalah nilai maksimum aritmetika pada sumbu ini, bukan "
            "penanda bahwa bulan itu 'menonjol' — ambang seperti itu belum ditetapkan. "
            "Bila dua bulan berjumlah sama, yang disebut adalah yang lebih awal."
        ),
        "source": _source("crime_incidents", first, last, total, polsek),
        "scope_basis": _scope_basis(polsek),
        "analysis_basis": ANALYSIS_BASIS,
        "related_analysis_basis": RELATED_ANALYSIS_BASIS,
    }


# ---------------------------------------------------------------------------
# Matriks hari x jam
# ---------------------------------------------------------------------------


@router.get("/analytics/time-pattern", summary="Sebaran hari dalam pekan x jam kejadian")
def time_pattern(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("analytics:read"),
    threat_type: str | None = Query(None, description="Batasi ke satu jenis, mis. CURANMOR"),
    date_from: date | None = Query(None, description="Tanggal awal (incident_date)"),
    date_to: date | None = Query(None, description="Tanggal akhir (incident_date)"),
) -> dict[str, Any]:
    """Matriks 7 hari x 24 jam — "jam rawan" dilihat bersama harinya.

    Crime Pattern DNA sudah menyajikan sebaran jam dan sebaran hari **secara terpisah**
    untuk satu jenis. Dua sebaran terpisah tidak dapat menjawab pertanyaan yang justru
    menentukan penjadwalan patroli: apakah puncak jam 20.00 itu merata sepanjang pekan atau
    terkumpul pada Sabtu malam. Perkaliannya yang menjawab, dan itu yang ada di sini.

    Seluruh 168 sel dikirim, termasuk yang bernilai nol, dan seluruhnya memakai penyebut
    yang sama: jumlah kejadian pada seluruh matriks.
    """
    polsek = jurisdiction_filter(current, "analytics:read")
    _validated_range(date_from, date_to)
    available = threat_types(session, polsek)
    requested = _validated_threat_type(available, threat_type)

    first, last, total = _extent(session, polsek, requested, date_from, date_to)

    day = cast(func.extract("isodow", CrimeIncident.incident_date), Integer).label("hari")
    hour = cast(func.extract("hour", CrimeIncident.incident_time), Integer).label("jam")
    query = (
        _ranged(incidents(polsek, requested), date_from, date_to)
        .add_columns(day, hour, func.count())
        .group_by(day, hour)
    )
    counts = {
        (int(row_day), int(row_hour)): int(count)
        for row_day, row_hour, count in session.execute(query).all()
    }

    rows: list[dict[str, Any]] = []
    for index, name in enumerate(DAY_LABELS):
        number = index + 1
        cells = [
            {
                "hour": position,
                "label": f"{position:02d}.00",
                "incidents": counts.get((number, position), 0),
                "share_percent": share(counts.get((number, position), 0), total),
            }
            for position in range(HOURS_PER_DAY)
        ]
        day_total = sum(counts.get((number, position), 0) for position in range(HOURS_PER_DAY))
        rows.append(
            {
                "day": number,
                "label": name,
                "incidents": day_total,
                "share_percent": share(day_total, total),
                "cells": cells,
            }
        )

    hours = [
        {
            "hour": position,
            "label": f"{position:02d}.00",
            "incidents": sum(counts.get((number, position), 0) for number in range(1, 8)),
            "share_percent": share(
                sum(counts.get((number, position), 0) for number in range(1, 8)), total
            ),
        }
        for position in range(HOURS_PER_DAY)
    ]

    peak = max(counts.items(), key=lambda item: (item[1], -item[0][0], -item[0][1]), default=None)
    cell_count = len(DAY_LABELS) * HOURS_PER_DAY

    return {
        "threat_type": requested,
        "threat_types": available,
        "days": rows,
        "hours": hours,
        "incidents": total,
        "denominator": total,
        "cells": cell_count,
        "peak_cell": (
            None
            if peak is None or total == 0
            else {
                "day": peak[0][0],
                "day_label": DAY_LABELS[peak[0][0] - 1],
                "hour": peak[0][1],
                "label": f"{DAY_LABELS[peak[0][0] - 1]} {peak[0][1]:02d}.00",
                "incidents": peak[1],
                "share_percent": share(peak[1], total),
            }
        ),
        "cell_basis": (
            f"Matriks ini memiliki {cell_count} sel (7 hari x 24 jam) yang berbagi "
            f"{total} kejadian; bila kejadian tersebar rata, tiap sel berisi "
            f"{round(total / cell_count, 1)} kejadian. Angka itu pembanding aritmetika, "
            "bukan ambang: tidak ada sel yang ditandai rawan oleh sistem."
        ),
        "time_basis": TIME_BASIS,
        "source": _source("crime_incidents", first, last, total, polsek),
        "scope_basis": _scope_basis(polsek),
        "analysis_basis": ANALYSIS_BASIS,
        "related_analysis_basis": RELATED_ANALYSIS_BASIS,
    }


# ---------------------------------------------------------------------------
# Perbandingan antarwilayah
# ---------------------------------------------------------------------------


@router.get("/analytics/spatial-pattern", summary="Perbandingan antarwilayah per jenis gangguan")
def spatial_pattern(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("analytics:read"),
    date_from: date | None = Query(None, description="Tanggal awal (incident_date)"),
    date_to: date | None = Query(None, description="Tanggal akhir (incident_date)"),
) -> dict[str, Any]:
    """Kejadian per kecamatan per jenis — satu matriks wilayah x jenis.

    Crime Pattern DNA menyajikan sebaran kecamatan untuk **satu** jenis; yang tidak dapat
    dibacanya adalah komposisi antarwilayah: dua kecamatan dengan jumlah total serupa bisa
    memiliki susunan gangguan yang sama sekali berbeda, dan tanggapan yang berbeda pula.

    Perhatikan `rate_basis`: perbandingan ini memakai jumlah mentah, bukan angka per
    penduduk. Pengguna yang dibatasi wilayah hanya akan melihat kecamatannya sendiri —
    keadaan itu dinyatakan lewat `comparison_basis`, bukan disamarkan sebagai perbandingan.
    """
    polsek = jurisdiction_filter(current, "analytics:read")
    _validated_range(date_from, date_to)

    first, last, total = _extent(session, polsek, None, date_from, date_to)

    query = (
        _ranged(incidents(polsek, None), date_from, date_to)
        .add_columns(
            Location.kecamatan,
            Location.polsek,
            CrimeIncident.incident_type,
            func.count(),
        )
        .group_by(Location.kecamatan, Location.polsek, CrimeIncident.incident_type)
    )

    areas: dict[str, dict[str, Any]] = {}
    per_threat: dict[str, int] = {}
    for kecamatan, area_polsek, incident_type, count in session.execute(query).all():
        area = areas.setdefault(
            str(kecamatan),
            {"kecamatan": str(kecamatan), "polsek": area_polsek, "counts": {}},
        )
        area["counts"][str(incident_type)] = int(count)
        per_threat[str(incident_type)] = per_threat.get(str(incident_type), 0) + int(count)

    # Kolom matriks: jenis gangguan urut terbanyak, nama sebagai pemutus.
    columns = sorted(per_threat, key=lambda name: (-per_threat[name], name))

    rows: list[dict[str, Any]] = []
    for area in areas.values():
        counts: dict[str, int] = area["counts"]
        area_total = sum(counts.values())
        rows.append(
            {
                "kecamatan": area["kecamatan"],
                "polsek": area["polsek"],
                "incidents": area_total,
                "share_percent": share(area_total, total),
                "denominator": area_total,
                "by_threat": [
                    {
                        "threat_type": name,
                        "incidents": counts.get(name, 0),
                        "share_of_area_percent": share(counts.get(name, 0), area_total),
                        "share_of_threat_percent": share(
                            counts.get(name, 0), per_threat.get(name, 0)
                        ),
                    }
                    for name in columns
                ],
            }
        )
    rows.sort(key=lambda row: (-int(row["incidents"]), str(row["kecamatan"])))

    return {
        "threat_types": [
            {
                "threat_type": name,
                "incidents": per_threat[name],
                "share_percent": share(per_threat[name], total),
            }
            for name in columns
        ],
        "areas": rows,
        "incidents": total,
        "denominator": total,
        "areas_compared": len(rows),
        "share_basis": (
            "Dua persentase berbeda penyebut pada tiap sel: share_of_area_percent memakai "
            "jumlah kejadian kecamatan itu sendiri (komposisi gangguan di wilayah "
            "tersebut), sedangkan share_of_threat_percent memakai jumlah kejadian jenis itu "
            "di seluruh cakupan (di mana jenis tersebut terkumpul)."
        ),
        "comparison_basis": (
            f"Perbandingan ini mencakup {len(rows)} kecamatan. Cakupan Anda dibatasi ke "
            f"{polsek}, sehingga tidak ada wilayah lain untuk dibandingkan — angka di sini "
            "menggambarkan komposisi gangguan di wilayah Anda sendiri."
            if polsek
            else f"Perbandingan ini mencakup {len(rows)} kecamatan di wilayah Polres."
        ),
        "rate_basis": RATE_BASIS,
        "source": _source("crime_incidents", first, last, total, polsek),
        "scope_basis": _scope_basis(polsek),
        "analysis_basis": ANALYSIS_BASIS,
        "related_analysis_basis": RELATED_ANALYSIS_BASIS,
    }
