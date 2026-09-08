"use client";

import { useActionState, useState } from "react";
import { Panel } from "@/components/panel";
import { submitRun } from "./actions";
import { HORIZONS, horizonLabel } from "./display";
import { IDLE_RUN } from "./run-state";
import { RunSummary } from "./run-summary";

/**
 * Menjalankan prediksi dari layar.
 *
 * Urutannya disengaja dan tidak dapat dilompati: **uji coba lebih dulu**, hasilnya dibaca,
 * baru penulisan dibuka. Tombol tulis tetap tertutup sampai ada hasil uji coba untuk
 * tanggal dan horizon yang sama — bukan karena backend memerlukannya (ia menolak sendiri
 * bila tanggal + horizon sudah terpakai), melainkan karena satu kali menulis menambah
 * ratusan baris yang akan terbaca di peta dan Warning Center.
 *
 * Seluruh yang diimpor berkas ini murni: `./display` tidak menarik `@/lib/api`, sehingga
 * tidak ada `next/headers` yang ikut masuk ke bundel peramban.
 */
export function RunPanel({ canRun, referenceDate }: { canRun: boolean; referenceDate: string }) {
  const [state, submit, pending] = useActionState(submitRun, IDLE_RUN);
  const [predictionDate, setPredictionDate] = useState("");
  const [horizon, setHorizon] = useState<string>("24H");

  const preview = state.result?.dry_run ? state.result : null;
  const previewMatches =
    preview !== null &&
    preview.horizon === horizon &&
    (predictionDate === "" || preview.prediction_date === predictionDate);

  return (
    <Panel
      title="Jalankan Prediksi"
      action={<span className="panel-action">waktu acuan {referenceDate}</span>}
    >
      <p className="mb-3 rounded border border-base-800 bg-base-950/40 px-3 py-2 text-2xs leading-relaxed text-ink-muted">
        Prediksi di sini <strong>bukan keluaran model terlatih</strong>. Ia proyeksi persistensi
        berbasis aturan atas penilaian risiko yang sudah ada: <code>model_version</code> menyebut
        versi aturan, bukan nama model, dan setiap faktor penjelas berlabel <code>RULE</code> — sama
        seperti label pada peta.
      </p>

      {canRun ? (
        <form action={submit} className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <label className="block">
              <span className="stat-label">Tanggal Prediksi</span>
              <input
                type="date"
                name="prediction_date"
                value={predictionDate}
                onChange={(event) => setPredictionDate(event.target.value)}
                className="mt-1.5 w-full rounded border border-base-700 bg-base-950/60 px-3 py-2 text-sm text-ink outline-none focus:border-accent"
              />
              <span className="mt-1 block text-2xs text-ink-muted">
                Kosong berarti tanggal pada waktu acuan aplikasi ({referenceDate}).
              </span>
            </label>

            <label className="block">
              <span className="stat-label">Horizon</span>
              <select
                name="horizon"
                value={horizon}
                onChange={(event) => setHorizon(event.target.value)}
                className="mt-1.5 w-full rounded border border-base-700 bg-base-950/60 px-3 py-2 text-sm text-ink outline-none focus:border-accent"
              >
                {HORIZONS.map((item) => (
                  <option key={item} value={item}>
                    {item} — {horizonLabel(item)} ke depan
                  </option>
                ))}
              </select>
              <span className="mt-1 block text-2xs text-ink-muted">
                Jarak dari tanggal prediksi ke hari yang diprediksi — bukan panjang rentang. Setiap
                horizon menghasilkan keempat jendela 6 jam pada hari sasarannya, sehingga jumlah
                barisnya sama untuk semua horizon.
              </span>
            </label>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              name="mode"
              value="uji"
              disabled={pending}
              className="rounded border border-accent/50 px-4 py-2 font-heading text-xs font-semibold uppercase tracking-wider text-accent transition hover:bg-accent/10 disabled:opacity-40"
            >
              {pending ? "Menghitung…" : "Uji Coba"}
            </button>
            <button
              type="submit"
              name="mode"
              value="tulis"
              disabled={pending || !previewMatches}
              className="rounded border border-risk-high/50 px-4 py-2 font-heading text-xs font-semibold uppercase tracking-wider text-risk-high transition hover:bg-risk-high/10 disabled:opacity-40"
            >
              Tulis Prediksi
            </button>
          </div>

          <p className="text-2xs leading-relaxed text-ink-muted">
            {previewMatches
              ? "Hasil uji coba di bawah belum tersimpan. Menulis akan menambah baris berstatus DRAFT — belum terbit, dan belum melahirkan peringatan apa pun."
              : "Jalankan uji coba lebih dulu untuk tanggal dan horizon yang dipilih. Hasilnya ditampilkan sebelum ada satu baris pun yang ditulis."}
          </p>
        </form>
      ) : (
        <p className="text-xs leading-relaxed text-ink-muted">
          Akun Anda tidak memiliki kewenangan <code>prediction:run</code>, sehingga prediksi hanya
          dapat dibaca dari layar ini. Dasar setiap prediksi tetap terbuka untuk diperiksa.
        </p>
      )}

      {state.error ? (
        <p role="alert" className="mt-3 text-xs text-risk-critical">
          {state.error}
        </p>
      ) : null}

      {state.result ? (
        <div className="mt-4 border-t border-base-800 pt-4">
          <RunSummary result={state.result} />
        </div>
      ) : null}
    </Panel>
  );
}
