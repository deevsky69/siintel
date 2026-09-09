import type { NextConfig } from "next";

/**
 * Asal permintaan yang boleh menjalankan Server Action.
 *
 * MENGAPA INI ADA. Next memeriksa `Origin` terhadap `X-Forwarded-Host` sebagai penangkal
 * CSRF pada Server Action. Di depan demo ini berdiri nginx pada mesin lain yang
 * meneruskan `X-Forwarded-Host` berisi ALAMAT IP internal (`10.3.3.87`), sedangkan
 * peramban mengirim `Origin: https://siintel.awansurya.com`. Keduanya tidak cocok, dan
 * Next membatalkan SETIAP Server Action dengan "Invalid Server Actions request".
 *
 * Akibatnya seluruh rantai human-in-the-loop mati di peramban demo — menyetujui
 * rekomendasi, menerima peringatan, mentriase laporan, menerbitkan imbauan — sementara
 * halaman yang hanya membaca tetap normal. Kegagalannya senyap: 500 tanpa pesan, dan
 * satu-satunya keterangan ada di log container.
 *
 * Ini menambal dari sisi aplikasi. Perbaikan yang sebenarnya ada di nginx tersebut
 * (`proxy_set_header Host $host;` dan `X-Forwarded-Host $host;`), tetapi mesin itu di luar
 * kendali repositori ini, dan demo tidak boleh bergantung pada konfigurasi yang tidak
 * dapat diuji di sini.
 *
 * Nilainya dibaca saat BUILD, bukan saat jalan: `output: "standalone"` membekukan config
 * ke dalam image. Karena itu ia diteruskan sebagai build arg, bukan environment runtime.
 */
const allowedOrigins = (process.env.APP_ALLOWED_ORIGINS ?? "siintel.awansurya.com")
  .split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Menghasilkan server mandiri di `.next/standalone` — dipakai image produksi
  // agar container tidak perlu memuat seluruh node_modules (infra/docker/Dockerfile).
  output: "standalone",
  experimental: {
    serverActions: { allowedOrigins },
  },
};

export default nextConfig;
