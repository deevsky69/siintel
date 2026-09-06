#!/usr/bin/env bash
#
# Memasang sertifikat swatandatangan MILIK KITA pada Traefik, menggantikan
# `TRAEFIK DEFAULT CERT`.
#
# MENGAPA INI PERLU, PADAHAL SUDAH ADA SERTIFIKAT SWATANDATANGAN
#
#   Yang disajikan Traefik sekarang adalah sertifikat bawaannya sendiri, dan ia
#   **dibuat ulang sewaktu-waktu** — pada server ini ia lahir 4 September padahal
#   proxy-nya hidup sejak 29 Agustus. Peramban tidak peduli: ia sudah menampilkan
#   peringatan dan pengguna menekan "lanjutkan".
#
#   Aplikasi Android peduli. Ia menolak sambungan HTTPS yang sertifikatnya tidak
#   tepercaya, dan satu-satunya cara membuatnya menerima sertifikat swatandatangan
#   adalah menyematkan sertifikat itu ke dalam APK. Sertifikat yang berganti sendiri
#   membuat APK mati tanpa peringatan pada hari yang tidak dapat diramalkan.
#
#   Sertifikat di bawah dibuat sekali, berlaku sepuluh tahun, dan tidak berganti
#   kecuali skrip ini dijalankan ulang. Itulah yang membuatnya dapat disematkan.
#
# INI BUKAN PENGGANTI SERTIFIKAT SUNGGUHAN
#
#   Peramban tetap menampilkan peringatan keamanan — tidak ada yang berubah di sana.
#   Yang berubah hanya: aplikasi Android dapat bekerja lewat internet hari ini, tanpa
#   menunggu DomaiNesia. Begitu sertifikat Let's Encrypt terbit (`docs/10` §3.2),
#   jalankan `pasang-sertifikat.sh`, lalu HAPUS penyematan pada kedua APK.
#
set -euo pipefail

DOMAIN="${DOMAIN:-siintel.awansurya.com}"
OUT="${OUT:-$HOME/siintel-cert}"
PROXY="coolify-proxy"
DAYS=3650

docker() { sg docker -c "docker $*"; }

mkdir -p "$OUT"

# MENGAPA DUA SERTIFIKAT, BUKAN SATU
#
#   Android menyematkan sertifikat sebagai **jangkar kepercayaan** (trust anchor), dan
#   jangkar wajib berupa CA. Sertifikat server swatandatangan biasa tidak membawa
#   `basicConstraints=CA:TRUE`, sehingga menyematkannya ditolak diam-diam pada sebagian
#   versi Android — gagal dengan cara yang sulit ditelusuri.
#
#   Karena itu dibuat dua: satu CA kecil milik satuan, dan satu sertifikat server yang
#   ditandatanganinya. Yang disematkan di APK adalah **CA-nya**. Dengan begitu sertifikat
#   server kelak dapat diperbarui tanpa membangun ulang APK, selama CA-nya tetap sama.

echo "==> Membuat CA milik satuan (berlaku $DAYS hari)"
openssl req -x509 -newkey rsa:2048 -sha256 -days "$DAYS" -nodes \
    -keyout "$OUT/ca.key" -out "$OUT/ca.crt" \
    -subj "/C=ID/ST=DKI Jakarta/O=Polres Metro Jakarta Selatan/CN=PREDIKSI PRESISI Internal CA" \
    -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" 2>/dev/null
chmod 600 "$OUT/ca.key"

echo "==> Membuat sertifikat server untuk $DOMAIN"
openssl req -newkey rsa:2048 -sha256 -nodes \
    -keyout "$OUT/siintel.key" -out "$OUT/siintel.csr" \
    -subj "/C=ID/ST=DKI Jakarta/L=Jakarta Selatan/O=Polres Metro Jakarta Selatan/CN=$DOMAIN" 2>/dev/null
chmod 600 "$OUT/siintel.key"

openssl x509 -req -in "$OUT/siintel.csr" -CA "$OUT/ca.crt" -CAkey "$OUT/ca.key" \
    -CAcreateserial -days "$DAYS" -sha256 -out "$OUT/siintel.crt" \
    -extfile <(printf '%s\n' \
        "subjectAltName=DNS:$DOMAIN,DNS:*.$DOMAIN,IP:111.68.123.134" \
        "basicConstraints=critical,CA:FALSE" \
        "keyUsage=critical,digitalSignature,keyEncipherment" \
        "extendedKeyUsage=serverAuth") 2>/dev/null
rm -f "$OUT/siintel.csr"

# Traefik disajikan rantai lengkap: sertifikat server lalu CA-nya. Tanpa CA di dalam
# rantai, klien yang belum memilikinya tidak dapat memverifikasi apa pun.
cat "$OUT/siintel.crt" "$OUT/ca.crt" > "$OUT/siintel-chain.crt"

echo "==> Memasang pada Traefik"
docker "exec $PROXY mkdir -p /traefik/certs"
docker "exec -i $PROXY sh -c 'cat > /traefik/certs/siintel.crt'" < "$OUT/siintel-chain.crt"
docker "exec -i $PROXY sh -c 'cat > /traefik/certs/siintel.key && chmod 600 /traefik/certs/siintel.key'" < "$OUT/siintel.key"

# Dipasang sebagai `certificates`, BUKAN `defaultCertificate`: mengganti sertifikat
# bawaan akan ikut mengubah perilaku seluruh aplikasi lain pada proxy yang sama.
docker "exec -i $PROXY sh -c 'cat > /traefik/dynamic/siintel.yml'" <<'YML'
# Sertifikat PREDIKSI PRESISI — swatandatangan, dipasang agar aplikasi Android dapat
# menyematkannya. Diganti oleh scripts/pasang-sertifikat.sh begitu Let's Encrypt terbit.
tls:
  certificates:
    - certFile: /traefik/certs/siintel.crt
      keyFile: /traefik/certs/siintel.key
YML

echo "==> Menunggu Traefik memuat ulang"
sleep 6

echo "==> Sertifikat yang kini disajikan"
openssl s_client -connect 127.0.0.1:443 -servername "$DOMAIN" </dev/null 2>/dev/null \
    | openssl x509 -noout -subject -dates -fingerprint -sha256

echo
echo "==> Sidik jari CA — inilah yang disematkan di APK"
openssl x509 -in "$OUT/ca.crt" -noout -fingerprint -sha256

echo
echo "Berkasnya tersimpan di $OUT."
echo "  ca.crt            disematkan di APK, boleh dibagikan"
echo "  ca.key            JANGAN dibagikan — dengan ini siapa pun dapat menyamar sebagai server"
echo "  siintel.key       JANGAN dibagikan"
