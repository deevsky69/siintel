"use client";

import { useActionState } from "react";
import { CASE_STAGES, type CaseTrack, threatLabel } from "@/lib/warga";
import { checkVehicle, type TrackState, trackCase, type VehicleState } from "./actions";

function DummyTag() {
  return (
    <span className="rounded-full bg-[rgb(var(--warga-amber))]/20 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-ink">
      Dummy · data peragaan
    </span>
  );
}

const inputClass =
  "w-full rounded-2xl border border-base-800 bg-base-900 px-4 py-3 text-sm text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none";

export function TrackForm() {
  const [state, action, pending] = useActionState<TrackState, FormData>(trackCase, {
    status: "idle",
  });
  return (
    <div className="space-y-4">
      <form action={action} className="space-y-3">
        <label className="block">
          <span className="text-sm font-semibold text-ink">Nomor Laporan Polisi (LP)</span>
          <input
            name="lp"
            required
            className={`${inputClass} mt-1.5 font-mono`}
            placeholder="LP/B/123/XI/2026/SPKT/POLSEK TEBET"
          />
        </label>
        <label className="block">
          <span className="text-sm font-semibold text-ink">PIN pelapor (4 angka)</span>
          <input
            name="pin"
            required
            inputMode="numeric"
            pattern="\d{4}"
            maxLength={4}
            className={`${inputClass} mt-1.5 font-mono tracking-[0.3em]`}
            placeholder="••••"
          />
          <span className="mt-1 block text-xs text-ink-faint">
            PIN diberikan petugas saat laporan dibuat. Tanpa PIN, laporan tidak dapat dibuka.
          </span>
        </label>
        {state.status === "error" ? (
          <p className="text-sm text-risk-high" role="alert">
            {state.message}
          </p>
        ) : null}
        <button
          type="submit"
          disabled={pending}
          className="warga-btn warga-btn-primary w-full disabled:opacity-50"
        >
          {pending ? "Mencari…" : "Lacak laporan"}
        </button>
      </form>
      {state.status === "found" ? <TrackResult data={state.data} /> : null}
    </div>
  );
}

function TrackResult({ data }: { data: CaseTrack }) {
  const stageIndex = CASE_STAGES.indexOf(data.stage as (typeof CASE_STAGES)[number]);
  return (
    <section className="rounded-2xl bg-base-850 p-4" aria-live="polite">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-ink-muted">{data.lp_number}</span>
        {data.is_dummy ? <DummyTag /> : null}
      </div>
      <h3 className="mt-1 text-lg font-bold text-ink">{threatLabel(data.crime_type)}</h3>
      <p className="text-xs text-ink-muted">
        {data.kelurahan ? `${data.kelurahan}, ` : ""}
        {data.kecamatan} · Polsek {data.polsek} · dilaporkan{" "}
        {new Date(data.reported_on).toLocaleDateString("id-ID", {
          day: "numeric",
          month: "long",
          year: "numeric",
        })}
      </p>
      <ol className="mt-4 space-y-3">
        {data.history.map((row, index) => (
          <li key={`${row.stage}-${row.changed_at}`} className="flex gap-3">
            <span
              className={`mt-1 h-3 w-3 shrink-0 rounded-full ${index === data.history.length - 1 ? "bg-accent" : "bg-risk-low"}`}
              aria-hidden="true"
            />
            <div>
              <p className="text-sm font-semibold text-ink">{row.stage_label}</p>
              <p className="text-xs text-ink-faint">
                {new Date(row.changed_at).toLocaleDateString("id-ID", {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                })}
              </p>
              {row.note ? <p className="mt-0.5 text-sm text-ink-muted">{row.note}</p> : null}
            </div>
          </li>
        ))}
      </ol>
      {stageIndex >= 0 && stageIndex < CASE_STAGES.length - 1 && data.stage !== "SP3" ? (
        <p className="mt-3 text-xs text-ink-faint">
          Tahap berikutnya akan tampil di sini begitu diperbarui penyidik.
        </p>
      ) : null}
      {data.vehicle ? (
        <p className="mt-3 rounded-xl bg-base-900 px-3 py-2 text-sm text-ink">
          Kendaraan: <span className="font-mono">{data.vehicle.plate}</span>
          {data.vehicle.description ? ` · ${data.vehicle.description}` : ""}
          {data.vehicle.recovered ? (
            <span className="ml-2 font-semibold text-risk-low">sudah ditemukan</span>
          ) : null}
        </p>
      ) : null}
      {data.summary ? (
        <p className="mt-3 text-sm leading-relaxed text-ink-muted">{data.summary}</p>
      ) : null}
      <p className="mt-3 text-[11px] leading-relaxed text-ink-faint">{data.basis}</p>
    </section>
  );
}

export function VehicleForm() {
  const [state, action, pending] = useActionState<VehicleState, FormData>(checkVehicle, {
    status: "idle",
  });
  return (
    <div className="space-y-4">
      <form action={action} className="space-y-3">
        <label className="block">
          <span className="text-sm font-semibold text-ink">Plat nomor</span>
          <input
            name="plat"
            className={`${inputClass} mt-1.5 font-mono uppercase`}
            placeholder="B 1234 ABC"
          />
        </label>
        <p className="text-center text-xs text-ink-faint">atau</p>
        <label className="block">
          <span className="text-sm font-semibold text-ink">Nomor rangka</span>
          <input
            name="rangka"
            className={`${inputClass} mt-1.5 font-mono uppercase`}
            placeholder="MH1…"
          />
        </label>
        {state.status === "error" ? (
          <p className="text-sm text-risk-high" role="alert">
            {state.message}
          </p>
        ) : null}
        <button
          type="submit"
          disabled={pending}
          className="warga-btn warga-btn-primary w-full disabled:opacity-50"
        >
          {pending ? "Memeriksa…" : "Cek kendaraan"}
        </button>
      </form>
      {state.status === "done" ? (
        <section
          className={`rounded-2xl p-4 ${state.data.found ? "bg-risk-high/10" : "bg-risk-low/10"}`}
          aria-live="polite"
        >
          <p
            className={`text-lg font-bold ${state.data.found ? "text-risk-high" : "text-risk-low"}`}
          >
            {state.data.found ? "Tercatat dalam laporan kehilangan" : "Tidak ada catatan"}
          </p>
          <p className="mt-1 text-sm text-ink">{state.data.advice}</p>
          {state.data.records.map((row) => (
            <p
              key={`${row.crime_type}-${row.kecamatan}-${row.reported_month}`}
              className="mt-2 flex flex-wrap items-center gap-2 text-xs text-ink-muted"
            >
              {threatLabel(row.crime_type)} · {row.kecamatan} · {row.reported_month}
              {row.recovered ? (
                <span className="font-semibold text-risk-low">sudah ditemukan</span>
              ) : null}
              {row.is_dummy ? <DummyTag /> : null}
            </p>
          ))}
          <p className="mt-3 text-[11px] leading-relaxed text-ink-faint">{state.data.basis}</p>
        </section>
      ) : null}
    </div>
  );
}
