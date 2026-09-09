"""Menjaga agar dokumen kewenangan tidak menyimpang dari konfigurasi yang dijalankan.

Pada 9 September 2026 `docs/03` §3 masih memuat kolom Command Center dan Analyst — dua
peran yang dihapus 1 September 2026 — dan `data/sample/role_permissions.csv` masih memuat
dua belas baris yang merujuk kedua peran itu. Tidak ada satu pun test yang gagal karena
keduanya: dokumen tidak diperiksa siapa pun, dan berkas dummy itu tidak lagi dibaca
seeder. Sisa seperti itu tetap dibaca manusia sebagai kebenaran.

Test di sini tidak butuh database.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
CONFIG = ROOT / "config" / "rbac" / "permissions.yaml"
DOC = ROOT / "docs" / "03-role-permission-matrix.md"
SAMPLE = ROOT / "data" / "sample"


def _roles() -> dict[str, dict[str, list[str]]]:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    roles: dict[str, dict[str, list[str]]] = config["roles"]
    return roles


def _csv_column(name: str, column: str) -> list[str]:
    rows = (SAMPLE / name).read_text(encoding="utf-8").splitlines()
    header = rows[0].split(",")
    index = header.index(column)
    return [row.split(",")[index] for row in rows[1:] if row.strip()]


def test_dummy_data_never_grants_a_role_that_does_not_exist() -> None:
    declared = set(_csv_column("roles.csv", "role_id"))

    assert set(_csv_column("role_permissions.csv", "role_id")) <= declared
    assert set(_csv_column("users.csv", "role_id")) <= declared


def test_documented_matrix_lists_exactly_the_roles_that_are_configured() -> None:
    matrix = re.search(
        r"<!-- matriks:mulai -->(.*?)<!-- matriks:selesai -->",
        DOC.read_text(encoding="utf-8"),
        re.DOTALL,
    )
    assert matrix is not None, "penanda matriks hilang dari docs/03 §3"

    header = next(line for line in matrix.group(1).splitlines() if line.startswith("| Resource"))
    columns = [cell.strip() for cell in header.strip("|").split("|")][1:]

    assert columns == list(_roles()), (
        "kolom docs/03 §3 tidak lagi sama dengan peran di config/rbac/permissions.yaml — "
        "jalankan `python3 scripts/matriks-rbac.py --tulis`"
    )


def test_documented_permission_counts_match_the_configuration() -> None:
    """Angka ringkasan paling mudah usang, dan paling sering dikutip saat paparan."""
    expected = {role: sum(len(v) for v in scopes.values()) for role, scopes in _roles().items()}
    line = re.search(r"Jumlah permission per peran: ([^.]+)\.", DOC.read_text(encoding="utf-8"))
    assert line is not None

    documented = {
        part.rsplit(" ", 1)[0]: int(part.rsplit(" ", 1)[1]) for part in line.group(1).split(", ")
    }

    assert documented == expected
