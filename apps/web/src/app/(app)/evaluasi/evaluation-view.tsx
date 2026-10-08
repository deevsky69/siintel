import { Basis } from "@/components/basis";
import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { StatusNotice } from "@/components/warnings/status-notice";
import {
  type EvaluationMetrics,
  type EvaluationSummary,
  formatPercent,
  formatRatio,
  MATCH_HINTS,
  MATCH_LABELS,
  MATCH_TYPES,
  type OutcomeVerdict,
  type RecommendationOutcome,
  type ThresholdSweep,
  VERDICT_LABELS,
} from "@/lib/evaluation";

function MetricCard({
  label,
  value,
  hint,
  accent,
}: {
  label: string;
  value: string;
  hint: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded border border-base-800 bg-base-850 px-3 py-2.5">
      <div className="stat-label">{label}</div>
      <div
        className={`mt-1 font-heading text-2xl font-bold leading-none ${
          accent ? "text-accent" : "text-ink"
        }`}
      >
        {value}
      </div>
      <div className="mt-1.5 text-2xs leading-relaxed text-ink-muted">{hint}</div>
    </div>
  );
}

/**
 * Evaluation Center (TASK 150–151) — bagian tampilan.
 *
 * Dipisahkan dari pengambilan data supaya dapat diuji tanpa backend.
 *
 * Penanda `status` dan teks `basis` dari API ditampilkan di atas seluruh angka. Precision
 * dan recall di sini adalah hasil hitung atas aturan pencocokan yang **belum ditetapkan**
 * (U-03); menyajikannya seolah angka final akan melampaui yang dapat dipertanggungjawabkan
 * saat paparan (CLAUDE.md §26).
 */
export function EvaluationView({
  metrics,
  summary,
  sweep = null,
  outcome,
}: {
  metrics: EvaluationMetrics;
  summary: EvaluationSummary;
  /** Precision/recall bila ambang terbit dinaikkan — bahan keputusan ambang. */
  sweep?: ThresholdSweep | null;
  /** Rekomendasi vs kenyataan tahun sasaran; `null` bila tidak termuat, `undefined` bila tidak diminta. */
  outcome?: RecommendationOutcome | null;
}) {
  const precisionPercent = formatPercent(metrics.precision);
  const recallPercent = formatPercent(metrics.recall);
  const threats = Object.keys(summary.per_threat).sort();

  return (
    <div className="space-y-3">
      <StatusNotice status={metrics.status} tone="caution">
        Angka pada halaman ini <strong>belum final</strong>.
      </StatusNotice>
      <Basis className="mt-0" label="Aturan pencocokan yang dipakai">
        {metrics.basis}
      </Basis>
      {metrics.evaluated_from && metrics.evaluated_to ? (
        <p className="text-xs leading-relaxed text-ink-muted">
          Periode evaluasi <span className="text-ink">{metrics.evaluated_from}</span> s.d.{" "}
          <span className="text-ink">{metrics.evaluated_to}</span>
          {metrics.warning_floor !== undefined
            ? `; prediksi dihitung "terbit" bila skornya mencapai ${metrics.warning_floor} (ambang versi ${metrics.threshold_version ?? "?"})`
            : ""}
          {metrics.threat_types && metrics.threat_types.length > 0
            ? `; jenis yang dievaluasi ${metrics.threat_types.join(", ")}`
            : ""}
          .
          {metrics.unevaluable_incidents ? (
            <>
              {" "}
              <span className="text-ink">{metrics.unevaluable_incidents} kejadian</span> pada
              periode ini tidak tercatat jamnya pada Laporan Polisi, sehingga tidak dapat
              ditempatkan pada jendela mana pun — tidak dihitung terbukti maupun luput, dan disebut
              di sini supaya tidak hilang dari angka.
            </>
          ) : null}
        </p>
      ) : null}

      <Panel
        title="Prediction vs Actual"
        action={
          <span className="panel-action">
            {metrics.evaluated_rows > 0
              ? `${metrics.evaluated_rows} baris dievaluasi`
              : "tidak ada baris dievaluasi"}
          </span>
        }
      >
        {metrics.evaluated_rows === 0 ? (
          // Keadaan kosong dinyatakan dengan kata, bukan deretan angka nol.
          <EmptyState label="Tidak ada baris evaluasi yang tercatat." />
        ) : (
          <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
            <MetricCard
              label="Precision"
              value={formatRatio(metrics.precision)}
              hint={
                precisionPercent
                  ? `${precisionPercent} prediksi yang terbit terbukti terjadi`
                  : "Belum ada prediksi terbit yang dapat dinilai"
              }
              accent
            />
            <MetricCard
              label="Recall"
              value={formatRatio(metrics.recall)}
              hint={
                recallPercent
                  ? `${recallPercent} kejadian nyata sempat diprediksi`
                  : "Belum ada kejadian nyata yang dapat dinilai"
              }
              accent
            />
            <MetricCard
              label={MATCH_LABELS.HIT}
              value={String(metrics.hits)}
              hint={MATCH_HINTS.HIT}
            />
            <MetricCard
              label={MATCH_LABELS.FALSE_POSITIVE}
              value={String(metrics.false_positives)}
              hint={MATCH_HINTS.FALSE_POSITIVE}
            />
            <MetricCard
              label={MATCH_LABELS.FALSE_NEGATIVE}
              value={String(metrics.false_negatives)}
              hint={MATCH_HINTS.FALSE_NEGATIVE}
            />
            <MetricCard
              label="Baris Dievaluasi"
              value={String(metrics.evaluated_rows)}
              hint="Seluruh baris pencocokan prediksi dan kejadian nyata"
            />
          </div>
        )}
      </Panel>

      {outcome === undefined ? null : <OutcomePanel outcome={outcome} />}

      {sweep && sweep.rows.length > 0 ? <SweepPanel sweep={sweep} /> : null}
      <div className="grid grid-cols-12 gap-3">
        <div className="col-span-12 xl:col-span-7">
          <Panel
            title="Rincian per Jenis Ancaman"
            action={
              <span className="panel-action">
                {summary.model_versions.length > 0
                  ? `versi model ${summary.model_versions.join(", ")}`
                  : "versi model tidak ada"}
              </span>
            }
          >
            {threats.length === 0 ? (
              <EmptyState label="Tidak ada rincian per jenis ancaman." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-base-800">
                      <th className="stat-label pb-2">Jenis Ancaman</th>
                      {MATCH_TYPES.map((match) => (
                        <th key={match} className="stat-label pb-2 text-right">
                          {MATCH_LABELS[match]}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {threats.map((threat) => {
                      const row = summary.per_threat[threat];
                      return (
                        <tr key={threat} className="border-b border-base-800/60 last:border-0">
                          <td className="py-2 font-heading font-semibold text-ink">{threat}</td>
                          {MATCH_TYPES.map((match) => (
                            <td key={match} className="py-2 text-right font-mono text-ink">
                              {/* Sel tanpa baris ditandai, bukan diisi nol. */}
                              {row[match] ?? "—"}
                            </td>
                          ))}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
            <p className="mt-3 border-t border-base-800 pt-3 text-2xs leading-relaxed text-ink-muted">
              Baris positif palsu tidak memiliki kejadian nyata sebagai pasangannya, sehingga
              terkumpul pada baris tanpa jenis ancaman.
            </p>
          </Panel>
        </div>

        <div className="col-span-12 xl:col-span-5">
          <Panel title="Cara Membaca Angka Ini">
            <dl className="space-y-3 text-xs leading-relaxed text-ink">
              <div>
                <dt className="font-heading font-semibold text-accent">Precision</dt>
                <dd className="mt-1 text-ink-muted">
                  Dari seluruh prediksi yang terbit, berapa bagian yang benar-benar terbukti.
                  Precision rendah berarti banyak peringatan terbit untuk keadaan yang tidak terjadi
                  — pasukan berangkat, tetapi tidak ada apa-apa.
                </dd>
              </div>
              <div>
                <dt className="font-heading font-semibold text-accent">Recall</dt>
                <dd className="mt-1 text-ink-muted">
                  Dari seluruh kejadian yang benar-benar terjadi, berapa bagian yang sempat
                  diprediksi lebih dulu. Recall rendah berarti banyak kejadian lolos tanpa
                  peringatan.
                </dd>
              </div>
              <div>
                <dt className="font-heading font-semibold text-ink">
                  Keduanya harus dibaca bersama
                </dt>
                <dd className="mt-1 text-ink-muted">
                  Menaikkan salah satunya biasanya menurunkan yang lain. Menurunkan ambang membuat
                  lebih banyak peringatan terbit — recall naik, precision turun. Titik seimbangnya
                  adalah keputusan pimpinan, bukan keputusan sistem.
                </dd>
              </div>
              <div>
                <dt className="font-heading font-semibold text-ink">
                  Negatif palsu tetap dihitung
                </dt>
                <dd className="mt-1 text-ink-muted">
                  Kejadian yang tidak diprediksi ikut tercatat, sehingga kelemahan sistem tidak
                  tersembunyi di balik angka precision yang terlihat baik.
                </dd>
              </div>
            </dl>
          </Panel>
        </div>
      </div>
    </div>
  );
}

function SweepPanel({ sweep }: { sweep: ThresholdSweep }) {
  const base = sweep.rows[0];
  const bestPrecision = Math.max(...sweep.rows.map((row) => row.precision ?? 0));
  const flat = base?.precision !== null && bestPrecision - (base?.precision ?? 0) < 0.02;
  return (
    <Panel
      title="Bila Ambang Terbit Dinaikkan"
      action={<span className="panel-action">ambang berlaku {sweep.current_floor}</span>}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-base-800">
              <th className="stat-label pb-2">Ambang</th>
              <th className="stat-label pb-2 text-right">Peringatan/hari</th>
              <th className="stat-label pb-2 text-right">Precision</th>
              <th className="stat-label pb-2 text-right">Recall</th>
              <th className="stat-label pb-2 text-right">Terbukti</th>
              <th className="stat-label pb-2 text-right">Luput</th>
            </tr>
          </thead>
          <tbody>
            {sweep.rows.map((row) => (
              <tr
                key={row.threshold}
                className={`border-b border-base-800/60 last:border-0 ${
                  row.threshold === sweep.current_floor ? "text-ink" : "text-ink-muted"
                }`}
              >
                <td className="py-1.5 font-mono">{row.threshold}</td>
                <td className="py-1.5 text-right font-mono">
                  {row.warnings_per_day?.toLocaleString("id-ID") ?? "—"}
                </td>
                <td className="py-1.5 text-right font-mono">{formatRatio(row.precision)}</td>
                <td className="py-1.5 text-right font-mono">{formatRatio(row.recall)}</td>
                <td className="py-1.5 text-right font-mono">{row.hits}</td>
                <td className="py-1.5 text-right font-mono">{row.false_negatives}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 border-t border-base-800 pt-3 text-2xs leading-relaxed text-ink-muted">
        {flat ? (
          <>
            <strong className="text-ink">Menaikkan ambang tidak menaikkan precision</strong> — yang
            turun hanya jumlah peringatan dan recall. Artinya skor aturan saat ini tidak membedakan
            hari yang akan ada kejadian dari hari yang tidak; yang perlu diperbaiki adalah cara skor
            dihitung, bukan ambangnya.{" "}
          </>
        ) : null}
      </p>
      <Basis>{sweep.basis}</Basis>
    </Panel>
  );
}

const VERDICT_TONE: Record<OutcomeVerdict, string> = {
  SEJALAN: "bg-risk-low/15 text-risk-low border-risk-low/40",
  SEBAGIAN: "bg-risk-moderate/15 text-risk-moderate border-risk-moderate/40",
  TIDAK_SEJALAN: "bg-risk-critical/15 text-risk-critical border-risk-critical/40",
  BELUM_DAPAT_DINILAI: "bg-base-800 text-ink-muted border-base-700",
};

function VerdictTag({ verdict }: { verdict: OutcomeVerdict }) {
  return (
    <span
      className={`inline-block rounded border px-1.5 py-0.5 font-heading text-2xs font-semibold uppercase tracking-wider ${VERDICT_TONE[verdict]}`}
    >
      {VERDICT_LABELS[verdict]}
    </span>
  );
}

const formatShare = (value: number | null) =>
  value === null ? "—" : `${value.toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`;

/**
 * Rekomendasi vs kenyataan tahun sasaran (permintaan pemilik proyek 8 Oktober 2026).
 *
 * Dua pembacaan ditampilkan berdampingan dan tidak dilebur: jendela harfiah (enam jam yang
 * persis diprediksi — hampir selalu kosong, dan itu disebut) dan pola tahun berjalan (tempat
 * dan blok jam yang direkomendasikan dibandingkan seluruh kejadian tahun sasaran). Putusan
 * per baris membawa angkanya sendiri; aturannya PROPOSED.
 */
function OutcomePanel({ outcome }: { outcome: RecommendationOutcome | null }) {
  if (outcome === null) {
    return (
      <Panel title="Rekomendasi vs Kenyataan">
        <EmptyState label="Pencocokan rekomendasi tidak termuat. Angka evaluasi lainnya tetap berlaku." />
      </Panel>
    );
  }
  const { summary: s } = outcome;
  const title = `Rekomendasi vs Kenyataan ${outcome.target_years.join(", ")}`.trim();
  return (
    <Panel
      title={title}
      action={
        <span className="panel-action">
          {s.total > 0
            ? `${s.total} rekomendasi · data sampai ${outcome.observed_to ?? "?"}`
            : "tidak ada rekomendasi"}
        </span>
      }
    >
      {s.total === 0 ? (
        <EmptyState label="Belum ada rekomendasi yang dapat dicocokkan." />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
            <MetricCard
              label="Sejalan"
              value={`${s.aligned} dari ${s.total}`}
              hint={
                s.aligned_percent === null
                  ? "Tempat dan jam yang direkomendasikan sama-sama terbukti"
                  : `${formatShare(s.aligned_percent)} rekomendasi: tempat dan jamnya sama-sama terbukti sepanjang tahun sasaran`
              }
              accent
            />
            <MetricCard
              label="Sebagian"
              value={String(s.partial)}
              hint="Kelurahannya memang mengalami jenis itu, tetapi tidak menonjol pada blok jam yang direkomendasikan"
            />
            <MetricCard
              label="Tidak sejalan"
              value={String(s.not_aligned)}
              hint="Kelurahan itu tidak mengalami jenis itu sama sekali pada tahun sasaran"
            />
            <MetricCard
              label="Jendela harfiah"
              value={`${s.literal_window_hits} dari ${s.total}`}
              hint="Ada kejadian pada enam jam yang persis diprediksi. Ukuran paling ketat; hampir selalu kosong karena satu kelurahan hanya mengalami beberapa kejadian setahun"
            />
          </div>

          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-base-800">
                  <th className="stat-label pb-2">Rekomendasi</th>
                  <th className="stat-label pb-2">Apa · Di mana · Kapan</th>
                  <th className="stat-label pb-2 text-right">Kejadian di kelurahan</th>
                  <th className="stat-label pb-2 text-right">Pada blok jam</th>
                  <th className="stat-label pb-2 text-right">Peringkat kelurahan</th>
                  <th className="stat-label pb-2 text-right">Putusan</th>
                </tr>
              </thead>
              <tbody>
                {outcome.rows.map((row) => (
                  <tr
                    key={row.code}
                    className="border-b border-base-800/60 align-top last:border-0"
                  >
                    <td className="py-2 pr-2 font-mono text-ink">{row.code}</td>
                    <td className="py-2 pr-2 text-ink">
                      <span className="font-heading font-semibold">{row.threat_type}</span>
                      {" · "}
                      {row.kelurahan ?? "—"}
                      {row.kecamatan ? `, ${row.kecamatan}` : ""}
                      {" · "}
                      <span className="font-mono">{row.time_window ?? "—"}</span>
                    </td>
                    <td className="py-2 pr-2 text-right font-mono text-ink">
                      {row.area_incidents}
                      {row.area_unknown_time > 0 ? (
                        <span className="text-ink-faint"> ({row.area_unknown_time} tanpa jam)</span>
                      ) : null}
                    </td>
                    <td className="py-2 pr-2 text-right font-mono text-ink">
                      {`${row.block_incidents} dari ${row.area_timed_incidents}`}
                      <span className="text-ink-faint">
                        {` · ${formatShare(row.block_share_percent)} vs ${formatShare(row.expected_share_percent)}`}
                      </span>
                    </td>
                    <td className="py-2 pr-2 text-right font-mono text-ink">
                      {row.area_rank === null ? "—" : `${row.area_rank} dari ${row.area_rank_of}`}
                    </td>
                    <td className="py-2 text-right">
                      <VerdictTag verdict={row.verdict} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-3 border-t border-base-800 pt-3 text-2xs leading-relaxed text-ink-muted">
            "Pada blok jam" membaca kejadian yang jamnya tercatat: berapa yang jatuh pada blok yang
            direkomendasikan, dibandingkan porsi jamnya (enam dari dua puluh empat jam = 25%).
            Peringkat kelurahan dihitung di antara kelurahan yang mengalami jenis itu pada tahun
            sasaran. Jumlah kecil (tiga–empat kejadian) membuat persentasenya mudah berubah; bacalah
            bersama angkanya.
          </p>
          <Basis>{outcome.basis}</Basis>
        </>
      )}
    </Panel>
  );
}
