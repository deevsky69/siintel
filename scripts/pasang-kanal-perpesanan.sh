#!/usr/bin/env bash
# Memasang kanal perpesanan (bot Telegram, dan WhatsApp bila ada) pada produksi.
#
# Yang dilakukan:
#   1. Membuat MESSAGING_API_KEY (kunci bersama API ⇄ bot) bila belum ada di .env.production.
#   2. Menyimpan TELEGRAM_BOT_TOKEN dari variabel lingkungan ke .env.production.
#   3. (Opsional) Menyimpan WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, dan
#      WHATSAPP_APP_SECRET (App Secret aplikasi Meta, untuk memverifikasi tanda tangan
#      webhook) bila ketiganya diberikan; WHATSAPP_VERIFY_TOKEN dibuat otomatis.
#   4. Memberi tahu langkah berikutnya (deploy).
#
# Tidak satu pun nilai rahasia dicetak ke layar. Pakai:
#
#   TELEGRAM_BOT_TOKEN='123456:ABC...' bash scripts/pasang-kanal-perpesanan.sh
#   TELEGRAM_BOT_TOKEN='...' WHATSAPP_ACCESS_TOKEN='...' WHATSAPP_PHONE_NUMBER_ID='...' \
#     bash scripts/pasang-kanal-perpesanan.sh
#
# Token Telegram didapat dari @BotFather (perintah /newbot). Nilai WhatsApp dari Meta
# Business Suite → WhatsApp → API Setup. WHATSAPP_VERIFY_TOKEN dibuat di sini bila kosong;
# nilainya yang harus Anda masukkan ke Meta saat mendaftarkan webhook
# https://<domain>/webhook/whatsapp.
set -euo pipefail
cd "$(dirname "$0")/.."
ENV_FILE="$(pwd)/.env.production"
[ -f "$ENV_FILE" ] || { echo ".env.production tidak ada"; exit 1; }

set_var() {
  local name="$1" value="$2"
  if grep -q "^${name}=" "$ENV_FILE"; then
    # ganti baris yang ada tanpa mencetak nilainya
    python3 - "$ENV_FILE" "$name" "$value" <<'PY'
import pathlib, sys
path, name, value = sys.argv[1], sys.argv[2], sys.argv[3]
lines = pathlib.Path(path).read_text().splitlines()
lines = [f"{name}={value}" if line.startswith(f"{name}=") else line for line in lines]
pathlib.Path(path).write_text("\n".join(lines) + "\n")
PY
  else
    printf '%s=%s\n' "$name" "$value" >> "$ENV_FILE"
  fi
  echo "  tersimpan: $name"
}

echo "== kunci bersama API ⇄ bot"
if grep -q "^MESSAGING_API_KEY=.\+" "$ENV_FILE"; then
  echo "  MESSAGING_API_KEY sudah ada, dipertahankan"
else
  set_var MESSAGING_API_KEY "$(openssl rand -hex 32)"
fi

echo "== Telegram"
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  set_var TELEGRAM_BOT_TOKEN "$TELEGRAM_BOT_TOKEN"
else
  echo "  TELEGRAM_BOT_TOKEN tidak diberikan — dilewati"
fi

echo "== WhatsApp"
if [ -n "${WHATSAPP_ACCESS_TOKEN:-}" ] && [ -n "${WHATSAPP_PHONE_NUMBER_ID:-}" ] && [ -n "${WHATSAPP_APP_SECRET:-}" ]; then
  set_var WHATSAPP_ACCESS_TOKEN "$WHATSAPP_ACCESS_TOKEN"
  set_var WHATSAPP_PHONE_NUMBER_ID "$WHATSAPP_PHONE_NUMBER_ID"
  set_var WHATSAPP_APP_SECRET "$WHATSAPP_APP_SECRET"
  if grep -q "^WHATSAPP_VERIFY_TOKEN=.\+" "$ENV_FILE"; then
    echo "  WHATSAPP_VERIFY_TOKEN sudah ada, dipertahankan"
  else
    set_var WHATSAPP_VERIFY_TOKEN "${WHATSAPP_VERIFY_TOKEN:-$(openssl rand -hex 16)}"
  fi
  echo "  daftarkan webhook di Meta: https://$(grep '^DOMAIN=' "$ENV_FILE" | cut -d= -f2)/webhook/whatsapp"
  echo "  verify token: lihat baris WHATSAPP_VERIFY_TOKEN di .env.production"
else
  echo "  WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID / WHATSAPP_APP_SECRET tidak lengkap — dilewati"
fi

chmod 600 "$ENV_FILE"
echo
echo "Selanjutnya: bash scripts/deploy-produksi.sh  (membangun kontainer bot dan memulai ulang API)"
