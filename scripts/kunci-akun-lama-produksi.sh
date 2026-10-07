#!/usr/bin/env bash
# Mengunci dua akun peragaan tinggalan (demo.commandcenter, demo.analyst) di PRODUKSI dan
# menghapus barisnya dari berkas kata sandi — keputusan pemilik proyek 7 Oktober 2026
# (opsi A: empat peran, empat akun). Jalankan dari root repo dengan awalan `!`.
#
# Akun dikunci, bukan dihapus: jejak audit merujuk ke akun itu dan tidak boleh putus.
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE=(docker compose --env-file .env.production -f infra/docker/docker-compose.prod.yml -f infra/docker/docker-compose.coolify.yml)
PASSFILE="$HOME/siintel-demo-passwords.txt"

# Perintah lock-user baru ada sejak 7 Oktober 2026: kontainer yang belum di-deploy tidak
# mengenalnya, dan galat argparse-nya membingungkan. Periksa dulu, beri tahu dengan jelas.
if ! "${COMPOSE[@]}" exec -T api python -m prediksi_presisi_api.cli --help 2>/dev/null | grep -q "lock-user"; then
  echo "Kontainer API produksi masih memakai kode lama (belum ada perintah lock-user)."
  echo "Jalankan dulu:  bash scripts/deploy-produksi.sh   lalu ulangi skrip ini."
  exit 1
fi

for akun in demo.commandcenter demo.analyst; do
  echo "== mengunci $akun"
  "${COMPOSE[@]}" exec -T api python -m prediksi_presisi_api.cli lock-user "$akun"
  if [[ -f "$PASSFILE" ]]; then
    sed -i "/^$akun /d" "$PASSFILE"
  fi
done

echo
echo "== akun yang tersisa (kata sandi tidak ditampilkan)"
"${COMPOSE[@]}" exec -T api python -m prediksi_presisi_api.cli list-users
