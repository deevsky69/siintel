"""Aritmetika konfigurasi risiko harus benar sebelum dipakai menghitung apa pun.

Bobot yang tidak berjumlah tepat 1 tidak menimbulkan kesalahan apa pun — ia hanya
menurunkan skor tertinggi yang mungkin dicapai, diam-diam. Bila jumlahnya 0,93, kelas
`CRITICAL` menjadi mustahil dan ambang 85 pada `warning-thresholds.yaml` tidak pernah
tersentuh. Tidak ada test lain yang akan menangkap itu: seluruh skor tetap "masuk akal",
hanya saja tidak pernah setinggi yang seharusnya.

Ini pernah benar-benar terjadi pada rancangan dua profil: Profil A berjumlah 0,93 dan
Profil B 0,80, karena satu faktor sengaja disetel nol tanpa membagi ulang sisanya.
"""

from __future__ import annotations

import math
from typing import Any

import pytest
import yaml

from prediksi_presisi_api.seeding.paths import REPO_ROOT

RISK_WEIGHTS = REPO_ROOT / "config" / "risk" / "risk-weights.yaml"
THRESHOLDS = REPO_ROOT / "config" / "risk" / "warning-thresholds.yaml"


def _catalogue() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(RISK_WEIGHTS.read_text())
    return loaded


def _profiles() -> dict[str, dict[str, Any]]:
    """Seluruh profil dari SELURUH versi, ditandai `versi/profil`.

    Diperiksa semuanya, bukan hanya versi aktif: versi lama tetap dipakai membaca
    skor lama, dan bobotnya yang rusak sama merugikannya.
    """
    catalogue = _catalogue()
    return {
        f"{version}/{name}": profile
        for version, body in catalogue["versions"].items()
        for name, profile in body["profiles"].items()
    }


def _thresholds() -> dict[str, Any]:
    """Ambang versi yang sedang berlaku — bukan tingkat atas berkas.

    Ambang diberi versi pada 1 September 2026, sama alasannya dengan bobot: ambang
    sebuah versi yang masih dirujuk baris `early_warnings` tidak boleh diubah.
    """
    catalogue: dict[str, Any] = yaml.safe_load(THRESHOLDS.read_text())
    resolved: dict[str, Any] = catalogue["versions"][str(catalogue["active_version"])]
    return resolved


def _threshold_versions() -> dict[str, Any]:
    catalogue: dict[str, Any] = yaml.safe_load(THRESHOLDS.read_text())
    versions: dict[str, Any] = catalogue["versions"]
    return versions


@pytest.mark.parametrize("profile", sorted(_profiles()))
def test_risk_weights_sum_correctly(profile: str) -> None:
    """Bobot **positif** berjumlah tepat 1 pada setiap profil.

    Yang dijumlahkan hanya yang positif: `readiness_factor` pada Profil B sengaja
    bertanda negatif dan berperan mengurangi skor, bukan menyusunnya. Menjumlahkan
    seluruh bobot akan membuat skor tertinggi Profil B menjadi 90.
    """
    weights = _profiles()[profile]["weights"]
    positive = sum(value for value in weights.values() if value > 0)

    assert math.isclose(positive, 1.0, abs_tol=1e-9), (
        f"profil '{profile}': bobot positif berjumlah {positive}, bukan 1. "
        f"Skor tertinggi yang mungkin dicapai menjadi {positive * 100:.0f}, "
        f"sehingga kelas tertinggi pada warning-thresholds.yaml tidak pernah tercapai."
    )


def test_the_highest_class_is_actually_reachable() -> None:
    """Skor sempurna harus jatuh di kelas tertinggi, bukan sedikit di bawahnya."""
    top = max(_thresholds()["risk_classes"], key=lambda item: int(item["max"]))

    for profile, definition in _profiles().items():
        positive = sum(value for value in definition["weights"].values() if value > 0)
        reachable = round(positive * 100)
        assert reachable >= int(top["min"]), (
            f"profil '{profile}' hanya dapat mencapai {reachable}, "
            f"sedangkan kelas {top['class']} mulai dari {top['min']}"
        )


def test_every_threat_type_belongs_to_exactly_one_profile() -> None:
    """Satu jenis ancaman dinilai satu cara, tidak dua.

    Jenis yang masuk dua profil akan menghasilkan dua skor berbeda untuk sel dan
    jendela waktu yang sama, dan tidak ada aturan yang menentukan mana yang berlaku.
    """
    # Diperiksa **per versi**: sebuah jenis boleh berpindah profil antar versi — TAWURAN
    # memang dinilai historis pada dummy-v1 dan terencana pada rancangan baru. Yang
    # dilarang adalah satu jenis masuk dua profil pada versi yang SAMA.
    for version, body in _catalogue()["versions"].items():
        seen: dict[str, str] = {}
        for name, profile in body["profiles"].items():
            for threat in profile["applies_to"]:
                assert threat not in seen, (
                    f"versi {version}: '{threat}' masuk profil '{seen[threat]}' dan "
                    f"'{name}' sekaligus, sehingga tidak ada aturan yang menentukan "
                    f"skor mana yang berlaku"
                )
                seen[threat] = name

    taxonomy = yaml.safe_load((REPO_ROOT / "config" / "taxonomy" / "mappings.yaml").read_text())
    declared = set(taxonomy["mappings"]["incident_type"].values())

    # Kelengkapan dituntut pada versi TERBARU saja. Versi lama sengaja tidak dipaksa
    # mencakup jenis yang baru ditambahkan — ia hanya perlu tetap dapat membaca skor
    # yang dahulu dihasilkannya.
    newest = max(_catalogue()["versions"])
    covered = {
        threat
        for profile in _catalogue()["versions"][newest]["profiles"].values()
        for threat in profile["applies_to"]
    }
    assert declared == covered, (
        f"versi {newest}: jenis tanpa profil penilaian {sorted(declared - covered)}; "
        f"profil menyebut jenis di luar taksonomi {sorted(covered - declared)}"
    )


def test_the_check_would_catch_an_unbalanced_profile() -> None:
    """Tanpa ini, pemeriksaan di atas dapat lulus karena pemeriksanya sendiri rusak."""
    broken = {"a": 0.25, "b": 0.20, "c": 0.18, "d": 0.12, "e": 0.10, "f": 0.08, "g": 0.00}
    assert not math.isclose(sum(broken.values()), 1.0, abs_tol=1e-9)
    assert math.isclose(sum(broken.values()), 0.93, abs_tol=1e-9)


def test_threshold_profiles_match_the_weight_profiles() -> None:
    """Nama profil ambang harus ada di profil bobot pada versi yang sama.

    Ambang untuk profil yang tidak ada tidak akan pernah dipakai, dan ketiadaannya tidak
    menimbulkan galat apa pun — peringatan Kelompok B sekadar tidak pernah terbit,
    diam-diam. Salah eja `planned` menjadi `plannned` cukup untuk itu.
    """
    weights = _catalogue()["versions"]

    for version, body in _threshold_versions().items():
        named = set(body["early_warning"].get("profiles", {}))
        if not named:
            continue

        assert version in weights, (
            f"ambang versi '{version}' menyebut profil, tetapi versi bobot dengan nama "
            f"itu tidak ada — keduanya harus berversi seiring"
        )
        available = set(weights[version]["profiles"])
        assert named <= available, (
            f"ambang versi '{version}' menyebut profil {sorted(named - available)} "
            f"yang tidak ada pada bobot; tersedia: {sorted(available)}"
        )


def test_planned_disturbances_warn_earlier_than_crime() -> None:
    """Kelompok B diperingatkan lebih awal — keputusan pemilik proyek, 1 September 2026.

    Alasannya bukan bahwa gangguan terencana lebih berbahaya, melainkan bahwa ia punya
    waktu persiapan: peringatan yang terbit sejam sebelum massa berkumpul sudah terlambat
    untuk menyiapkan pengamanan.
    """
    proposed = _threshold_versions()["proposed-2026-09-01"]["early_warning"]
    planned = proposed["profiles"]["planned"]["minimum_score"]

    assert planned < proposed["default"]["minimum_score"]
    assert planned == 60


# --------------------------------------------------------------------------------------
# Status penetapan (U-01, U-02)
# --------------------------------------------------------------------------------------


def _threshold_catalogue() -> dict[str, Any]:
    """SELURUH isi berkas ambang, bukan hanya versi yang berlaku.

    Berbeda dari `_thresholds()` di atas — yang menjawab isi versi aktif — karena yang
    diperiksa di bagian ini justru versi mana yang aktif dan apa statusnya.
    """
    loaded: dict[str, Any] = yaml.safe_load(THRESHOLDS.read_text())
    return loaded


@pytest.mark.parametrize("berkas", ["bobot", "ambang"])
def test_the_configuration_in_force_has_actually_been_adopted(berkas: str) -> None:
    """Versi yang dipakai menghitung harus berstatus FINAL, bukan usulan.

    Pemilik proyek menetapkan bobot dan ambang `dummy-v1` pada 9 September 2026 (U-02 dan
    U-01). Sejak itu, menjalankan sistem di atas versi yang masih PROPOSED bukan lagi
    keadaan sementara yang dapat dimaklumi melainkan kemunduran: setiap skor dan setiap
    peringatan akan terbit di bawah aturan yang tidak pernah diputus siapa pun, dan tidak
    ada gejala apa pun yang menandainya.

    Test ini TIDAK memeriksa nilai bobot maupun ambangnya — hanya bahwa versi yang berlaku
    sudah ditetapkan. Menetapkan angka yang keliru tetap mungkin, dan itu memang keputusan
    pemilik proyek, bukan keputusan test.
    """
    catalogue = _catalogue() if berkas == "bobot" else _threshold_catalogue()
    active = str(catalogue["active_version"])
    body = catalogue["versions"][active]

    assert body["status"] == "FINAL", (
        f"versi aktif '{active}' berstatus {body['status']}; "
        "menyalakan versi yang belum ditetapkan menuntut keputusan pemilik proyek"
    )
    assert body["ditetapkan"], f"versi '{active}' berstatus FINAL tanpa tanggal penetapan"


def test_versions_that_are_merely_proposed_are_not_the_ones_in_force() -> None:
    """Rancangan boleh hidup di berkas yang sama, asalkan tidak diam-diam menyala.

    `proposed-2026-09-01` mengubah bobot DAN memindahkan TAWURAN ke profil lain, sehingga
    menyalakannya mengubah angka — itu keputusan tersendiri yang menuntut pembangkitan
    ulang skor, bukan akibat sampingan dari penetapan 9 September 2026.
    """
    for catalogue in (_catalogue(), _threshold_catalogue()):
        for name, body in catalogue["versions"].items():
            if name == str(catalogue["active_version"]):
                continue
            assert body["status"] != "FINAL", (
                f"versi '{name}' ditandai FINAL tetapi tidak dipakai menghitung apa pun; "
                "status FINAL pada versi yang tidak aktif membuat 'ditetapkan' kehilangan arti"
            )


def test_each_leadership_display_block_carries_its_own_status() -> None:
    """Dua keputusan berbeda tidak boleh berbagi satu penanda.

    Test ini lahir 9 September 2026 untuk menjaga U-22 agar tidak ikut terbawa penetapan
    U-01/U-02, dan waktu itu ia berbunyi "pemetaan ini masih PROPOSED". Pada hari yang
    sama pemilik proyek menetapkan U-22 dengan sengaja — sehingga yang perlu dijaga bukan
    lagi nilainya, melainkan bahwa kedua blok punya statusnya masing-masing.

    Sebelum pemisahan, menetapkan pemetaan status wilayah akan diam-diam ikut menetapkan
    ambang peringkat volume laporan — 0,70 dan 0,40 — yang tidak pernah menjadi bagian
    U-22 dan bahkan bukan tentang risiko sama sekali.
    """
    display = _threshold_catalogue()["leadership_display"]

    assert "status" not in display, "status gabungan menetapkan dua hal sekaligus"
    for nama in ("area_status", "report_volume"):
        assert display[nama]["status"] in {"FINAL", "PROPOSED"}, nama

    # Yang ditetapkan 9 September 2026 hanyalah pemetaan status wilayah.
    assert display["area_status"]["status"] == "FINAL"
    assert display["area_status"]["ditetapkan"]
    assert display["report_volume"]["status"] == "PROPOSED"
