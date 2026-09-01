"use client";

import { useActionState, useState } from "react";
import type { ResultStatus } from "@/lib/operations";
import { record } from "./actions";
import { RESULT_IDLE } from "./operation-state";

/**
 * Formulir mencatat hasil nyata di lapangan.
 *
 * Inilah yang menutup rantai: tanpa hasil nyata, evaluasi tidak dapat menghitung berapa
 * prediksi yang terbukti dan berapa yang meleset (CLAUDE.md §9, §26).
 *
 * "Dibatalkan" berdiri sejajar dengan "Selesai" dan bukan pilihan tersembunyi: penugasan
 * yang tidak jadi dijalankan adalah kenyataan yang harus tercatat, bukan yang disamarkan
 * agar angka keberhasilan terlihat bagus.
 */

/** Label tombol berupa kata kerja/keadaan akhir; kelas ditulis utuh agar Tailwind memindainya. */
const CHOICES: { value: ResultStatus; label: string; tone: string }[] = [
  {
    value: "COMPLETED",
    label: "Selesai",
    tone: "border-risk-low/50 text-risk-low hover:bg-risk-low/10",
  },
  {
    value: "CANCELLED",
    label: "Dibatalkan",
    tone: "border-risk-critical/50 text-risk-critical hover:bg-risk-critical/10",
  },
];

const FIELD =
  "mt-1.5 w-full rounded border border-base-700 bg-base-950/60 px-3 py-2 text-sm text-ink outline-none focus:border-accent";

export function ResultForm({
  code,
  startHint,
}: {
  code: string;
  /** Waktu mulai penugasan yang sudah diformat, sebagai batas bawah waktu selesai. */
  startHint: string;
}) {
  const [state, submit, pending] = useActionState(record, RESULT_IDLE);
  const [choice, setChoice] = useState<ResultStatus | null>(null);

  return (
    <form action={submit} className="mt-4 border-t border-base-800 pt-4">
      <input type="hidden" name="code" value={code} />
      <input type="hidden" name="status" value={choice ?? ""} />

      <fieldset>
        <legend className="stat-label">Keadaan Akhir Penugasan</legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {CHOICES.map((item) => (
            <button
              key={item.value}
              type="button"
              aria-pressed={choice === item.value}
              onClick={() => setChoice(choice === item.value ? null : item.value)}
              className={[
                "rounded border px-3 py-1.5 font-heading text-[11px] font-semibold uppercase tracking-wider transition",
                item.tone,
                choice === item.value ? "bg-base-800" : "",
              ].join(" ")}
            >
              {item.label}
            </button>
          ))}
        </div>
      </fieldset>

      {choice ? (
        <>
          <label className="mt-3 block">
            <span className="stat-label">
              {choice === "CANCELLED" ? "Alasan Pembatalan" : "Hasil Nyata di Lapangan"}
            </span>
            <textarea name="result" rows={3} required className={FIELD} />
            <span className="mt-1 block text-[10px] text-ink-muted">
              Uraikan apa yang benar-benar terjadi, termasuk bila tidak ada kejadian sama sekali.
              Hasil inilah yang dibandingkan dengan prediksi saat evaluasi.
            </span>
          </label>

          <label className="mt-3 block">
            <span className="stat-label">Waktu Selesai (WIB)</span>
            <input type="datetime-local" name="end_at" required className={FIELD} />
            <span className="mt-1 block text-[10px] text-ink-muted">
              Wajib diisi dan harus setelah waktu mulai ({startHint}). Durasi penugasan tidak
              diisikan otomatis agar tidak ada waktu yang dikarang.
            </span>
          </label>
        </>
      ) : null}

      {state.error ? (
        <p role="alert" className="mt-3 text-xs text-risk-critical">
          {state.error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={pending || choice === null}
        className="mt-3 rounded bg-accent/20 px-4 py-2 font-heading text-[11px] font-semibold uppercase tracking-wider text-accent transition hover:bg-accent/30 disabled:opacity-40"
      >
        {pending ? "Mencatat…" : "Catat Hasil Nyata"}
      </button>
      <p className="mt-2 text-[10px] text-ink-muted">
        Hasil hanya dapat dicatat sekali; setelah tercatat, tindakan {code} berstatus akhir dan
        tidak dapat diubah dari layar ini.
      </p>
    </form>
  );
}
