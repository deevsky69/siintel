#!/usr/bin/env bash
# Menjalankan satu putaran retensi lampiran laporan masyarakat pada tumpukan produksi.
#
# Dipanggil systemd timer `predpol-retensi.timer` setiap jam. Sengaja SETIAP JAM, bukan
# harian: masa titipan unggahan hanya 30 menit (`STAGING_TTL_MINUTES`), sehingga jadwal
# harian akan membiarkan berkas yang tidak jadi dikirim menganggur sampai 24 jam di kanal
# yang terbuka untuk umum. Pemusnahan 90 hari bersifat idempoten dan murah, jadi tidak ada
# ruginya ikut berjalan sesering itu.
set -euo pipefail

cd /home/kim/siintel

exec docker compose \
  --env-file .env.production \
  -f infra/docker/docker-compose.prod.yml \
  -f infra/docker/docker-compose.coolify.yml \
  exec -T api python -m prediksi_presisi_api.retention
