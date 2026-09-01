"""Pembacaan berkas CSV pada `data/sample/`.

Berkas sumber **tidak pernah disunting** oleh proses seed. Bila isinya melanggar
integritas, seed berhenti dan melaporkan barisnya (docs/08 PHASE 3).
"""

from __future__ import annotations

import csv
from collections.abc import Iterator
from datetime import UTC, date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from .errors import SeedError
from .paths import SAMPLE_DATA_DIR

#: Dataset dummy dicatat dalam waktu lokal Jakarta tanpa offset (docs/02 K-3).
SOURCE_TIMEZONE = ZoneInfo("Asia/Jakarta")

_DATETIME_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M")


def read_rows(name: str, directory: Path | None = None) -> list[dict[str, str]]:
    """Membaca satu berkas CSV menjadi daftar baris."""
    source = (directory or SAMPLE_DATA_DIR) / name
    if not source.exists():
        message = f"berkas data dummy tidak ditemukan: {source}"
        raise SeedError(message)

    with source.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def iter_rows(name: str, directory: Path | None = None) -> Iterator[dict[str, str]]:
    """Versi iterator dari `read_rows`."""
    yield from read_rows(name, directory)


def text(row: dict[str, str], field: str) -> str | None:
    """Nilai teks; string kosong menjadi `None`."""
    value = (row.get(field) or "").strip()
    return value or None


def required_text(row: dict[str, str], field: str, where: str) -> str:
    value = text(row, field)
    if value is None:
        message = f"{where}: kolom wajib '{field}' kosong"
        raise SeedError(message)
    return value


def integer(row: dict[str, str], field: str) -> int | None:
    value = text(row, field)
    return None if value is None else int(value)


def parse_date(value: str, where: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        message = f"{where}: tanggal tidak valid '{value}'"
        raise SeedError(message) from exc


def parse_time(value: str, where: str) -> time:
    raw = value.strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            continue
    message = f"{where}: jam tidak valid '{value}'"
    raise SeedError(message)


def parse_datetime(value: str, where: str) -> datetime:
    """Menerima ISO ber-offset, format `T`, maupun spasi; hasilnya selalu UTC (docs/02 K-3)."""
    raw = value.strip()

    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        pass
    else:
        # Nilai tanpa offset dianggap waktu lokal Jakarta.
        aware = parsed if parsed.tzinfo else parsed.replace(tzinfo=SOURCE_TIMEZONE)
        return aware.astimezone(UTC)

    for fmt in _DATETIME_FORMATS:
        try:
            naive = datetime.strptime(raw, fmt)
        except ValueError:
            continue
        return naive.replace(tzinfo=SOURCE_TIMEZONE).astimezone(UTC)

    message = f"{where}: waktu tidak valid '{value}'"
    raise SeedError(message)


def combine(day: date, moment: time) -> datetime:
    """Menggabungkan tanggal dan jam lokal menjadi satu waktu UTC."""
    return datetime.combine(day, moment, tzinfo=SOURCE_TIMEZONE).astimezone(UTC)
