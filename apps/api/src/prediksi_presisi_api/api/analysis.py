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
