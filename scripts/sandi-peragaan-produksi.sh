#!/usr/bin/env bash
# Menetapkan SATU kata sandi yang sama untuk keempat akun peragaan di PRODUKSI, lalu
# menulis ulang ~/siintel-demo-passwords.txt. Kata sandi diberikan lewat variabel
# lingkungan supaya tidak masuk riwayat perintah sebagai argumen:
#
#   SANDI='kata-sandi-baru' bash scripts/sandi-peragaan-produksi.sh
#
# Server menolak kata sandi di bawah 12 karakter (pengaman teknis; kebijakan resmi
# menunggu U-05). Skrip ini tidak pernah mencetak kata sandinya.
set -euo pipefail
cd "$(dirname "$0")/.."

: "${SANDI:?Isi variabel SANDI, mis. SANDI='...' bash scripts/sandi-peragaan-produksi.sh}"
if (( ${#SANDI} < 12 )); then
  echo "Kata sandi minimal 12 karakter (sekarang ${#SANDI})." >&2
  exit 1
fi

COMPOSE=(docker compose --env-file .env.production -f infra/docker/docker-compose.prod.yml -f infra/docker/docker-compose.coolify.yml)
PASSFILE="$HOME/siintel-demo-passwords.txt"
AKUN=(demo.pimpinan demo.polsek demo.fungsi demo.admin)

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
  echo "Satu kata sandi untuk keempat akun. Ganti setelah paparan."
  echo
  for akun in "${AKUN[@]}"; do echo "$akun $SANDI"; done
} > "$PASSFILE"
chmod 600 "$PASSFILE"
echo
echo "Selesai. Keempat akun memakai kata sandi yang sama; berkas $PASSFILE diperbarui (mode 600)."
