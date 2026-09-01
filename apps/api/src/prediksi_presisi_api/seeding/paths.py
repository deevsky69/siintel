"""Lokasi berkas data dan konfigurasi.

Akar repository dicari lewat penanda, bukan dengan menghitung `parents[n]`: menghitung
level akan diam-diam salah begitu berkas dipindahkan satu tingkat — dan itu sudah terjadi
sekali saat modul ini dibuat.
"""

from __future__ import annotations

from pathlib import Path

#: Penanda akar repository, dipilih karena hanya ada di akar.
_ROOT_MARKERS = ("pnpm-workspace.yaml", "CLAUDE.md")


def find_repo_root(start: Path | None = None) -> Path:
    """Menelusuri direktori ke atas sampai menemukan akar repository."""
    current = (start or Path(__file__)).resolve()
    for candidate in (current, *current.parents):
        if all((candidate / marker).exists() for marker in _ROOT_MARKERS):
            return candidate

    message = (
        "akar repository tidak ditemukan: tidak ada direktori induk yang memuat "
        f"{' dan '.join(_ROOT_MARKERS)}"
    )
    raise RuntimeError(message)


REPO_ROOT = find_repo_root()
SAMPLE_DATA_DIR = REPO_ROOT / "data" / "sample"
TAXONOMY_FILE = REPO_ROOT / "config" / "taxonomy" / "mappings.yaml"
RBAC_FILE = REPO_ROOT / "config" / "rbac" / "permissions.yaml"
