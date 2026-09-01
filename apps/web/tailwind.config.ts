import type { Config } from "tailwindcss";

/**
 * Tema command-center PREDIKSI PRESISI.
 *
 * Palet dan tipografi mengikuti referensi visual pada `design/gambaran-website.png`
 * dan aplikasi acuan yang ditunjuk pemilik proyek: latar biru malam pekat, aksen sian,
 * dan tangga warna risiko yang dipakai konsisten di peta, badge, maupun grafik.
 *
 * Warna risiko sengaja diberi nama menurut **maknanya** (`risk.low` … `risk.critical`),
 * bukan menurut rupanya, supaya ambang yang belum final (U-01) dapat berubah tanpa
 * mengganti nama kelas di seluruh antarmuka.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: {
          950: "#050b18", // latar aplikasi
          900: "#0a1424", // latar panel
          850: "#0e1b2e",
          800: "#132339", // garis panel / hover
          700: "#1b2f4a",
          600: "#27436b",
        },
        ink: {
          DEFAULT: "#e6f0ff",
          muted: "#8ea6c8",
          faint: "#5b7796",
        },
        accent: {
          DEFAULT: "#22d3ee", // sian — aksen utama
          soft: "#67e8f9",
          deep: "#0891b2",
        },
        risk: {
          low: "#38bdf8",
          moderate: "#4ade80",
          high: "#fb923c",
          critical: "#ef4444",
        },
      },
      fontFamily: {
        heading: ["var(--font-heading)", "system-ui", "sans-serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(148,197,255,0.06) inset, 0 8px 24px -12px rgba(0,0,0,0.8)",
        glow: "0 0 24px -6px rgba(34,211,238,0.45)",
      },
    },
  },
  plugins: [],
};

export default config;
