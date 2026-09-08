import type { Config } from "tailwindcss";

/**
 * Tema PREDIKSI PRESISI.
 *
 * ## Warna adalah variabel, bukan nilai
 *
 * Tidak satu pun warna di bawah ini berupa nilai heks. Semuanya menunjuk variabel CSS yang
 * didefinisikan dua kali di `globals.css` — sekali untuk mode terang, sekali untuk gelap.
 * Akibatnya seluruh aplikasi berganti tema **tanpa satu kelas pun berubah**: `bg-base-900`
 * berarti "latar panel", dan latar panel memang berbeda di kedua mode.
 *
 * Nilainya ditulis sebagai tiga bilangan `R G B` supaya penanda kelegapan Tailwind tetap
 * bekerja: `bg-base-900/80` menghasilkan `rgb(var(--surface-panel) / 0.8)`.
 *
 * **Angka pada `base` adalah tingkat kedalaman, bukan tingkat kegelapan.** `base-950`
 * berarti latar terjauh dan `base-600` garis terkuat; di mode terang urutannya sama
 * meskipun warnanya justru menjadi terang. Nama lama dipertahankan karena mengubahnya
 * berarti menyentuh 150 berkas tanpa menambah satu pun kejelasan.
 *
 * Warna risiko tetap dinamai menurut **maknanya** (`risk.low` … `risk.critical`), bukan
 * rupanya, supaya ambang yang belum final (U-01) dapat berubah tanpa mengganti nama kelas.
 *
 * ## Tangga ukuran huruf
 *
 * Lantainya **12 px**. Sebelum ini antarmuka memakai 9, 10, dan 11 piksel di 435 tempat —
 * ukuran yang dapat dibaca pada layar 27 inci di meja, tetapi tidak pada ponsel di lapangan
 * maupun oleh mata yang tidak lagi muda. Ukuran di bawah `2xs` sengaja tidak disediakan.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  // Kelas `dark` pada <html>, bukan `prefers-color-scheme` langsung: pilihan pengguna harus
  // dapat mengalahkan setelan sistem, dan itu mustahil bila mode gelap hanya media query.
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        base: {
          950: "rgb(var(--surface-app) / <alpha-value>)", // latar aplikasi
          900: "rgb(var(--surface-panel) / <alpha-value>)", // latar panel
          850: "rgb(var(--surface-raised) / <alpha-value>)", // latar yang ditinggikan
          800: "rgb(var(--line) / <alpha-value>)", // garis panel / hover
          700: "rgb(var(--line-strong) / <alpha-value>)",
          600: "rgb(var(--line-stronger) / <alpha-value>)",
        },
        ink: {
          DEFAULT: "rgb(var(--text) / <alpha-value>)",
          muted: "rgb(var(--text-muted) / <alpha-value>)",
          faint: "rgb(var(--text-faint) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "rgb(var(--accent) / <alpha-value>)",
          soft: "rgb(var(--accent-soft) / <alpha-value>)",
          deep: "rgb(var(--accent-deep) / <alpha-value>)",
        },
        risk: {
          low: "rgb(var(--risk-low) / <alpha-value>)",
          moderate: "rgb(var(--risk-moderate) / <alpha-value>)",
          high: "rgb(var(--risk-high) / <alpha-value>)",
          critical: "rgb(var(--risk-critical) / <alpha-value>)",
        },
      },
      fontSize: {
        // Lantai tangga. Untuk lencana dan label mikro — bukan untuk kalimat.
        "2xs": ["0.75rem", { lineHeight: "1rem" }], // 12px
        xs: ["0.8125rem", { lineHeight: "1.125rem" }], // 13px
        sm: ["0.875rem", { lineHeight: "1.375rem" }], // 14px
        base: ["1rem", { lineHeight: "1.625rem" }], // 16px
      },
      fontFamily: {
        heading: ["var(--font-heading)", "system-ui", "sans-serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "var(--shadow-panel)",
        glow: "var(--shadow-glow)",
      },
    },
  },
  plugins: [],
};

export default config;
