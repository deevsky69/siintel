"""Skeleton aplikasi FastAPI (TASK 001, dilengkapi konfigurasi pada TASK 002).

Belum ada business logic, database, autentikasi, maupun endpoint domain.
Health endpoint, error handling, validation, dan logging dibuat pada TASK 030 — API Foundation.
"""

from __future__ import annotations

from fastapi import FastAPI

from . import __version__
from .config import get_settings

app = FastAPI(
    title="PREDIKSI PRESISI API",
    version=__version__,
    description="Backend API PREDIKSI PRESISI. Skeleton — belum ada fitur bisnis.",
)


@app.get("/")
def root() -> dict[str, str]:
    """Menandakan aplikasi berjalan. Bukan health check (lihat TASK 030)."""
    settings = get_settings()
    return {
        "name": "prediksi-presisi-api",
        "version": __version__,
        "state": "skeleton",
        "env": settings.app_env,
    }
