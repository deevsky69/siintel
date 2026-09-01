"""Konfigurasi aplikasi (TASK 002).

Seluruh nilai dibaca dari environment — tidak ada nilai rahasia maupun URL peta
yang di-hardcode (CLAUDE.md §28, keputusan B-1).

`database_url` di sini hanya **placeholder**: koneksi, session, dan migration
dibuat pada TASK 010.
"""

from __future__ import annotations

import logging
import secrets
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

    # ---- Autentikasi (SDL-06) ----
    jwt_secret: str = ""
    jwt_access_token_ttl_minutes: int = 15
    jwt_refresh_token_ttl_days: int = 7

    # Waktu acuan untuk dataset demo (SDL-16). Kosong = pakai waktu nyata.
    demo_reference_time: str | None = None

    app_timezone: str = "Asia/Jakarta"

    @property
    def cors_origins(self) -> list[str]:
        """Daftar origin CORS yang diizinkan."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


#: Panjang minimum JWT_SECRET. HMAC-SHA256 dengan kunci lebih pendek dari 32 byte
#: melemahkan tanda tangan token (RFC 7518 §3.2).
MINIMUM_SECRET_BYTES = 32


def _ephemeral_secret() -> str:
    """Secret sekali pakai untuk pengembangan.

    Sengaja berubah setiap kali proses dijalankan ulang: token lama menjadi tidak
    berlaku, dan tidak ada nilai default yang diam-diam terbawa ke produksi.
    """
    return secrets.token_urlsafe(48)


@lru_cache
def get_settings() -> Settings:
    """Settings tunggal per proses."""
    settings = Settings()

    if not settings.jwt_secret:
        if settings.app_env == "production":
            message = (
                "JWT_SECRET wajib diisi pada lingkungan produksi. "
                "Buat nilai acak dengan secrets.token_urlsafe(48)."
            )
            raise RuntimeError(message)

        logging.getLogger("prediksi_presisi").warning(
            "JWT_SECRET kosong; memakai secret sementara. Seluruh sesi akan berakhir "
            "setiap aplikasi dijalankan ulang. Isi JWT_SECRET pada .env agar sesi bertahan."
        )
        settings = settings.model_copy(update={"jwt_secret": _ephemeral_secret()})

    elif len(settings.jwt_secret.encode()) < MINIMUM_SECRET_BYTES:
        message = (
            f"JWT_SECRET terlalu pendek ({len(settings.jwt_secret.encode())} byte). "
            f"Minimal {MINIMUM_SECRET_BYTES} byte agar tanda tangan token tidak lemah "
            "(RFC 7518 §3.2)."
        )
        raise RuntimeError(message)

    return settings
