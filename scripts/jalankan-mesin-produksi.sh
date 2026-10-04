#!/usr/bin/env bash
#
# Menjalankan mesin di PRODUKSI pada jam acuan yang berlaku: penilaian risiko, prediksi
# 24H, publikasi massal (yang melahirkan peringatan + rekomendasi), lalu pemeriksaan.
# Aman diulang: bila penilaian/prediksi untuk tanggal itu sudah ada, API menjawab 409 dan
# skrip melanjutkan ke langkah berikutnya.
#
# Pakai: bash scripts/jalankan-mesin-produksi.sh [https://alamat]
# Kata sandi demo.admin dibaca dari ~/siintel-demo-passwords.txt (baris: demo.admin<spasi>sandi).

set -uo pipefail
BASE="${1:-https://siintel.awansurya.com}"
PASSFILE="$HOME/siintel-demo-passwords.txt"

[ -r "$PASSFILE" ] || { echo "GAGAL: $PASSFILE tidak dapat dibaca."; exit 1; }
ADMIN_PASS="$(awk '$1=="demo.admin"{print $2}' "$PASSFILE")"
if [ -z "$ADMIN_PASS" ]; then
  echo "GAGAL: baris 'demo.admin <sandi>' tidak ada di $PASSFILE."
  echo "Tetapkan dulu: pnpm prod:password -- demo.admin, lalu tambahkan barisnya ke berkas itu."
  exit 1
fi
LOGIN="$(curl -s -X POST "$BASE/api/v1/auth/login" -H 'content-type: application/json' \
  --data-binary "$(python3 -c 'import json,sys;print(json.dumps({"username":"demo.admin","password":sys.argv[1]}))' "$ADMIN_PASS")")"
unset ADMIN_PASS
TOKEN="$(printf '%s' "$LOGIN" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')"
if [ -z "$TOKEN" ]; then
  echo "GAGAL masuk sebagai demo.admin:"; printf '%s\n' "$LOGIN" | python3 -c 'import sys,json;print(json.load(sys.stdin).get("error",{}).get("message"))'
  exit 1
fi
AUTH=(-H "Authorization: Bearer $TOKEN" -H 'content-type: application/json')

tampil() { python3 -c '
import sys,json;d=json.load(sys.stdin)
if "error" in d: print("  ->", d["error"]["code"], d["error"]["message"][:160])
else: print("  ->", {k:d[k] for k in sys.argv[1:] if k in d})' "$@"; }

echo "1. Penilaian risiko (tanggal = jam acuan)"
curl -s -X POST "$BASE/api/v1/risk-scores/run" "${AUTH[@]}" -d '{"dry_run":false}' | tampil assessment_date written existing_rows
echo "2. Prediksi 24H"
RUN="$(curl -s -X POST "$BASE/api/v1/predictions/run" "${AUTH[@]}" -d '{"horizon":"24H","dry_run":false}')"
printf '%s' "$RUN" | tampil prediction_date target_date written existing_rows
PRED_DATE="$(printf '%s' "$RUN" | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d.get("prediction_date") or "")')"
if [ -z "$PRED_DATE" ]; then
  PRED_DATE="$(curl -s "$BASE/api/v1/dashboard/summary" "${AUTH[@]}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["reference_time"][:10])')"
fi
echo "3. Publikasi massal penjalanan $PRED_DATE/24H"
curl -s -X POST "$BASE/api/v1/predictions/publish-run" "${AUTH[@]}" -d "{\"prediction_date\":\"$PRED_DATE\",\"horizon\":\"24H\",\"dry_run\":false}" | python3 -c '
import sys,json;d=json.load(sys.stdin)
if "error" in d: print("  ->", d["error"]["code"], d["error"]["message"][:160])
else: print("  -> dipublikasikan:", d["published"], "| peringatan:", d["issuance"]["warnings_issued"], "| rekomendasi:", d["issuance"]["recommendations_issued"])'
unset TOKEN

echo "4. Pemeriksaan"
bash "$(dirname "$0")/periksa-produksi.sh" "$BASE"
bash "$(dirname "$0")/status-produksi.sh" "$BASE"
