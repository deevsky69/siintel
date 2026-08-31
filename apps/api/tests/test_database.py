"""Test lapisan database dan sistem migration (TASK 010).

Seluruh test di sini berjalan **tanpa** database hidup: yang diuji adalah konfigurasi,
penanganan kesalahan, dan integritas rangkaian migration.
Test yang memerlukan koneksi nyata dibuat bersama tabel pertamanya (TASK 011).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from prediksi_presisi_api import db
from prediksi_presisi_api.config import Settings
from prediksi_presisi_api.db import Base, DatabaseNotConfiguredError

API_ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = API_ROOT.parent.parent / "database" / "migrations"


def _alembic_config() -> Config:
    config = Config(str(API_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    return config


def test_engine_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db, "get_settings", lambda: Settings(database_url=""))
    db.get_engine.cache_clear()

    with pytest.raises(DatabaseNotConfiguredError):
        db.get_engine()

    db.get_engine.cache_clear()


def test_engine_is_built_from_settings_without_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "postgresql+psycopg://user:pass@localhost:5432/example"
    monkeypatch.setattr(db, "get_settings", lambda: Settings(database_url=url))
    db.get_engine.cache_clear()

    engine = db.get_engine()

    assert engine.dialect.name == "postgresql"
    assert engine.url.database == "example"

    db.get_engine.cache_clear()


def test_no_tables_defined_yet() -> None:
    # Entitas dibuat mulai TASK 011; baseline hanya mengaktifkan ekstensi.
    assert Base.metadata.tables == {}


def test_migrations_have_single_head() -> None:
    script = ScriptDirectory.from_config(_alembic_config())

    heads = script.get_heads()

    assert len(heads) == 1, f"rangkaian migration bercabang: {heads}"


def test_baseline_migration_enables_postgis_and_pgcrypto() -> None:
    script = ScriptDirectory.from_config(_alembic_config())
    base_revision = script.get_revision("0001")

    assert base_revision.down_revision is None

    source = Path(str(base_revision.path)).read_text(encoding="utf-8")
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in source
    assert "CREATE EXTENSION IF NOT EXISTS pgcrypto" in source
