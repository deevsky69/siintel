"""Pemetaan nilai taksonomi dari `config/taxonomy/mappings.yaml`.

Pemetaannya berada di konfigurasi, bukan di kode maupun di ENUM database. Nilai yang tidak
dikenal **menghentikan seed** alih-alih diterima apa adanya — nilai asing yang lolos akan
menjadi taksonomi bayangan yang tidak pernah disetujui siapa pun.

Taksonomi ditetapkan pemilik proyek 9 September 2026 (U-16). Penetapan itu tidak membuat
pemetaannya boleh pindah ke kode: justru sebaliknya, menambah nilai baru kini menuntut
versi baru pada konfigurasi, bukan penyuntingan diam-diam.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import SeedError
from .paths import TAXONOMY_FILE


@dataclass(frozen=True)
class Taxonomy:
    """Pemetaan nilai per domain, mis. `status_crime` atau `risk_class`."""

    version: str
    #: Status penetapan versi ini — `FINAL` atau `PROPOSED`. Dibawa keluar apa adanya
    #: supaya layar tidak perlu menuliskannya sendiri dan kemudian menyimpang darinya.
    status: str
    mappings: dict[str, dict[str, str]]
    labels: dict[str, dict[str, str]]

    def map(self, domain: str, raw: str | None) -> str | None:
        """Memetakan satu nilai. `None`/kosong tetap `None`."""
        if raw is None or raw.strip() == "":
            return None

        table = self.mappings.get(domain)
        if table is None:
            message = f"domain taksonomi '{domain}' tidak ada di {TAXONOMY_FILE.name}"
            raise SeedError(message)

        value = raw.strip()
        if value in table:
            return table[value]

        # Nilai yang sudah berbentuk enum tersimpan diterima apa adanya.
        if value in set(table.values()):
            return value

        message = (
            f"nilai '{raw}' tidak dikenal pada domain '{domain}'. "
            f"Tambahkan pemetaannya di config/taxonomy/mappings.yaml "
            f"atau perbaiki data sumbernya. Nilai yang dikenal: {sorted(table)}"
        )
        raise SeedError(message)

    def require(self, domain: str, raw: str | None) -> str:
        """Seperti `map`, tetapi nilai kosong dianggap kesalahan."""
        mapped = self.map(domain, raw)
        if mapped is None:
            message = f"nilai wajib pada domain '{domain}' kosong"
            raise SeedError(message)
        return mapped


def load_taxonomy(path: Path | None = None) -> Taxonomy:
    """Memuat pemetaan taksonomi dari konfigurasi."""
    source = path or TAXONOMY_FILE
    if not source.exists():
        message = f"berkas taksonomi tidak ditemukan: {source}"
        raise SeedError(message)

    raw: dict[str, Any] = yaml.safe_load(source.read_text(encoding="utf-8"))

    return Taxonomy(
        version=str(raw.get("version", "unknown")),
        status=str(raw.get("status", "PROPOSED")),
        mappings={k: dict(v) for k, v in (raw.get("mappings") or {}).items()},
        labels={k: dict(v) for k, v in (raw.get("labels") or {}).items()},
    )
