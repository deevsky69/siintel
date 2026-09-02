#!/usr/bin/env bash
#
# Menyelesaikan penerbitan sertifikat Let's Encrypt lewat tantangan DNS-01 dan
# memasangnya pada Traefik milik Coolify.
#
# MENGAPA DNS-01, BUKAN HTTP-01
#
#   Let's Encrypt SELALU menghubungi port 80 (HTTP-01) atau 443 (TLS-ALPN-01) pada
#   domain yang diverifikasi. Nomor port itu bagian dari spesifikasi ACME dan tidak
#   dapat diarahkan ulang. Server ini berbagi satu IP publik, sehingga 80 dan 443
#   dipakai host lain dan aplikasi ini menerima 8997 → 80 dan 8998 → 443.
#
#   DNS-01 tidak memerlukan sambungan masuk sama sekali: Let's Encrypt hanya membaca
#   satu record TXT. Karena itu ia bekerja pada pemetaan port seperti apa pun.
#
# PRASYARAT
#
#   Record TXT `_acme-challenge.siintel.awansurya.com` sudah dipasang di panel DNS
#   (DomaiNesia) dan sudah menyebar. Nilainya diberikan oleh perintah `--issue`.
#   Periksa lebih dulu:
#
#       dig +short TXT _acme-challenge.siintel.awansurya.com @8.8.8.8
#
# YANG DIUBAH DI LUAR REPOSITORY
#
#   Skrip ini menulis DUA berkas baru ke dalam direktori proxy milik Coolify
#   (`/data/coolify/proxy`, terpasang sebagai `/traefik` di dalam container):
#
#       /traefik/certs/siintel.crt   sertifikat
#       /traefik/certs/siintel.key   kunci privat (mode 600)
#       /traefik/dynamic/siintel.yml konfigurasi TLS
#
#   Tidak ada berkas milik Coolify yang diubah atau dihapus, dan resolver ACME
#   milik Coolify tidak disentuh. Traefik sudah berjalan dengan
#   `--providers.file.directory=/traefik/dynamic/ --providers.file.watch=true`,
#   sehingga berkas ini terbaca sendiri tanpa perlu restart.
#
#   Untuk membatalkan: hapus ketiga berkas itu, lalu Traefik kembali memakai
#   sertifikat bawaannya.
#
set -euo pipefail

DOMAIN="${DOMAIN:-siintel.awansurya.com}"
ACME="$HOME/.acme.sh/acme.sh"
PROXY_CONTAINER="coolify-proxy"

docker() { sg docker -c "docker $*"; }

# `+nocookie` dipakai dengan sengaja: sebagian jaringan memutus DNS cookie di tengah
# jalan, dan dig lalu menjawab "Client COOKIE mismatch" dengan keluaran KOSONG. Tanpa
# opsi ini, pemeriksaan di bawah menyimpulkan recordnya belum ada padahal ada.
dig_txt() { dig +nocookie +short TXT "_acme-challenge.$DOMAIN" "@$1" 2>/dev/null | grep -v '^$' || true; }

echo "==> Memeriksa record TXT"
# Ditanyakan ke nameserver otoritatif LEBIH DULU, bukan hanya ke resolver publik:
# resolver publik dapat menyimpan jawaban NXDOMAIN lama selama berjam-jam, sehingga
# record yang sudah benar tetap terbaca "belum ada".
FOUND="$(dig_txt ns1.domainesia.net)"
[ -n "$FOUND" ] || FOUND="$(dig_txt 8.8.8.8)"
if [ -z "$FOUND" ]; then
    echo "GAGAL: record TXT _acme-challenge.$DOMAIN belum ada di nameserver otoritatif." >&2
    echo "       Pasang dulu di panel DNS, tunggu penyebarannya, lalu ulangi." >&2
    exit 1
fi
echo "$FOUND" | sed 's/^/    terbaca: /'

echo "==> Menyelesaikan verifikasi Let's Encrypt"
"$ACME" --renew -d "$DOMAIN" --yes-I-know-dns-manual-mode-enough-go-ahead-please

CERT_DIR="$HOME/.acme.sh/${DOMAIN}_ecc"
[ -s "$CERT_DIR/fullchain.cer" ] || { echo "GAGAL: sertifikat tidak terbentuk." >&2; exit 1; }

echo "==> Memasang sertifikat pada Traefik"
docker "exec $PROXY_CONTAINER mkdir -p /traefik/certs"
docker "exec -i $PROXY_CONTAINER sh -c 'cat > /traefik/certs/siintel.crt'" < "$CERT_DIR/fullchain.cer"
docker "exec -i $PROXY_CONTAINER sh -c 'cat > /traefik/certs/siintel.key && chmod 600 /traefik/certs/siintel.key'" < "$CERT_DIR/$DOMAIN.key"

# Sertifikat dipasang sebagai `certificates`, BUKAN `defaultCertificate`: mengganti
# sertifikat bawaan akan ikut mengubah perilaku seluruh aplikasi lain di proxy ini.
docker "exec -i $PROXY_CONTAINER sh -c 'cat > /traefik/dynamic/siintel.yml'" <<'YML'
# Sertifikat PREDIKSI PRESISI (siintel.awansurya.com), diterbitkan lewat DNS-01.
# Ditambahkan di luar Coolify; tidak mengubah resolver ACME miliknya.
tls:
  certificates:
    - certFile: /traefik/certs/siintel.crt
      keyFile: /traefik/certs/siintel.key
YML

echo "==> Menunggu Traefik memuat ulang konfigurasi"
sleep 6

echo "==> Memeriksa sertifikat yang benar-benar disajikan"
openssl s_client -connect 127.0.0.1:443 -servername "$DOMAIN" </dev/null 2>/dev/null \
    | openssl x509 -noout -subject -issuer -dates

echo
echo "Selesai. Bila penerbit sudah berbunyi Let's Encrypt, buka:"
echo "    https://$DOMAIN:8998"
echo
echo "Sertifikat berlaku 90 hari. Perpanjangannya manual karena DomaiNesia tidak"
echo "memiliki plugin DNS otomatis pada acme.sh: jalankan --issue lagi, pasang nilai"
echo "TXT yang baru, lalu jalankan skrip ini kembali."
