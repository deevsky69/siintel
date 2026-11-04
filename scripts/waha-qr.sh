#!/usr/bin/env bash
# Memasangkan NOMOR CADANGAN ke sesi WAHA (kanal WhatsApp peragaan, klien tidak resmi).
#
# WAHA tidak membuka port ke host dan tidak punya rute Traefik, jadi API-nya dipanggil dari
# dalam kontainer bot (python + httpx sudah ada di sana). Yang dilakukan:
#   1. menampilkan status sesi (STARTING / SCAN_QR_CODE / WORKING / FAILED);
#   2. bila SCAN_QR_CODE, MENCETAK kode QR di terminal (pindai langsung dari layar) dan
#      menyimpannya juga sebagai PNG di .waha-qr.png (akar repo) untuk cadangan.
#      QR berganti tiap ±20 detik; bila kedaluwarsa jalankan lagi.
#
# Pindai: WhatsApp (nomor cadangan) → Perangkat tertaut → Tautkan perangkat.
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

# `-i` wajib: program Python dikirim lewat stdin.
STATUS=$(docker exec -i "$BOT" python - <<'PY'
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
    docker exec -i "$BOT" python - <<'PY' > "$OUT"
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
    # Nilai mentah QR dicetak sebagai blok teks supaya dapat dipindai langsung dari layar.
    RAW=$(docker exec -i "$BOT" python - <<'PY'
import os, httpx
base = os.environ["WAHA_BASE_URL"]
key = os.environ["WAHA_API_KEY"]
name = os.environ.get("WAHA_SESSION", "default")
r = httpx.get(f"{base}/api/{name}/auth/qr", params={"format": "raw"},
              headers={"X-Api-Key": key}, timeout=20)
r.raise_for_status()
print(r.json()["value"])
PY
)
    if command -v uv >/dev/null 2>&1; then
      # Nilai lewat variabel lingkungan (stdin dipakai program); ukuran QR mengikuti datanya.
      QR_RAW="$RAW" uv run -q --no-project --with 'qrcode==8.2' python -c '
import os, qrcode
qr = qrcode.QRCode(border=1)
qr.add_data(os.environ["QR_RAW"].strip())
qr.make(fit=True)
qr.print_ascii(invert=True)
' || true
    fi
    echo "QR juga tersimpan: $OUT  (berlaku ±20 detik; jalankan lagi bila kedaluwarsa)"
    echo "pindai: WhatsApp (nomor cadangan) → Perangkat tertaut → Tautkan perangkat."
    ;;
  BELUM-ADA)
    echo "sesi belum dibuat — bot membuatnya saat menyala; tunggu ±30 detik lalu ulangi." ;;
  *)
    echo "periksa log: docker logs --tail 50 predpol-prod-waha" ;;
esac
