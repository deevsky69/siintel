#!/usr/bin/env bash
#
# Deploy biasa ke PRODUKSI: bangun ulang image dari kode di pohon kerja, nyalakan ulang
# stack, terapkan migration yang belum terpasang, lalu periksa.
#
# Tidak menghapus data, tidak menyentuh .env.production. Untuk perubahan data atau jam
# acuan ada skrip tersendiri (terapkan-*.sh). Pakai: bash scripts/deploy-produksi.sh

set -euo pipefail
cd "$(dirname "$0")/.."
ENV_FILE="$(pwd)/.env.production"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f infra/docker/docker-compose.prod.yml -f infra/docker/docker-compose.coolify.yml)
API=predpol-prod-api
BASE="${BASE:-https://siintel.awansurya.com}"

[ -f "$ENV_FILE" ] || { echo ".env.production tidak ada"; exit 1; }
echo "== kode: $(git rev-parse --short HEAD) $(git log -1 --format=%s | cut -c1-70)"

echo "== bangun ulang image"
"${COMPOSE[@]}" build
echo "== nyalakan ulang"
# Bot dinyalakan SETELAH migrasi (9 Oktober 2026): ia langsung memanggil /messaging/*,
# yang menuntut tabel 0013 — menyalakannya lebih dulu hanya menghasilkan galat 500 sia-sia.
"${COMPOSE[@]}" up -d db api web
for _ in $(seq 1 60); do
  [ "$(docker inspect -f '{{.State.Health.Status}}' "$API" 2>/dev/null)" = "healthy" ] && break
  sleep 5
done
docker inspect -f '{{.State.Health.Status}}' "$API"

echo "== migration"
docker exec "$API" alembic upgrade head
docker exec "$API" alembic current
echo "== bot kanal perpesanan"
"${COMPOSE[@]}" up -d bot

echo "== pemeriksaan"
# Traefik butuh beberapa detik mendaftarkan ulang rute container yang baru dibuat; tanpa
# jeda, pemeriksaan pertama gagal padahal stack sehat.
for _ in $(seq 1 12); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$BASE/api/v1/health")" = "200" ] && break
  sleep 5
done
bash scripts/periksa-produksi.sh "$BASE"
