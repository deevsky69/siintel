"use client";

import type { EntryState } from "./entry-state";

/**
 * Hasil satu percobaan menyimpan: kalimat kegagalan, atau kode yang terbentuk.
 *
 * Dua hal yang dijaga di sini dan sama untuk ketiga formulir:
 *
 * - **Kegagalan ditampilkan sebagai kalimat, bukan kode.** Petugas piket tidak membaca
 *   `404`; ia membaca "berada di luar cakupan wilayah akun Anda" (CLAUDE.md §23).
 * - **Keberhasilan menampilkan kode yang terbentuk.** Tanpa kode, baris yang baru ditulis
 *   tidak dapat ditelusuri kembali di layar lain — dan pemasukan data yang tidak dapat
 *   ditelusuri tidak dapat diperiksa.
 */
export function EntryFeedback({ state, noun }: { state: EntryState; noun: string }) {
  if (state.error) {
    return (
      <p
        role="alert"
        className="mt-4 rounded border border-risk-critical/40 bg-risk-critical/10 px-3 py-2 text-xs leading-relaxed text-risk-critical"
      >
        {state.error}
      </p>
    );
  }

  if (!state.done) return null;

  return (
    <div
      role="status"
      className="mt-4 rounded border border-risk-low/40 bg-risk-low/10 px-3 py-2 text-xs leading-relaxed text-risk-low"
    >
      <span>{noun} tersimpan dengan kode </span>
      <span className="font-mono font-semibold">{state.done.code}</span>
      <span className="mt-1 block text-2xs text-ink-muted">{state.done.detail}</span>
    </div>
  );
}
