import type { DistrictIntel, PredictionRow } from "@/lib/map-data";
import { RISK_BG, RISK_LABELS, RISK_TEXT, riskClassOf } from "@/lib/risk";
import { factorLabel, SOURCE_NOTE } from "./factors";

/**
 * Panel rincian satu kecamatan: potensi ancaman, jam rawan, dan prediksi beserta WHY.
 *
 * Setiap prediksi wajib tampil lengkap dengan `dominant_factors` **termasuk asalnya**
 * (`RULE`/`MODEL`). Menyembunyikan asal akan menyajikan hasil aturan seolah temuan model
 * (CLAUDE.md §27).
 */

const HORIZON_LABEL: Record<string, string> = {
  "6H": "+6 jam",
  "12H": "+12 jam",
  "24H": "+24 jam",
  "3D": "+3 hari",
  "7D": "+7 hari",
};

const STATUS_LABEL: Record<string, string> = {
  PUBLISHED: "Dipublikasikan",
  VALIDATED: "Tervalidasi",
  DRAFT: "Draf",
};

function formatDate(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}

/** Baris skor dengan batang risiko — bentuknya sama dengan daftar berperingkat dashboard. */
function ScoreRow({ label, score }: { label: string; score: number }) {
  const risk = riskClassOf(score);
  return (
    <li className="flex items-center gap-2.5">
      <span className="w-28 shrink-0 truncate text-xs text-ink" title={label}>
        {label}
      </span>
      <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-base-800">
        <span
          className={`block h-full rounded-full ${RISK_BG[risk]}`}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </span>
      <span className={`w-7 text-right font-mono text-xs font-semibold ${RISK_TEXT[risk]}`}>
        {score}
      </span>
      <span className="w-11 text-right text-[10px] uppercase text-ink-muted">
        {RISK_LABELS[risk]}
      </span>
    </li>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="stat-label mb-2">{children}</h3>;
}

function PredictionCard({ prediction }: { prediction: PredictionRow }) {
  const risk = riskClassOf(prediction.risk_score);

  return (
    <li className="rounded border border-base-800 bg-base-950/40 p-2.5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          {/* WHAT */}
          <p className="truncate font-heading text-sm font-semibold text-ink">
            {prediction.threat_type}
          </p>
          {/* WHERE */}
          <p className="truncate text-[11px] text-ink-muted">
            {prediction.kelurahan ? `${prediction.kelurahan} · ` : ""}
            {prediction.grid_id}
          </p>
        </div>
        <div className="shrink-0 text-right">
          {/* RISK */}
          <span className={`font-heading text-xl font-bold leading-none ${RISK_TEXT[risk]}`}>
            {prediction.risk_score}
          </span>
          <span className="ml-1 text-[10px] text-ink-faint">/100</span>
          <p className={`text-[10px] uppercase ${RISK_TEXT[risk]}`}>{RISK_LABELS[risk]}</p>
        </div>
      </div>

      <dl className="mt-2 grid grid-cols-3 gap-2 text-[11px]">
        <div>
          {/* WHEN */}
          <dt className="text-ink-faint">Jendela</dt>
          <dd className="font-mono text-ink">{prediction.time_window ?? "tidak ada"}</dd>
        </div>
        <div>
          {/* CONFIDENCE */}
          <dt className="text-ink-faint">Confidence</dt>
          <dd className="font-mono text-ink">
            {prediction.confidence === null ? "tidak ada" : `${prediction.confidence}%`}
          </dd>
        </div>
        <div>
          <dt className="text-ink-faint">Status</dt>
          <dd className="text-ink">{STATUS_LABEL[prediction.status] ?? prediction.status}</dd>
        </div>
      </dl>

      {/* WHY */}
      <div className="mt-2.5 border-t border-base-800 pt-2">
        <p className="stat-label mb-1.5">Why</p>
        {prediction.dominant_factors.length === 0 ? (
          <p className="text-[11px] text-ink-muted">Tidak ada faktor dominan yang tercatat.</p>
        ) : (
          <ul className="space-y-1.5">
            {prediction.dominant_factors.map((factor) => (
              <li key={factor.factor} className="flex items-center gap-2">
                <span className="badge bg-base-800 text-accent-soft">{factor.source}</span>
                <span className="min-w-0 flex-1 truncate text-[11px] text-ink">
                  {factorLabel(factor.factor)}
                </span>
                <span className="h-1 w-14 shrink-0 overflow-hidden rounded-full bg-base-800">
                  <span
                    className="block h-full rounded-full bg-accent"
                    style={{ width: `${Math.min(100, Math.max(0, factor.contribution * 100))}%` }}
                  />
                </span>
                <span className="w-9 shrink-0 text-right font-mono text-[11px] text-ink-muted">
                  {Math.round(factor.contribution * 100)}%
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <p className="mt-2 font-mono text-[10px] text-ink-faint">
        {prediction.code} · {formatDate(prediction.prediction_date)} ·{" "}
        {prediction.model_version ?? "versi model tidak tercatat"}
      </p>
    </li>
  );
}

/**
 * Panel ini berganti isi setiap kali wilayah lain dipilih pada peta, sehingga diberi
 * nama sendiri: pengguna papan ketik/pembaca layar dapat melompat langsung ke sini
 * tanpa harus menelusuri seluruh peta. Namanya sengaja berbeda dari judul panel
 * pembungkusnya agar keduanya tidak tertukar.
 */
const REGION = { role: "region", "aria-label": "Rincian wilayah terpilih" } as const;

export function DistrictDetail({
  district,
  horizon,
  assessmentDate,
  weightsVersion,
}: {
  district: DistrictIntel | null;
  horizon: string;
  assessmentDate: string | null;
  weightsVersion: string | null;
}) {
  if (district === null) {
    return (
      <div {...REGION}>
        <p className="text-sm text-ink-muted">
          Pilih salah satu kecamatan pada peta untuk melihat potensi ancamannya.
        </p>
      </div>
    );
  }

  const risk = district.riskScore === null ? null : riskClassOf(district.riskScore);
  const criticalWindow = district.windows[0] ?? null;

  return (
    <div className="space-y-4" {...REGION}>
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate font-heading text-base font-bold text-ink">
            {district.kecamatan}
          </h2>
          <p className="text-[11px] text-ink-muted">
            {assessmentDate
              ? `Penilaian ${formatDate(assessmentDate)}`
              : "Belum ada tanggal penilaian"}
            {weightsVersion ? ` · bobot ${weightsVersion}` : ""}
          </p>
        </div>
        <div className="shrink-0 text-right">
          {district.riskScore === null || risk === null ? (
            <span className="text-sm text-ink-muted">tidak ada data</span>
          ) : (
            <>
              <span className={`font-heading text-3xl font-bold leading-none ${RISK_TEXT[risk]}`}>
                {district.riskScore}
              </span>
              <span className="ml-1 text-[11px] text-ink-faint">/100</span>
              <p className={`text-[11px] font-semibold uppercase ${RISK_TEXT[risk]}`}>
                {RISK_LABELS[risk]}
              </p>
            </>
          )}
        </div>
      </header>

      <section>
        <SectionTitle>Potensi Ancaman</SectionTitle>
        {district.threats.length === 0 ? (
          <p className="text-sm text-ink-muted">
            Tidak ada penilaian risiko untuk wilayah ini pada tanggal penilaian terakhir.
          </p>
        ) : (
          <ul className="space-y-2">
            {district.threats.map((cell) => (
              <ScoreRow key={cell.label} label={cell.label} score={cell.score} />
            ))}
          </ul>
        )}
      </section>

      <section>
        <SectionTitle>Jendela Waktu Paling Rawan</SectionTitle>
        {criticalWindow === null ? (
          <p className="text-sm text-ink-muted">Tidak ada data jendela waktu untuk wilayah ini.</p>
        ) : (
          <>
            <p className="mb-2 font-heading text-lg font-bold text-ink">
              {criticalWindow.label}{" "}
              <span className={`text-sm ${RISK_TEXT[riskClassOf(criticalWindow.score)]}`}>
                {criticalWindow.score}
              </span>
            </p>
            <ul className="space-y-2">
              {district.windows.map((cell) => (
                <ScoreRow key={cell.label} label={cell.label} score={cell.score} />
              ))}
            </ul>
          </>
        )}
      </section>

      <section>
        <SectionTitle>Prediksi {HORIZON_LABEL[horizon] ?? horizon}</SectionTitle>
        {district.predictions.length === 0 ? (
          <p className="text-sm text-ink-muted">
            Tidak ada prediksi terpublikasi untuk wilayah ini pada horizon{" "}
            {HORIZON_LABEL[horizon] ?? horizon}.
          </p>
        ) : (
          <>
            <ul className="space-y-2">
              {district.predictions.map((prediction) => (
                <PredictionCard key={prediction.code} prediction={prediction} />
              ))}
            </ul>
            <p className="mt-2 text-[10px] leading-relaxed text-ink-faint">{SOURCE_NOTE}</p>
          </>
        )}
      </section>
    </div>
  );
}
