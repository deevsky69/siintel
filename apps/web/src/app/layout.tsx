import type { Metadata } from "next";
import { Chakra_Petch, Inter, JetBrains_Mono } from "next/font/google";
import { THEME_BOOTSTRAP, THEME_STORAGE_KEY } from "@/lib/theme";
import "./globals.css";

// Font dimuat lewat next/font sehingga ikut ter-bundle: demo harus berjalan
// tanpa mengambil apa pun dari internet saat paparan.
const heading = Chakra_Petch({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-heading",
});
const sans = Inter({ subsets: ["latin"], variable: "--font-sans" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "PREDIKSI PRESISI — Polres Metro Jakarta Selatan",
  description:
    "Sistem pendukung keputusan Kamtibmas berbasis predictive policing dan spatial intelligence.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="id"
      // `suppressHydrationWarning` diperlukan justru karena skrip di bawah SENGAJA
      // mengubah elemen ini sebelum React sempat menghidrasinya. Tanpa itu React
      // memperingatkan tentang perbedaan yang memang kita inginkan.
      suppressHydrationWarning
      className={`${heading.variable} ${sans.variable} ${mono.variable}`}
    >
      <head>
        {/*
          Tema dipasang SEBELUM apa pun tergambar.

          Bila ini dikerjakan React setelah hidrasi, pengguna mode terang akan melihat
          kedipan biru malam selama beberapa ratus milidetik pada setiap pemuatan halaman —
          cacat yang tidak dapat diperbaiki dari dalam React, karena React baru berjalan
          setelah halaman tergambar sekali.
        */}
        {/* biome-ignore lint/security/noDangerouslySetInnerHtml: isinya tetapan yang
            ditulis pada waktu kompilasi (`THEME_BOOTSTRAP`), bukan masukan pengguna. Tidak
            ada jalan lain menjalankan skrip sinkron di dalam <head> pada React. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOTSTRAP }} />
      </head>
      <body data-theme-key={THEME_STORAGE_KEY}>{children}</body>
    </html>
  );
}
