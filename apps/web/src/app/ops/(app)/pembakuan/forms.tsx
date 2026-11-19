"use client";

import { useActionState } from "react";
import type { MatchCandidate } from "@/lib/standardization";
import {
  confirmAreaAction,
  impactAction,
  matchAction,
  resolveDuplicateAction,
  type StandardState,
} from "./actions";

const IDLE: StandardState = { error: null, done: null };
const field = "rounded border border-base-700 bg-base-850 px-2 py-1 text-xs text-ink";
const button = "rounded border px-2.5 py-1 text-xs font-semibold disabled:opacity-50";

export function AreaForm({
  code,
  options,
}: {
  code: string;
  options: { code: string; kelurahan: string }[];
}) {
  const [state, submit, pending] = useActionState(confirmAreaAction, IDLE);
  if (state.done) return <span className="text-xs text-risk-low">{state.done}</span>;
  return (
    <form action={submit} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="code" value={code} />
      <select name="location_code" required className={field} defaultValue="">
        <option value="" disabled>
          Kelurahan…
        </option>
        {options.map((option) => (
          <option key={option.code} value={option.code}>
            {option.kelurahan}
          </option>
        ))}
      </select>
      <input name="note" placeholder="Catatan" className={field} />
      <button
        type="submit"
        disabled={pending}
        className={`${button} border-accent/60 bg-accent/10 text-accent`}
      >
        Pastikan
      </button>
      {state.error ? <span className="text-xs text-risk-critical">{state.error}</span> : null}
    </form>
  );
}

export function DuplicateForm({ code }: { code: string }) {
  const [state, submit, pending] = useActionState(resolveDuplicateAction, IDLE);
  if (state.done) return <span className="text-xs text-risk-low">{state.done}</span>;
  return (
    <form action={submit} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="code" value={code} />
      <input name="note" required placeholder="Alasan (wajib)" className={field} />
      <button
        type="submit"
        name="status"
        value="CONFIRMED"
        disabled={pending}
        className={`${button} border-risk-high/60 bg-risk-high/10 text-risk-high`}
      >
        Ganda
      </button>
      <button
        type="submit"
        name="status"
        value="CLEARED"
        disabled={pending}
        className={`${button} border-risk-low/60 bg-risk-low/10 text-risk-low`}
      >
        Bukan ganda
      </button>
      {state.error ? <span className="text-xs text-risk-critical">{state.error}</span> : null}
    </form>
  );
}

/**
 * Keputusan kecocokan laporan warga. Pilihan kosong berarti "tidak ada padanan resmi" —
 * laporan menjadi kejadian tambahan terverifikasi. Sistem hanya mengusulkan; alasan wajib.
 */
export function MatchForm({ code, candidates }: { code: string; candidates: MatchCandidate[] }) {
  const [state, submit, pending] = useActionState(matchAction, IDLE);
  if (state.done) return <span className="text-xs text-risk-low">{state.done}</span>;
  return (
    <form action={submit} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="code" value={code} />
      <select name="incident_code" defaultValue="" aria-label="Kejadian padanan" className={field}>
        <option value="">Tidak ada padanan resmi</option>
        {candidates.map((row) => (
          <option key={row.code} value={row.code}>
            {row.code} · {row.incident_type} · {row.incident_date} ·{" "}
            {row.kelurahan ?? row.kecamatan}
          </option>
        ))}
      </select>
      <input name="reason" required placeholder="Alasan (wajib)" className={field} />
      <button
        type="submit"
        disabled={pending}
        className={`${button} border-accent/60 bg-accent/10 text-accent`}
      >
        Simpan keputusan
      </button>
      {state.error ? <span className="text-xs text-risk-critical">{state.error}</span> : null}
    </form>
  );
}

/** Isian dampak (naskah Lampiran 9): kerugian, cedera, status verifikasi, dan sumbernya. */
export function ImpactForm({ code }: { code: string }) {
  const [state, submit, pending] = useActionState(impactAction, IDLE);
  if (state.done) return <span className="text-xs text-risk-low">{state.done}</span>;
  return (
    <form action={submit} className="flex flex-wrap items-center gap-2">
      <input type="hidden" name="code" value={code} />
      <select name="loss_status" defaultValue="PRESENT" aria-label="Kerugian" className={field}>
        <option value="PRESENT">Ada kerugian/kerusakan</option>
        <option value="NONE">Tanpa kerugian</option>
        <option value="UNKNOWN">Belum diketahui</option>
      </select>
      <select name="injury_level" defaultValue="NONE" aria-label="Cedera" className={field}>
        <option value="NONE">Tanpa cedera</option>
        <option value="INJURY">Cedera</option>
        <option value="SEVERE">Cedera berat</option>
        <option value="DEATH">Meninggal</option>
        <option value="UNKNOWN">Belum diketahui</option>
      </select>
      <select name="status" defaultValue="VERIFIED" aria-label="Status" className={field}>
        <option value="VERIFIED">Terverifikasi</option>
        <option value="PENDING">Menunggu pemeriksaan</option>
        <option value="NEEDS_CLARIFICATION">Perlu klarifikasi</option>
      </select>
      <input name="source" required placeholder="Rujukan sumber (wajib)" className={field} />
      <button
        type="submit"
        disabled={pending}
        className={`${button} border-accent/60 bg-accent/10 text-accent`}
      >
        Catat
      </button>
      {state.error ? <span className="text-xs text-risk-critical">{state.error}</span> : null}
    </form>
  );
}
