"""Koneksi database (TASK 010).

Menyediakan engine, session factory, dan base class model.
Belum ada tabel — entitas dibuat mulai TASK 011 mengikuti `docs/02-data-dictionary.md`.

Engine dibuat **malas** (lazy) supaya mengimpor modul ini tidak membuka koneksi;
dengan begitu test dan proses build tidak memerlukan database yang hidup.
"""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    """Base class seluruh model ORM."""


class DatabaseNotConfiguredError(RuntimeError):
    """DATABASE_URL belum diisi."""

    def __init__(self) -> None:
        super().__init__(
            "DATABASE_URL belum diisi. Salin .env.example menjadi .env, "
            "lalu jalankan database lewat: pnpm db:up"
        )


@lru_cache
def get_engine() -> Engine:
    """Engine tunggal per proses."""
    settings = get_settings()
    if not settings.database_url:
        raise DatabaseNotConfiguredError
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Session factory tunggal per proses."""
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """Dependency FastAPI: satu session per permintaan."""
    with get_session_factory()() as session:
        yield session
