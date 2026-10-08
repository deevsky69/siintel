"use client";

import { useEffect, useState } from "react";
import { applyThemeChoice, readThemeChoice, resolveTheme } from "@/lib/theme";

type Theme = "light" | "dark";

const LABEL: Record<Theme, string> = { light: "Terang", dark: "Gelap" };

/**
 * Pengalih tema: terang ↔ gelap.
 *
 * ## Mengapa dua keadaan, bukan tiga
 *
 * Sampai 8 Oktober 2026 tombol ini berputar sistem → terang → gelap, dengan ikon monitor
 * untuk "ikut perangkat". Pemilik proyek memutuskan: dua ikon saja. Keadaan ketiga membuat
 * tombol harus ditekan dua kali untuk sampai ke tema yang diinginkan, dan ikon monitornya
 * tidak dimengerti siapa pun. Setelan perangkat tetap dipakai sebagai tema AWAL sebelum
 * pengguna pernah memilih (lihat `THEME_BOOTSTRAP`); setelah memilih, pilihannya diingat.
 *
 * ## Mengapa ikonnya baru muncul setelah terpasang
 *
 * Server tidak tahu tema pengguna — ia ada di `localStorage` dan pada setelan perangkat,
 * keduanya hanya terbaca di peramban. Menggambar tebakan lalu memperbaikinya menghasilkan
 * ikon yang berkedip berganti pada setiap pemuatan. Karena itu tombol digambar dengan
 * ruang yang sama tetapi tanpa isi sampai nilainya diketahui.
 */
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme | null>(null);

  useEffect(() => {
    setTheme(resolveTheme(readThemeChoice()));
  }, []);

  const next = () => {
    const value: Theme = (theme ?? "dark") === "dark" ? "light" : "dark";
    setTheme(value);
    applyThemeChoice(value);
  };

  return (
    <button
      type="button"
      onClick={next}
      title={theme ? `Tema: ${LABEL[theme]}. Klik untuk mengganti.` : "Tema"}
      aria-label={theme ? `Tema ${LABEL[theme]}, ganti tema` : "Ganti tema"}
      className="flex h-9 w-9 items-center justify-center rounded border border-base-700 text-ink-muted transition hover:border-accent/40 hover:text-accent"
    >
      {theme === null ? null : theme === "dark" ? <MoonIcon /> : <SunIcon />}
    </button>
  );
}

const STROKE = {
  width: 18,
  height: 18,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;

function SunIcon() {
  return (
    <svg {...STROKE} aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg {...STROKE} aria-hidden="true">
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" />
    </svg>
  );
}
