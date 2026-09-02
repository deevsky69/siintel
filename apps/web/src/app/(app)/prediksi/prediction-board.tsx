"use client";

import Link from "next/link";
import { useActionState } from "react";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import type { PredictionRow } from "@/lib/prediction-center";
import { RISK_TEXT, riskClassOf } from "@/lib/risk";
import { submitPublish } from "./actions";
import {
  contributionText,
  factorLabel,
  factorValue,
  formatWib,
  HORIZONS,
  horizonLabel,
  STATUS_HINTS,
  STATUSES,
  statusLabel,
  windowText,
} from "./display";
import { IDLE_PUBLISH } from "./run-state";

/**
 * Daftar prediksi, rinciannya, dan kendali publikasi.
 *
 * Rincian disusun mengikuti CLAUDE.md §10 — WHAT, WHERE, WHEN, RISK, CONFIDENCE, WHY —
 * karena itulah yang harus dapat dijawab sebuah prediksi. **WHY** diambil apa adanya dari
 * `dominant_factors` yang dikembalikan API, lengkap dengan label `RULE`: penjelasan ini
 * berasal dari aturan yang benar-benar dijalankan, bukan dari model (CLAUDE.md §27).
 *
 * Penyaring horizon dan status berbentuk tautan, bukan keadaan di peramban: pilihan dapat
 * dibagikan sebagai URL saat paparan, dan penyaringannya dikerjakan backend di query —
 * bukan di klien setelah semua data terlanjur terambil.
 *
 * Tombol publikasi disembunyikan dari peran tanpa `prediction:publish`. Itu kenyamanan
 * belaka; penolakan sesungguhnya terjadi di backend (CLAUDE.md §21).
 */

/** Kelas badge ditulis utuh supaya Tailwind benar-benar membangkitkan kelasnya. */
const STATUS_BADGE: Record<string, string> = {
  DRAFT: "bg-base-800 text-ink-muted",
  PUBLISHED: "bg-risk-low/15 text-risk-low",
  VALIDATED: "bg-accent/15 text-accent",
};

export type Filter = { horizon: string | null; status: string | null };

function hrefFor(filter: Filter, patch: Partial<Filter>, selected?: string | null): string {
  const merged = { ...filter, ...patch };
  const query = new URLSearchParams();
  if (merged.horizon) query.set("horizon", merged.horizon);
  if (merged.status) query.set("status", merged.status);
  if (selected) query.set("dipilih", selected);
  const text = query.toString();
  return text ? `/prediksi?${text}` : "/prediksi";
}

function FilterRow({
  label,
  options,
  active,
  hrefOf,
  optionLabel,
}: {
  label: string;
  options: readonly string[];
  active: string | null;
  hrefOf: (value: string | null) => string;
  optionLabel: (value: string) => string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="stat-label mr-1">{label}</span>
      <Link
        href={hrefOf(null)}
        aria-current={active === null ? "true" : undefined}
        className={`badge ${active === null ? "bg-accent/15 text-accent" : "bg-base-800 text-ink-muted"}`}
      >
        Semua
      </Link>
      {options.map((option) => (
        <Link
          key={option}
          href={hrefOf(option)}
          aria-current={active === option ? "true" : undefined}
          className={`badge ${active === option ? "bg-accent/15 text-accent" : "bg-base-800 text-ink-muted"}`}
        >
          {optionLabel(option)}
        </Link>
      ))}
    </div>
  );
}

function PredictionCard({
  prediction,
  selected,
  filter,
}: {
  prediction: PredictionRow;
  selected: boolean;
  filter: Filter;
}) {
  const risk = riskClassOf(prediction.risk_score);

  return (
    <li>
      <Link
        href={hrefFor(filter, {}, prediction.code)}
        aria-current={selected ? "true" : undefined}
        className={`block rounded border px-3 py-2.5 transition-colors ${
          selected
            ? "border-accent/60 bg-accent/5"
            : "border-base-800 bg-base-950/40 hover:border-base-600"
        }`}
      >
        <div className="flex items-start gap-3">
          <span className={`badge shrink-0 ${STATUS_BADGE[prediction.status] ?? "bg-base-800"}`}>
            {statusLabel(prediction.status)}
          </span>
          <span className="flex-1 font-heading text-sm font-semibold text-ink">
            {prediction.threat_type}
          </span>
          <span className={`font-heading text-lg font-bold tabular-nums ${RISK_TEXT[risk]}`}>
            {prediction.risk_score}
          </span>
        </div>
        <p className="mt-1 text-[11px] text-ink-muted">
          {prediction.kecamatan}
          {prediction.grid_id ? ` · ${prediction.grid_id}` : ""} · horizon{" "}
          {prediction.forecast_horizon} · {prediction.time_window ?? "—"}
        </p>
        <p className="text-[10px] text-ink-muted">
          {prediction.code} · dibuat {prediction.prediction_date} · keyakinan{" "}
          {prediction.confidence ?? "—"}
        </p>
      </Link>
    </li>
  );
}

function Detail({ prediction, canPublish }: { prediction: PredictionRow; canPublish: boolean }) {
  const [state, submit, pending] = useActionState(submitPublish, IDLE_PUBLISH);
  const risk = riskClassOf(prediction.risk_score);
  const factors = prediction.dominant_factors ?? [];
  const publishable = prediction.status === "DRAFT";

  return (
    <div className="space-y-3">
      <dl className="grid grid-cols-1 gap-2 md:grid-cols-2">
        <div className="rounded border border-base-800 bg-base-950/40 px-3 py-2">
          <dt className="stat-label">Apa (WHAT)</dt>
          <dd className="mt-1 font-heading text-sm font-bold text-ink">{prediction.threat_type}</dd>
        </div>
        <div className="rounded border border-base-800 bg-base-950/40 px-3 py-2">
          <dt className="stat-label">Di mana (WHERE)</dt>
          <dd className="mt-1 text-[12px] text-ink">
            {prediction.kecamatan}
            {prediction.kelurahan ? ` · ${prediction.kelurahan}` : ""}
            {prediction.grid_id ? ` · sel ${prediction.grid_id}` : ""}
          </dd>
        </div>
        <div className="rounded border border-base-800 bg-base-950/40 px-3 py-2 md:col-span-2">
          <dt className="stat-label">Kapan (WHEN)</dt>
          <dd className="mt-1 text-[12px] text-ink">
            {windowText(prediction.window_start, prediction.window_end)}
          </dd>
          <dd className="mt-0.5 text-[10px] text-ink-muted">
            Jendela {prediction.time_window ?? "—"} · horizon {prediction.forecast_horizon} (
            {horizonLabel(prediction.forecast_horizon)}) · dibuat {prediction.prediction_date}
          </dd>
        </div>
        <div className="rounded border border-base-800 bg-base-950/40 px-3 py-2">
          <dt className="stat-label">Risiko (RISK)</dt>
          <dd className={`mt-1 font-heading text-2xl font-bold tabular-nums ${RISK_TEXT[risk]}`}>
            {prediction.risk_score}
          </dd>
        </div>
        <div className="rounded border border-base-800 bg-base-950/40 px-3 py-2">
          <dt className="stat-label">Keyakinan (CONFIDENCE)</dt>
          <dd className="mt-1 font-heading text-2xl font-bold tabular-nums text-ink">
            {prediction.confidence ?? "—"}
          </dd>
        </div>
      </dl>

      <section className="rounded border border-base-800 px-3 py-2.5">
        <h3 className="font-heading text-[12px] font-semibold uppercase tracking-wider text-ink">
          Mengapa (WHY)
        </h3>
        {factors.length > 0 ? (
          <ul className="mt-2 space-y-1">
            {factors.map((factor) => (
              <li
                key={factor.factor}
                className="flex flex-wrap items-baseline justify-between gap-x-3 text-[11px]"
              >
                <span className="text-ink-muted">
                  {factorLabel(factor.factor)}
                  <span className="ml-1.5 rounded bg-base-800 px-1 py-px text-[9px] uppercase tracking-wider text-ink-muted">
                    {factor.source}
                  </span>
                  {factor.reason ? (
                    <span className="ml-1.5 text-ink-muted">({factor.reason})</span>
                  ) : null}
                </span>
                <span className="tabular-nums text-ink">
                  {factorValue(factor.value)}
                  <span className="ml-2 text-ink-muted">
                    {contributionText(factor.contribution, factor.weight)}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-[11px] text-ink-muted">
            Prediksi ini tidak membawa satu pun faktor penjelas. Angkanya tidak dapat
            dipertanggungjawabkan tanpa itu, dan layar tidak menyusun penjelasan pengganti.
          </p>
        )}
        <p className="mt-2 text-[10px] leading-relaxed text-ink-muted">
          Versi aturan <code>{prediction.model_version ?? "—"}</code>. Bukan nama model: tidak ada
          model terlatih di balik angka ini, dan seluruh faktor di atas berlabel <code>RULE</code>.
        </p>
      </section>

      <section className="rounded border border-base-800 px-3 py-2.5">
        <h3 className="font-heading text-[12px] font-semibold uppercase tracking-wider text-ink">
          Publikasi
        </h3>
        <p className="mt-1 text-[11px] text-ink-muted">
          Status sekarang <strong className="text-ink">{statusLabel(prediction.status)}</strong> —{" "}
          {STATUS_HINTS[prediction.status] ?? "status di luar taksonomi yang dikenal layar ini"}.
        </p>

        {canPublish && publishable ? (
          <form action={submit} className="mt-2">
            <input type="hidden" name="code" value={prediction.code} />
            <button
              type="submit"
              disabled={pending}
              className="rounded border border-risk-high/50 px-4 py-2 font-heading text-[11px] font-semibold uppercase tracking-wider text-risk-high transition hover:bg-risk-high/10 disabled:opacity-40"
            >
              {pending ? "Menerbitkan…" : "Publikasikan"}
            </button>
            <p className="mt-1.5 text-[10px] leading-relaxed text-ink-muted">
              Setelah terbit, prediksi ini boleh menjadi dasar peringatan dini. Publikasi tidak
              dapat diulang maupun dibatalkan dari layar ini.
            </p>
          </form>
        ) : null}

        {canPublish && !publishable ? (
          <p className="mt-2 text-[10px] leading-relaxed text-ink-muted">
            Hanya prediksi berstatus Draf yang dapat dipublikasikan.
          </p>
        ) : null}

        {!canPublish ? (
          <p className="mt-2 text-[10px] leading-relaxed text-ink-muted">
            Akun Anda tidak memiliki kewenangan <code>prediction:publish</code>.
          </p>
        ) : null}

        {state.error ? (
          <p role="alert" className="mt-2 text-xs text-risk-critical">
            {state.error}
          </p>
        ) : null}

        {state.published ? (
          <p className="mt-2 text-[11px] text-risk-low">
            {state.published.code} kini berstatus {statusLabel(state.published.status)}.
          </p>
        ) : null}
      </section>
    </div>
  );
}

export function PredictionBoard({
  rows,
  total,
  selected,
  filter,
  canPublish,
}: {
  rows: PredictionRow[];
  total: number;
  selected: PredictionRow | null;
  filter: Filter;
  canPublish: boolean;
}) {
  return (
    <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <Panel
        title="Daftar Prediksi"
        action={
          <span className="panel-action">
            {rows.length} dari {total}
          </span>
        }
      >
        <div className="space-y-2">
          <FilterRow
            label="Horizon"
            options={HORIZONS}
            active={filter.horizon}
            hrefOf={(value) => hrefFor(filter, { horizon: value })}
            optionLabel={(value) => value}
          />
          <FilterRow
            label="Status"
            options={STATUSES}
            active={filter.status}
            hrefOf={(value) => hrefFor(filter, { status: value })}
            optionLabel={statusLabel}
          />
        </div>

        {rows.length === 0 ? (
          <div className="mt-3">
            <EmptyState label="Tidak ada prediksi pada penyaring ini." />
          </div>
        ) : (
          <ul className="mt-3 max-h-[32rem] space-y-2 overflow-y-auto pr-1">
            {rows.map((prediction) => (
              <PredictionCard
                key={prediction.code}
                prediction={prediction}
                selected={selected?.code === prediction.code}
                filter={filter}
              />
            ))}
          </ul>
        )}
      </Panel>

      <Panel
        title="Rincian Prediksi"
        action={
          selected ? (
            <span className="panel-action">
              {selected.code} · {formatWib(selected.window_start)}
            </span>
          ) : undefined
        }
      >
        {selected ? (
          <Detail key={selected.code} prediction={selected} canPublish={canPublish} />
        ) : (
          <EmptyState label="Pilih satu prediksi untuk melihat dasarnya." />
        )}
      </Panel>
    </div>
  );
}
