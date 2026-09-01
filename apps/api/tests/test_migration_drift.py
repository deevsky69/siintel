"""Menjaga migration tidak menyimpang dari model, tanpa memerlukan database.

Alembic merender seluruh SQL dalam mode offline, lalu hasilnya dibandingkan dengan
`Base.metadata`: nama kolom, nullability, nama constraint, dan nama index.

Cakupan constraint/index ditambahkan setelah sebuah CHECK sempat ditulis di migration
tetapi tidak di model — versi test yang hanya membandingkan kolom tidak menangkapnya.
"""

from __future__ import annotations

import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import pytest

from prediksi_presisi_api.db import Base

API_ROOT = Path(__file__).resolve().parents[1]
ALL_TABLES = sorted(Base.metadata.tables)

#: Daftar tabel yang sudah dibuat, diperbarui setiap kelompok tabel baru selesai.
#: Berfungsi sebagai pengingat: menambah model tanpa memperbarui daftar ini akan gagal.
EXPECTED_TABLES = {
    # TASK 011 — inti
    "locations",
    "police_units",
    "crime_incidents",
    "intelligence_reports",
    "patrol_activity",
    # TASK 012 — publik
    "citizen_reports",
    "public_alerts",
    "community_feedback",
    # TASK 015 — administrasi
    "roles",
    "users",
    "permissions",
    "role_permissions",
    "audit_logs",
    # TASK 013 — intelijen
    "risk_scores",
    "predictions",
    "early_warnings",
    "recommendations",
}


def test_expected_tables_so_far() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


@lru_cache
def _offline_sql() -> str:
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


def _create_table_body(table: str) -> str:
    match = re.search(rf"CREATE TABLE {table} \((.*?)\n\);", _offline_sql(), re.DOTALL)
    assert match, f"CREATE TABLE {table} tidak ditemukan pada SQL migration"
    return match.group(1)


def _columns_from_sql(table: str) -> dict[str, bool]:
    """Nama kolom -> boleh NULL."""
    columns: dict[str, bool] = {}
    for line in _create_table_body(table).splitlines():
        stripped = line.strip().rstrip(",")
        if not stripped or stripped.startswith(("CONSTRAINT", "PRIMARY KEY", "FOREIGN KEY")):
            continue
        columns[stripped.split()[0]] = "NOT NULL" not in stripped
    return columns


def _constraints_from_sql(table: str) -> set[str]:
    """Constraint dari CREATE TABLE **dan** dari ALTER TABLE ... ADD CONSTRAINT.

    Constraint yang dipasang belakangan (mis. FK yang menunggu tabel acuannya dibuat)
    hanya muncul sebagai ALTER TABLE, sehingga keduanya perlu dibaca.
    """
    inline = set(re.findall(r"CONSTRAINT (\w+)", _create_table_body(table)))
    altered = set(
        re.findall(
            rf"ALTER TABLE {table} ADD CONSTRAINT (\w+)",
            _offline_sql(),
        )
    )
    return inline | altered


def _indexes_from_sql(table: str) -> set[str]:
    pattern = rf"CREATE INDEX (\w+) ON {table} "
    return set(re.findall(pattern, _offline_sql()))


@pytest.mark.parametrize("table", ALL_TABLES)
def test_columns_and_nullability_match(table: str) -> None:
    from_model = {name: column.nullable for name, column in Base.metadata.tables[table].c.items()}

    assert _columns_from_sql(table) == from_model


@pytest.mark.parametrize("table", ALL_TABLES)
def test_constraint_names_match(table: str) -> None:
    from_model = {
        constraint.name
        for constraint in Base.metadata.tables[table].constraints
        if constraint.name is not None
    }

    assert _constraints_from_sql(table) == from_model


@pytest.mark.parametrize("table", ALL_TABLES)
def test_index_names_match(table: str) -> None:
    from_model = {index.name for index in Base.metadata.tables[table].indexes}

    assert _indexes_from_sql(table) == from_model
