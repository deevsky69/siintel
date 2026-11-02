"use client";

import { useActionState } from "react";
import type { CaseRow } from "@/lib/case-files";
import { type CaseActionState, moveStage, recordCase } from "./actions";

const IDLE: CaseActionState = { error: null, done: null };
const field = "w-full rounded border border-base-700 bg-base-850 px-2 py-1.5 text-xs text-ink";

export function StageForm({
  row,
  stages,
}: {
  row: CaseRow;
  stages: { code: string; label: string }[];
}) {
  const [state, submit, pending] = useActionState(moveStage, IDLE);
  if (state.done) return <p className="mt-2 text-xs text-risk-low">{state.done}</p>;
  return (
    <form action={submit} className="mt-2 flex flex-wrap items-center gap-2">
      <input type="hidden" name="lp" value={row.lp_number} />
      <select name="stage" defaultValue={row.stage} className={`${field} w-auto`}>
        {stages.map((stage) => (
          <option key={stage.code} value={stage.code}>
            {stage.label}
          </option>
        ))}
      </select>
      <input
        name="note"
        maxLength={300}
        placeholder="Catatan untuk pelapor (opsional)"
        className={`${field} min-w-[220px] flex-1`}
      />
      {row.vehicle_plate ? (
        <label className="flex items-center gap-1 text-xs text-ink-muted">
          <input type="checkbox" name="vehicle_recovered" defaultChecked={row.vehicle_recovered} />{" "}
          kendaraan ditemukan
        </label>
      ) : null}
      <button
        type="submit"
        disabled={pending}
        className="rounded border border-accent/60 bg-accent/10 px-3 py-1 text-xs font-semibold text-accent disabled:opacity-50"
      >
        Simpan tahap
      </button>
      {state.error ? <span className="text-xs text-risk-critical">{state.error}</span> : null}
    </form>
  );
}

export function NewCaseForm({ areas }: { areas: { kecamatan: string; kelurahan: string[] }[] }) {
  const [state, submit, pending] = useActionState(recordCase, IDLE);
  return (
    <form action={submit} className="grid gap-2 sm:grid-cols-2">
      <label className="text-xs text-ink-muted sm:col-span-2">
        Nomor LP
        <input
          name="lp_number"
          required
          className={`${field} mt-1 font-mono`}
          placeholder="LP/B/123/XI/2026/SPKT/POLSEK TEBET"
        />
      </label>
      <label className="text-xs text-ink-muted">
        Jenis
        <select name="crime_type" className={`${field} mt-1`}>
          <option value="CURANMOR">CURANMOR</option>
          <option value="CURAT">CURAT</option>
          <option value="CURAS">CURAS</option>
        </select>
      </label>
      <label className="text-xs text-ink-muted">
        Tanggal laporan
        <input name="reported_on" type="date" required className={`${field} mt-1`} />
      </label>
      <label className="text-xs text-ink-muted">
        Kecamatan
        <select name="kecamatan" className={`${field} mt-1`}>
          {areas.map((row) => (
            <option key={row.kecamatan} value={row.kecamatan}>
              {row.kecamatan}
            </option>
          ))}
        </select>
      </label>
      <label className="text-xs text-ink-muted">
        Kelurahan
        <select name="kelurahan" className={`${field} mt-1`}>
          {areas.flatMap((row) =>
            row.kelurahan.map((name) => (
              <option key={`${row.kecamatan}-${name}`} value={name}>
                {name} ({row.kecamatan})
              </option>
            )),
          )}
        </select>
      </label>
      <label className="text-xs text-ink-muted">
        Plat nomor (Curanmor)
        <input
          name="vehicle_plate"
          className={`${field} mt-1 font-mono uppercase`}
          placeholder="B 1234 ABC"
        />
      </label>
      <label className="text-xs text-ink-muted">
        Nomor rangka
        <input name="vehicle_vin" className={`${field} mt-1 font-mono uppercase`} />
      </label>
      <label className="text-xs text-ink-muted sm:col-span-2">
        Kendaraan
        <input
          name="vehicle_desc"
          className={`${field} mt-1`}
          placeholder="Honda Vario 150 hitam"
        />
      </label>
      <label className="text-xs text-ink-muted sm:col-span-2">
        Uraian singkat untuk pelapor
        <textarea name="summary" rows={2} maxLength={1000} className={`${field} mt-1`} />
      </label>
      <label className="flex items-center gap-2 text-xs text-ink-muted sm:col-span-2">
        <input type="checkbox" name="is_dummy" /> Data peragaan (DUMMY) — PIN boleh ditampilkan di
        layar ini
      </label>
      <div className="sm:col-span-2">
        <button
          type="submit"
          disabled={pending}
          className="rounded border border-accent/60 bg-accent/10 px-3 py-1.5 text-xs font-semibold text-accent disabled:opacity-50"
        >
          Catat perkara
        </button>
        {state.error ? <p className="mt-2 text-xs text-risk-critical">{state.error}</p> : null}
        {state.done ? (
          <p className="mt-2 text-xs text-risk-low">
            {state.done} PIN pelapor:{" "}
            <strong className="font-mono text-sm text-ink">{state.pin}</strong> — sampaikan
            sekarang; sistem tidak dapat menampilkannya lagi.
          </p>
        ) : null}
      </div>
    </form>
  );
}
