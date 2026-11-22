"""Luas kelurahan untuk PAI (config/ranking/kelurahan-area.yaml) — naskah Taskap revisi 7,
Lampiran J bagian M: luas BPS 28 kelurahan dan luas wilayah hukum 144,75 km².

Porsi luas = luas kelurahan pilihan / luas wilayah hukum. Bila ada kelurahan pilihan yang
luasnya belum tercantum, porsi luas — dan dengan itu PAI — TIDAK DIHITUNG; naskah berbuat
sama untuk metode yang daftar pilihannya memuat kelurahan di luar tabel.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from ..seeding.paths import REPO_ROOT
from . import config_cache

AREA_FILE = REPO_ROOT / "config" / "ranking" / "kelurahan-area.yaml"


@lru_cache(maxsize=1)
def _raw() -> dict[str, Any]:
    if not AREA_FILE.exists():
        return {}
    loaded: dict[str, Any] = config_cache.load_yaml(AREA_FILE)
    return loaded


def areas() -> dict[str, float]:
    """Luas per kelurahan (km²); hanya kelurahan yang tercantum pada naskah."""
    return {str(name): float(value) for name, value in (_raw().get("kelurahan") or {}).items()}


def total_km2() -> float | None:
    """Luas wilayah hukum Polres (km²)."""
    value = _raw().get("total_km2")
    return float(value) if value else None


def source() -> str | None:
    value = _raw().get("source")
    return str(value) if value else None


def share(selected: list[str], whole_jurisdiction: bool = True) -> float | None:
    """Porsi luas kelurahan pilihan terhadap luas wilayah hukum.

    `whole_jurisdiction=False` (angka dibatasi ke satu Polsek): pembaginya bukan lagi luas
    wilayah hukum Polres dan luas tiap Polsek tidak ada pada naskah, jadi tidak dihitung.
    """
    known = areas()
    total = total_km2()
    if not whole_jurisdiction or not total or not selected:
        return None
    if any(name not in known for name in selected):
        return None
    return sum(known[name] for name in selected) / total
