#!/usr/bin/env python3
"""Menyusun matriks role → permission pada `docs/03` §3 dari `config/rbac/permissions.yaml`.

Matriks itu sebelumnya ditulis tangan, dan pada 9 September 2026 ia sudah menyimpang jauh:
ia masih memuat kolom Command Center dan Analyst — dua peran yang dihapus 1 September 2026
— serta memberi Administrator hanya `read` pada hampir semua resource, padahal peran itu
sesungguhnya memegang 40 dari 43 permission. Dokumen yang bertentangan dengan konfigurasi
yang benar-benar dijalankan lebih berbahaya daripada dokumen yang tidak ada, karena ia
tetap dibaca sebagai kebenaran.

Jalankan setiap kali `config/rbac/permissions.yaml` berubah:

    python3 scripts/matriks-rbac.py            # cetak ke layar
    python3 scripts/matriks-rbac.py --tulis    # tulis langsung ke docs/03 §3

Berkas ini hanya MEMBACA konfigurasi. Ia tidak pernah menjadi sumber kewenangan.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "rbac" / "permissions.yaml"
DOC = ROOT / "docs" / "03-role-permission-matrix.md"

AWAL = "<!-- matriks:mulai -->"
AKHIR = "<!-- matriks:selesai -->"


def bangun() -> tuple[str, dict[str, int]]:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    permissions: dict[str, list[str]] = config["permissions"]
    roles: dict[str, dict[str, list[str]]] = config["roles"]

    # resource -> role -> scope -> action
    granted: dict[str, dict[str, dict[str, list[str]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    for role, scopes in roles.items():
        for scope, entries in scopes.items():
            for entry in entries:
                resource, action = entry.split(":", 1)
                if action not in permissions.get(resource, []):
                    message = f"{role}/{scope}: '{entry}' tidak ada di katalog permission"
                    raise SystemExit(message)
                granted[resource][role][scope].append(action)

    def cell(resource: str, role: str) -> str:
        per_scope = granted[resource].get(role)
        if not per_scope:
            return "—"
        # Urutan action mengikuti katalog, bukan urutan penulisan di YAML: matriks yang
        # urutannya berpindah-pindah membuat diff dokumen mustahil dibaca.
        return " · ".join(
            f"{', '.join(a for a in permissions[resource] if a in actions)}({scope})"
            for scope, actions in per_scope.items()
        )

    names = list(roles)
    baris = [
        "| Resource | " + " | ".join(names) + " |",
        "|---" * (len(names) + 1) + "|",
    ]
    baris += [
        f"| {resource} | " + " | ".join(cell(resource, role) for role in names) + " |"
        for resource in permissions
    ]
    jumlah = {role: sum(len(v) for v in scopes.values()) for role, scopes in roles.items()}
    return "\n".join(baris), jumlah


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tulis", action="store_true", help="tulis langsung ke docs/03")
    args = parser.parse_args()

    tabel, jumlah = bangun()
    ringkas = ", ".join(f"{role} {n}" for role, n in jumlah.items())

    if not args.tulis:
        print(tabel)
        print()
        print(f"Jumlah permission per peran: {ringkas}.")
        return 0

    doc = DOC.read_text(encoding="utf-8")
    if AWAL not in doc or AKHIR not in doc:
        print(f"{DOC}: penanda {AWAL} / {AKHIR} tidak ditemukan", file=sys.stderr)
        return 1

    isi = f"{AWAL}\n\n{tabel}\n\nJumlah permission per peran: {ringkas}.\n\n{AKHIR}"
    doc = re.sub(re.escape(AWAL) + r".*?" + re.escape(AKHIR), isi, doc, flags=re.DOTALL)
    DOC.write_text(doc, encoding="utf-8")
    print(f"{DOC} diperbarui — {ringkas}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
