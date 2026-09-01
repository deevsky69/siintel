import type { Metadata } from "next";
import { Chakra_Petch, Inter, JetBrains_Mono } from "next/font/google";
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
    <html lang="id" className={`${heading.variable} ${sans.variable} ${mono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
