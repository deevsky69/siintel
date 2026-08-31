import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PREDIKSI PRESISI",
  description: "Sistem pendukung keputusan Kamtibmas — predictive policing & spatial intelligence.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  );
}
