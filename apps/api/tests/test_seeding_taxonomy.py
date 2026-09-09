"""Test pemetaan taksonomi dan pembacaan CSV (TASK 020). Tidak memerlukan database."""

from __future__ import annotations

from datetime import UTC, date, time

import pytest
import yaml

from prediksi_presisi_api.seeding import SeedError, load_taxonomy
from prediksi_presisi_api.seeding import csv_source as src
from prediksi_presisi_api.seeding.paths import RBAC_FILE, SAMPLE_DATA_DIR, TAXONOMY_FILE


def test_configuration_files_exist() -> None:
    assert TAXONOMY_FILE.exists()
    assert RBAC_FILE.exists()
    assert SAMPLE_DATA_DIR.exists()


def test_indonesian_values_map_to_stored_enums() -> None:
    taxonomy = load_taxonomy()

    assert taxonomy.map("status_crime", "Dilaporkan") == "REPORTED"
    assert taxonomy.map("risk_class", "Moderate") == "MODERATE"
    assert taxonomy.map("priority", "Sedang") == "MEDIUM"
    assert taxonomy.map("function", "Reskrim") == "RESKRIM"


def test_values_already_in_stored_form_are_accepted() -> None:
    taxonomy = load_taxonomy()

    assert taxonomy.map("status_crime", "REPORTED") == "REPORTED"


def test_blank_values_stay_empty() -> None:
    taxonomy = load_taxonomy()

    assert taxonomy.map("status_crime", "") is None
    assert taxonomy.map("status_crime", None) is None


def test_unknown_value_stops_the_seed() -> None:
    # Nilai asing yang diterima diam-diam akan menjadi taksonomi bayangan
    # yang tidak pernah disetujui siapa pun.
    taxonomy = load_taxonomy()

    with pytest.raises(SeedError, match="tidak dikenal"):
        taxonomy.map("status_crime", "Entah")


def test_unknown_domain_stops_the_seed() -> None:
    taxonomy = load_taxonomy()

    with pytest.raises(SeedError, match="tidak ada"):
        taxonomy.map("domain_tidak_ada", "Dilaporkan")


def test_required_value_rejects_blank() -> None:
    taxonomy = load_taxonomy()

    with pytest.raises(SeedError, match="wajib"):
        taxonomy.require("status_crime", "")


def test_every_dataset_value_is_mappable() -> None:
    """Setiap nilai pada dataset dummy harus punya pemetaan — jika tidak, seed akan gagal."""
    taxonomy = load_taxonomy()
    checks = (
        ("crime_incidents.csv", "status", "status_crime"),
        ("crime_incidents.csv", "incident_type", "incident_type"),
        ("intelligence_reports.csv", "status", "status_intelligence"),
        ("intelligence_reports.csv", "impact", "impact"),
        ("police_units.csv", "function", "function"),
        ("police_units.csv", "status", "status_unit"),
        ("users.csv", "status", "status_user"),
        ("risk_scores.csv", "risk_class", "risk_class"),
        ("early_warnings.csv", "severity", "severity"),
        ("early_warnings.csv", "status", "status_warning"),
        ("predictions.csv", "status", "status_prediction"),
        ("recommendations.csv", "priority", "priority"),
        ("recommendations.csv", "status", "status_recommendation"),
        ("commander_decisions.csv", "decision", "decision"),
        ("operational_actions.csv", "status", "status_action"),
        ("citizen_reports.csv", "status", "status_citizen_report"),
        ("community_feedback.csv", "status", "status_community_feedback"),
        ("community_feedback.csv", "feedback_type", "feedback_type"),
        ("prediction_actual.csv", "match_type", "match_type"),
    )

    for filename, column, domain in checks:
        values = {row[column] for row in src.read_rows(filename) if row.get(column)}
        for value in values:
            assert taxonomy.map(domain, value) is not None, f"{filename}.{column} = {value}"


def test_datetime_is_normalised_to_utc_from_both_formats() -> None:
    # Dataset memakai dua gaya penulisan; keduanya waktu lokal Jakarta (docs/02 K-3).
    with_t = src.parse_datetime("2025-10-03T19:06", "uji")
    with_space = src.parse_datetime("2025-10-03 19:06", "uji")

    assert with_t == with_space
    assert with_t.tzinfo == UTC
    assert with_t.hour == 12  # 19:06 WIB = 12:06 UTC


def test_date_and_time_are_combined_into_utc() -> None:
    moment = src.combine(date(2025, 12, 26), time(13, 51))

    assert moment.tzinfo == UTC
    assert (moment.hour, moment.minute) == (6, 51)


def test_invalid_datetime_stops_the_seed() -> None:
    with pytest.raises(SeedError, match="waktu tidak valid"):
        src.parse_datetime("26 Desember 2025", "uji")


def test_missing_file_stops_the_seed() -> None:
    with pytest.raises(SeedError, match="tidak ditemukan"):
        src.read_rows("berkas_yang_tidak_ada.csv")


def test_seeded_report_categories_are_all_offered_on_the_public_form() -> None:
    """Kategori pada data contoh harus ada di daftar yang ditawarkan kanal publik.

    Keduanya hidup di tempat berbeda — pembangkit data di `seeding/regenerate.py`, daftar
    pilihan di `config/taxonomy/mappings.yaml` — dan tidak ada yang menghubungkannya selain
    test ini. Bila keduanya menyimpang, layar publik menawarkan kategori yang tidak pernah
    muncul di data, atau data memuat kategori yang tidak dapat dipilih siapa pun. Keduanya
    tidak menimbulkan galat apa pun.
    """
    from prediksi_presisi_api.api.routers.public_intake import load_report_categories
    from prediksi_presisi_api.seeding.regenerate import REPORT_CATEGORIES

    offered = set(load_report_categories())
    seeded = {category.name for category in REPORT_CATEGORIES}

    assert seeded <= offered, f"kategori pada data contoh tidak ditawarkan: {seeded - offered}"


# --------------------------------------------------------------------------------------
# Status penetapan (U-16)
# --------------------------------------------------------------------------------------


def test_the_taxonomy_in_use_has_actually_been_adopted() -> None:
    """Taksonomi ditetapkan pemilik proyek 9 September 2026.

    Seed MENGHENTIKAN dirinya pada nilai yang tidak dikenal — perilaku yang hanya masuk
    akal bila daftar nilainya memang sudah diputus. Selama statusnya PROPOSED, penolakan
    itu menegakkan daftar yang belum disetujui siapa pun.

    Yang diperiksa hanyalah bahwa taksonomi yang dipakai sudah ditetapkan dan bertanggal.
    Isi daftarnya tetap keputusan pemilik proyek, bukan keputusan test.
    """
    raw = yaml.safe_load(TAXONOMY_FILE.read_text(encoding="utf-8"))

    assert raw["status"] == "FINAL"
    assert raw["ditetapkan"], "berstatus FINAL tanpa tanggal penetapan"
    assert load_taxonomy().status == "FINAL", "status tidak dibawa keluar dari konfigurasi"


def test_the_version_name_never_contradicts_its_own_status() -> None:
    """Versi FINAL yang namanya berbunyi "proposed" adalah dua pernyataan bertentangan.

    Nama versi ini dicetak apa adanya pada layar Entri Data, di sebelah statusnya. Sebelum
    9 September 2026 keduanya berbunyi `proposed-2026-09-01` dan `FINAL` berdampingan.
    """
    raw = yaml.safe_load(TAXONOMY_FILE.read_text(encoding="utf-8"))

    if raw["status"] == "FINAL":
        assert "proposed" not in str(raw["version"]).lower()


def test_field_terminology_stays_out_of_the_mapped_taxonomy() -> None:
    """`modus`, `target_type`, dan `location_type` sengaja TIDAK dipetakan (docs/02 §22).

    Ketiganya istilah lapangan, bukan taksonomi berjenjang. Penetapan U-16 tidak mengubah
    keputusan teknis itu, dan menambahkannya diam-diam ke berkas pemetaan akan membuat seed
    menolak istilah lapangan yang belum terdaftar — perubahan perilaku yang menuntut
    keputusan pemilik proyek, bukan kelengkapan yang kebetulan terlewat.
    """
    mapped = set(load_taxonomy().mappings)

    assert {"modus", "target_type", "location_type"}.isdisjoint(mapped)
