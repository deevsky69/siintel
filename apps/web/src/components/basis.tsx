/**
 * Keterangan asal angka (`*_basis` dari API), DILIPAT secara bawaan.
 *
 * Keputusan pemilik proyek 8 Oktober 2026: layar terlalu padat informasi. Kalimat dasar
 * perhitungan ("nilai per kecamatan adalah hasil agregasi sel grid di lapisan API…") tetap
 * ada — ketertelusuran tidak dilepas (CLAUDE.md §27, §41) — tetapi baru terbuka bila
 * pembaca memintanya. Elemen `<details>` asli: bekerja tanpa JavaScript, tanpa keadaan,
 * aman dipakai dari komponen server.
 *
 * `getByText` pada test tetap menemukan isinya: isi `<details>` tertutup ada di DOM.
 */
import type { ReactNode } from "react";

export function Basis({
  children,
  label = "Dasar perhitungan",
  className = "",
}: {
  children: ReactNode;
  label?: string;
  className?: string;
}) {
  return (
    <details className={`group mt-2 ${className}`}>
      <summary className="inline-flex cursor-pointer select-none list-none items-center gap-1 text-2xs uppercase tracking-wider text-ink-faint transition-colors hover:text-accent [&::-webkit-details-marker]:hidden">
        <span aria-hidden="true" className="group-open:hidden">
          +
        </span>
        <span aria-hidden="true" className="hidden group-open:inline">
          −
        </span>
        {label}
      </summary>
      <div className="mt-1 space-y-1 text-2xs leading-relaxed text-ink-faint">{children}</div>
    </details>
  );
}

/** Varian untuk penjelasan WHY (faktor dominan): label bertanya, isi lebih terbaca. */
export function Why({
  children,
  label = "Mengapa? Lihat faktor penjelas",
  className = "",
}: {
  children: ReactNode;
  label?: string;
  className?: string;
}) {
  return (
    <details className={`group mt-2 rounded border border-base-800 px-3 py-2 ${className}`}>
      <summary className="inline-flex cursor-pointer select-none list-none items-center gap-1.5 text-xs font-semibold text-accent transition-colors hover:text-accent-soft [&::-webkit-details-marker]:hidden">
        <span aria-hidden="true" className="group-open:hidden">
          +
        </span>
        <span aria-hidden="true" className="hidden group-open:inline">
          −
        </span>
        {label}
      </summary>
      <div className="mt-2">{children}</div>
    </details>
  );
}
