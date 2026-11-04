#!/usr/bin/env bash
# Memasangkan NOMOR CADANGAN ke sesi WAHA (kanal WhatsApp peragaan, klien tidak resmi).
#
# WAHA tidak membuka port ke host dan tidak punya rute Traefik, jadi API-nya dipanggil dari
# dalam kontainer bot (python + httpx sudah ada di sana). Yang dilakukan:
#   1. memeriksa status sesi; bila FAILED/STOPPED (WAHA menghentikan paksa sesi yang QR-nya
#      tidak dipindai ±3 menit) sesi dinyalakan lagi dan ditunggu sampai QR siap;
#   2. MENCETAK kode QR di terminal — pindai langsung dari layar dalam ±20 detik; bila
#      kedaluwarsa jalankan lagi.
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
[ -f "$ENV_FILE" ] || { echo ".env.production tidak ada"; exit 1; }
grep -q '^WAHA_API_KEY=.\+' "$ENV_FILE" || {
  echo "WAHA belum dipasang: WAHA=peragaan bash scripts/pasang-kanal-perpesanan.sh"; exit 1; }

# `-i` wajib: program Python dikirim lewat stdin. Keluaran: baris 1 status, baris 2 nilai QR.
RESULT=$(docker exec -i "$BOT" python - <<'PY'
import os, sys, time, httpx
base = os.environ["WAHA_BASE_URL"]
name = os.environ.get("WAHA_SESSION", "default")
http = httpx.Client(base_url=base, headers={"X-Api-Key": os.environ["WAHA_API_KEY"]}, timeout=20)

def status() -> str:
    r = http.get(f"/api/sessions/{name}")
    if r.status_code == 404:
        return "BELUM-ADA"
    if r.status_code >= 400:
        return f"HTTP {r.status_code}"
    return str(r.json().get("status", "?"))

s = status()
if s in ("FAILED", "STOPPED"):
    http.post(f"/api/sessions/{name}/start").raise_for_status()
    s = "STARTING"
for _ in range(12):  # tunggu QR siap, paling lama ±60 detik
    if s not in ("STARTING",):
        break
    time.sleep(5)
    s = status()
print(s)
if s == "SCAN_QR_CODE":
    r = http.get(f"/api/{name}/auth/qr", params={"format": "raw"})
    r.raise_for_status()
    print(r.json()["value"])
PY
)
STATUS=$(printf '%s\n' "$RESULT" | sed -n 1p)
RAW=$(printf '%s\n' "$RESULT" | sed -n 2p)
echo "sesi: $STATUS"
case "$STATUS" in
  WORKING)
    echo "nomor sudah terpasang; kirim 'mulai' ke nomor itu dari WhatsApp lain untuk mencoba." ;;
  SCAN_QR_CODE)
    if command -v uv >/dev/null 2>&1; then
      # Nilai lewat variabel lingkungan; ukuran QR mengikuti datanya.
      QR_RAW="$RAW" uv run -q --no-project --with 'qrcode==8.2' python -c '
import os, qrcode
qr = qrcode.QRCode(border=1)
qr.add_data(os.environ["QR_RAW"].strip())
qr.make(fit=True)
qr.print_ascii(invert=True)
' || echo "(uv/qrcode gagal; QR tidak dapat dicetak)"
    else
      echo "uv tidak ada di host; QR tidak dapat dicetak sebagai teks."
    fi
    echo "berlaku ±20 detik — jalankan lagi bila kedaluwarsa."
    echo "pindai: WhatsApp (nomor cadangan) → Perangkat tertaut → Tautkan perangkat."
    ;;
  BELUM-ADA)
    echo "sesi belum dibuat — bot membuatnya saat menyala; tunggu ±30 detik lalu ulangi." ;;
  STARTING)
    echo "sesi masih menyala; ulangi sebentar lagi." ;;
  *)
    echo "periksa log: docker logs --tail 50 predpol-prod-waha" ;;
esac
