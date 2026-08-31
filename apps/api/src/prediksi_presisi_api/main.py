"""Skeleton aplikasi FastAPI (TASK 001).

Belum ada business logic, database, autentikasi, maupun endpoint domain.
Konfigurasi, error handling, validation, logging, dan health endpoint
dibuat pada TASK 030 — API Foundation.
"""

from fastapi import FastAPI

from . import __version__

app = FastAPI(
    title="PREDIKSI PRESISI API",
    version=__version__,
    description="Backend API PREDIKSI PRESISI. Skeleton — belum ada fitur bisnis.",
)


@app.get("/")
def root() -> dict[str, str]:
    """Menandakan aplikasi berjalan. Bukan health check (lihat TASK 030)."""
    return {"name": "prediksi-presisi-api", "version": __version__, "state": "skeleton"}
