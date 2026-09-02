import { Panel } from "@/components/panel";
import { StatusNotice } from "@/components/warnings/status-notice";
import type { ScoringConfig, ScoringVersion } from "@/lib/scoring";
import { factorLabel, PROFILE_HINTS, profileLabel, weightPercent } from "./display";

/**
 * Dasar perhitungan penilaian risiko — bagian tampilan.
 *
 * Bobot ditampilkan **sebelum** hasil, dan statusnya (`DEMO`/`PROPOSED`) diletakkan di
 * atas, bukan sebagai catatan kaki: angka risiko yang tampil tanpa asalnya tidak dapat
 * diperdebatkan siapa pun, dan bobot pada layar ini belum ditetapkan pemilik proyek
 * (U-02, CLAUDE.md §11).
 *
 * Dipisahkan dari pengambilan data supaya dapat diuji tanpa backend.
 */

function FactorRow({
  factor,
  weight,
  persisted,
  basis,
}: {
  factor: string;
  weight: number;
  persisted: boolean;
  basis: string | null;
}) {
  const negative = weight < 0;
  const zero = weight === 0;

  return (
    <tr className="border-t border-base-800 align-top">
      <th scope="row" className="py-2 pr-3 text-left font-normal">
        <span className="text-ink">{factorLabel(factor)}</span>
        <span className="ml-2 font-mono text-[10px] text-ink-muted">{factor}</span>
        {basis ? <p className="mt-1 text-[10px] leading-relaxed text-ink-muted">{basis}</p> : null}
      </th>
      <td
        className={`py-2 pr-3 text-right font-heading text-sm font-bold tabular-nums ${
          negative ? "text-risk-low" : zero ? "text-ink-muted" : "text-ink"
        }`}
      >
        {weightPercent(weight)}
      </td>
      <td className="py-2 text-right text-[10px] text-ink-muted">
        {negative ? "mengurangi skor" : zero ? "tidak menyumbang" : "menyusun skor"}
        <span className="block">{persisted ? "tersimpan" : "tidak tersimpan"}</span>
      </td>
    </tr>
  );
}

function VersionPanel({ version }: { version: ScoringVersion }) {
  return (
    <Panel
      title={`Versi ${version.version}`}
      action={
        <span className="panel-action">
          {version.active ? "berlaku sekarang" : "belum dipakai menghitung"}
        </span>
      }
    >
      <div className="space-y-4">
        <span className="badge bg-accent/15 text-accent">{version.status}</span>

        {version.profiles.map((profile) => (
          <section key={profile.profile}>
            <h3 className="font-heading text-[12px] font-semibold uppercase tracking-wider text-ink">
              {profileLabel(profile.profile)}
            </h3>
            <p className="mt-1 text-[11px] leading-relaxed text-ink-muted">
              {PROFILE_HINTS[profile.profile] ?? ""}
            </p>

            <div className="mt-2 flex flex-wrap gap-1.5">
              {profile.applies_to.map((threat) => (
                <span key={threat} className="badge bg-base-800 text-ink">
                  {threat}
                </span>
              ))}
            </div>

            <div className="mt-2 overflow-x-auto">
              <table className="w-full min-w-[26rem] text-[11px]">
                <caption className="sr-only">
                  Bobot faktor {profileLabel(profile.profile)} versi {version.version}
                </caption>
                <thead>
                  <tr className="text-left text-ink-muted">
                    <th scope="col" className="pb-1 font-normal">
                      Faktor
                    </th>
                    <th scope="col" className="pb-1 text-right font-normal">
                      Bobot
                    </th>
                    <th scope="col" className="pb-1 text-right font-normal">
                      Peran
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {profile.factors.map((factor) => (
                    <FactorRow
                      key={factor.factor}
                      factor={factor.factor}
                      weight={factor.weight}
                      persisted={factor.persisted}
                      basis={factor.basis}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            <p className="mt-2 text-[10px] leading-relaxed text-ink-muted">
              Jumlah bobot positif {weightPercent(profile.positive_weight_total)}. Bila kurang dari
              100%, skor tertinggi yang mungkin dicapai ikut turun tanpa terlihat — dan kelas
              tertinggi tidak akan pernah tersentuh.
            </p>
          </section>
        ))}
      </div>
    </Panel>
  );
}

export function ScoringBasis({ config }: { config: ScoringConfig }) {
  const active = config.versions.find((version) => version.active);
  const others = config.versions.filter((version) => !version.active);

  return (
    <div className="space-y-3">
      <StatusNotice status={config.active_status} tone="caution">
        Bobot versi <strong>{config.active_version}</strong> belum ditetapkan pemilik proyek.{" "}
        {config.config_basis}
      </StatusNotice>

      <Panel title="Yang Dihitung Layar Ini">
        <p className="text-[11px] leading-relaxed text-ink-muted">{config.score_basis}</p>
        <dl className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
          <div className="rounded border border-base-800 bg-base-950/40 px-3 py-2">
            <dt className="stat-label">Versi Bobot</dt>
            <dd className="mt-1 font-heading text-sm font-bold text-ink">
              {config.active_version}
            </dd>
          </div>
          <div className="rounded border border-base-800 bg-base-950/40 px-3 py-2">
            <dt className="stat-label">Versi Ambang</dt>
            <dd className="mt-1 font-heading text-sm font-bold text-ink">
              {config.thresholds.version}
            </dd>
          </div>
          <div className="rounded border border-base-800 bg-base-950/40 px-3 py-2">
            <dt className="stat-label">Sel Grid</dt>
            <dd className="mt-1 font-heading text-sm font-bold text-ink">
              {config.coverage.locations}
            </dd>
          </div>
          <div className="rounded border border-base-800 bg-base-950/40 px-3 py-2">
            <dt className="stat-label">Jendela Waktu</dt>
            <dd className="mt-1 font-heading text-sm font-bold text-ink">
              {config.time_windows.length}
            </dd>
          </div>
        </dl>
        <p className="mt-3 text-[10px] leading-relaxed text-ink-muted">
          {config.persistence_basis}
        </p>
      </Panel>

      <Panel
        title="Kelas Risiko"
        action={<span className="panel-action">{config.thresholds.status}</span>}
      >
        <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
          {config.thresholds.risk_classes.map((band) => (
            <div
              key={band.class}
              className="rounded border border-base-800 bg-base-950/40 px-3 py-2"
            >
              <div className="stat-label">{band.class}</div>
              <div className="mt-1 font-heading text-sm font-bold tabular-nums text-ink">
                {band.min}–{band.max}
              </div>
            </div>
          ))}
        </div>
        <p className="mt-2 text-[10px] leading-relaxed text-ink-muted">
          Kelas dibaca dari <code>config/risk/warning-thresholds.yaml</code> versi{" "}
          {config.thresholds.version} dan tidak dihitung ulang di kode mana pun.
        </p>
      </Panel>

      {active ? <VersionPanel version={active} /> : null}
      {others.map((version) => (
        <VersionPanel key={version.version} version={version} />
      ))}
    </div>
  );
}
