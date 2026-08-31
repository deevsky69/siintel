"""Konfigurasi aplikasi (TASK 002).

Seluruh nilai dibaca dari environment — tidak ada nilai rahasia maupun URL peta
yang di-hardcode (CLAUDE.md §28, keputusan B-1).

`database_url` di sini hanya **placeholder**: koneksi, session, dan migration
dibuat pada TASK 010.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[4]
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    """Konfigurasi yang dibaca dari environment atau berkas .env di root repository."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "info"
    api_port: int = 8000

    # Placeholder — belum ada koneksi database (TASK 010).
    database_url: str = ""

    cors_allowed_origins: str = "http://localhost:3000"

    # Waktu acuan untuk dataset demo (SDL-16). Kosong = pakai waktu nyata.
    demo_reference_time: str | None = None

    app_timezone: str = "Asia/Jakarta"

    @property
    def cors_origins(self) -> list[str]:
        """Daftar origin CORS yang diizinkan."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Settings tunggal per proses."""
    return Settings()
