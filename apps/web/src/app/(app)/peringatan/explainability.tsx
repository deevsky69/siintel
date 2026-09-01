import { EmptyState } from "@/components/data-state";
import { Panel } from "@/components/panel";
import { factorLabel, formatWib, type PredictionDetail, type WarningDetail } from "@/lib/warnings";

/** Keterangan asal penjelasan. Ditulis apa adanya, tidak diterjemahkan menjadi seolah temuan model. */
const SOURCE_NOTE: Record<string, string> = {
  RULE: "Berasal dari aturan yang dijalankan, bukan temuan model terlatih.",
  MODEL: "Berasal dari kontribusi fitur pada model.",
};

function SourceBadge({ source }: { source: string }) {
  const style = source === "MODEL" ? "bg-accent/15 text-accent" : "bg-risk-high/15 text-risk-high";
  return <span className={`badge ${style}`}>{source}</span>;
}

function Meta({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt className="stat-label">{label}</dt>
      <dd className="mt-0.5 font-mono text-xs text-ink">{value}</dd>
    </div>
  );
}

/**
 * Panel WHY: prediksi sumber sebuah peringatan beserta faktor dominannya.
 *
 * `source` tiap faktor **selalu** ikut tampil. Menyembunyikannya akan membuat hasil
 * aturan terbaca sebagai temuan model, dan itu persis yang dilarang CLAUDE.md §27.
 */
export function ExplainabilityPanel({
  warning,
  prediction,
}: {
  warning: WarningDetail | null;
  prediction: PredictionDetail | null;
}) {
  if (!warning) {
    return (
      <Panel title="Dasar Peringatan (WHY)">
        <EmptyState label="Tidak ada peringatan yang dipilih." />
      </Panel>
    );
  }

  if (!prediction) {
    return (
      <Panel
        title="Dasar Peringatan (WHY)"
        action={<span className="panel-action">{warning.code}</span>}
      >
        {/* Lebih baik menyatakan penjelasan tidak tersedia daripada menampilkan
            penjelasan pengganti yang tidak berasal dari prediksi itu. */}
        <p className="text-xs leading-relaxed text-ink-muted">
          Prediksi sumber <span className="font-mono text-ink">{warning.prediction_code}</span>{" "}
          tidak berada pada halaman prediksi yang dimuat, sehingga faktor penjelasnya tidak dapat
          ditampilkan.
        </p>
      </Panel>
    );
  }

  const factors = prediction.dominant_factors ?? [];
  const sources = [...new Set(factors.map((factor) => factor.source))];

  return (
    <Panel
      title="Dasar Peringatan (WHY)"
      action={<span className="panel-action">{prediction.code}</span>}
    >
      <dl className="mb-3 grid grid-cols-2 gap-x-3 gap-y-2.5">
        <Meta label="Peringatan" value={warning.code} />
        <Meta label="Prediksi" value={prediction.code} />
        <Meta label="Tanggal Prediksi" value={prediction.prediction_date} />
        <Meta label="Horizon" value={prediction.forecast_horizon} />
        <Meta label="Versi Model" value={prediction.model_version ?? "—"} />
        <Meta label="Status Prediksi" value={prediction.status} />
        <Meta label="Risk Score" value={`${prediction.risk_score}/100`} />
        <Meta
          label="Confidence"
          value={prediction.confidence !== null ? `${prediction.confidence}%` : "—"}
        />
      </dl>

      <h3 className="stat-label mb-2 border-t border-base-800 pt-3">Faktor Dominan</h3>

      {factors.length === 0 ? (
        <p className="text-xs text-ink-muted">Tidak ada faktor penjelas pada prediksi ini.</p>
      ) : (
        <ul className="space-y-2">
          {factors.map((factor) => (
            <li key={`${factor.factor}-${factor.source}`}>
              <div className="flex items-center gap-2">
                <span className="flex-1 text-xs text-ink">{factorLabel(factor.factor)}</span>
                <SourceBadge source={factor.source} />
                <span className="w-12 text-right font-mono text-xs text-ink">
                  {factor.contribution.toLocaleString("id-ID", {
                    minimumFractionDigits: 3,
                    maximumFractionDigits: 3,
                  })}
                </span>
              </div>
              <span className="mt-1 block h-1.5 overflow-hidden rounded-full bg-base-800">
                <span
                  className="block h-full rounded-full bg-accent/70"
                  style={{ width: `${Math.min(100, Math.max(0, factor.contribution * 100))}%` }}
                />
              </span>
            </li>
          ))}
        </ul>
      )}

      {sources.length > 0 ? (
        <div className="mt-3 space-y-1 border-t border-base-800 pt-3">
          {sources.map((source) => (
            <p key={source} className="text-[10px] leading-relaxed text-ink-muted">
              <span className="font-mono text-ink">{source}</span> —{" "}
              {SOURCE_NOTE[source] ?? "Asal penjelasan tidak dikenali."}
            </p>
          ))}
        </div>
      ) : null}

      <p className="mt-2 text-[10px] leading-relaxed text-ink-muted">
        Jendela prediksi {prediction.time_window ?? "—"} · lokasi {prediction.kecamatan}
        {prediction.kelurahan ? ` — ${prediction.kelurahan}` : ""} · peringatan terbit{" "}
        {formatWib(warning.created_at)}.
      </p>
    </Panel>
  );
}
