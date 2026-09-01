"""CLI seed: `uv run python -m prediksi_presisi_api.seeding <perintah>`.

Perintah:
  master   Memuat locations, police_units, roles, permissions, role_permissions, users (TASK 020)
  crime    Memuat crime_incidents, intelligence_reports, patrol_activity (TASK 021)
  all      Menjalankan seluruh perintah di atas secara berurutan

Seluruh perintah berjalan dalam satu transaksi: bila ada satu baris yang melanggar
integritas, tidak ada yang tersimpan (fail-fast, docs/08 PHASE 3).
"""

from __future__ import annotations

import argparse
import sys

from ..db import get_session_factory
from .crime import seed_crime_data
from .errors import SeedError
from .master import SeedSummary, seed_master_data
from .taxonomy import load_taxonomy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="seeding", description="Memuat data dummy PREDIKSI PRESISI"
    )
    parser.add_argument(
        "command", choices=["master", "crime", "all"], help="kelompok data yang dimuat"
    )
    arguments = parser.parse_args(argv)

    taxonomy = load_taxonomy()
    print(f"Taksonomi: versi {taxonomy.version}")

    summary = SeedSummary()
    try:
        with get_session_factory()() as session, session.begin():
            if arguments.command in {"master", "all"}:
                summary.merge(seed_master_data(session, taxonomy))
            if arguments.command in {"crime", "all"}:
                summary.merge(seed_crime_data(session, taxonomy))
    except SeedError as error:
        print(f"\nSEED DIHENTIKAN: {error}", file=sys.stderr)
        return 1

    print("\nHasil:")
    for line in summary.as_lines():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
