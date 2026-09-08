import type { RunForecast, RunResult } from "@/lib/prediction-center";
import {
  baselineAgeText,
  contributionText,
  factorLabel,
  factorValue,
  formatWib,
  horizonLabel,
} from "./display";

/**
 * Ringkasan hasil menjalankan prediksi.
 *
 * Empat hal sengaja tampil berdampingan, bukan dipilih salah satunya:
 *
 * 1. berapa kombinasi yang **diprediksi** dan berapa yang **tidak dapat diprediksi**,
 *    beserta alasannya — kombinasi tanpa dasar bukan kombinasi berisiko nol;
 * 2. baris `risk_scores` yang menjadi dasar setiap prediksi contoh, lengkap dengan
 *    umurnya, sehingga angkanya dapat ditelusuri ke penilaian yang menghasilkannya;
 * 3. dasar `confidence` apa adanya — termasuk ketika dasarnya tipis;
 * 4. pernyataan bahwa ini **bukan** model terlatih, diambil dari respons API, bukan
 *    ditulis ulang di layar.
 *
 * Tidak ada modul `@/lib/api` yang tertarik ke sini: berkas ini dipakai komponen
 * `"use client"`.
 */

function ForecastCard({ forecast }: { forecast: RunForecast }) {
  return (
    <li className="rounded border border-base-800 bg-base-850 px-3 py-2.5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <span className="font-heading text-xs font-semibold text-ink">{forecast.grid_id}</span>
          <span className="ml-2 text-xs text-ink-muted">
            {forecast.kecamatan}
            {forecast.kelurahan ? ` · ${forecast.kelurahan}` : ""} · {forecast.threat_type} ·{" "}
            {forecast.time_window}
          </span>
        </div>
        <div className="text-right">
          <span className="font-heading text-xl font-bold tabular-nums text-ink">
            {forecast.risk_score === null ? "—" : forecast.risk_score}
          </span>
          <span className="ml-2 text-2xs uppercase tracking-wider text-ink-muted">
            {forecast.risk_class ?? "tidak diprediksi"}
          </span>
        </div>
      </div>

      <p className="mt-1 text-2xs text-ink-muted">
        {formatWib(forecast.window_start)} s.d. {formatWib(forecast.window_end)}
      </p>

      {forecast.not_predicted_reason ? (
        <p className="mt-1.5 text-2xs leading-relaxed text-risk-high">
          {forecast.not_predicted_reason}
        </p>
      ) : null}

      <p className="mt-1.5 text-2xs leading-relaxed text-ink-muted">
        Keyakinan{" "}
        <span className="tabular-nums text-ink">
          {forecast.confidence === null ? "—" : forecast.confidence}
        </span>{" "}
        — {forecast.confidence_reason}
      </p>

      {forecast.baseline_code ? (
        <p className="mt-1 text-2xs leading-relaxed text-ink-muted">
          Dasar: penilaian <span className="text-ink">{forecast.baseline_code}</span> tanggal{" "}
          {forecast.baseline_assessment_date} ({baselineAgeText(forecast.baseline_age_days)}), versi
          bobot {forecast.weights_version ?? "—"}.
        </p>
      ) : null}

      {forecast.dominant_factors.length > 0 ? (
        <ul className="mt-2 space-y-1">
          {forecast.dominant_factors.map((factor) => (
            <li
              key={factor.factor}
              className="flex flex-wrap items-baseline justify-between gap-x-3 text-xs"
            >
              <span className="text-ink-muted">
                {factorLabel(factor.factor)}
                <span className="ml-1.5 rounded bg-base-800 px-1 py-px text-2xs uppercase tracking-wider text-ink-muted">
                  {factor.source}
                </span>
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
      ) : null}
    </li>
  );
}

export function RunSummary({ result }: { result: RunResult }) {
  const classes = Object.entries(result.risk_class_distribution);

  return (
    <div className="space-y-3">
      <div
        className={`rounded border px-3 py-2.5 text-xs leading-relaxed ${
          result.dry_run
            ? "border-accent/25 bg-accent/5 text-accent-soft"
            : "border-risk-low/40 bg-risk-low/10 text-risk-low"
        }`}
      >
        {result.dry_run ? (
          <>
            <strong>Uji coba</strong> untuk tanggal {result.prediction_date}, horizon{" "}
            {horizonLabel(result.horizon)}. {result.dry_run_basis}
          </>
        ) : (
          <>
            <strong>{result.written} baris</strong> prediksi tertulis untuk tanggal{" "}
            {result.prediction_date}, horizon {horizonLabel(result.horizon)}, berstatus{" "}
            {result.status_written}. {result.status_basis}
          </>
        )}
      </div>

      {result.not_computed_reason ? (
        <p className="rounded border border-risk-high/40 bg-risk-high/5 px-3 py-2 text-xs leading-relaxed text-risk-high">
          {result.not_computed_reason}
        </p>
      ) : null}

      <dl className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <div className="rounded border border-base-800 bg-base-850 px-3 py-2">
          <dt className="stat-label">Kombinasi</dt>
          <dd className="mt-1 font-heading text-sm font-bold tabular-nums text-ink">
            {result.combinations}
          </dd>
        </div>
        <div className="rounded border border-base-800 bg-base-850 px-3 py-2">
          <dt className="stat-label">Diprediksi</dt>
          <dd className="mt-1 font-heading text-sm font-bold tabular-nums text-ink">
            {result.predicted}
          </dd>
        </div>
        <div className="rounded border border-base-800 bg-base-850 px-3 py-2">
          <dt className="stat-label">Tidak Diprediksi</dt>
          <dd className="mt-1 font-heading text-sm font-bold tabular-nums text-ink">
            {result.not_predicted}
          </dd>
        </div>
        <div className="rounded border border-base-800 bg-base-850 px-3 py-2">
          <dt className="stat-label">Hari Diprediksi</dt>
          <dd className="mt-1 text-xs text-ink">
            {formatWib(result.window_from)} s.d. {formatWib(result.window_to)}
          </dd>
        </div>
      </dl>

      {classes.length > 0 ? (
        <ul className="flex flex-wrap gap-1.5">
          {classes.map(([name, count]) => (
            <li key={name} className="badge bg-base-800 text-ink">
              {name} {count}
            </li>
          ))}
        </ul>
      ) : null}

      {result.by_threat_type.length > 0 ? (
        <div>
          <p className="stat-label">Per jenis ancaman</p>
          <ul className="mt-1 space-y-1">
            {result.by_threat_type.map((item) => (
              <li
                key={item.threat_type}
                className="flex flex-wrap items-baseline justify-between gap-x-3 text-xs"
              >
                <span className="text-ink">{item.threat_type}</span>
                <span className="tabular-nums text-ink-muted">
                  {item.windows} jendela · tertinggi {item.highest} · rata-rata {item.average} ·
                  keyakinan rata-rata {item.average_confidence}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {result.not_predicted_reasons.length > 0 ? (
        <div>
          <p className="stat-label">Mengapa sebagian tidak diprediksi</p>
          <ul className="mt-1 space-y-1">
            {result.not_predicted_reasons.map((item) => (
              <li key={item.reason} className="text-2xs leading-relaxed text-ink-muted">
                <span className="tabular-nums text-ink">{item.combinations}</span> kombinasi —{" "}
                {item.reason}
              </li>
            ))}
          </ul>
          <p className="mt-1 text-2xs leading-relaxed text-ink-muted">
            {result.not_predicted_basis}
          </p>
        </div>
      ) : null}

      {result.sample.length > 0 ? (
        <div>
          <p className="stat-label">Contoh baris berisiko tertinggi</p>
          <ul className="mt-1.5 space-y-2">
            {result.sample.map((forecast) => (
              <ForecastCard
                key={`${forecast.grid_id}-${forecast.threat_type}-${forecast.window_start}`}
                forecast={forecast}
              />
            ))}
          </ul>
        </div>
      ) : null}

      <p className="text-2xs leading-relaxed text-ink-muted">{result.horizon_basis}</p>
      <p className="text-2xs leading-relaxed text-ink-muted">{result.projection_basis}</p>
      <p className="text-2xs leading-relaxed text-ink-muted">{result.confidence_basis}</p>
    </div>
  );
}
