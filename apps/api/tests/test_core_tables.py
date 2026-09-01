"""Test tabel inti (TASK 011): definisi model terhadap `docs/02-data-dictionary.md`.

Pemeriksaan bahwa migration tidak menyimpang dari model ada di `test_migration_drift.py`
dan berlaku untuk seluruh tabel, bukan hanya tabel inti.
"""

from __future__ import annotations

from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, UniqueConstraint

from prediksi_presisi_api import models
from prediksi_presisi_api.db import Base

CORE_TABLES = {
    "locations",
    "police_units",
    "crime_incidents",
    "intelligence_reports",
    "patrol_activity",
}


def test_core_tables_are_registered() -> None:
    assert set(Base.metadata.tables) >= CORE_TABLES


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
