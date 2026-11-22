#!/usr/bin/env bash
# Cadangan harian basis data PRODUKSI — "data dicadangkan secara terjadwal" (SOP deteksi dini,
# naskah Taskap revisi Lampiran I butir 9; catatan 192).
#
# Menulis ~/siintel-cadangan-harian/sigap-YYYYMMDD.sql.gz (mode 600) dan menghapus berkas
# buatannya sendiri yang lebih tua dari SIMPAN_HARI (bawaan 14). Hanya membaca basis data.
# Hasilnya diperiksa pemegang Audit Log tiap bulan dan dicatat pada Kalender SOP.
#
# Dipasang lewat crontab pengguna, mis. setiap hari pukul 02.30:
#   30 2 * * * /home/kim/siintel/infra/cadangan-harian.sh >> /home/kim/log/cadangan-harian.log 2>&1
set -euo pipefail

TUJUAN="${TUJUAN:-$HOME/siintel-cadangan-harian}"
SIMPAN_HARI="${SIMPAN_HARI:-14}"
KONTAINER="${KONTAINER:-predpol-prod-db}"

umask 077
mkdir -p "$TUJUAN"
berkas="$TUJUAN/sigap-$(date +%Y%m%d).sql.gz"
sementara="$berkas.tmp"

# Ditulis ke berkas sementara lebih dulu: cadangan yang terpotong tidak pernah menimpa yang utuh.
docker exec "$KONTAINER" sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$sementara"
gzip -t "$sementara"
mv "$sementara" "$berkas"

find "$TUJUAN" -maxdepth 1 -name 'sigap-*.sql.gz' -mtime +"$SIMPAN_HARI" -delete
echo "$(date '+%F %T') cadangan $(basename "$berkas") $(du -h "$berkas" | cut -f1); tersimpan $(find "$TUJUAN" -maxdepth 1 -name 'sigap-*.sql.gz' | wc -l) berkas"
