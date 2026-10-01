"""Bahan agregasi yang dipakai bersama Crime Pattern DNA dan Crime Analytics.

Ketujuh nama di bawah semula tinggal di `routers/patterns.py` dengan awalan garis bawah,
lalu diimpor `routers/analytics.py`. Itu berjalan dan teruji, tetapi menyesatkan:
awalan garis bawah menyatakan "milik modul ini saja", padahal modul lain bergantung
padanya. Mengganti nama sebuah pembantu di `patterns.py` akan memutus `analytics.py`
tanpa satu pun tanda peringatan.

Dipindahkan ke sini supaya ketergantungannya menjadi kontrak yang terlihat, bukan
kebetulan. Keduanya kini mengimpor dari satu tempat, dan itu juga yang menjamin kedua
layar menjawab angka yang sama untuk pertanyaan yang sama —
`test_analytics_agrees_with_crime_pattern_dna_on_the_same_numbers` menjaganya.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ..models import CrimeIncident, Location

#: Panjang maksimal nilai `threat_type` yang diterima. Nilai yang lebih panjang ditolak
#: sebagai kesalahan masukan sebelum menyentuh database (CLAUDE.md §21).
MAX_THREAT_TYPE_LENGTH = 50

#: Nama hari untuk `extract(isodow)` PostgreSQL: 1 = Senin … 7 = Minggu.
DAY_LABELS = ("Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu")

HOURS_PER_DAY = 24

#: Keputusan pemilik proyek 30 September 2026: PREDIKSI memakai jendela 6 jam, ANALITIK
#: menampilkan jam dalam BLOK 3 JAM. Sebaran per jam tunggal pada data asli terlalu tipis
#: — 22% kejadian tanpa jam, dan satu jam tunggal mudah berpindah karena kebetulan —
#: sementara blok 6 jam terlalu kasar untuk membaca jam rawan. Tiga jam adalah satuan
#: yang sama dengan jendela patroli pada rekomendasi layar Pimpinan.
HOUR_BLOCK_HOURS = 3
HOUR_BLOCK_STARTS = tuple(range(0, HOURS_PER_DAY, HOUR_BLOCK_HOURS))

HOUR_BLOCK_BASIS = (
    f"Jam disajikan dalam blok {HOUR_BLOCK_HOURS} jam (keputusan pemilik proyek 30 September "
    "2026). Kejadian yang jamnya tidak tercatat pada Laporan Polisi tidak membentuk pola jam "
    "dan dihitung terpisah sebagai unknown_time; pada data Pusiknas jam yang tercatat dapat "
    "berupa waktu kejadian diketahui, bukan waktu kejadian berlangsung — terutama Curat."
)


def hour_block_of(hour: int) -> int:
    """Awal blok yang memuat sebuah jam: 14 -> 12."""
    return (hour // HOUR_BLOCK_HOURS) * HOUR_BLOCK_HOURS


def hour_block_label(start: int) -> str:
    """Label blok untuk layar: 12 -> 12.00-15.00, 21 -> 21.00-24.00."""
    end = start + HOUR_BLOCK_HOURS
    return f"{start:02d}.00-{end:02d}.00"


TIME_BASIS = (
    "Jam diambil dari kolom incident_time dan hari dari incident_date — keduanya waktu "
    "setempat (WIB). Kolom occurred_at menyimpan UTC dan tidak dipakai di sini karena "
    "akan menggeser jam rawan sebesar tujuh jam."
)


def scoped(query: Select[Any], polsek: str | None) -> Select[Any]:
    """Membatasi query pada wilayah pengguna — di query, bukan setelah data terambil."""
    return query if polsek is None else query.where(Location.polsek == polsek)


def incidents(polsek: str | None, threat_type: str | None = None) -> Select[Any]:
    """Kerangka query kejadian yang sudah tersaring cakupan (dan jenis, bila diminta)."""
    query = scoped(
        select()
        .select_from(CrimeIncident)
        .join(Location, Location.location_id == CrimeIncident.location_id),
        polsek,
    )
    return query if threat_type is None else query.where(CrimeIncident.incident_type == threat_type)


def share(count: int, denominator: int) -> float:
    """Persentase satu golongan terhadap penyebutnya, satu angka di belakang koma."""
    return 0.0 if denominator == 0 else round(100 * count / denominator, 1)


#: Label sumber data untuk layar, menurut kode `crime_incidents.data_source`. Kode yang
#: tidak terdaftar ditampilkan apa adanya — bukan disembunyikan.
DATA_SOURCE_LABELS: dict[str, str] = {
    "PUSIKNAS-2026-09-29": "Pusiknas, posisi 29 September 2026",
    "PUSIKNAS-2026-09-29/TANPA-TANGGAL-KEJADIAN": (
        "Pusiknas, posisi 29 September 2026 (tanggal kejadian diisi tanggal lapor)"
    ),
}


def data_sources(session: Session, polsek: str | None) -> list[dict[str, Any]]:
    """Asal data kejadian di dalam cakupan pengguna, beserta jumlah barisnya.

    Sebelum 1 Oktober 2026 seluruh kejadian sintetis dan kolom ini kosong; layar lalu
    menulis "data dummy" sebagai teks tetap. Sejak data asli, asal data dibaca dari
    barisnya sendiri supaya layar dan basis data tidak pernah bercerita berbeda.
    """
    query = (
        incidents(polsek)
        .add_columns(CrimeIncident.data_source, func.count())
        .group_by(CrimeIncident.data_source)
        .order_by(func.count().desc())
    )
    return [
        {
            "code": source,
            "label": (
                DATA_SOURCE_LABELS.get(str(source), str(source))
                if source is not None
                else "tanpa keterangan sumber"
            ),
            "incidents": int(count),
        }
        for source, count in session.execute(query).all()
    ]


def threat_types(session: Session, polsek: str | None) -> list[dict[str, Any]]:
    """Jenis gangguan yang ada di dalam cakupan pengguna, beserta jumlahnya."""
    query = (
        incidents(polsek)
        .add_columns(CrimeIncident.incident_type, func.count())
        .group_by(CrimeIncident.incident_type)
        .order_by(func.count().desc(), CrimeIncident.incident_type)
    )
    return [
        {"threat_type": incident_type, "incidents": int(count)}
        for incident_type, count in session.execute(query).all()
    ]
