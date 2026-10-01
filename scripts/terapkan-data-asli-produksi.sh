#!/usr/bin/env bash
#
# Menerapkan data asli Pusiknas ke PRODUKSI (siintel.awansurya.com) — Fase 5.
#
# Dijalankan DI SERVER oleh orang yang memegang persetujuan pemilik proyek 30 September
# 2026 ("ganti seluruh data menjadi data asli; hapus ketujuh tabel sintetis"). Skrip ini
# sengaja berhenti pada tiap langkah yang tidak dapat dibatalkan dan meminta ketikan
# "LANJUT" — bukan karena langkahnya rumit, melainkan karena ia menghapus data produksi.
#
# Urutannya mengikuti CLAUDE.md §20 (migration -> apply -> test) dan §17/§18:
#
#   0. prasyarat: data/raw/*.xlsx ada, data/processed/ dibangun ulang dari impor
#   1. cadangan DB produksi (pg_dump) ke ~/siintel-cadangan/
#   2. bangun ulang image API + web dari kode terbaru
#   3. nyalakan ulang stack; migrasi ke 0010 (alembic upgrade head) di dalam container API
#   4. kosongkan tabel sintetis dan turunannya (urutan FK), sisakan master + users + audit
#   5. seed --source processed (kejadian asli + lokasi kelurahan)
#   6. jalankan penilaian risiko, prediksi 24H, publikasi massal, evaluasi mundur
#   7. pnpm prod:periksa
#
# Tidak ada kata sandi di berkas ini. Kata sandi akun demo produksi dibaca dari
# ~/siintel-demo-passwords.txt (mode 600) hanya untuk login API pada langkah 6, dan tidak
# pernah dicetak.

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
BASE="${BASE:-https://siintel.awansurya.com}"
ENV_FILE="$ROOT/.env.production"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f infra/docker/docker-compose.prod.yml -f infra/docker/docker-compose.coolify.yml)
API=predpol-prod-api
DB=predpol-prod-db
REFERENCE_TIME="2026-09-29T00:00:00+07:00"
BACKTEST_FROM="2026-01-01"
BACKTEST_TO="2026-09-28"

konfirmasi() {
  echo
  echo ">>> $1"
  read -r -p "Ketik LANJUT untuk meneruskan: " jawab
  [ "$jawab" = "LANJUT" ] || { echo "Dibatalkan."; exit 1; }
}

langkah() { printf '\n\033[1m== %s ==\033[0m\n' "$1"; }

# ---------------------------------------------------------------------------
langkah "0. Prasyarat"
[ -f "$ENV_FILE" ] || { echo ".env.production tidak ada"; exit 1; }
ls data/raw/*.xlsx >/dev/null 2>&1 || { echo "data/raw/*.xlsx tidak ada — unduh berkas resmi ke data/raw/ lebih dahulu"; exit 1; }
(cd apps/api && uv run --group analysis python ../../scripts/import/pusiknas.py)
[ -f data/processed/crime_incidents.csv ] || { echo "impor tidak menghasilkan data/processed/crime_incidents.csv"; exit 1; }
python3 - <<'PY'
import json; m = json.load(open("data/processed/MANIFEST.json")); print("MANIFEST:", {k: m[k] for k in ("incidents", "locations", "position") if k in m})
PY

# ---------------------------------------------------------------------------
langkah "1. Cadangan DB produksi"
mkdir -p "$HOME/siintel-cadangan"
CADANGAN="$HOME/siintel-cadangan/predpol-prod-$(date +%Y%m%d-%H%M%S).sql.gz"
docker exec "$DB" sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | gzip > "$CADANGAN"
chmod 600 "$CADANGAN"
echo "cadangan: $CADANGAN ($(du -h "$CADANGAN" | cut -f1))"

# ---------------------------------------------------------------------------
langkah "2. Jam acuan produksi -> posisi data ($REFERENCE_TIME)"
if grep -q '^DEMO_REFERENCE_TIME=' "$ENV_FILE"; then
  sed -i "s|^DEMO_REFERENCE_TIME=.*|DEMO_REFERENCE_TIME=$REFERENCE_TIME|" "$ENV_FILE"
else
  echo "DEMO_REFERENCE_TIME=$REFERENCE_TIME" >> "$ENV_FILE"
fi
grep '^DEMO_REFERENCE_TIME=' "$ENV_FILE"

langkah "3. Bangun ulang image dan nyalakan ulang stack"
"${COMPOSE[@]}" build
"${COMPOSE[@]}" up -d
echo "menunggu API sehat..."
for _ in $(seq 1 60); do
  if [ "$(docker inspect -f '{{.State.Health.Status}}' "$API" 2>/dev/null)" = "healthy" ]; then break; fi
  sleep 5
done
docker inspect -f '{{.State.Health.Status}}' "$API"

langkah "4. Migrasi skema (alembic upgrade head)"
docker exec "$API" alembic upgrade head
docker exec "$API" alembic current

# ---------------------------------------------------------------------------
konfirmasi "Langkah berikut MENGHAPUS seluruh data sintetis di produksi (kejadian, lokasi grid, dan ketujuh tabel sintetis beserta turunannya). Cadangan ada di $CADANGAN."
langkah "5. Kosongkan tabel sintetis (urutan FK)"
docker exec -i "$DB" sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
begin;
-- turunan paling ujung lebih dahulu
delete from operational_actions;
delete from commander_decisions;
delete from public_alerts;
delete from community_feedback;
delete from citizen_report_attachments;
delete from citizen_reports;
delete from recommendations;
delete from early_warnings;
delete from prediction_actual;
delete from predictions;
delete from risk_scores;
delete from intelligence_reports;
delete from patrol_activity;
delete from crime_incidents;
delete from police_units;
delete from locations;
commit;
SQL

langkah "6. Seed data asli (--source processed)"
docker exec "$API" python -m prediksi_presisi_api.seeding --source processed all

# ---------------------------------------------------------------------------
langkah "7. Mesin: penilaian risiko, prediksi 24H, publikasi, evaluasi mundur"
PASSFILE="$HOME/siintel-demo-passwords.txt"
[ -r "$PASSFILE" ] || { echo "$PASSFILE tidak dapat dibaca; jalankan langkah 7 secara manual"; exit 1; }
ADMIN_PASS="$(awk '$1=="demo.admin"{print $2}' "$PASSFILE")"
[ -n "$ADMIN_PASS" ] || { echo "kata sandi demo.admin tidak ditemukan di $PASSFILE"; exit 1; }
TOKEN="$(curl -sf -X POST "$BASE/api/v1/auth/login" -H 'content-type: application/json' \
  --data-binary "$(python3 -c 'import json,sys;print(json.dumps({"username":"demo.admin","password":sys.argv[1]}))' "$ADMIN_PASS")" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')"
unset ADMIN_PASS
AUTH=(-H "Authorization: Bearer $TOKEN" -H 'content-type: application/json')
curl -sf -X POST "$BASE/api/v1/risk-scores/run" "${AUTH[@]}" -d '{"assessment_date":"2026-09-29","dry_run":false}' | python3 -c 'import sys,json;d=json.load(sys.stdin);print("risk_scores ditulis:",d["written"])'
curl -sf -X POST "$BASE/api/v1/predictions/run" "${AUTH[@]}" -d '{"prediction_date":"2026-09-29","horizon":"24H","dry_run":false}' | python3 -c 'import sys,json;d=json.load(sys.stdin);print("predictions ditulis:",d["written"])'
curl -sf -X POST "$BASE/api/v1/predictions/publish-run" "${AUTH[@]}" -d '{"prediction_date":"2026-09-29","horizon":"24H","dry_run":false}' | python3 -c 'import sys,json;d=json.load(sys.stdin);print("dipublikasikan:",d["published"],"peringatan:",d["issuance"]["warnings_issued"])'
unset TOKEN
docker exec "$API" python -m prediksi_presisi_api.cli backtest --dari "$BACKTEST_FROM" --sampai "$BACKTEST_TO" \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print({k:d[k] for k in ("predictions","hits","false_positives","false_negatives","unevaluable_incidents","precision","recall")})'

# ---------------------------------------------------------------------------
langkah "8. Pemeriksaan produksi"
bash scripts/periksa-produksi.sh "$BASE"
echo
echo "Selesai. Cadangan sebelum perubahan: $CADANGAN"
