"""Kesalahan saat memuat data dummy."""

from __future__ import annotations


class SeedError(RuntimeError):
    """Data dummy melanggar aturan integritas dan tidak boleh dimuat.

    Sengaja menghentikan proses: mengoreksi data secara diam-diam akan menyembunyikan
    masalah yang justru harus terlihat (docs/08 PHASE 3).
    """
