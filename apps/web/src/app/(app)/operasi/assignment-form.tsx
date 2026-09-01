"use client";

import { useActionState } from "react";
import type { PoliceUnitRow } from "@/lib/operations";
import { assign } from "./actions";
import { ASSIGNMENT_IDLE } from "./operation-state";

/**
 * Formulir mencatat penugasan lapangan dari sebuah keputusan.
 *
 * Formulir ini tidak memutuskan apa pun: keputusannya sudah diambil pejabat di layar
 * `/rekomendasi`. Yang dicatat di sini adalah **pelaksanaannya** — siapa yang ditugaskan
 * dan sejak kapan (CLAUDE.md §9, §13).
 *
 * Formulir disembunyikan bagi peran tanpa `operation:write`, tetapi itu hanya kenyamanan:
 * penolakan sesungguhnya terjadi di backend (CLAUDE.md §21).
 */

/**
 * Label fungsi dan status satuan ditulis ulang di berkas klien ini dengan sengaja.
 *
 * Mengimpornya dari `@/lib/decisions` atau `@/lib/operations` akan ikut menarik
 * `@/lib/api`, dan modul itu memuat `next/headers` yang tidak boleh masuk bundel peramban.
 * Isinya mengikuti `docs/02-data-dictionary.md`.
 */
const FUNCTION_LABELS: Record<string, string> = {
  SAMAPTA: "Samapta",
  BINMAS: "Binmas",
  INTELKAM: "Intelkam",
  RESKRIM: "Reskrim",
  LANTAS: "Lantas",
};

const UNIT_STATUS_LABELS: Record<string, string> = {
  ACTIVE: "Aktif",
  STANDBY: "Standby",
};

const FIELD =
  "mt-1.5 w-full rounded border border-base-700 bg-base-950/60 px-3 py-2 text-sm text-ink outline-none focus:border-accent";

export function AssignmentForm({
  decisionCode,
  units,
  scopeBasis,
}: {
  decisionCode: string;
  units: PoliceUnitRow[];
  /** Keterangan cakupan dari `/police-units`; menjelaskan mengapa daftarnya berisi ini. */
  scopeBasis: string | null;
}) {
  const [state, submit, pending] = useActionState(assign, ASSIGNMENT_IDLE);

  if (units.length === 0) {
    // Daftar berasal dari `/police-units` dan sudah disaring backend menurut cakupan
    // pengguna. Bila kosong, keadaannya dinyatakan apa adanya — bukan diisi daftar karangan.
    return (
      <p className="mt-4 border-t border-base-800 pt-4 text-xs text-ink-muted">
        Tidak ada satuan yang dapat ditugaskan dalam cakupan akun Anda, sehingga penugasan belum
        dapat dicatat dari layar ini.
      </p>
    );
  }

  return (
    <form action={submit} className="mt-4 border-t border-base-800 pt-4">
      <input type="hidden" name="decision_code" value={decisionCode} />

      <label className="block">
        <span className="stat-label">Satuan yang Ditugaskan</span>
        <select name="unit_code" required defaultValue="" className={FIELD}>
          <option value="" disabled>
            Pilih satuan…
          </option>
          {units.map((unit) => (
            <option key={unit.code} value={unit.code}>
              {unit.unit_name} · {FUNCTION_LABELS[unit.function] ?? unit.function} ·{" "}
              {UNIT_STATUS_LABELS[unit.status] ?? unit.status} ({unit.code})
            </option>
          ))}
        </select>
        <span className="mt-1 block text-[10px] text-ink-muted">
          Satuan berstatus Standby tetap dapat ditugaskan; statusnya ditampilkan agar pilihan
          diambil dengan sadar, bukan disembunyikan dari daftar.
        </span>
        {scopeBasis ? (
          <span className="mt-1 block text-[10px] text-ink-muted">{scopeBasis}</span>
        ) : null}
      </label>

      <label className="mt-3 block">
        <span className="stat-label">Waktu Mulai (WIB)</span>
        <input type="datetime-local" name="start_at" className={FIELD} />
        <span className="mt-1 block text-[10px] text-ink-muted">
          Boleh dikosongkan; sistem memakai waktu acuan aplikasi — jam demo yang beku pada dataset,
          bukan jam dinding.
        </span>
      </label>

      <label className="mt-3 block">
        <span className="stat-label">Catatan Penugasan</span>
        <textarea name="notes" rows={2} className={FIELD} />
      </label>

      {state.error ? (
        <p role="alert" className="mt-3 text-xs text-risk-critical">
          {state.error}
        </p>
      ) : null}

      <button
        type="submit"
        disabled={pending}
        className="mt-3 rounded bg-accent/20 px-4 py-2 font-heading text-[11px] font-semibold uppercase tracking-wider text-accent transition hover:bg-accent/30 disabled:opacity-40"
      >
        {pending ? "Mencatat…" : "Catat Penugasan"}
      </button>
      <p className="mt-2 text-[10px] text-ink-muted">
        Penugasan terikat pada keputusan {decisionCode} dan lokasi prediksi asalnya, serta tercatat
        beserta nama petugas dan waktunya.
      </p>
    </form>
  );
}
