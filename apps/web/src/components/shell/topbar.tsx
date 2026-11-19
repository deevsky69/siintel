"use client";

import { Clock } from "./clock";
import { ThemeToggle } from "./theme-toggle";

/**
 * Topbar: identitas sistem, satuan wilayah, jam WIB, tema, dan pengguna aktif.
 *
 * ## Apa yang menghilang lebih dulu saat layar menyempit
 *
 * Urutannya disengaja, dari yang paling mudah dilepas:
 *
 * ```text
 * < 1280px  nama satuan di tengah, anak judul, dan jam
 * < 1024px  tautan Modul dan nama pengguna
 * ```
 *
 * Yang tidak pernah hilang: tombol menu, nama sistem, lonceng antrean, dan tombol keluar.
 * Selain nama sistem, ketiganya tindakan; sisanya keterangan.
 *
 * **Nama sistem tidak pernah dipendekkan.** Sebelum aturan ini ia dibiarkan terpotong
 * menjadi "PREDIK…" pada lebar tablet — bilah yang memperkenalkan sistem lalu gagal
 * menyebut namanya. Yang dilepas lebih dulu adalah keterangan di sekelilingnya.
 */
export function Topbar({
  name,
  roleName,
  notifications,
  onMenu,
}: {
  name: string;
  roleName: string;
  /** Lonceng antrean pekerjaan; dirakit di layout supaya bilah ini tetap murni tampilan. */
  notifications?: React.ReactNode;
  /** Membuka laci navigasi. Hanya dipakai pada layar sempit. */
  onMenu?: () => void;
}) {
  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-base-800 bg-base-900/70 px-3 sm:h-16 sm:gap-5 sm:px-5">
      <button
        type="button"
        onClick={onMenu}
        aria-label="Buka menu navigasi"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded border border-base-700 text-ink-muted transition hover:border-accent/40 hover:text-accent lg:hidden"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <path d="M4 7h16M4 12h16M4 17h16" />
        </svg>
      </button>

      {/* Jenama dan satuan dalam SATU blok yang boleh menyusut (`min-w-0` + `truncate`).
          Sebelumnya nama satuan berdiri sendiri di tengah dengan `flex-1`, diapit dua blok
          `shrink-0`: pada layar 1280–1500 px sisa ruangnya hanya ±250 px, sehingga teksnya
          terlipat dua baris dan menabrak tulisan di kiri-kanannya. */}
      <div className="flex min-w-0 items-center gap-2.5">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-accent/30 bg-accent/10 font-heading text-sm font-bold text-accent sm:h-10 sm:w-10">
          S
        </div>
        <div className="min-w-0 leading-tight">
          <div className="flex min-w-0 items-baseline gap-2.5">
            <span className="shrink-0 font-heading text-sm font-bold tracking-wide text-ink sm:text-base">
              SIGAP
            </span>
            <span className="hidden truncate text-2xs uppercase tracking-[0.12em] text-ink-faint 2xl:block">
              Sistem Intelijen Geospasial dan Analitik Prediktif
            </span>
          </div>
          <div className="hidden truncate font-heading text-2xs font-semibold uppercase tracking-[0.14em] text-ink-muted sm:block">
            Polres Metro Jakarta Selatan
          </div>
        </div>
      </div>

      <div className="ml-auto flex shrink-0 items-center gap-2 sm:gap-4">
        {/* Modul penggunaan disajikan sebagai halaman berdiri sendiri di `public/`,
            bukan di dalam shell aplikasi: ia punya tata letak dan gaya cetaknya
            sendiri. Middleware tetap melindunginya seperti halaman lain. */}
        <a
          href="/modul.html"
          target="_blank"
          rel="noopener"
          className="hidden rounded border border-base-700 px-2.5 py-1.5 font-heading text-2xs uppercase tracking-wider text-ink-muted transition hover:border-accent/40 hover:text-accent lg:block"
        >
          Modul
        </a>
        <ThemeToggle />
        {notifications}
        <div className="hidden xl:block">
          <Clock />
        </div>
        <div className="flex items-center gap-2 border-l border-base-800 pl-2 sm:pl-4">
          <div className="hidden text-right leading-tight lg:block">
            <div className="max-w-[160px] truncate text-xs font-semibold text-ink">{name}</div>
            <div className="text-2xs uppercase tracking-wider text-ink-muted">{roleName}</div>
          </div>
          <form action="/api/auth/logout" method="post">
            <button
              type="submit"
              className="rounded border border-base-700 px-2.5 py-1.5 text-2xs uppercase tracking-wider text-ink-muted transition hover:border-accent/40 hover:text-accent"
            >
              Keluar
            </button>
          </form>
        </div>
      </div>
    </header>
  );
}
