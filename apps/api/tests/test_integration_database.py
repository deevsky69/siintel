"""Integration test terhadap PostgreSQL + PostGIS sungguhan.

Dilewati otomatis bila `DATABASE_URL` tidak diisi, sehingga `pytest` tetap hijau
di mesin tanpa database. Di CI, service PostGIS disediakan sehingga test ini benar-benar jalan.

Tujuannya menutup celah yang ditemukan pada TASK 010–011: migration sempat hanya
diverifikasi lewat render SQL, tanpa pernah menyentuh database nyata.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import DatabaseError

DATABASE_URL = os.environ.get("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tidak diisi — jalankan `pnpm db:up` lalu ulangi",
)

CORE_TABLES = {
    "locations",
    "police_units",
    "crime_incidents",
    "intelligence_reports",
    "patrol_activity",
}

_SAMPLE_LOCATION = text("""
    INSERT INTO locations
        (code, grid_id, polsek, kecamatan, kelurahan, grid_size_m, latitude, longitude, geom)
    VALUES
        ('LOC-IT', 'JKS-IT', 'Polsek Tebet', 'Tebet', 'Tebet Timur', 500, -6.230653, 106.855133,
         ST_SetSRID(ST_MakePoint(106.855133, -6.230653), 4326))
    RETURNING location_id
""")


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    created = create_engine(DATABASE_URL, future=True)
    yield created
    created.dispose()


def test_migrations_are_applied(engine: Engine) -> None:
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    assert revision == "0002", "database belum di-migrate: jalankan `pnpm db:migrate`"


def test_postgis_and_pgcrypto_are_installed(engine: Engine) -> None:
    with engine.connect() as connection:
        extensions = set(
            connection.scalars(text("SELECT extname FROM pg_extension")).all(),
        )

    assert {"postgis", "pgcrypto"} <= extensions


def test_core_tables_exist(engine: Engine) -> None:
    with engine.connect() as connection:
        tables = set(
            connection.scalars(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            ).all()
        )

    assert tables >= CORE_TABLES


def test_geometry_column_is_point_4326(engine: Engine) -> None:
    with engine.connect() as connection:
        row = connection.execute(
            text("""
                SELECT type, srid FROM geometry_columns
                WHERE f_table_name = 'locations' AND f_geometry_column = 'geom'
            """)
        ).one()

    assert row.type == "POINT"
    assert row.srid == 4326


def test_uuid_default_and_spatial_query(engine: Engine) -> None:
    with engine.begin() as connection:
        location_id = connection.execute(_SAMPLE_LOCATION).scalar_one()
        assert location_id is not None, "gen_random_uuid() tidak menghasilkan primary key"

        distance = connection.execute(
            text("""
                SELECT round(ST_Distance(
                    geom::geography,
                    ST_SetSRID(ST_MakePoint(106.8552, -6.2307), 4326)::geography
                )::numeric, 1)
                FROM locations WHERE code = 'LOC-IT'
            """)
        ).scalar_one()
        assert distance < 100

        connection.rollback()


def test_foreign_key_restrict_is_enforced(engine: Engine) -> None:
    with engine.begin() as connection:
        location_id = connection.execute(_SAMPLE_LOCATION).scalar_one()
        connection.execute(
            text("""
                INSERT INTO crime_incidents
                    (code, incident_type, occurred_at, incident_date, incident_time, location_id)
                VALUES
                    ('INC-IT', 'CURANMOR', now(), current_date, '13:51', :location_id)
            """),
            {"location_id": location_id},
        )

        with pytest.raises(DatabaseError):
            connection.execute(text("DELETE FROM locations WHERE code = 'LOC-IT'"))

        connection.rollback()


def test_score_check_constraint_is_enforced(engine: Engine) -> None:
    with engine.begin() as connection:
        location_id = connection.execute(_SAMPLE_LOCATION).scalar_one()

        with pytest.raises(DatabaseError):
            connection.execute(
                text("""
                    INSERT INTO intelligence_reports
                        (code, report_date, category, location_id, confidence)
                    VALUES
                        ('INT-IT', current_date, 'Potensi Tawuran', :location_id, 150)
                """),
                {"location_id": location_id},
            )

        connection.rollback()
