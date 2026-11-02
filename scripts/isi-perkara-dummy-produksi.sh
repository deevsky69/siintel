#!/usr/bin/env bash
# Menanam berkas perkara DUMMY berlabel ke produksi untuk peragaan lacak laporan dan cek
# kendaraan (keputusan pemilik proyek 2 November 2026: "mulai dengan data dummy, beri label").
# Idempoten — aman dijalankan berulang. Mencetak contoh nomor LP + PIN untuk dicoba.
#
#   bash scripts/isi-perkara-dummy-produksi.sh
set -euo pipefail
docker exec predpol-prod-api python -m prediksi_presisi_api.cli seed-case-files-dummy
