#!/usr/bin/env bash
#
# Potret keadaan produksi yang hanya terlihat SETELAH masuk: jam acuan, batas tampilan,
# tanggal penilaian terakhir, jumlah prediksi/peringatan, dan angka rencana patroli.
# Baca-saja. Kata sandi demo.admin dibaca dari ~/siintel-demo-passwords.txt dan tidak dicetak.
#
# Pakai: bash scripts/status-produksi.sh [https://alamat]

set -euo pipefail
BASE="${1:-https://siintel.awansurya.com}"
PASSFILE="$HOME/siintel-demo-passwords.txt"
ADMIN_PASS="$(awk '$1=="demo.admin"{print $2}' "$PASSFILE")"
[ -n "$ADMIN_PASS" ] || { echo "kata sandi demo.admin tidak ditemukan di $PASSFILE"; exit 1; }
TOKEN="$(curl -sf -X POST "$BASE/api/v1/auth/login" -H 'content-type: application/json' \
  --data-binary "$(python3 -c 'import json,sys;print(json.dumps({"username":"demo.admin","password":sys.argv[1]}))' "$ADMIN_PASS")" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')"
unset ADMIN_PASS
AUTH=(-H "Authorization: Bearer $TOKEN")

echo "Memeriksa $BASE"
curl -sf "$BASE/api/v1/health" | python3 -c 'import sys,json;d=json.load(sys.stdin);print("skema:", d["database"]["migration"])'
curl -sf "$BASE/api/v1/dashboard/summary" "${AUTH[@]}" | python3 -c '
import sys,json;d=json.load(sys.stdin)
print("jam acuan:", d.get("reference_time"), "| tanggal penilaian terakhir:", d.get("assessment_date"))'
curl -sf "$BASE/api/v1/analytics/trend" "${AUTH[@]}" | python3 -c '
import sys,json;d=json.load(sys.stdin);s=d["source"]
print("kejadian yang tampil:", s["incidents"], "|", s["date_from"], "s.d.", s["date_to"])'
curl -sf "$BASE/api/v1/predictions?page_size=1&status=PUBLISHED" "${AUTH[@]}" | python3 -c '
import sys,json;d=json.load(sys.stdin);r=d["data"][0] if d["data"] else {}
print("prediksi PUBLISHED:", d["pagination"]["total_items"], "| terbaru:", r.get("prediction_date"), r.get("forecast_horizon"))'
curl -sf "$BASE/api/v1/warnings?page_size=1&status=ACTIVE" "${AUTH[@]}" | python3 -c '
import sys,json;d=json.load(sys.stdin);print("peringatan ACTIVE:", d["pagination"]["total_items"])'
curl -sf "$BASE/api/v1/evaluation/metrics" "${AUTH[@]}" | python3 -c '
import sys,json;d=json.load(sys.stdin)
print("evaluasi mundur:", d.get("evaluated_from"), "s.d.", d.get("evaluated_to"), "| precision", d.get("precision"), "recall", d.get("recall"))'
curl -sf "$BASE/api/v1/patrol-plan/evaluation" "${AUTH[@]}" | python3 -c '
import sys,json;d=json.load(sys.stdin);o=d["overall"]
print("rencana patroli", d["target_year"], "| pola jam", o["hour_similarity_percent"], "% | pola wilayah", o["area_similarity_percent"], "% | ketepatan slot", o["slot_hit_rate_percent"], "% | cakupan", o["coverage_percent"], "%")'
unset TOKEN
