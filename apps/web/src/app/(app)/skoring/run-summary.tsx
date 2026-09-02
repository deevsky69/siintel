import type { RunCell, RunProfile, RunResult } from "@/lib/scoring";
import { contributionText, factorLabel, factorValue, profileLabel, weightPercent } from "./display";

/**
 * Ringkasan hasil menjalankan penilaian.
 *
 * Tiga hal yang sengaja tampil berdampingan, bukan dipilih salah satunya:
 *
 * 1. berapa kombinasi yang **dinilai** dan berapa yang **tidak dapat dinilai**, beserta
 *    alasannya — baris tanpa skor bukan baris berskor nol;
 * 2. faktor pembentuk setiap baris contoh lengkap dengan bobot dan sumbangannya, sehingga
 *    skornya dapat dihitung ulang oleh pembaca;
 * 3. penanda `RULE` pada setiap faktor: penjelasan ini berasal dari aturan yang benar-benar
 *    dijalankan, bukan dari model (CLAUDE.md §27).
 *
 * Tidak ada modul `@/lib/api` yang tertarik ke sini: berkas ini dipakai komponen
 * `"use client"`.
 */

function CellCard({ cell }: { cell: RunCell }) {
  return (
    <li className="rounded border border-base-800 bg-base-950/40 px-3 py-2.5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <span className="font-heading text-[12px] font-semibold text-ink">{cell.grid_id}</span>
          <span className="ml-2 text-[11px] text-ink-muted">
            {cell.kecamatan}
            {cell.kelurahan ? ` · ${cell.kelurahan}` : ""} · {cell.threat_type} · {cell.time_window}
          </span>
        </div>
        <div className="text-right">
          <span className="font-heading text-xl font-bold tabular-nums text-ink">
            {cell.risk_score === null ? "—" : cell.risk_score}
          </span>
          <span className="ml-2 text-[10px] uppercase tracking-wider text-ink-muted">
            {cell.risk_class ?? "tidak dinilai"}
          </span>
        </div>
      </div>

      {cell.unscored_reason ? (
        <p className="mt-1.5 text-[10px] leading-relaxed text-risk-high">{cell.unscored_reason}</p>
      ) : null}

      <ul className="mt-2 space-y-1">
        {cell.factors.map((factor) => (
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
                <span className="ml-1.5 text-risk-high">({factor.reason})</span>
              ) : null}
            </span>
            <span className="tabular-nums text-ink">
              {factorValue(factor.value)}
              <span className="ml-2 text-ink-muted">
                {factor.weight === null ? "—" : weightPercent(factor.weight)} ·{" "}
                {contributionText(factor.contribution, factor.weight)}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </li>
  );
}

function ProfileBlock({ profile }: { profile: RunProfile }) {
  const classes = Object.entries(profile.risk_class_distribution);

  return (
    <section className="rounded border border-base-800 px-3 py-2.5">
      <h3 className="font-heading text-[12px] font-semibold uppercase tracking-wider text-ink">
        {profileLabel(profile.profile)}
      </h3>

      {profile.not_computed_reason ? (
        // Profil yang tidak menghasilkan apa pun menyatakan alasannya, bukan menghilang
        // begitu saja — dan tidak diisi dengan contoh yang dikarang.
        <p className="mt-1.5 text-[11px] leading-relaxed text-risk-high">
          {profile.not_computed_reason}
        </p>
      ) : null}

      <dl className="mt-2 grid grid-cols-2 gap-2 md:grid-cols-4">
        <div>
          <dt className="stat-label">Kombinasi</dt>
          <dd className="font-heading text-sm font-bold tabular-nums text-ink">
            {profile.combinations}
          </dd>
        </div>
        <div>
          <dt className="stat-label">Dinilai</dt>
          <dd className="font-heading text-sm font-bold tabular-nums text-ink">{profile.scored}</dd>
        </div>
        <div>
          <dt className="stat-label">Tidak Dinilai</dt>
          <dd className="font-heading text-sm font-bold tabular-nums text-ink">
            {profile.unscored}
          </dd>
        </div>
        <div>
          <dt className="stat-label">Jenis Ancaman</dt>
          <dd className="font-heading text-sm font-bold tabular-nums text-ink">
            {profile.threat_types.length}
          </dd>
        </div>
      </dl>

      {classes.length > 0 ? (
        <ul className="mt-2 flex flex-wrap gap-1.5">
          {classes.map(([name, count]) => (
            <li key={name} className="badge bg-base-800 text-ink">
              {name} {count}
            </li>
          ))}
        </ul>
      ) : null}

      {profile.unscored_reasons.length > 0 ? (
        <div className="mt-2">
          <p className="stat-label">Mengapa sebagian tidak dinilai</p>
          <ul className="mt-1 space-y-1">
            {profile.unscored_reasons.map((item) => (
              <li key={item.reason} className="text-[10px] leading-relaxed text-ink-muted">
                <span className="tabular-nums text-ink">{item.combinations}</span> kombinasi —{" "}
                {item.reason}
              </li>
            ))}
          </ul>
          <p className="mt-1 text-[10px] leading-relaxed text-ink-muted">
            {profile.unscored_basis}
          </p>
        </div>
      ) : null}

      {profile.sample.length > 0 ? (
        <div className="mt-3">
          <p className="stat-label">Contoh baris berskor tertinggi</p>
          <ul className="mt-1.5 space-y-2">
            {profile.sample.map((cell) => (
              <CellCard
                key={`${cell.grid_id}-${cell.threat_type}-${cell.time_window}`}
                cell={cell}
              />
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

export function RunSummary({ result }: { result: RunResult }) {
  return (
    <div className="space-y-3">
      <div
        className={`rounded border px-3 py-2.5 text-[11px] leading-relaxed ${
          result.dry_run
            ? "border-accent/25 bg-accent/5 text-accent-soft"
            : "border-risk-low/40 bg-risk-low/10 text-risk-low"
        }`}
      >
        {result.dry_run ? (
          <>
            <strong>Uji coba</strong> untuk tanggal penilaian {result.assessment_date}.{" "}
            {result.dry_run_basis}
          </>
        ) : (
          <>
            <strong>{result.written} baris</strong> penilaian tertulis untuk tanggal{" "}
            {result.assessment_date} dengan versi bobot {result.weights_version}.
          </>
        )}
      </div>

      <dl className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <div className="rounded border border-base-800 bg-base-950/40 px-3 py-2">
          <dt className="stat-label">Tanggal Penilaian</dt>
          <dd className="mt-1 font-heading text-sm font-bold text-ink">{result.assessment_date}</dd>
        </div>
        <div className="rounded border border-base-800 bg-base-950/40 px-3 py-2">
          <dt className="stat-label">Baris Sudah Ada</dt>
          <dd className="mt-1 font-heading text-sm font-bold tabular-nums text-ink">
            {result.existing_rows}
          </dd>
        </div>
        <div className="rounded border border-base-800 bg-base-950/40 px-3 py-2">
          <dt className="stat-label">Kejadian Ditimbang</dt>
          <dd className="mt-1 font-heading text-sm font-bold tabular-nums text-ink">
            {result.evidence.incidents}
          </dd>
        </div>
        <div className="rounded border border-base-800 bg-base-950/40 px-3 py-2">
          <dt className="stat-label">Rentang Data</dt>
          <dd className="mt-1 text-[11px] text-ink">
            {result.evidence.date_from ?? "—"} s.d. {result.evidence.date_to ?? "—"}
          </dd>
        </div>
      </dl>

      {result.profiles.map((profile) => (
        <ProfileBlock key={profile.profile} profile={profile} />
      ))}

      <p className="text-[10px] leading-relaxed text-ink-muted">{result.score_basis}</p>
      <p className="text-[10px] leading-relaxed text-ink-muted">{result.persistence_basis}</p>
    </div>
  );
}
