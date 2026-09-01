"""Test rantai seed pada database kosong (`seeding all`).

Bug yang dijaga di sini pernah terjadi dan tidak terlihat oleh satu pun test lain:
`uv run python -m prediksi_presisi_api.seeding all` gagal di database kosong dengan
`rekomendasi 'REC-0001' tidak ditemukan`, padahal menjalankan `master`, `crime`,
`analytics`, lalu `operational` satu per satu berhasil.

Sebabnya: session dibuat dengan `autoflush=False`, dan `seed_analytics_data` melakukan
flush **di antara** sub-langkahnya tetapi tidak setelah yang terakhir. Bila keempat
kelompok berjalan dalam satu transaksi, `seed_operational_data` mencari rekomendasi
yang masih tertahan di memori dan tidak menemukannya.

Ini bukan bug yang bisa diabaikan sampai paparan: `docs/10-panduan-deployment.md`
menjalankan `seeding all` untuk mengisi database produksi, sehingga deploy demo akan
berhenti tepat di langkah itu.

Test lain tidak dapat menangkapnya karena seluruhnya berjalan di atas database yang
sudah terisi — pada keadaan itu seed tidak menyisipkan apa pun dan bug tidak muncul.
Karena itu test ini mengosongkan tabel domain lebih dulu, di dalam transaksi yang
dibatalkan setelahnya (`TRUNCATE` bersifat transaksional di PostgreSQL).
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.models import (
    CommanderDecision,
    CrimeIncident,
    Location,
    OperationalAction,
    Prediction,
    PredictionActual,
    Recommendation,
    User,
)
from prediksi_presisi_api.seeding.analytics import seed_analytics_data
from prediksi_presisi_api.seeding.crime import seed_crime_data
from prediksi_presisi_api.seeding.master import seed_master_data
from prediksi_presisi_api.seeding.operational import seed_operational_data
from prediksi_presisi_api.seeding.taxonomy import load_taxonomy

DATABASE_URL = os.environ.get("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="DATABASE_URL tidak diisi — jalankan `pnpm db:up` lalu ulangi",
)

#: Tabel domain yang dikosongkan sebelum rantai dijalankan. `alembic_version` sengaja
#: tidak ikut: menghapusnya akan membuat database tampak belum pernah dimigrasikan.
DOMAIN_TABLES = (
    "prediction_actual",
    "operational_actions",
    "commander_decisions",
    "recommendations",
    "public_alerts",
    "early_warnings",
    "predictions",
    "risk_scores",
    "community_feedback",
    "citizen_reports",
    "patrol_activity",
    "intelligence_reports",
    "crime_incidents",
    "audit_logs",
    "role_permissions",
    "permissions",
    "users",
    "roles",
    "police_units",
    "locations",
)


@pytest.fixture
def empty_database() -> Iterator[Session]:
    """Database kosong di dalam transaksi yang selalu dibatalkan."""
    engine = create_engine(DATABASE_URL, future=True)
    connection = engine.connect()
    transaction = connection.begin()
    # `sessionmaker` di sini menyalin `autoflush=False` dari konfigurasi aplikasi —
    # tanpa itu, test ini akan lulus karena alasan yang salah.
    opened = sessionmaker(bind=connection, autoflush=False, expire_on_commit=False)()

    opened.execute(text(f"TRUNCATE {', '.join(DOMAIN_TABLES)} RESTART IDENTITY CASCADE"))

    yield opened

    opened.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


def _count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_the_whole_chain_runs_in_a_single_transaction(empty_database: Session) -> None:
    """Inilah yang dijalankan `seeding all` — dan yang dipakai runbook deployment."""
    session = empty_database
    assert _count(session, Location) == 0, "database belum benar-benar kosong"

    taxonomy = load_taxonomy()
    seed_master_data(session, taxonomy)
    seed_crime_data(session, taxonomy)
    seed_analytics_data(session, taxonomy)
    seed_operational_data(session, taxonomy)
    session.flush()

    # Setiap kelompok bergantung pada kelompok sebelumnya lewat kode, bukan lewat id —
    # jadi angka bukan nol di baris terakhir berarti seluruh rantai benar-benar tersambung.
    assert _count(session, Location) == 33
    assert _count(session, User) == 6
    assert _count(session, CrimeIncident) == 1200
    assert _count(session, Prediction) == 180
    assert _count(session, Recommendation) == 84
    assert _count(session, CommanderDecision) == 63
    assert _count(session, OperationalAction) == 52
    assert _count(session, PredictionActual) == 241


def test_every_group_leaves_its_rows_visible_to_the_next(empty_database: Session) -> None:
    """Kontrak tiap kelompok: begitu ia kembali, barisnya sudah dapat di-query.

    Sub-langkah di dalam kelompok sudah saling mem-flush; yang dahulu terlewat adalah
    flush setelah sub-langkah **terakhir**.
    """
    session = empty_database
    taxonomy = load_taxonomy()

    for seed in (seed_master_data, seed_crime_data, seed_analytics_data, seed_operational_data):
        seed(session, taxonomy)
        assert not session.new, (
            f"{seed.__name__} kembali dengan baris yang belum ter-flush; "
            f"kelompok berikutnya tidak akan melihatnya"
        )
