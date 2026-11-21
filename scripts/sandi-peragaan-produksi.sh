#!/usr/bin/env bash
# Menetapkan SATU kata sandi yang sama untuk kesembilan akun peragaan di PRODUKSI, lalu
# menulis ulang ~/siintel-demo-passwords.txt. Kata sandi diberikan lewat variabel
# lingkungan supaya tidak masuk riwayat perintah sebagai argumen:
#
#   SANDI='kata-sandi-baru' bash scripts/sandi-peragaan-produksi.sh
#
# Server menolak kata sandi di bawah 10 karakter (pengaman teknis; kebijakan resmi
# menunggu U-05). Skrip ini tidak pernah mencetak kata sandinya.
set -euo pipefail
cd "$(dirname "$0")/.."

: "${SANDI:?Isi variabel SANDI, mis. SANDI='...' bash scripts/sandi-peragaan-produksi.sh}"
if (( ${#SANDI} < 10 )); then
  echo "Kata sandi minimal 10 karakter (sekarang ${#SANDI})." >&2
  exit 1
fi

COMPOSE=(docker compose --env-file .env.production -f infra/docker/docker-compose.prod.yml -f infra/docker/docker-compose.coolify.yml)
PASSFILE="$HOME/siintel-demo-passwords.txt"
# demo.kasat dikunci migrasi 0023 (10 November 2026) dan dihidupkan lagi migrasi 0026
# (17 November 2026, produk bulanan tiga tahap). Sampai skrip ini dijalankan, akun itu
# belum punya kata sandi yang sah. demo.analis berperan Analis Intelkam.
# demo.kbo dan demo.humas dibuat migrasi 0029 (19 November 2026) tanpa kata sandi yang sah.
# demo.wakasat dibuat migrasi 0031 (21 November 2026), juga tanpa kata sandi yang sah.
AKUN=(demo.pimpinan demo.kasat demo.wakasat demo.kbo demo.analis demo.humas demo.polsek demo.fungsi demo.admin)

for akun in "${AKUN[@]}"; do
  echo "== $akun"
  # set_password menerima kata sandi sebagai argumen fungsi; dibaca dari lingkungan
  # kontainer, bukan ditulis pada baris perintah.
  "${COMPOSE[@]}" exec -T -e SANDI="$SANDI" api python -c \
    "import os, sys; from prediksi_presisi_api.cli import set_password; sys.exit(set_password('$akun', os.environ['SANDI']))"
done

umask 077
{
  echo "PASSWORD AKUN DEMO — ditetapkan $(date +%F) lewat scripts/sandi-peragaan-produksi.sh"
  echo "Satu kata sandi untuk kesembilan akun. Ganti setelah paparan."
  echo
  for akun in "${AKUN[@]}"; do echo "$akun $SANDI"; done
} > "$PASSFILE"
chmod 600 "$PASSFILE"
echo
echo "Selesai. Kesembilan akun memakai kata sandi yang sama; berkas $PASSFILE diperbarui (mode 600)."
