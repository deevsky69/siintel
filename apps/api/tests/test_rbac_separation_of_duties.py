"""Pemisahan kewenangan yang menopang klaim Taskap.

Dua pertanyaan yang paling mungkin diajukan penguji, dan jawabannya harus dijaga kode —
bukan hanya tertulis di dokumen:

    "Siapa yang memutuskan tindakan?"        -> Pimpinan, dan hanya Pimpinan.
    "Siapa yang memverifikasi ketepatannya?" -> Pimpinan, bukan yang menghasilkan angkanya.

Keduanya rapuh terhadap perubahan yang tampak tidak berbahaya. Menggabungkan peran,
menambah satu permission ke peran administratif, atau menyalin daftar kewenangan dari
peran lain — semuanya dapat meruntuhkannya tanpa satu pun test lain gagal, sebab
aplikasinya tetap berjalan sempurna.

Test ini pernah dibutuhkan: pada 1 September 2026 tiga peran digabung menjadi
Administrator, dan `evaluation:run` sempat ikut terkumpul di peran yang juga menulis
data kejadian, menjalankan prediksi, dan mencatat hasil operasi.
"""

from __future__ import annotations

from typing import Any

import yaml

from prediksi_presisi_api.seeding.paths import RBAC_FILE

#: Kewenangan yang **menghasilkan** angka yang kelak dinilai.
PRODUCES_THE_NUMBERS = frozenset(
    {
        "crime:write",  # data kejadian, bahan seluruh penilaian
        "risk_score:run",  # skor risiko
        "prediction:run",  # prediksi
        "prediction:publish",  # menerbitkan prediksi yang akan dievaluasi
        "operation:write",  # hasil nyata di lapangan, pembanding prediksi
    }
)

#: Kewenangan yang **menilai** angka itu.
JUDGES_THE_NUMBERS = "evaluation:run"

#: Kewenangan memutuskan tindakan operasional.
DECIDES = "commander_decision:approve"


def _roles() -> dict[str, dict[str, list[str]]]:
    catalogue: dict[str, Any] = yaml.safe_load(RBAC_FILE.read_text())
    roles: dict[str, dict[str, list[str]]] = catalogue["roles"]
    return roles


def _granted(grants: dict[str, list[str]]) -> set[str]:
    return {permission for perms in grants.values() for permission in perms}


def _holders(permission: str) -> list[str]:
    return sorted(role for role, grants in _roles().items() if permission in _granted(grants))


def test_only_one_role_may_approve_recommendations() -> None:
    """Inti rantai human-in-the-loop: yang mengusulkan bukan yang memutuskan."""
    assert _holders(DECIDES) == ["Pimpinan"], (
        f"`{DECIDES}` dipegang {_holders(DECIDES)}. Bila lebih dari satu peran dapat "
        f"memutuskan, pertanggungjawaban keputusan operasional menjadi kabur."
    )


def test_nobody_evaluates_the_numbers_they_produced() -> None:
    """Yang menghasilkan angka tidak boleh menjadi yang menilai ketepatannya.

    Inilah yang membuat precision dan recall bermakna sebagai ukuran independen. Bila
    satu peran memegang keduanya, angka validasi Taskap dinilai oleh pihak yang
    berkepentingan atas hasilnya — dan penguji berhak menolaknya.
    """
    offenders = {
        role: sorted(PRODUCES_THE_NUMBERS & _granted(grants))
        for role, grants in _roles().items()
        if JUDGES_THE_NUMBERS in _granted(grants) and PRODUCES_THE_NUMBERS & _granted(grants)
    }

    assert not offenders, (
        f"peran berikut memegang `{JUDGES_THE_NUMBERS}` sekaligus kewenangan yang "
        f"menghasilkan angkanya: {offenders}"
    )


def test_the_evaluator_is_the_one_who_relies_on_the_measurement() -> None:
    """`evaluation:run` berada di Pimpinan, bukan di peran administratif.

    Yang bergantung pada alat ukur adalah yang memerintahkan pengukurannya. Menaruhnya
    di peran administratif membuat evaluasi menjadi pekerjaan teknis internal, bukan
    pemeriksaan atas alat yang dipakai mengambil keputusan.
    """
    assert _holders(JUDGES_THE_NUMBERS) == ["Pimpinan"]


def test_the_check_would_catch_a_regression() -> None:
    """Tanpa ini, pemeriksaan di atas dapat lulus karena daftarnya sendiri kosong."""
    assert PRODUCES_THE_NUMBERS
    assert JUDGES_THE_NUMBERS not in PRODUCES_THE_NUMBERS

    # Susunan yang dahulu berlaku dan tidak boleh kembali tanpa disadari: satu peran
    # memegang penulisan data, penjalanan prediksi, dan evaluasinya sekaligus.
    previously_merged = {"crime:write", "prediction:run", JUDGES_THE_NUMBERS}
    assert PRODUCES_THE_NUMBERS & previously_merged, (
        "daftar kewenangan penghasil angka tidak lagi mencakup yang dahulu bermasalah"
    )


def test_publishing_to_the_public_is_a_command_decision_not_a_technical_one() -> None:
    """`public_alert:publish` ada pada Pimpinan, dan TIDAK pada Administrator (U-10).

    Sampai 9 September 2026 permission ini ada di katalog tetapi tidak dipegang satu peran
    pun: katalog menyatakan sebuah kewenangan yang tidak berlaku bagi siapa-siapa, dan
    kanal peringatan kepada masyarakat tidak dapat dijalankan siapa pun. Tidak ada test
    yang gagal karenanya — permission yatim tidak menimbulkan gejala apa-apa.

    Ia diletakkan pada Pimpinan karena mengumumkan peringatan kepada masyarakat mengubah
    perilaku orang di luar organisasi dan tidak dapat ditarik kembali setelah terbaca.
    Administrator — peran yang menjalankan prediksi — karenanya kekurangan tepat tiga
    permission, dan ketiganya keputusan komando: memutuskan tindakan, menilai ketepatan,
    dan mengumumkan kepada publik.
    """
    roles = yaml.safe_load(RBAC_FILE.read_text(encoding="utf-8"))["roles"]
    holders = {
        name
        for name, scopes in roles.items()
        for entries in scopes.values()
        if "public_alert:publish" in entries
    }

    assert holders == {"Pimpinan"}, (
        f"pemegang public_alert:publish: {sorted(holders) or 'tidak ada'}"
    )


def test_the_three_permissions_administrator_lacks_are_all_command_decisions() -> None:
    """Yang menjalankan prediksi tidak memutuskan, tidak menilai, dan tidak mengumumkan."""
    config = yaml.safe_load(RBAC_FILE.read_text(encoding="utf-8"))
    catalogue = {
        f"{resource}:{action}"
        for resource, actions in config["permissions"].items()
        for action in actions
    }
    admin = {entry for entries in config["roles"]["Administrator"].values() for entry in entries}

    assert catalogue - admin == {
        "commander_decision:approve",
        "evaluation:run",
        "public_alert:publish",
    }
