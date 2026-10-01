"""CLI seed: `uv run python -m prediksi_presisi_api.seeding <perintah>`.

Perintah:
  master   Memuat locations, police_units, roles, permissions, role_permissions, users (TASK 020)
  crime    Memuat crime_incidents, intelligence_reports, patrol_activity (TASK 021)
  analytics  Memuat risk_scores, predictions, early_warnings, recommendations (TASK 022)
  operational Memuat commander_decisions, operational_actions, prediction_actual (TASK 023)
  public   Memuat citizen_reports, public_alerts, community_feedback (TASK 024)
  regenerate Membangkitkan ulang data dummy pada data/sample (TASK 022–024)
  all      Menjalankan seluruh perintah di atas secara berurutan

Seluruh perintah berjalan dalam satu transaksi: bila ada satu baris yang melanggar
integritas, tidak ada yang tersimpan (fail-fast, docs/08 PHASE 3).
"""

from __future__ import annotations

import argparse
import sys

from ..db import get_session_factory
from . import csv_source as src
from .analytics import seed_analytics_data
from .crime import seed_crime_data
from .errors import SeedError
from .master import SeedSummary, seed_master_data
from .operational import seed_operational_data
from .paths import PROCESSED_DATA_DIR
from .public import seed_public_data
from .regenerate import regenerate, regenerate_operational, regenerate_public
from .taxonomy import load_taxonomy


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="seeding", description="Memuat data dummy PREDIKSI PRESISI"
    )
    parser.add_argument(
        "command",
        choices=["master", "crime", "analytics", "operational", "public", "all", "regenerate"],
        help="kelompok data yang dimuat",
    )
    parser.add_argument(
        "--source",
        choices=["sample", "processed"],
        default="sample",
        help=(
            "sample = data sintetis di data/sample (bawaan); processed = data ASLI hasil "
            "scripts/import/pusiknas.py di data/processed"
        ),
    )
    arguments = parser.parse_args(argv)

    # Data asli hanya menyediakan master lokasi dan kejadian. Tujuh tabel sintetis lain
    # tidak punya sumber asli dan — keputusan pemilik proyek 30 September 2026 — tidak lagi
    # dimuat: layarnya terisi dari pemakaian nyata, bukan dari karangan. Perintah yang
    # meminta kelompok itu pada sumber `processed` ditolak terang-terangan.
    if arguments.source == "processed":
        if arguments.command in {"analytics", "operational", "public", "regenerate"}:
            print(
                f"'{arguments.command}' tidak tersedia pada --source processed: kelompok data "
                "itu tidak punya sumber asli dan tidak lagi dimuat.",
                file=sys.stderr,
            )
            return 2
        if not (PROCESSED_DATA_DIR / "crime_incidents.csv").exists():
            print(
                f"{PROCESSED_DATA_DIR} belum berisi hasil impor. Jalankan dulu:\n"
                "  uv run --group analysis python ../../scripts/import/pusiknas.py",
                file=sys.stderr,
            )
            return 2
        src.use_directory(PROCESSED_DATA_DIR)
        print(f"Sumber data: ASLI ({PROCESSED_DATA_DIR})")

    if arguments.command == "regenerate":
        try:
            counts = regenerate()
            counts.update(regenerate_operational())
            # Dijalankan terakhir: imbauan publik menyalin severity, jenis ancaman, dan
            # batas jendela dari early_warnings.csv yang baru disesuaikan `regenerate()`.
            counts.update(regenerate_public())
        except SeedError as error:
            print(f"\nPEMBANGKITAN DIHENTIKAN: {error}", file=sys.stderr)
            return 1
        print("Data dummy analitik dibangkitkan ulang:")
        for name, value in counts.items():
            print(f"  {name:<22} {value}")
        return 0

    taxonomy = load_taxonomy()
    print(f"Taksonomi: versi {taxonomy.version}")

    summary = SeedSummary()
    try:
        with get_session_factory()() as session, session.begin():
            if arguments.command in {"master", "all"}:
                summary.merge(seed_master_data(session, taxonomy))
            if arguments.command in {"crime", "all"}:
                summary.merge(seed_crime_data(session, taxonomy))
            sintetis = arguments.source == "sample"
            if arguments.command in {"analytics", "all"} and sintetis:
                summary.merge(seed_analytics_data(session, taxonomy))
            if arguments.command in {"operational", "all"} and sintetis:
                summary.merge(seed_operational_data(session, taxonomy))
            # Setelah analytics: imbauan publik menunjuk early_warnings.
            if arguments.command in {"public", "all"} and sintetis:
                summary.merge(seed_public_data(session, taxonomy))
    except SeedError as error:
        print(f"\nSEED DIHENTIKAN: {error}", file=sys.stderr)
        return 1

    print("\nHasil:")
    for line in summary.as_lines():
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
