"""API Crime Pattern DNA — profil where–when–how–target–repeat (TASK 094).

Modul ini menjawab satu pertanyaan saja: **untuk satu jenis gangguan, seperti apa sebaran
kejadian yang sudah terjadi** menurut lima dimensi pada docs/01 §5.4 dan Resume Spesifikasi §3:

```text
WHERE   locations.kecamatan, crime_incidents.location_type (kategori TKP)
WHEN    crime_incidents.incident_time (jam), crime_incidents.incident_date (hari)
HOW     crime_incidents.modus
TARGET  crime_incidents.target_type
REPEAT  pengulangan pada grid yang sama untuk jenis yang sama
```

Lima batas yang menentukan bentuk modul ini:

1. **Ini analisis deskriptif, bukan model.** Yang dikembalikan adalah distribusi kejadian
   yang **sudah terjadi**. Tidak ada skor risiko, tidak ada `confidence`, tidak ada
   kalimat yang menyatakan apa yang akan terjadi. Menyebutnya lebih dari itu berarti
   menyajikan hitungan frekuensi sebagai temuan model (CLAUDE.md §27).

2. **Tidak ada ambang "pola signifikan".** Modul ini sengaja **tidak** menandai satu nilai
   pun sebagai menonjol, dominan, atau bermakna: ambang seperti itu belum ditetapkan
   siapa pun (CLAUDE.md §11). Yang dikembalikan hanyalah jumlah dan persentase; pembaca
   yang menilai. Bila kelak pemilik proyek menetapkan aturan penandaan, tempatnya di sini
   dengan `*_basis` yang menyebut dasarnya.

3. **Persentase tidak pernah tampil tanpa penyebutnya.** Setiap distribusi membawa
   `denominator`, dan setiap profil membawa `sample_note` yang menyatakan berapa persen
   poin yang diwakili satu kejadian (100/n). Untuk jenis dengan sedikit kejadian, kalimat
   itu sendiri sudah menyatakan bahwa persentasenya rapuh — tanpa perlu mengarang batas
   "terlalu sedikit".

4. **Jam dan hari dihitung dari kolom waktu setempat.** `incident_time` dan
   `incident_date` menyimpan waktu setempat (WIB), sementara `occurred_at` menyimpan UTC.
   Memakai `occurred_at` akan menggeser "jam rawan" tujuh jam.

5. **Grid muncul lewat dimensi REPEAT, bukan diulang di WHERE.** Sebaran per grid dan
   pengulangan per grid dihitung dari agregasi yang sama; menyajikannya dua kali hanya
   menggandakan baris tanpa menambah informasi. Ringkasan REPEAT menyebut berapa grid
   yang hanya memuat satu kejadian, sehingga gambaran per grid tetap utuh.

Penyaringan cakupan dilakukan **di query** (`Location.polsek`), sama seperti endpoint
daftar: pengguna ber-scope `OWN_JURISDICTION` tidak menerima kejadian wilayah lain, bahkan
tidak dalam jumlah total maupun dalam daftar jenis gangguan yang tersedia.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import Integer, cast, func
from sqlalchemy.orm import Session

from ...models import CrimeIncident, Location
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

# Path mengikuti kontrak `docs/05` §2.5 — sekelompok dengan analitik lain, sejalan
# dengan permission yang dipakainya (`analytics:read`).
router = APIRouter(prefix="/analytics", tags=["pola kejahatan"])

#: Label yang dipakai bila kolom taksonomi kosong. Kejadian tanpa modus/target tetap
#: dihitung — membuangnya diam-diam akan mengubah penyebut tanpa diketahui pembaca.
UNRECORDED_LABEL = "Tidak dicatat"

#: Sebuah grid disebut "berulang" bila memuat lebih dari satu kejadian jenis yang sama
#: sepanjang rentang data. Ini hitungan pengulangan sederhana, bukan analisis near-repeat.
REPEAT_MIN_INCIDENTS = 2

ANALYSIS_BASIS = (
    "Profil ini adalah sebaran kejadian yang SUDAH TERJADI pada tabel crime_incidents — "
    "bukan prediksi, bukan skor risiko, dan tidak memiliki tingkat keyakinan. Tidak ada "
    "nilai yang ditandai 'signifikan': ambang untuk itu belum ditetapkan (CLAUDE.md §11), "
    "sehingga yang disajikan hanya jumlah dan persentase beserta penyebutnya."
)

REPEAT_BASIS = (
    f"Sebuah grid dihitung berulang bila memuat sekurang-kurangnya {REPEAT_MIN_INCIDENTS} "
    "kejadian jenis ini sepanjang rentang data, tanpa memandang jarak waktu antar "
    "kejadian. Ini pengulangan sederhana per grid, BUKAN analisis near-repeat "
    "(pengulangan berdekatan dalam ruang dan waktu) yang disebut docs/01 §5.4 — analisis "
    "itu belum dikerjakan dan tidak diwakili oleh angka di sini."
)


def _bucket(key: str, label: str, count: int, denominator: int) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "incidents": count,
        "share_percent": share(count, denominator),
    }


def _ranked_distribution(
    session: Session,
    polsek: str | None,
    threat_type: str,
    column: Any,
    *,
    dimension_id: str,
    label: str,
    denominator: int,
) -> dict[str, Any]:
    """Distribusi satu kolom kategori, berperingkat dari yang terbanyak.

    Urutan kedua memakai nilai kolomnya sendiri supaya golongan berjumlah sama selalu
    tampil dalam urutan yang sama — hasil yang dapat direproduksi (CLAUDE.md §25).
    """
    query = (
        incidents(polsek, threat_type)
        .add_columns(column, func.count())
        .group_by(column)
        .order_by(func.count().desc(), column)
    )

    buckets = [
        _bucket(
            "" if value is None else str(value),
            UNRECORDED_LABEL if value is None else str(value),
            int(count),
            denominator,
        )
        for value, count in session.execute(query).all()
    ]

    return {
        "id": dimension_id,
        "label": label,
        "ordering": "rank",
        "denominator": denominator,
        "buckets": buckets,
    }


def _hour_distribution(
    session: Session, polsek: str | None, threat_type: str, denominator: int
) -> dict[str, Any]:
    """Sebaran 24 jam, urut jam — termasuk jam tanpa kejadian.

    Diurutkan menurut jam, bukan menurut jumlah: jam rawan hanya terbaca bila jam-jam di
    sekitarnya ikut terlihat. Jam berjumlah nol tetap dikirim sebagai nol karena memang
    nol, bukan karena datanya tidak ada.
    """
    hour = cast(func.extract("hour", CrimeIncident.incident_time), Integer).label("jam")
    query = incidents(polsek, threat_type).add_columns(hour, func.count()).group_by(hour)
    counts = {int(value): int(count) for value, count in session.execute(query).all()}

    return {
        "id": "hour",
        "label": "Jam kejadian",
        "ordering": "natural",
        "denominator": denominator,
        "buckets": [
            _bucket(str(index), f"{index:02d}.00", counts.get(index, 0), denominator)
            for index in range(HOURS_PER_DAY)
        ],
    }


def _day_distribution(
    session: Session, polsek: str | None, threat_type: str, denominator: int
) -> dict[str, Any]:
    """Sebaran hari dalam pekan, urut Senin–Minggu — termasuk hari tanpa kejadian."""
    day = cast(func.extract("isodow", CrimeIncident.incident_date), Integer).label("hari")
    query = incidents(polsek, threat_type).add_columns(day, func.count()).group_by(day)
    counts = {int(value): int(count) for value, count in session.execute(query).all()}

    return {
        "id": "day_of_week",
        "label": "Hari kejadian",
        "ordering": "natural",
        "denominator": denominator,
        "buckets": [
            _bucket(str(index + 1), name, counts.get(index + 1, 0), denominator)
            for index, name in enumerate(DAY_LABELS)
        ],
    }


def _repeat_profile(
    session: Session, polsek: str | None, threat_type: str, denominator: int
) -> dict[str, Any]:
    """Pengulangan per grid: berapa kali, sejak kapan, sampai kapan.

    Rentang tanggal ikut dikembalikan karena tanpa itu "8 kejadian di satu grid" tidak
    dapat dibedakan antara delapan kejadian dalam sepekan dan delapan kejadian dalam tiga
    tahun — dua keadaan yang menuntut tanggapan berbeda.
    """
    query = (
        incidents(polsek, threat_type)
        .add_columns(
            Location.grid_id,
            Location.kecamatan,
            func.count(),
            func.min(CrimeIncident.incident_date),
            func.max(CrimeIncident.incident_date),
        )
        .group_by(Location.grid_id, Location.kecamatan)
        .order_by(func.count().desc(), Location.grid_id)
    )
    rows = session.execute(query).all()

    grids: list[dict[str, Any]] = []
    incidents_in_repeat_grids = 0
    for grid_id, kecamatan, count, first_date, last_date in rows:
        total = int(count)
        if total < REPEAT_MIN_INCIDENTS:
            continue

        incidents_in_repeat_grids += total
        first: date = first_date
        last: date = last_date
        grids.append(
            {
                "grid_id": grid_id,
                "kecamatan": kecamatan,
                "incidents": total,
                "share_percent": share(total, denominator),
                "first_date": first,
                "last_date": last,
                "span_days": (last - first).days,
            }
        )

    return {
        "grids_with_incidents": len(rows),
        "repeat_grids": len(grids),
        "single_incident_grids": len(rows) - len(grids),
        "incidents_in_repeat_grids": incidents_in_repeat_grids,
        "share_percent": share(incidents_in_repeat_grids, denominator),
        "denominator": denominator,
        "grids": grids,
        "basis": REPEAT_BASIS,
    }


def _sample_note(threat_type: str, incidents: int) -> str:
    """Seberapa besar pengaruh satu kejadian terhadap persentase profil ini.

    Bukan penilaian "cukup" atau "tidak cukup" — batas seperti itu tidak ada dasarnya.
    Yang dinyatakan adalah aritmetikanya: pada 464 kejadian satu kejadian bernilai 0,2
    persen poin, sedangkan pada 3 kejadian satu kejadian bernilai 33,3 persen poin, dan
    angka itu sendiri sudah memberi tahu pembaca seberapa rapuh persentasenya.
    """
    if incidents == 0:
        return (
            f"Tidak ada kejadian {threat_type} dalam cakupan Anda, "
            "sehingga tidak ada pola untuk dibaca."
        )

    # Koma sebagai pemisah desimal — kalimat ini dibaca pengguna, bukan diurai mesin.
    points = f"{100 / incidents:.1f}".replace(".", ",")
    return (
        f"Seluruh persentase profil ini dihitung dari {incidents} kejadian {threat_type} "
        f"dalam cakupan Anda; satu kejadian setara {points} persen poin."
    )


def _range(session: Session, polsek: str | None, threat_type: str | None) -> tuple[Any, Any, int]:
    """Rentang tanggal dan jumlah baris yang menghasilkan angka — `source` docs/05 §2.5."""
    query = incidents(polsek, threat_type).add_columns(
        func.min(CrimeIncident.incident_date),
        func.max(CrimeIncident.incident_date),
        func.count(),
    )
    date_from, date_to, total = session.execute(query).one()
    return date_from, date_to, int(total)


def _profile(session: Session, polsek: str | None, threat_type: str) -> dict[str, Any]:
    """Profil lima dimensi satu jenis gangguan."""
    date_from, date_to, incidents = _range(session, polsek, threat_type)

    return {
        "threat_type": threat_type,
        "incidents": incidents,
        "date_from": date_from,
        "date_to": date_to,
        "sample_note": _sample_note(threat_type, incidents),
        "where": [
            _ranked_distribution(
                session,
                polsek,
                threat_type,
                Location.kecamatan,
                dimension_id="kecamatan",
                label="Kecamatan",
                denominator=incidents,
            ),
            _ranked_distribution(
                session,
                polsek,
                threat_type,
                CrimeIncident.location_type,
                dimension_id="location_type",
                label="Kategori TKP",
                denominator=incidents,
            ),
        ],
        "when": [
            _hour_distribution(session, polsek, threat_type, incidents),
            _day_distribution(session, polsek, threat_type, incidents),
        ],
        "how": [
            _ranked_distribution(
                session,
                polsek,
                threat_type,
                CrimeIncident.modus,
                dimension_id="modus",
                label="Modus",
                denominator=incidents,
            )
        ],
        "target": [
            _ranked_distribution(
                session,
                polsek,
                threat_type,
                CrimeIncident.target_type,
                dimension_id="target_type",
                label="Sasaran",
                denominator=incidents,
            )
        ],
        "repeat": _repeat_profile(session, polsek, threat_type, incidents),
        "time_basis": TIME_BASIS,
    }


@router.get(
    "/crime-pattern-dna",
    summary="Crime Pattern DNA: where-when-how-target-repeat per jenis",
)
def crime_pattern_dna(
    session: Session = Depends(get_db),
    current: CurrentUser = require_permission("analytics:read"),
    threat_type: str | None = Query(
        None, description="Jenis gangguan, mis. CURANMOR. Kosongkan untuk daftar jenis saja."
    ),
) -> dict[str, Any]:
    """Sebaran kejadian historis satu jenis gangguan menurut lima dimensi.

    Tanpa `threat_type`, yang dikembalikan hanya daftar jenis beserta jumlahnya — layar
    pemilih tidak perlu menarik seluruh profil untuk menampilkan pilihannya.

    Jenis yang tidak ada di dalam cakupan pengguna dijawab **400** beserta daftar jenis
    yang tersedia, bukan profil kosong: profil kosong terbaca seolah jenis itu ada tetapi
    tidak berkejadian, padahal yang terjadi adalah nama yang tidak dikenal.
    """
    polsek = jurisdiction_filter(current, "analytics:read")
    available = threat_types(session, polsek)

    requested: str | None = None
    if threat_type is not None:
        requested = threat_type.strip().upper()
        known = {row["threat_type"] for row in available}
        if len(requested) > MAX_THREAT_TYPE_LENGTH or requested not in known:
            raise ApiError(
                status.HTTP_400_BAD_REQUEST,
                "Jenis gangguan tidak dikenal pada data yang dapat Anda lihat.",
                details=[
                    {"field": "threat_type", "issue": f"harus salah satu dari {sorted(known)}"}
                ],
            )

    date_from, date_to, total = _range(session, polsek, None)

    return {
        "threat_types": available,
        "threat_type": requested,
        "profile": None if requested is None else _profile(session, polsek, requested),
        "source": {
            "table": "crime_incidents",
            "date_from": date_from,
            "date_to": date_to,
            "incidents": total,
            "scope": polsek,
        },
        "scope_basis": (
            f"Seluruh angka dihitung hanya dari kejadian di wilayah {polsek}."
            if polsek
            else "Seluruh angka dihitung dari kejadian di seluruh wilayah Polres."
        ),
        "analysis_basis": ANALYSIS_BASIS,
    }
