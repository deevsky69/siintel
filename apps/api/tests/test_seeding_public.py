"""Test seed kanal masyarakat (TASK 024).

Yang paling penting di sini adalah `test_citizen_reports_carry_no_personal_identity`.
Tabel `citizen_reports` sengaja tidak menyimpan identitas pelapor (docs/02 §6 U-13,
CLAUDE.md §16), dan keputusan pemilik proyek 1 September 2026 menetapkan masyarakat
sebagai kanal **tanpa akun** (docs/14 §3, §6). Satu-satunya kolom teks bebas yang tersisa
adalah `description`, dan justru di situ identitas paling mudah menyelinap masuk kembali
tanpa disadari. Test ini menjaga pintu itu.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from prediksi_presisi_api.models import CitizenReport, CommunityFeedback, PublicAlert
from prediksi_presisi_api.seeding import csv_source as src
from prediksi_presisi_api.seeding.paths import SAMPLE_DATA_DIR
from prediksi_presisi_api.seeding.public import seed_public_data
from prediksi_presisi_api.seeding.regenerate import (
    CITIZEN_REPORT_COUNT,
    COMMUNITY_FEEDBACK_COUNT,
    PUBLIC_ALERT_COUNT,
    REPORT_STATUS_STAGES,
    regenerate_public,
)
from prediksi_presisi_api.seeding.taxonomy import load_taxonomy

DATABASE_URL = os.environ.get("DATABASE_URL", "")


# --------------------------------------------------------------------------------------
# Berkas sumber — tanpa database
# --------------------------------------------------------------------------------------


def test_source_files_have_the_expected_volume() -> None:
    assert len(src.read_rows("citizen_reports.csv")) == CITIZEN_REPORT_COUNT
    assert len(src.read_rows("public_alerts.csv")) == PUBLIC_ALERT_COUNT
    assert len(src.read_rows("community_feedback.csv")) == COMMUNITY_FEEDBACK_COUNT


#: Pola yang menandakan identitas orang menyelinap ke dalam data laporan.
#:
#: Bukan daftar lengkap dan tidak dimaksudkan menjadi penyaring keamanan — gunanya
#: menangkap kelalaian yang paling mungkin terjadi: nomor telepon, NIK 16 digit, alamat
#: surel, dan gelar sapaan yang selalu diikuti nama orang.
_IDENTITY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("nomor telepon", r"(?:\+62|\b08)\d{6,}"),
    ("NIK 16 digit", r"\b\d{16}\b"),
    ("alamat surel", r"[\w.+-]+@[\w-]+\.[\w.]+"),
    ("sapaan bernama", r"\b(?:Bapak|Ibu|Sdr|Sdri|Saudara|Nama pelapor|a\.n\.)\b"),
)

#: Kolom yang tidak boleh ada sama sekali pada berkas laporan masyarakat.
_FORBIDDEN_REPORT_COLUMNS = {
    "reporter_id",
    "reporter_name",
    "nama",
    "nama_pelapor",
    "nik",
    "phone",
    "telepon",
    "no_hp",
    "email",
    "alamat",
}


def test_citizen_reports_carry_no_personal_identity() -> None:
    """Tidak ada identitas pelapor — tidak sebagai kolom, tidak pula di dalam deskripsi."""
    rows = src.read_rows("citizen_reports.csv")
    assert rows

    columns = {name.lower() for name in rows[0]}
    assert not (columns & _FORBIDDEN_REPORT_COLUMNS), sorted(columns & _FORBIDDEN_REPORT_COLUMNS)

    for row in rows:
        haystack = " ".join(row.values())
        for label, pattern in _IDENTITY_PATTERNS:
            assert not re.search(pattern, haystack), f"{row['report_id']}: {label}"


def test_citizen_report_statuses_follow_the_taxonomy() -> None:
    taxonomy = load_taxonomy()
    for row in src.read_rows("citizen_reports.csv"):
        assert row["status"] in REPORT_STATUS_STAGES, row["report_id"]
        # Label Indonesia pada berkas harus benar-benar dapat dipetakan ke nilai tersimpan.
        assert taxonomy.require("status_citizen_report", row["status"])


def test_citizen_reports_stay_inside_the_incident_period() -> None:
    """Rentang tanggal disamakan dengan `crime_incidents.csv` (2023-01..2025-12)."""
    days = sorted(row["incident_date"] for row in src.read_rows("crime_incidents.csv"))
    first, last = date.fromisoformat(days[0]), date.fromisoformat(days[-1])

    for row in src.read_rows("citizen_reports.csv"):
        reported = src.parse_datetime(row["reported_at"], "citizen_reports.csv").date()
        assert first <= reported <= last, row["report_id"]

        if row["incident_time"]:
            # Kejadian lebih dulu, laporan menyusul.
            assert row["incident_time"] < row["reported_at"], row["report_id"]


def test_citizen_reports_reference_real_grids_or_none() -> None:
    """`location_id` nullable: laporan boleh belum terpetakan, tetapi tidak boleh salah tunjuk."""
    grids = {row["grid_id"] for row in src.read_rows("locations.csv")}
    rows = src.read_rows("citizen_reports.csv")

    for row in rows:
        if row["grid_id"]:
            assert row["grid_id"] in grids, row["report_id"]

    unmapped = sum(1 for row in rows if not row["grid_id"])
    assert 0 < unmapped < len(rows), "jalur laporan tanpa grid tidak terwakili di dataset"


def test_citizen_report_scores_are_within_the_check_constraint() -> None:
    for row in src.read_rows("citizen_reports.csv"):
        assert 0 <= int(row["urgency_score"]) <= 100, row["report_id"]
        assert 0 <= int(row["verification_score"]) <= 100, row["report_id"]


def test_public_alerts_point_to_real_warnings() -> None:
    warnings = {row["warning_id"] for row in src.read_rows("early_warnings.csv")}

    for row in src.read_rows("public_alerts.csv"):
        assert row["warning_id"] in warnings, row["public_alert_id"]


def test_public_alerts_never_expose_the_internal_grid() -> None:
    """docs/02 §7: imbauan publik memakai `area_text` setingkat kecamatan, bukan grid.

    Kecamatan adalah satuan wilayah **paling halus** yang boleh keluar ke publik. Menyebut
    kelurahan atau grid akan mempersempit sasaran sampai ke tingkat yang justru berguna
    bagi pelaku (CLAUDE.md §24).

    Pemeriksaan dilakukan dengan pencocokan tepat, bukan pencarian substring: sebagian
    kelurahan bernama sama dengan kecamatannya (mis. Jagakarsa), sehingga pencarian
    substring akan menuduh `area_text` yang sebenarnya benar.
    """
    locations = src.read_rows("locations.csv")
    kecamatan = {row["kecamatan"] for row in locations}
    rows = src.read_rows("public_alerts.csv")

    assert "grid_id" not in rows[0]
    assert "location_id" not in rows[0]
    for row in rows:
        assert "JKS-" not in row["public_message"], row["public_alert_id"]
        assert row["area_text"].startswith("Kecamatan "), row["public_alert_id"]
        assert row["area_text"].removeprefix("Kecamatan ") in kecamatan, row["area_text"]


def test_community_feedback_points_to_real_reports_and_comes_after_them() -> None:
    reports = {row["report_id"]: row["reported_at"] for row in src.read_rows("citizen_reports.csv")}
    rows = src.read_rows("community_feedback.csv")

    for row in rows:
        assert row["report_id"] in reports, row["feedback_id"]
        assert row["submitted_at"] > reports[row["report_id"]], row["feedback_id"]

    # Satu umpan balik satu laporan; tanpa ini sebagian laporan akan menumpuk tanggapan.
    assert len({row["report_id"] for row in rows}) == len(rows)


def test_regeneration_is_deterministic() -> None:
    """Menjalankan ulang harus menghasilkan berkas yang sama persis (`row_rng` per baris).

    Test ini benar-benar menulis ulang `data/sample/`. Itu disengaja: kalimat "deterministik"
    hanya bermakna bila pembangkitnya sungguh dijalankan lagi di atas hasilnya sendiri.
    """
    names = ("citizen_reports.csv", "public_alerts.csv", "community_feedback.csv")
    before = {name: (SAMPLE_DATA_DIR / name).read_bytes() for name in names}

    regenerate_public()

    for name in names:
        assert (SAMPLE_DATA_DIR / name).read_bytes() == before[name], name


# --------------------------------------------------------------------------------------
# Dengan database
# --------------------------------------------------------------------------------------

requires_database = pytest.mark.skipif(
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


#: Berkas sumber tiap tabel kanal masyarakat beserta kolom kodenya.
PUBLIC_SOURCES = (
    ("citizen_reports.csv", "report_id", CitizenReport),
    ("public_alerts.csv", "public_alert_id", PublicAlert),
    ("community_feedback.csv", "feedback_id", CommunityFeedback),
)


@requires_database
def test_public_seed_loads_every_row_of_its_source(session: Session) -> None:
    """Seluruh baris berkas sumber termuat — tidak ada yang diam-diam terlewat."""
    seed_public_data(session)
    session.flush()

    for name, column, model in PUBLIC_SOURCES:
        codes = {row[column] for row in src.read_rows(name)}
        loaded = session.scalar(
            select(func.count()).select_from(model).where(model.code.in_(codes))
        )
        assert loaded == len(codes), f"{name}: {loaded} dari {len(codes)} baris termuat"


@requires_database
def test_feedback_sees_reports_from_the_same_seed_run(session: Session) -> None:
    """Umpan balik menunjuk laporan yang baru disisipkan pada kelompok yang sama.

    Session memakai `autoflush=False`. Tanpa `session.flush()` di antara kelompok, laporan
    yang baru ditambahkan tidak terlihat oleh query umpan balik dan seluruh baris ditolak
    sebagai "laporan tidak ditemukan" — persis bug yang pernah terjadi pada `seeding all`
    (lihat `tests/test_seeding_chain.py`).
    """
    seed_public_data(session)
    session.flush()

    codes = {row["feedback_id"] for row in src.read_rows("community_feedback.csv")}
    linked = session.scalar(
        select(func.count())
        .select_from(CommunityFeedback)
        .join(CitizenReport, CitizenReport.report_id == CommunityFeedback.report_id)
        .where(CommunityFeedback.code.in_(codes))
    )
    assert linked == len(codes)


@requires_database
def test_seeded_reports_keep_the_unmapped_ones_unmapped(session: Session) -> None:
    """Laporan tanpa grid tidak boleh dipaksa masuk ke sel terdekat (docs/02 §6)."""
    seed_public_data(session)
    session.flush()

    expected = {
        row["report_id"] for row in src.read_rows("citizen_reports.csv") if not row["grid_id"]
    }
    actual = set(
        session.scalars(
            select(CitizenReport.code).where(
                CitizenReport.location_id.is_(None), CitizenReport.code.in_(expected)
            )
        ).all()
    )

    assert actual == expected


@requires_database
def test_public_alerts_are_stored_without_any_location_column(session: Session) -> None:
    seed_public_data(session)
    session.flush()

    columns = set(PublicAlert.__table__.c.keys())
    assert "location_id" not in columns
    assert "grid_id" not in columns

    alert = session.scalar(select(PublicAlert).limit(1))
    assert alert is not None
    assert alert.area_text


def test_a_status_left_untranslated_is_repaired_not_left_to_rot(session: Session) -> None:
    """Ditemukan di produksi 9 September 2026: status tersimpan sebagai label Indonesia.

    Basis data demo menyimpan `Diterima` alih-alih `RECEIVED`, karena barisnya masuk lewat
    versi seeder yang belum memetakan taksonomi — dan seed yang hanya-menambah tidak pernah
    memperbaikinya. Seluruh kueri menyaring nilai enum, sehingga produksi melaporkan NOL
    laporan menunggu verifikasi padahal ada 17, dan antrean petugas pada aplikasi Android
    kosong sama sekali.
    """
    seed_public_data(session)
    session.flush()

    rusak = session.scalars(select(CitizenReport).limit(1)).one()
    kode, semula = rusak.code, rusak.status
    rusak.status = "Diterima"
    session.flush()

    seed_public_data(session)
    session.flush()
    session.expire_all()

    diperbaiki = session.scalar(select(CitizenReport).where(CitizenReport.code == kode))
    assert diperbaiki is not None
    assert diperbaiki.status == "RECEIVED", "status berbahasa Indonesia dibiarkan apa adanya"
    assert semula in {"RECEIVED", "VERIFIED", "FORWARDED", "IN_PROGRESS", "CLOSED"}


def test_an_operational_status_change_is_never_undone_by_reseeding(session: Session) -> None:
    """Verifikasi yang benar-benar dilakukan petugas TIDAK boleh dibatalkan seed berikutnya.

    Inilah sebabnya perbaikan di atas hanya menyentuh nilai yang bukan enum sah, alih-alih
    menyegarkan status dari CSV seperti yang dikerjakan untuk `recommendation_text`.
    Kalimat rekomendasi adalah keterangan yang dibangkitkan; status laporan adalah keadaan
    operasional, dan menyegarkannya merusak lebih banyak daripada yang diperbaiki.
    """
    seed_public_data(session)
    session.flush()

    laporan = session.scalars(
        select(CitizenReport).where(CitizenReport.status == "RECEIVED").limit(1)
    ).one()
    kode = laporan.code
    laporan.status = "VERIFIED"
    session.flush()

    seed_public_data(session)
    session.flush()
    session.expire_all()

    tetap = session.scalar(select(CitizenReport).where(CitizenReport.code == kode))
    assert tetap is not None
    assert tetap.status == "VERIFIED", "seed membatalkan verifikasi petugas"
