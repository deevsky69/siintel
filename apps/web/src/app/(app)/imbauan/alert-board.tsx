"use client";

import { useActionState, useState } from "react";
import { Panel } from "@/components/panel";
import { StatusNotice } from "@/components/warnings/status-notice";
import type { AlertCandidate, PublicAlert } from "@/lib/public-alerts";
import { type PublishState, publish, withdraw } from "./actions";

/**
 * Layar kanal imbauan.
 *
 * Dua hal yang sengaja dibuat demikian:
 *
 * 1. **Kotak isian sudah terisi rancangan, tetapi tetap wajib dibaca.** Rancangan itu
 *    diturunkan aturan dari kolom peringatannya, bukan dari model bahasa, dan layar
 *    menyatakannya. Yang tersimpan adalah teks yang benar-benar dikirim.
 *
 * 2. **Ketiadaan ambang severity dinyatakan terbuka.** Seluruh peringatan hidup dapat
 *    diumumkan apa pun tingkatnya, karena severity minimum belum ditetapkan (sisa U-10).
 *    Layar yang diam soal ini membuat pembacanya mengira ada penyaringan.
 */

const IDLE: PublishState = { error: null, done: null };

const SEVERITY_TONE: Record<string, string> = {
  CRITICAL: "bg-risk-critical/15 text-risk-critical",
  WARNING: "bg-risk-high/15 text-risk-high",
  WATCH: "bg-risk-moderate/15 text-risk-moderate",
  LOW: "bg-risk-low/15 text-risk-low",
};

function Badge({ value }: { value: string }) {
  return <span className={`badge ${SEVERITY_TONE[value] ?? "bg-base-800 text-ink"}`}>{value}</span>;
}

function PublishForm({ candidate }: { candidate: AlertCandidate }) {
  const [state, action, pending] = useActionState(publish, IDLE);
  const [message, setMessage] = useState(candidate.suggested_message);

  return (
    <form action={action} className="mt-2 space-y-2">
      <input type="hidden" name="warning_code" value={candidate.warning_code} />
      <label className="block">
        <span className="stat-label">Isi imbauan yang akan dibaca masyarakat</span>
        <textarea
          name="public_message"
          rows={4}
          required
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          className="mt-1.5 w-full rounded border border-base-700 bg-base-850 px-3 py-2 text-xs leading-relaxed text-ink outline-none focus:border-accent"
        />
      </label>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="submit"
          disabled={pending}
          className="rounded border border-risk-high/50 px-3 py-1.5 font-heading text-2xs font-semibold uppercase tracking-wider text-risk-high transition hover:bg-risk-high/10 disabled:opacity-40"
        >
          {pending ? "Menerbitkan…" : "Terbitkan Imbauan"}
        </button>
        <span className="text-2xs text-ink-faint">
          {message.trim().length} huruf · tidak dapat ditarik kembali setelah terbaca
        </span>
      </div>

      {state.error ? (
        <p className="text-2xs leading-relaxed text-risk-high">{state.error}</p>
      ) : null}
    </form>
  );
}

function WithdrawForm({ code }: { code: string }) {
  const [state, action, pending] = useActionState(withdraw, IDLE);

  return (
    <form action={action} className="mt-2">
      <input type="hidden" name="code" value={code} />
      <button
        type="submit"
        disabled={pending}
        className="rounded border border-base-700 px-2.5 py-1 font-heading text-2xs uppercase tracking-wider text-ink-muted transition hover:border-base-600 hover:text-ink disabled:opacity-40"
      >
        {pending ? "Mencabut…" : "Cabut Imbauan"}
      </button>
      {state.error ? (
        <p className="mt-1 text-2xs leading-relaxed text-risk-high">{state.error}</p>
      ) : null}
    </form>
  );
}

export function AlertBoard({
  alerts,
  candidates,
  canPublish,
  gateBasis,
  draftBasis,
  listBasis,
}: {
  alerts: PublicAlert[];
  candidates: AlertCandidate[];
  /** Hanya menentukan tombol mana yang tampak; backend tetap yang menolak. */
  canPublish: boolean;
  gateBasis: string;
  draftBasis: string;
  listBasis: string;
}) {
  const active = alerts.filter((alert) => alert.status === "ACTIVE");
  const past = alerts.filter((alert) => alert.status !== "ACTIVE");

  return (
    <div className="space-y-3">
      <StatusNotice status="TANPA AMBANG" tone="caution">
        {gateBasis}
      </StatusNotice>

      <div className="grid grid-cols-12 gap-3">
        <div className="col-span-12 flex flex-col gap-3 xl:col-span-7">
          <Panel
            title="Sedang Berlaku"
            action={<span className="stat-label">{active.length}</span>}
          >
            {active.length === 0 ? (
              <p className="text-xs text-ink-muted">
                Tidak ada imbauan yang sedang beredar. Halaman publik menampilkan bagian ini kosong
                — bukan berarti tidak ada peringatan dini, melainkan belum ada yang diputuskan untuk
                diumumkan.
              </p>
            ) : (
              <ul className="space-y-2">
                {active.map((alert) => (
                  <li key={alert.code} className="rounded border border-base-800 bg-base-850 p-3">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <div className="flex flex-wrap items-baseline gap-2">
                        <Badge value={alert.severity} />
                        <span className="text-xs text-ink">{alert.threat_type}</span>
                        <span className="text-2xs text-ink-muted">{alert.area_text}</span>
                      </div>
                      <span className="font-mono text-2xs text-ink-faint">{alert.code}</span>
                    </div>
                    <p className="mt-1.5 text-2xs leading-relaxed text-ink-muted">
                      {alert.public_message}
                    </p>
                    <p className="mt-1 text-2xs text-ink-faint">
                      Dasar: {alert.warning_code ?? "tanpa peringatan"}
                      {alert.time_window ? ` · ${alert.time_window} WIB` : ""}
                    </p>
                    {canPublish ? <WithdrawForm code={alert.code} /> : null}
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-3 text-2xs leading-relaxed text-ink-faint">{listBasis}</p>
          </Panel>

          <Panel
            title="Sudah Tidak Beredar"
            action={<span className="stat-label">{past.length}</span>}
          >
            {past.length === 0 ? (
              <p className="text-xs text-ink-muted">Belum ada imbauan yang dicabut.</p>
            ) : (
              <ul className="space-y-1.5">
                {past.slice(0, 12).map((alert) => (
                  <li
                    key={alert.code}
                    className="flex flex-wrap items-baseline justify-between gap-2 text-2xs"
                  >
                    <span className="text-ink-muted">
                      {alert.threat_type} · {alert.area_text}
                    </span>
                    <span className="font-mono text-ink-faint">
                      {alert.code} · {alert.status}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>

        <div className="col-span-12 xl:col-span-5">
          <Panel
            title="Menunggu Diumumkan"
            action={<span className="stat-label">{candidates.length}</span>}
          >
            {!canPublish ? (
              <p className="text-xs leading-relaxed text-ink-muted">
                Akun Anda dapat membaca imbauan yang beredar, tetapi tidak menerbitkannya.
                Menerbitkan imbauan kepada masyarakat adalah keputusan komando dan berada pada
                Pimpinan.
              </p>
            ) : candidates.length === 0 ? (
              <p className="text-xs text-ink-muted">
                Tidak ada peringatan hidup yang belum diumumkan.
              </p>
            ) : (
              <ul className="space-y-3">
                {candidates.slice(0, 8).map((candidate) => (
                  <li
                    key={candidate.warning_code}
                    className="rounded border border-base-800 bg-base-850 p-3"
                  >
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <div className="flex flex-wrap items-baseline gap-2">
                        <Badge value={candidate.severity} />
                        <span className="text-xs text-ink">{candidate.threat_type}</span>
                        <span className="text-2xs text-ink-muted">{candidate.kecamatan}</span>
                      </div>
                      <span className="font-mono text-2xs text-ink-faint">
                        {candidate.warning_code}
                      </span>
                    </div>
                    <PublishForm candidate={candidate} />
                  </li>
                ))}
              </ul>
            )}
            {canPublish ? (
              <p className="mt-3 text-2xs leading-relaxed text-ink-faint">{draftBasis}</p>
            ) : null}
          </Panel>
        </div>
      </div>
    </div>
  );
}
