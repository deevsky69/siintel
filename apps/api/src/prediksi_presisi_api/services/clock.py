"""Waktu acuan aplikasi (keputusan SDL-16).

Dataset dummy berhenti pada 31 Desember 2025, sedangkan demo dijalankan jauh setelah itu.
Tanpa waktu acuan, seluruh panel "24 jam terakhir" dan "peringatan aktif" akan kosong saat
paparan — dan panel kosong sulit dibedakan dari sistem yang rusak.

Tanggal historis **tidak digeser**: menggesernya akan merusak pembagian data latih/validasi
2023–2024 / Jan–Sep 2025 / Okt–Des 2025 pada `docs/01` §8. Yang digeser adalah "sekarang".

`DEMO_REFERENCE_TIME` kosong berarti memakai waktu sebenarnya.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from ..config import get_settings

JAKARTA = ZoneInfo("Asia/Jakarta")


def reference_now() -> datetime:
    """Waktu yang dianggap 'sekarang' oleh aplikasi."""
    setting = get_settings().demo_reference_time
    if not setting:
        return datetime.now(UTC)

    parsed = datetime.fromisoformat(setting)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=JAKARTA)


def is_demo_clock() -> bool:
    """Benar bila aplikasi memakai waktu acuan, bukan waktu sebenarnya.

    Dipakai antarmuka untuk menyatakannya terbuka: pembaca layar harus tahu bahwa
    "24 jam terakhir" dihitung terhadap waktu acuan dataset.
    """
    return bool(get_settings().demo_reference_time)


def window(hours: int) -> tuple[datetime, datetime]:
    """Rentang `hours` jam ke belakang dari waktu acuan."""
    end = reference_now()
    return end - timedelta(hours=hours), end


def forward_window(hours: int) -> tuple[datetime, datetime]:
    """Rentang `hours` jam ke depan dari waktu acuan."""
    start = reference_now()
    return start, start + timedelta(hours=hours)


def to_jakarta(moment: datetime) -> datetime:
    """Mengubah waktu tersimpan (UTC) menjadi WIB untuk tampilan."""
    return moment.astimezone(JAKARTA)
