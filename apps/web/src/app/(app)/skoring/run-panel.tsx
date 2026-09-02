"use client";

import { useActionState, useState } from "react";
import { Panel } from "@/components/panel";
import { runAssessment } from "./actions";
import { IDLE } from "./run-state";
import { RunSummary } from "./run-summary";

/**
 * Menjalankan penilaian risiko dari layar.
 *
 * Urutannya disengaja dan tidak dapat dilompati: **uji coba lebih dulu**, hasilnya dibaca,
 * baru penulisan dibuka. Tombol tulis tetap tertutup sampai ada hasil uji coba untuk
 * tanggal yang sama — bukan karena backend memerlukannya (ia menolak sendiri bila tanggal
 * penilaian sudah terpakai), melainkan karena menulis penilaian mengubah angka yang
 * dipakai peta, dashboard, dan brief.
 *
 * Menyembunyikan tombol bagi peran tanpa `risk_score:run` hanyalah kenyamanan; penolakan
 * sesungguhnya terjadi di backend (CLAUDE.md §21).
 */
export function RunPanel({ canRun, referenceDate }: { canRun: boolean; referenceDate: string }) {
  const [state, submit, pending] = useActionState(runAssessment, IDLE);
  const [assessmentDate, setAssessmentDate] = useState("");

  const preview = state.result?.dry_run ? state.result : null;
  const previewMatchesDate =
    preview !== null && (assessmentDate === "" || preview.assessment_date === assessmentDate);

  return (
    <Panel
      title="Jalankan Penilaian"
      action={<span className="panel-action">waktu acuan {referenceDate}</span>}
    >
      {canRun ? (
        <form action={submit} className="space-y-3">
          <label className="block max-w-xs">
            <span className="stat-label">Tanggal Penilaian</span>
            <input
              type="date"
              name="assessment_date"
              value={assessmentDate}
              onChange={(event) => setAssessmentDate(event.target.value)}
              className="mt-1.5 w-full rounded border border-base-700 bg-base-950/60 px-3 py-2 text-sm text-ink outline-none focus:border-accent"
            />
            <span className="mt-1 block text-[10px] text-ink-muted">
              Kosong berarti tanggal pada waktu acuan aplikasi ({referenceDate}).
            </span>
          </label>

          <div className="flex flex-wrap gap-2">
            <button
              type="submit"
              name="mode"
              value="uji"
              disabled={pending}
              className="rounded border border-accent/50 px-4 py-2 font-heading text-[11px] font-semibold uppercase tracking-wider text-accent transition hover:bg-accent/10 disabled:opacity-40"
            >
              {pending ? "Menghitung…" : "Uji Coba"}
            </button>
            <button
              type="submit"
              name="mode"
              value="tulis"
              disabled={pending || !previewMatchesDate}
              className="rounded border border-risk-high/50 px-4 py-2 font-heading text-[11px] font-semibold uppercase tracking-wider text-risk-high transition hover:bg-risk-high/10 disabled:opacity-40"
            >
              Tulis Penilaian
            </button>
          </div>

          <p className="text-[10px] leading-relaxed text-ink-muted">
            {previewMatchesDate
              ? "Hasil uji coba di bawah belum tersimpan. Menulis akan menambah baris penilaian baru dan tidak dapat menimpa tanggal penilaian yang sudah terpakai."
              : "Jalankan uji coba lebih dulu. Hasilnya ditampilkan sebelum ada satu baris pun yang ditulis."}
          </p>
        </form>
      ) : (
        <p className="text-[11px] leading-relaxed text-ink-muted">
          Akun Anda tidak memiliki kewenangan <code>risk_score:run</code>, sehingga penilaian hanya
          dapat dibaca dari layar ini. Dasar perhitungan di atas tetap terbuka untuk diperiksa.
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
