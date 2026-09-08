"use client";

import { useEffect, useState } from "react";
import { applyThemeChoice, readThemeChoice, type ThemeChoice } from "@/lib/theme";

const ORDER: readonly ThemeChoice[] = ["system", "light", "dark"];

const LABEL: Record<ThemeChoice, string> = {
  system: "Ikut perangkat",
  light: "Terang",
  dark: "Gelap",
};

/**
 * Pengalih tema: sistem → terang → gelap → sistem.
 *
 * ## Mengapa tiga keadaan dan bukan satu sakelar
 *
 * Sakelar dua keadaan memaksa pengguna memilih, dan sekali memilih ia terkunci: ponsel yang
 * beralih gelap sendiri saat malam tidak lagi diikuti. Keadaan "ikut perangkat" adalah yang
 * bawaan, dan hanya ditinggalkan bila pengguna benar-benar menghendaki sesuatu yang lain.
 *
 * ## Mengapa ikonnya baru muncul setelah terpasang
 *
 * Server tidak tahu tema pengguna — ia ada di `localStorage` dan pada setelan perangkat,
 * keduanya hanya terbaca di peramban. Menggambar tebakan lalu memperbaikinya menghasilkan
 * ikon yang berkedip berganti pada setiap pemuatan. Karena itu tombol digambar dengan
 * ruang yang sama tetapi tanpa isi sampai nilainya diketahui.
 */
export function ThemeToggle() {
  const [choice, setChoice] = useState<ThemeChoice | null>(null);

  useEffect(() => {
    setChoice(readThemeChoice());
  }, []);

  // Saat "ikut perangkat", perubahan setelan sistem harus langsung terasa — pengguna yang
  // menyalakan mode gelap ponselnya tidak akan memuat ulang halaman ini untuk membuktikannya.
  useEffect(() => {
    if (choice !== "system") return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const follow = () => applyThemeChoice("system");
    media.addEventListener("change", follow);
    return () => media.removeEventListener("change", follow);
  }, [choice]);

  const next = () => {
    const value = ORDER[(ORDER.indexOf(choice ?? "system") + 1) % ORDER.length];
    setChoice(value);
    applyThemeChoice(value);
  };

  return (
    <button
      type="button"
      onClick={next}
      title={choice ? `Tema: ${LABEL[choice]}. Klik untuk mengganti.` : "Tema"}
      aria-label={choice ? `Tema ${LABEL[choice]}, ganti tema` : "Ganti tema"}
      className="flex h-9 w-9 items-center justify-center rounded border border-base-700 text-ink-muted transition hover:border-accent/40 hover:text-accent"
    >
      {choice === null ? null : choice === "dark" ? (
        <MoonIcon />
      ) : choice === "light" ? (
        <SunIcon />
      ) : (
        <DeviceIcon />
      )}
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

function DeviceIcon() {
  return (
    <svg {...STROKE} aria-hidden="true">
      <rect x="2" y="4" width="20" height="13" rx="2" />
      <path d="M8 21h8M12 17v4" />
    </svg>
  );
}
