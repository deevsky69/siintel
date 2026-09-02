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

import pytest
import yaml

from prediksi_presisi_api.seeding.paths import REPO_ROOT

RISK_WEIGHTS = REPO_ROOT / "config" / "risk" / "risk-weights.yaml"
THRESHOLDS = REPO_ROOT / "config" / "risk" / "warning-thresholds.yaml"


def _weights() -> dict[str, dict]:
    catalogue = yaml.safe_load(RISK_WEIGHTS.read_text())
    profiles: dict[str, dict] = catalogue["profiles"]
    return profiles


def _thresholds() -> dict:
    loaded: dict = yaml.safe_load(THRESHOLDS.read_text())
    return loaded


@pytest.mark.parametrize("profile", sorted(_weights()))
def test_risk_weights_sum_correctly(profile: str) -> None:
    """Bobot **positif** berjumlah tepat 1 pada setiap profil.

    Yang dijumlahkan hanya yang positif: `readiness_factor` pada Profil B sengaja
    bertanda negatif dan berperan mengurangi skor, bukan menyusunnya. Menjumlahkan
    seluruh bobot akan membuat skor tertinggi Profil B menjadi 90.
    """
    weights = _weights()[profile]["weights"]
    positive = sum(value for value in weights.values() if value > 0)

    assert math.isclose(positive, 1.0, abs_tol=1e-9), (
        f"profil '{profile}': bobot positif berjumlah {positive}, bukan 1. "
        f"Skor tertinggi yang mungkin dicapai menjadi {positive * 100:.0f}, "
        f"sehingga kelas tertinggi pada warning-thresholds.yaml tidak pernah tercapai."
    )


def test_the_highest_class_is_actually_reachable() -> None:
    """Skor sempurna harus jatuh di kelas tertinggi, bukan sedikit di bawahnya."""
    top = max(_thresholds()["risk_classes"], key=lambda item: int(item["max"]))

    for profile, definition in _weights().items():
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
    seen: dict[str, str] = {}
    for profile, definition in _weights().items():
        for threat in definition["applies_to"]:
            assert threat not in seen, (
                f"'{threat}' masuk profil '{seen[threat]}' dan '{profile}' sekaligus"
            )
            seen[threat] = profile

    taxonomy = yaml.safe_load((REPO_ROOT / "config" / "taxonomy" / "mappings.yaml").read_text())
    declared = set(taxonomy["mappings"]["incident_type"].values())

    # Setiap jenis pada taksonomi harus punya cara menilainya; tanpa itu ia tidak akan
    # pernah menghasilkan risk score sama sekali, dan ketiadaannya sulit disadari.
    assert declared == set(seen), (
        f"jenis tanpa profil penilaian: {sorted(declared - set(seen))}; "
        f"profil menyebut jenis yang tidak ada di taksonomi: {sorted(set(seen) - declared)}"
    )


def test_the_check_would_catch_an_unbalanced_profile() -> None:
    """Tanpa ini, pemeriksaan di atas dapat lulus karena pemeriksanya sendiri rusak."""
    broken = {"a": 0.25, "b": 0.20, "c": 0.18, "d": 0.12, "e": 0.10, "f": 0.08, "g": 0.00}
    assert not math.isclose(sum(broken.values()), 1.0, abs_tol=1e-9)
    assert math.isclose(sum(broken.values()), 0.93, abs_tol=1e-9)
