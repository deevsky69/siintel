#!/usr/bin/env bash
#
# Pemeriksaan cepat demo produksi — yang TIDAK terlihat dari halaman yang hanya dibaca.
#
# MENGAPA BERKAS INI ADA
#
#   Pada 9 September 2026 ditemukan bahwa SELURUH Server Action di demo ditolak Next
#   sebagai dugaan CSRF, karena nginx di depannya meneruskan `X-Forwarded-Host` berisi
#   alamat IP internal. Akibatnya seluruh lengan tulis mati — menyetujui rekomendasi,
#   menerima peringatan, mentriase laporan — sementara demo tampak sehat sepenuhnya,
#   sebab setiap halaman yang hanya MEMBACA tetap normal.
#
#   Kegagalan itu senyap: HTTP 500 tanpa pesan di layar, dan satu-satunya keterangan ada
#   di log container. Tidak ada yang akan menyadarinya sampai seseorang menekan tombol di
#   depan penguji.
#
#   Pemeriksaan di bawah menyentuh justru hal-hal yang senyap semacam itu.
#
# Pakai:  bash scripts/periksa-produksi.sh [https://alamat-demo]
set -uo pipefail

BASE="${1:-https://siintel.awansurya.com}"
gagal=0

lulus() { printf '  \033[32mOK\033[0m   %s\n' "$1"; }
tidak() { printf '  \033[31mGAGAL\033[0m %s\n' "$1"; gagal=$((gagal + 1)); }

echo "Memeriksa $BASE"
echo

# 1. API hidup.
if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$BASE/api/v1/health")" = "200" ]; then
  lulus "API menjawab"
else
  tidak "API tidak menjawab — sisanya tidak dapat diperiksa"
  exit 1
fi

# 2. Kanal publik terbuka tanpa akun.
for jalur in /api/v1/public/report-options /api/v1/public/alerts; do
  kode=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$BASE$jalur")
  [ "$kode" = "200" ] && lulus "kanal publik $jalur" || tidak "kanal publik $jalur menjawab $kode"
done

# 3. Endpoint berkewenangan MENOLAK tanpa token. Menjawab 200 di sini berarti kebocoran.
for jalur in /api/v1/notifications /api/v1/auth/me /api/v1/public-alerts; do
  kode=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$BASE$jalur")
  [ "$kode" = "401" ] && lulus "tanpa token, $jalur ditolak" \
    || tidak "tanpa token, $jalur menjawab $kode — seharusnya 401"
done

# 4. SERVER ACTION — inti berkas ini.
#
#    Next menolak action bila `Origin` tidak cocok dengan `X-Forwarded-Host` yang
#    diteruskan proxy. Yang diperiksa di sini bukan berhasilnya sebuah aksi (itu menuntut
#    akun), melainkan bahwa permintaannya tidak ditolak MENTAH-MENTAH sebelum sampai ke
#    kode aplikasi. Action yang ditolak menjawab 500; yang sampai menjawab 303/200/4xx.
kode=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 -X POST "$BASE/masuk" \
  -H "Origin: $BASE" \
  -H "Content-Type: multipart/form-data; boundary=x" \
  -H "Next-Action: 00000000000000000000000000000000000000" \
  --data-binary $'--x--\r\n')
if [ "$kode" = "500" ]; then
  tidak "Server Action ditolak proxy (500) — periksa \`X-Forwarded-Host\` di nginx depan"
  echo "         nginx harus meneruskan nama host asli, bukan alamat IP:"
  echo "           proxy_set_header Host              \$host;"
  echo "           proxy_set_header X-Forwarded-Host  \$host;"
else
  lulus "Server Action sampai ke aplikasi (HTTP $kode, bukan 500)"
fi

# 5. Sertifikat masih jauh dari kedaluwarsa.
habis=$(echo | openssl s_client -connect "${BASE#https://}:443" -servername "${BASE#https://}" 2>/dev/null \
  | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
if [ -n "$habis" ]; then
  sisa=$(( ($(date -d "$habis" +%s) - $(date +%s)) / 86400 ))
  [ "$sisa" -gt 14 ] && lulus "sertifikat berlaku $sisa hari lagi" \
    || tidak "sertifikat tinggal $sisa hari"
else
  tidak "sertifikat tidak dapat dibaca"
fi

echo
[ "$gagal" -eq 0 ] && echo "Seluruh pemeriksaan lulus." || echo "$gagal pemeriksaan GAGAL."
exit "$gagal"
