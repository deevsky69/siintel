"""Test tabel inti (TASK 011).

Seluruh test berjalan tanpa database hidup:
1. memeriksa definisi model terhadap `docs/02-data-dictionary.md`;
2. memeriksa migration `0002` **tidak menyimpang** dari model, dengan merender SQL
   dalam mode offline lalu membandingkan kolom tiap tabel.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, UniqueConstraint

from prediksi_presisi_api import models
from prediksi_presisi_api.db import Base

API_ROOT = Path(__file__).resolve().parents[1]

CORE_TABLES = {
    "locations",
    "police_units",
    "crime_incidents",
    "intelligence_reports",
    "patrol_activity",
}


def test_core_tables_are_registered() -> None:
    assert set(Base.metadata.tables) >= CORE_TABLES


def test_only_core_tables_exist_so_far() -> None:
    # Tabel publik/analitik/operasional/administrasi menyusul pada TASK 012–015.
    assert set(Base.metadata.tables) == CORE_TABLES


def test_locations_has_natural_keys_and_point_geometry() -> None:
    table = Base.metadata.tables["locations"]

    unique_columns = {
        tuple(constraint.columns.keys())
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("code",) in unique_columns
    assert ("grid_id",) in unique_columns

    geom_type = table.c.geom.type
    assert isinstance(geom_type, Geometry)
    assert geom_type.geometry_type == "POINT"
    assert geom_type.srid == 4326


def test_transaction_tables_reference_locations_with_restrict() -> None:
    for model in (
        models.CrimeIncident,
        models.IntelligenceReport,
        models.PatrolActivity,
    ):
        foreign_keys = list(model.__table__.c.location_id.foreign_keys)

        assert len(foreign_keys) == 1, model.__tablename__
        assert foreign_keys[0].column.table.name == "locations"
        assert foreign_keys[0].ondelete == "RESTRICT"


def test_transaction_tables_do_not_duplicate_area_columns() -> None:
    # docs/02 K-8: kecamatan/kelurahan diperoleh lewat join, tidak diduplikasi.
    duplicated = {"kecamatan", "kelurahan", "polsek", "grid_id"}

    for name in CORE_TABLES - {"locations", "police_units"}:
        columns = set(Base.metadata.tables[name].c.keys())
        assert not (columns & duplicated), f"{name} menduplikasi kolom wilayah"


def test_score_columns_are_range_constrained() -> None:
    checks = {
        constraint.name
        for constraint in Base.metadata.tables["intelligence_reports"].constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_intelligence_reports_confidence_range" in checks
    assert "ck_intelligence_reports_urgency_range" in checks


def test_taxonomy_columns_are_text_not_database_enum() -> None:
    # Taksonomi belum final (U-16): nilai divalidasi di aplikasi, bukan dikunci ENUM database,
    # supaya perubahan daftar nilai tidak memerlukan migration ALTER TYPE.
    columns = [
        models.CrimeIncident.__table__.c.incident_type,
        models.CrimeIncident.__table__.c.modus,
        models.CrimeIncident.__table__.c.target_type,
        models.CrimeIncident.__table__.c.status,
        models.PoliceUnit.__table__.c.function,
    ]

    for column in columns:
        assert column.type.python_type is str
        assert type(column.type).__name__ == "String"


def _render_offline_sql() -> str:
    """Menjalankan `alembic upgrade head --sql` — tidak memerlukan database."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=API_ROOT,
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin",
            "DATABASE_URL": "postgresql+psycopg://u:p@localhost:5432/x",
        },
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _columns_from_sql(sql: str, table: str) -> dict[str, bool]:
    """Nama kolom -> boleh NULL, dibaca dari CREATE TABLE hasil render migration."""
    match = re.search(rf"CREATE TABLE {table} \((.*?)\n\);", sql, re.DOTALL)
    assert match, f"CREATE TABLE {table} tidak ditemukan pada SQL migration"

    columns: dict[str, bool] = {}
    for line in match.group(1).splitlines():
        stripped = line.strip().rstrip(",")
        if not stripped or stripped.startswith(("CONSTRAINT", "PRIMARY KEY", "FOREIGN KEY")):
            continue
        columns[stripped.split()[0]] = "NOT NULL" not in stripped
    return columns


@pytest.mark.parametrize("table", sorted(CORE_TABLES))
def test_migration_matches_model_columns(table: str) -> None:
    """Migration tidak boleh menyimpang dari model: nama kolom dan nullability harus sama."""
    sql = _render_offline_sql()

    from_model = {name: column.nullable for name, column in Base.metadata.tables[table].c.items()}

    assert _columns_from_sql(sql, table) == from_model
