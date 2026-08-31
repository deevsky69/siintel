"""Konfigurasi runtime Alembic (TASK 010).

URL database selalu berasal dari environment (`DATABASE_URL`), tidak pernah dari alembic.ini,
supaya tidak ada kredensial yang masuk ke repository (CLAUDE.md §28).
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from prediksi_presisi_api.config import get_settings
from prediksi_presisi_api.db import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model belum ada — entitas dibuat mulai TASK 011.
target_metadata = Base.metadata


def _database_url() -> str:
    settings = get_settings()
    if not settings.database_url:
        message = (
            "DATABASE_URL belum diisi. Salin .env.example menjadi .env "
            "lalu jalankan database dengan: pnpm db:up"
        )
        raise RuntimeError(message)
    return settings.database_url


def run_migrations_offline() -> None:
    """Menghasilkan SQL tanpa terhubung ke database."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Menjalankan migration terhadap database yang hidup."""
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _database_url()

    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
