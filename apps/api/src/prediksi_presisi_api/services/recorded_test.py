"""Rekaman pilihan kelurahan pada uji prediksi naskah (config/ranking/uji-naskah.yaml).

Naskah Taskap revisi 7, Lampiran J bagian H–J mencetak enam kelurahan pilihan model untuk
tiap bulan uji, dalam urutan peringkat. Uji historis aplikasi memakai rekaman itu untuk baris
model, supaya yang dinilai adalah pilihan yang sama dengan naskah. Yang direkam hanya NAMA
kelurahan; kejadian tercakup, cakupan, porsi luas, dan PAI tetap dihitung dari data.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from ..seeding.paths import REPO_ROOT
from . import config_cache

FILE = REPO_ROOT / "config" / "ranking" / "uji-naskah.yaml"

#: Jenis rekaman: uji bulanan (informasi diperbarui tiap bulan) dan uji tetap.
MONTHLY = "monthly"
FIXED = "fixed"


@lru_cache(maxsize=1)
def _raw() -> dict[str, Any]:
    if not FILE.exists():
        return {}
    loaded: dict[str, Any] = config_cache.load_yaml(FILE)
    return loaded


def source() -> str | None:
    value = _raw().get("source")
    return str(value) if value else None


def selection(kind: str, month: str, scope: str, top_n: int) -> list[str] | None:
    """`top_n` kelurahan teratas menurut rekaman naskah untuk bulan itu (YYYY-MM); `None`
    bila bulan itu tidak direkam, cakupannya lain, atau rekamannya lebih pendek dari `top_n`."""
    raw = _raw()
    if not raw or str(raw.get("scope")) != scope:
        return None
    names = (raw.get(kind) or {}).get(month)
    if not names or len(names) < top_n:
        return None
    return [str(name) for name in names[:top_n]]
