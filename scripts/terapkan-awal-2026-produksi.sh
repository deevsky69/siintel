#!/usr/bin/env bash
#
# Memindahkan PRODUKSI ke "awal 2026" — keputusan pemilik proyek 4 Oktober 2026:
# layar hanya memuat kejadian sampai 31 Desember 2025, jam acuan 1 Januari 2026, dan
# mesin penilaian/prediksi dijalankan dari posisi itu. Kejadian 2026 tetap tersimpan
# untuk pencocokan rencana patroli dan evaluasi mundur.
#
# Prasyarat: data asli sudah diterapkan (scripts/terapkan-data-asli-produksi.sh).
#
#   1. .env.production: DEMO_REFERENCE_TIME=2026-01-01T00:00:00+07:00, DISPLAY_DATA_UNTIL=2025-12-31
#   2. bangun ulang image, nyalakan ulang stack
#   3. hapus penjalanan 29 September 2026 (skor, prediksi, peringatan, rekomendasi) —
#      ia dihitung dari posisi data September dan tidak lagi sesuai jam acuan
#   4. penilaian risiko + prediksi 24H + publikasi massal pada posisi 1 Januari 2026
#   5. pnpm prod:periksa
#
# Pemakaian: bash scripts/terapkan-awal-2026-produksi.sh [--yakin]
# Tidak ada kata sandi di berkas ini (dibaca dari ~/siintel-demo-passwords.txt, tidak dicetak).

set -euo pipefail

YAKIN=0
[ "${1:-}" = "--yakin" ] && YAKIN=1

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
BASE="${BASE:-https://siintel.awansurya.com}"
ENV_FILE="$ROOT/.env.production"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f infra/docker/docker-compose.prod.yml -f infra/docker/docker-compose.coolify.yml)
API=predpol-prod-api
DB=predpol-prod-db
REFERENCE_TIME="2026-01-01T00:00:00+07:00"
DISPLAY_UNTIL="2025-12-31"
OLD_RUN_DATE="2026-09-29"

langkah() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }
setenv() {
  if grep -q "^$1=" "$ENV_FILE"; then sed -i "s|^$1=.*|$1=$2|" "$ENV_FILE"; else echo "$1=$2" >> "$ENV_FILE"; fi
  grep "^$1=" "$ENV_FILE"
}

langkah "1. Jam acuan dan batas tampilan"
[ -f "$ENV_FILE" ] || { echo ".env.production tidak ada"; exit 1; }
setenv DEMO_REFERENCE_TIME "$REFERENCE_TIME"
setenv DISPLAY_DATA_UNTIL "$DISPLAY_UNTIL"

langkah "2. Bangun ulang image dan nyalakan ulang stack"
"${COMPOSE[@]}" build
"${COMPOSE[@]}" up -d
for _ in $(seq 1 60); do
  [ "$(docker inspect -f '{{.State.Health.Status}}' "$API" 2>/dev/null)" = "healthy" ] && break
  sleep 5
done
docker inspect -f '{{.State.Health.Status}}' "$API"
docker exec "$API" alembic current

langkah "3. Hapus penjalanan $OLD_RUN_DATE"
if [ "$YAKIN" != "1" ]; then
  if [ ! -t 0 ]; then echo "Tidak ada terminal; jalankan ulang dengan --yakin."; exit 1; fi
  read -r -p "Hapus skor/prediksi/peringatan/rekomendasi penjalanan $OLD_RUN_DATE? Ketik LANJUT: " jawab
  [ "$jawab" = "LANJUT" ] || { echo "Dibatalkan."; exit 1; }
fi
docker exec -i "$DB" sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<SQL
begin;
delete from commander_decisions where recommendation_id in (
  select recommendation_id from recommendations where prediction_id in (
    select prediction_id from predictions where prediction_date = '$OLD_RUN_DATE'));
delete from recommendations where prediction_id in (
  select prediction_id from predictions where prediction_date = '$OLD_RUN_DATE');
delete from public_alerts where warning_id in (
  select warning_id from early_warnings where prediction_id in (
    select prediction_id from predictions where prediction_date = '$OLD_RUN_DATE'));
delete from early_warnings where prediction_id in (
  select prediction_id from predictions where prediction_date = '$OLD_RUN_DATE');
delete from predictions where prediction_date = '$OLD_RUN_DATE';
delete from risk_scores where assessment_date = '$OLD_RUN_DATE';
-- Evaluasi mundur untuk hari sasaran 1–2 Januari 2026 dilepas: tanggal prediksinya
-- (31 Des 2025 / 1 Jan 2026) bertabrakan dengan penjalanan langsung pada posisi
-- 1 Januari 2026. Periode evaluasi menjadi 3 Januari – 28 September 2026.
delete from prediction_actual where prediction_id in (
  select prediction_id from predictions where status = 'VALIDATED' and prediction_date <= '2026-01-01');
delete from prediction_actual where prediction_id is null and evaluation_date <= '2026-01-02';
delete from predictions where status = 'VALIDATED' and prediction_date <= '2026-01-01';
commit;
SQL

langkah "4. Mesin pada posisi $REFERENCE_TIME"
PASSFILE="$HOME/siintel-demo-passwords.txt"
ADMIN_PASS="$(awk '$1=="demo.admin"{print $2}' "$PASSFILE")"
[ -n "$ADMIN_PASS" ] || { echo "kata sandi demo.admin tidak ditemukan di $PASSFILE"; exit 1; }
TOKEN="$(curl -sf -X POST "$BASE/api/v1/auth/login" -H 'content-type: application/json' \
  --data-binary "$(python3 -c 'import json,sys;print(json.dumps({"username":"demo.admin","password":sys.argv[1]}))' "$ADMIN_PASS")" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')"
unset ADMIN_PASS
AUTH=(-H "Authorization: Bearer $TOKEN" -H 'content-type: application/json')
curl -sf -X POST "$BASE/api/v1/risk-scores/run" "${AUTH[@]}" -d '{"dry_run":false}' | python3 -c 'import sys,json;d=json.load(sys.stdin);print("risk_scores", d["assessment_date"], "ditulis:", d["written"])'
curl -sf -X POST "$BASE/api/v1/predictions/run" "${AUTH[@]}" -d '{"horizon":"24H","dry_run":false}' | python3 -c 'import sys,json;d=json.load(sys.stdin);print("predictions", d["prediction_date"], "ditulis:", d["written"])'
curl -sf -X POST "$BASE/api/v1/predictions/publish-run" "${AUTH[@]}" -d '{"prediction_date":"2026-01-01","horizon":"24H","dry_run":false}' | python3 -c 'import sys,json;d=json.load(sys.stdin);print("dipublikasikan:",d["published"],"peringatan:",d["issuance"]["warnings_issued"])'
curl -sf "$BASE/api/v1/patrol-plan/evaluation" "${AUTH[@]}" | python3 -c 'import sys,json;d=json.load(sys.stdin);print("rencana patroli:", d["overall"])'
unset TOKEN

langkah "5. Pemeriksaan produksi"
bash scripts/periksa-produksi.sh "$BASE"
