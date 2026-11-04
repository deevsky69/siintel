#!/usr/bin/env bash
# Memasangkan NOMOR CADANGAN ke sesi WAHA (kanal WhatsApp peragaan, klien tidak resmi).
#
# WAHA tidak membuka port ke host dan tidak punya rute Traefik, jadi API-nya dipanggil dari
# dalam kontainer bot (python + httpx sudah ada di sana). Yang dilakukan:
#   1. menampilkan status sesi (STARTING / SCAN_QR_CODE / WORKING / FAILED);
#   2. bila SCAN_QR_CODE, menyimpan kode QR sebagai PNG di .waha-qr.png (akar repo) —
#      salin ke komputer Anda (scp) lalu pindai: WhatsApp → Perangkat tertaut → Tautkan.
#      QR berganti tiap ±20 detik; bila kedaluwarsa jalankan lagi.
#
# JANGAN memindai dengan nomor resmi Polres: Meta dapat memblokir nomor yang dipakai klien
# tidak resmi (docs/01 §19.2). Kunci API tidak dicetak ke layar.
#
# Pakai: bash scripts/waha-qr.sh            (sesi dari WAHA_SESSION di .env.production)
set -euo pipefail
cd "$(dirname "$0")/.."
ENV_FILE="$(pwd)/.env.production"
BOT=predpol-prod-bot
OUT="$(pwd)/.waha-qr.png"
[ -f "$ENV_FILE" ] || { echo ".env.production tidak ada"; exit 1; }
grep -q '^WAHA_API_KEY=.\+' "$ENV_FILE" || {
  echo "WAHA belum dipasang: WAHA=peragaan bash scripts/pasang-kanal-perpesanan.sh"; exit 1; }

STATUS=$(docker exec "$BOT" python - <<'PY'
import os, httpx
base = os.environ["WAHA_BASE_URL"]
key = os.environ["WAHA_API_KEY"]
name = os.environ.get("WAHA_SESSION", "default")
r = httpx.get(f"{base}/api/sessions/{name}", headers={"X-Api-Key": key}, timeout=20)
if r.status_code == 404:
    print("BELUM-ADA")
elif r.status_code >= 400:
    print(f"HTTP {r.status_code}")
else:
    print(r.json().get("status", "?"))
PY
)
echo "sesi: $STATUS"
case "$STATUS" in
  WORKING)
    echo "nomor sudah terpasang; kirim 'mulai' ke nomor itu dari WhatsApp lain untuk mencoba." ;;
  SCAN_QR_CODE)
    docker exec "$BOT" python - <<'PY' > "$OUT"
import os, sys, httpx
base = os.environ["WAHA_BASE_URL"]
key = os.environ["WAHA_API_KEY"]
name = os.environ.get("WAHA_SESSION", "default")
r = httpx.get(
    f"{base}/api/{name}/auth/qr",
    params={"format": "image"},
    headers={"X-Api-Key": key, "Accept": "image/png"},
    timeout=20,
)
r.raise_for_status()
sys.stdout.buffer.write(r.content)
PY
    chmod 600 "$OUT"
    echo "QR tersimpan: $OUT  (berlaku ±20 detik)"
    echo "ambil ke komputer Anda, mis.:  scp <user>@<server>:$OUT ."
    echo "lalu pindai: WhatsApp (nomor cadangan) → Perangkat tertaut → Tautkan perangkat."
    ;;
  BELUM-ADA)
    echo "sesi belum dibuat — bot membuatnya saat menyala; tunggu ±30 detik lalu ulangi." ;;
  *)
    echo "periksa log: docker logs --tail 50 predpol-prod-waha" ;;
esac
