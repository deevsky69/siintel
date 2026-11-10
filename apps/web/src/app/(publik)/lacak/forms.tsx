"use client";

import { useActionState, useState } from "react";
import { CASE_STAGES, type CaseTrack, threatLabel } from "@/lib/warga";
import { checkVehicle, type TrackState, trackCase, type VehicleState } from "./actions";

const STAGE_LABEL: Record<string, string> = {
  DITERIMA: "Laporan diterima",
  LIDIK: "Penyelidikan",
  SIDIK: "Penyidikan",
  P21: "Berkas lengkap (P21)",
  SP3: "Penyidikan dihentikan (SP3)",
  SELESAI: "Selesai",
};
const FINAL = new Set(["P21", "SP3", "SELESAI"]);

function DummyTag() {
  return <span className="warga-dummy">Dummy · data peragaan</span>;
}

function tanggal(value: string, long = false) {
  return new Date(value).toLocaleDateString("id-ID", {
    day: "numeric",
    month: long ? "long" : "short",
    year: "numeric",
  });
}

export function TrackForm() {
  const [state, action, pending] = useActionState<TrackState, FormData>(trackCase, {
    status: "idle",
  });
  return (
    <div>
      <form action={action} className="flex flex-wrap items-end gap-3.5">
        <label className="flex flex-[2_1_280px] flex-col gap-1.5">
          <span className="warga-label">Nomor LP</span>
          <input
            name="lp"
            required
            className="warga-field min-h-[52px] font-mono text-base"
            placeholder="LP/B/[nomor]/[bulan]/[tahun]/SPKT/…"
          />
        </label>
        <label className="flex flex-[1_1_160px] flex-col gap-1.5">
          <span className="warga-label">PIN pelapor</span>
          <input
            name="pin"
            required
            type="password"
            inputMode="numeric"
            pattern="\d{4}"
            maxLength={4}
            className="warga-field min-h-[52px] font-mono tracking-[0.2em]"
            placeholder="4 digit"
          />
        </label>
        <button
          type="submit"
          disabled={pending}
          className="warga-btn warga-btn-primary min-h-[52px] px-7 disabled:opacity-50"
        >
          {pending ? "Mencari…" : "Lacak"}
        </button>
      </form>
      <p className="warga-help mt-3">
        Nomor LP dan PIN diberikan pada saat laporan dibuat. Apabila PIN hilang, hubungi SPKT Polres
        Metro Jakarta Selatan.
      </p>
      {state.status === "error" ? (
        <p className="warga-error mt-4" role="alert">
          {state.message}
        </p>
      ) : null}
      {state.status === "found" ? <TrackResult data={state.data} /> : null}
    </div>
  );
}

function TrackResult({ data }: { data: CaseTrack }) {
  const done = FINAL.has(data.stage);
  const stageIndex = CASE_STAGES.indexOf(data.stage as (typeof CASE_STAGES)[number]);
  return (
    <section className="warga-card mt-7 p-6" aria-live="polite">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.08em] text-ink-faint">Laporan</p>
          <p className="mt-0.5 break-all font-mono text-lg font-extrabold text-[rgb(var(--warga-navy))]">
            {data.lp_number}
          </p>
          <p className="mt-1 text-sm text-ink-faint">
            {threatLabel(data.crime_type)} · {data.kelurahan ? `${data.kelurahan}, ` : ""}Kec.{" "}
            {data.kecamatan} · Polsek {data.polsek} · dilaporkan {tanggal(data.reported_on, true)}
          </p>
          {data.is_dummy ? (
            <p className="mt-1.5">
              <DummyTag />
            </p>
          ) : null}
        </div>
        <span className="warga-status">{done ? STAGE_LABEL[data.stage] : "Sedang ditangani"}</span>
      </div>
      <ol className="warga-timeline mt-6">
        {data.history.map((row, index) => {
          const last = index === data.history.length - 1;
          return (
            <li key={`${row.stage}-${row.changed_at}`}>
              <div className="warga-timeline-rail">
                <span className="warga-timeline-dot">{index + 1}</span>
                {!last || (!done && stageIndex >= 0) ? (
                  <span className="warga-timeline-line" />
                ) : null}
              </div>
              <div className="pb-5">
                <p className="text-[15px] font-bold text-[rgb(var(--warga-navy))]">
                  {row.stage_label}
                </p>
                <p className="text-xs text-ink-faint">{tanggal(row.changed_at)}</p>
                {row.note ? (
                  <p className="mt-0.5 text-sm leading-relaxed text-ink-faint">{row.note}</p>
                ) : null}
              </div>
            </li>
          );
        })}
        {!done && stageIndex >= 0 ? (
          <li>
            <div className="warga-timeline-rail">
              <span className="warga-timeline-dot is-pending">{data.history.length + 1}</span>
            </div>
            <div className="pb-1">
              <p className="text-[15px] font-bold text-ink-faint">Tahap berikutnya</p>
              <p className="text-xs text-ink-faint">
                Akan tampil di sini begitu diperbarui penyidik.
              </p>
            </div>
          </li>
        ) : null}
      </ol>
      {data.vehicle ? (
        <p className="mt-2 bg-base-950 px-3.5 py-2.5 text-sm text-ink">
          Kendaraan: <span className="font-mono font-bold">{data.vehicle.plate}</span>
          {data.vehicle.description ? ` · ${data.vehicle.description}` : ""}
          {data.vehicle.recovered ? (
            <span className="ml-2 font-semibold text-[#166534]">sudah ditemukan</span>
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
  const [mode, setMode] = useState<"plat" | "rangka">("plat");
  return (
    <div>
      <form action={action} className="flex flex-col gap-4">
        <fieldset className="m-0 flex flex-wrap gap-2.5 border-0 p-0">
          <legend className="warga-label mb-2 p-0">Cari berdasarkan</legend>
          {(["plat", "rangka"] as const).map((value) => (
            <label
              key={value}
              className={`inline-flex min-h-[44px] cursor-pointer items-center gap-2 border-[1.5px] px-4 text-sm font-semibold ${
                mode === value ? "border-[rgb(var(--warga-navy))] bg-base-850" : "border-base-700"
              }`}
            >
              <input
                type="radio"
                name="jenis"
                value={value}
                checked={mode === value}
                onChange={() => setMode(value)}
                className="accent-[rgb(var(--warga-navy))]"
              />
              {value === "plat" ? "Nomor plat" : "Nomor rangka"}
            </label>
          ))}
        </fieldset>
        <div className="flex flex-wrap items-end gap-3.5">
          {mode === "plat" ? (
            <label className="flex flex-[1_1_320px] flex-col gap-1.5">
              <span className="warga-label">Nomor plat</span>
              <input
                name="plat"
                required
                className="warga-field min-h-[52px] font-mono text-lg font-bold uppercase tracking-[0.08em]"
                placeholder="B 1234 XYZ"
              />
            </label>
          ) : (
            <label className="flex flex-[1_1_320px] flex-col gap-1.5">
              <span className="warga-label">Nomor rangka</span>
              <input
                name="rangka"
                required
                className="warga-field min-h-[52px] font-mono uppercase"
                placeholder="MH1…"
              />
            </label>
          )}
          <button
            type="submit"
            disabled={pending}
            className="warga-btn warga-btn-primary min-h-[52px] px-7 disabled:opacity-50"
          >
            {pending ? "Memeriksa…" : "Cek kendaraan"}
          </button>
        </div>
      </form>
      {state.status === "error" ? (
        <p className="warga-error mt-4" role="alert">
          {state.message}
        </p>
      ) : null}
      {state.status === "done" ? (
        <section
          className={`mt-6 flex gap-3.5 p-5 ${state.data.found ? "border border-[#FECACA] bg-[#FEF2F2]" : "warga-ok"}`}
          aria-live="polite"
        >
          <span
            className={`inline-flex h-10 w-10 flex-none items-center justify-center ${state.data.found ? "bg-[#FEE2E2] text-[#991B1B]" : "bg-[#DCFCE7] text-[#166534]"}`}
            aria-hidden="true"
          >
            {state.data.found ? "!" : "✓"}
          </span>
          <div>
            <p
              className={`text-[17px] font-extrabold ${state.data.found ? "text-[#7F1D1D]" : "text-[#14532D]"}`}
            >
              {state.data.found
                ? "Tercatat dalam laporan kehilangan"
                : "Tidak tercatat dalam laporan kehilangan"}
            </p>
            <p
              className={`mt-1 text-sm leading-relaxed ${state.data.found ? "text-[#7F1D1D]" : "text-[#166534]"}`}
            >
              {state.data.advice}
            </p>
            {state.data.records.map((row) => (
              <p
                key={`${row.crime_type}-${row.kecamatan}-${row.reported_month}`}
                className="mt-2 flex flex-wrap items-center gap-2 text-xs text-ink-muted"
              >
                {threatLabel(row.crime_type)} · {row.kecamatan} · {row.reported_month}
                {row.recovered ? (
                  <span className="font-semibold text-[#166534]">sudah ditemukan</span>
                ) : null}
                {row.is_dummy ? <DummyTag /> : null}
              </p>
            ))}
            <p className="mt-3 text-[11px] leading-relaxed text-ink-faint">{state.data.basis}</p>
          </div>
        </section>
      ) : null}
    </div>
  );
}
