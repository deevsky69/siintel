"use client";

import { useActionState } from "react";
import type { StatusState } from "@/app/(app)/laporan-petugas/actions";

/**
 * Pengubah status satu baris, langsung di tempat barisnya terlihat.
 *
 * Diletakkan di daftar, bukan di formulir tersendiri, karena pertanyaan yang memicunya
 * — "bagaimana cara mengganti status?" — muncul justru saat seseorang sedang menatap
 * daftarnya. Formulir yang berada di layar lain menuntut pengguna mengingat kode barisnya
 * dan berpindah dua kali.
 *
 * Formulir triase pada `Input Data` tetap ada dan tidak dihapus: ia berguna ketika
 * beberapa laporan ditriase berurutan tanpa mencarinya satu per satu.
 */
export function StatusForm({
  code,
  current,
  options,
  action,
}: {
  code: string;
  current: string | null;
  /** Nilai tersimpan → label yang dibaca pengguna. */
  options: Record<string, string>;
  action: (previous: StatusState, form: FormData) => Promise<StatusState>;
}) {
  const [state, submit, pending] = useActionState<StatusState, FormData>(action, {
    error: null,
    done: null,
  });

  return (
    <form action={submit} className="flex flex-wrap items-center gap-1.5">
      <input type="hidden" name="code" value={code} />
      <select
        name="status"
        defaultValue=""
        aria-label={`Status baru untuk ${code}`}
        className="rounded border border-base-700 bg-base-950 px-1.5 py-1 text-2xs text-ink focus:border-accent/60 focus:outline-none"
      >
        <option value="" disabled>
          Ubah ke…
        </option>
        {Object.entries(options)
          // Status yang sedang berlaku dibuang dari pilihan: memilihnya dijawab 409 oleh
          // backend, dan menawarkan pilihan yang pasti ditolak hanya memancing kekeliruan.
          .filter(([value]) => value !== current)
          .map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
      </select>
      <button
        type="submit"
        disabled={pending}
        className="rounded border border-accent/40 bg-accent/10 px-2 py-1 text-2xs uppercase tracking-wider text-accent transition-colors hover:bg-accent/20 disabled:opacity-50"
      >
        {pending ? "…" : "Simpan"}
      </button>
      {state.error ? (
        <span role="alert" className="text-2xs text-risk-critical">
          {state.error}
        </span>
      ) : null}
      {state.done ? <span className="text-2xs text-risk-moderate">Tersimpan</span> : null}
    </form>
  );
}
