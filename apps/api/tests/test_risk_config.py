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
    loaded: dict[str, Any] = yaml.safe_load(THRESHOLDS.read_text())
    return loaded


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
