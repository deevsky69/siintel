"""Test seed data kejadian (TASK 021).

Fokus pada dua acceptance criteria yang baru benar-benar teruji pada volume nyata:
A-2 (pemetaan `grid_id` → `location_id`) dan A-11 (normalisasi waktu ke UTC).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import UTC

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.models import CrimeIncident, IntelligenceReport, PatrolActivity
from prediksi_presisi_api.seeding import SeedError
from prediksi_presisi_api.seeding import csv_source as src
from prediksi_presisi_api.seeding.crime import _resolve_location, seed_crime_data

DATABASE_URL = os.environ.get("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tidak diisi — jalankan `pnpm db:up` lalu ulangi",
)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(DATABASE_URL, future=True)
    connection = engine.connect()
    transaction = connection.begin()
    opened = sessionmaker(bind=connection, expire_on_commit=False)()

    yield opened

    opened.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


def test_unknown_grid_stops_the_seed() -> None:
    """A-2: grid yang tidak dikenal tidak boleh dilewati diam-diam."""
    with pytest.raises(SeedError, match="tidak ada pada tabel locations"):
        _resolve_location({"JKS-001": uuid.uuid4()}, "JKS-TIDAK-ADA", "uji")


def test_missing_grid_stops_the_seed() -> None:
    with pytest.raises(SeedError, match="kosong"):
        _resolve_location({}, None, "uji")


#: Berkas sumber tiap tabel beserta kolom kodenya.
CRIME_SOURCES = (
    ("crime_incidents.csv", "incident_id", CrimeIncident),
    ("intelligence_reports.csv", "intelligence_id", IntelligenceReport),
    ("patrol_activity.csv", "patrol_id", PatrolActivity),
)


def test_crime_seed_loads_every_row_of_its_source(session: Session) -> None:
    """Seluruh baris berkas sumber termuat — tidak ada yang diam-diam terlewat.

    Yang diperiksa adalah baris yang berasal dari berkas sumber, bukan jumlah seluruh
    isi tabel. Versi sebelumnya menegaskan `COUNT(*) == 1200`, dan gagal begitu aplikasi
    akhirnya punya pintu masuk data: kejadian yang dimasukkan petugas lewat `/input`
    adalah baris yang **sah** — justru bukti bahwa prototipe ini bekerja.

    Ini pola kesalahan yang sama dengan `test_operational_seed_loads_expected_volumes`
    dan `test_seeding_never_creates_a_usable_password`, dan pantas dicatat sebagai
    kecenderungan: test yang mengunci keadaan basis data akan patah tepat ketika sistem
    mulai berguna.
    """
    seed_crime_data(session)
    session.flush()

    for name, column, model in CRIME_SOURCES:
        codes = {row[column] for row in src.read_rows(name)}
        loaded = session.scalar(
            select(func.count()).select_from(model).where(model.code.in_(codes))
        )
        assert loaded == len(codes), f"{name}: {loaded} dari {len(codes)} baris termuat"


def test_every_incident_is_attached_to_a_location(session: Session) -> None:
    """A-2 pada volume penuh: tidak ada kejadian tanpa lokasi."""
    seed_crime_data(session)
    session.flush()

    orphans = session.scalar(
        select(func.count()).select_from(CrimeIncident).where(CrimeIncident.location_id.is_(None))
    )

    assert orphans == 0


def test_local_time_is_stored_as_utc(session: Session) -> None:
    """A-11: 13:51 WIB tersimpan sebagai 06:51 UTC."""
    seed_crime_data(session)
    session.flush()

    incident = session.scalar(select(CrimeIncident).where(CrimeIncident.code == "INC-00001"))

    assert incident is not None
    assert incident.occurred_at.astimezone(UTC).hour == 6
    assert incident.occurred_at.astimezone(UTC).minute == 51
    assert incident.incident_time.hour == 13  # jam lokal dipertahankan untuk analisis jam rawan


def test_status_values_are_stored_in_english(session: Session) -> None:
    seed_crime_data(session)
    session.flush()

    statuses = set(session.scalars(select(CrimeIncident.status).distinct()).all())

    assert statuses == {"REPORTED", "PRELIMINARY_INVESTIGATION", "INVESTIGATION", "CLOSED"}


def test_field_terms_are_kept_verbatim(session: Session) -> None:
    # modus/target_type adalah istilah lapangan, bukan taksonomi berjenjang (docs/02 §22).
    seed_crime_data(session)
    session.flush()

    modus = set(session.scalars(select(CrimeIncident.modus).distinct()).all())

    assert "kunci_t" in modus


def test_crime_seed_is_idempotent(session: Session) -> None:
    seed_crime_data(session)
    session.flush()

    second = seed_crime_data(session)
    session.flush()

    assert sum(second.inserted.values()) == 0


def test_patrol_activity_is_linked_to_units_and_locations(session: Session) -> None:
    seed_crime_data(session)
    session.flush()

    unlinked = session.scalar(
        select(func.count())
        .select_from(PatrolActivity)
        .where(PatrolActivity.unit_id.is_(None) | PatrolActivity.location_id.is_(None))
    )

    assert unlinked == 0


def test_dataset_row_counts_match_the_source_files() -> None:
    """Menjaga agar berkas sumber tidak berubah diam-diam."""
    # Naik pada 8 September 2026 bersama penambahan Kecamatan Pesanggrahan.
    assert len(src.read_rows("crime_incidents.csv")) == 1345
    assert len(src.read_rows("intelligence_reports.csv")) == 135
    assert len(src.read_rows("patrol_activity.csv")) == 202
