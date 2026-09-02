/**
 * Keadaan ketiga formulir pemasukan data.
 *
 * Dipisahkan dari `actions.ts` karena berkas `"use server"` hanya boleh mengekspor fungsi
 * async: mengekspor nilai dari sana membuat Next menolak seluruh modul ketika action
 * dipanggil — kegagalan yang tidak terlihat oleh `next build` maupun test, dan baru muncul
 * sebagai 500 saat tombol pertama kali ditekan. Lihat `app/server-actions.test.ts`.
 */

/**
 * Hasil satu percobaan menyimpan.
 *
 * `done` membawa kode yang terbentuk beserta keterangan singkatnya. Kode itu wajib
 * ditampilkan: tanpa kode, pengisi tidak punya apa pun untuk menelusuri barisnya kembali
 * di layar lain — dan pemasukan data yang tidak dapat ditelusuri sama saja dengan
 * pemasukan data yang tidak dapat diperiksa (CLAUDE.md §37, prioritas *Traceability*).
 */
export type EntryState = {
  error: string | null;
  done: { code: string; detail: string } | null;
};

export const ENTRY_IDLE: EntryState = { error: null, done: null };
