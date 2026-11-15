"""Pembacaan berkas konfigurasi YAML dengan cache berkunci waktu ubah berkas.

Audit 15 November 2026: pemuat aturan (bobot risiko, ambang, aturan patroli, fungsi
rekomendasi, taksonomi, imbauan) membaca dan mem-parse ulang YAML pada SETIAP permintaan —
termasuk di `/notifications` yang dipanggil setiap halaman. Parse YAML murni-Python untuk
berkas belasan KB memakan milidetik yang berulang ribuan kali.

Cache ini aman untuk pengembangan dan operasi: kuncinya `(path, st_mtime_ns)`, sehingga
berkas yang disunting (lalu API dimulai ulang, atau bahkan tanpa dimulai ulang) langsung
terbaca ulang. Hasil dikembalikan sebagai salinan dalam agar pemanggil yang mengubah dict
tidak meracuni pemanggil berikutnya.
"""

from __future__ import annotations

import copy
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@lru_cache(maxsize=64)
def _parse(path: str, mtime_ns: int) -> Any:
    del mtime_ns  # hanya bagian dari kunci cache
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_yaml(path: Path) -> Any:
    """Isi YAML `path` (dict/list/None), di-parse sekali per versi berkas."""
    return copy.deepcopy(_parse(str(path), path.stat().st_mtime_ns))
