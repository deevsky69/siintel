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
    <div className="rounded border border-base-800 bg-base-950/40 px-3 py-2.5">
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
}: {
  metrics: EvaluationMetrics;
  summary: EvaluationSummary;
}) {
  const precisionPercent = formatPercent(metrics.precision);
  const recallPercent = formatPercent(metrics.recall);
  const threats = Object.keys(summary.per_threat).sort();

  return (
    <div className="space-y-3">
      <StatusNotice status={metrics.status} tone="caution">
        Angka pada halaman ini <strong>belum final</strong>. {metrics.basis}
      </StatusNotice>

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
